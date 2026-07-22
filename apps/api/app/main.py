from contextlib import asynccontextmanager
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from .database import DEFAULT_DATABASE_URL, Database
from .models import Evaluation, EvaluationCitation, Ticket
from .providers import DeterministicContextProvider
from .schemas import (
    EvaluationResponse,
    MetricsResponse,
    ReviewRequest,
    TicketCreate,
    TicketList,
    TicketResponse,
)
from .service import evaluate_with_context, reviewed_decision, snapshot_ticket


def evaluation_response(evaluation: Evaluation) -> EvaluationResponse:
    return EvaluationResponse(
        id=evaluation.id,
        ticket_id=evaluation.ticket_id,
        route=evaluation.route,
        reason=evaluation.reason,
        draft=evaluation.draft,
        citations=[row.source_id for row in evaluation.citation_rows],
        confidence=evaluation.confidence,
        automatic_send_allowed=evaluation.automatic_send_allowed,
        human_review_status=evaluation.human_review_status,
        external_action_state=evaluation.external_action_state,
        latency_ms=evaluation.latency_ms,
    )


def create_app(
    *,
    database_url: str | None = None,
    auto_create_schema: bool | None = None,
    context_provider: Any | None = None,
) -> FastAPI:
    resolved_database_url = database_url or os.environ.get(
        "DATABASE_URL", DEFAULT_DATABASE_URL
    )
    if auto_create_schema is None:
        auto_create_schema = os.environ.get("AUTO_CREATE_SCHEMA", "true").lower() == "true"
    database = Database(resolved_database_url)
    provider = context_provider or DeterministicContextProvider()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if auto_create_schema:
            await database.create_schema()
        yield
        await database.dispose()

    app = FastAPI(
        title="Support Readiness Workbench API",
        version="0.3.0",
        description=(
            "Local API for synthetic support-readiness evaluation. "
            "It contains no customer-send adapter."
        ),
        lifespan=lifespan,
    )
    app.state.database = database
    app.state.context_provider = provider

    allowed_origin = os.environ.get("WEB_ORIGIN", "http://127.0.0.1:3000")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[allowed_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readiness() -> dict[str, str]:
        try:
            async with database.sessions() as session:
                await session.execute(text("SELECT 1"))
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "database_unavailable"},
            ) from error
        return {"database": "ready", "status": "ready"}

    @app.post(
        "/api/v1/tickets",
        response_model=TicketResponse,
        status_code=201,
    )
    async def create_ticket(payload: TicketCreate) -> Ticket:
        ticket = Ticket(**payload.model_dump(), status="pending")
        try:
            async with database.sessions() as session:
                session.add(ticket)
                await session.commit()
                await session.refresh(ticket)
        except IntegrityError as error:
            raise HTTPException(
                status_code=409,
                detail={"code": "external_id_conflict"},
            ) from error
        return ticket

    @app.get("/api/v1/tickets", response_model=TicketList)
    async def list_tickets(
        limit: int = Query(default=20, ge=1, le=100),
        cursor: str | None = None,
        status: str | None = Query(default=None, pattern="^(pending|evaluated)$"),
    ) -> TicketList:
        async with database.sessions() as session:
            query = select(Ticket)
            if status:
                query = query.where(Ticket.status == status)
            if cursor:
                cursor_ticket = await session.get(Ticket, cursor)
                if cursor_ticket is None or (
                    status is not None and cursor_ticket.status != status
                ):
                    raise HTTPException(
                        status_code=400,
                        detail={"code": "invalid_cursor"},
                    )
                query = query.where(
                    or_(
                        Ticket.created_at < cursor_ticket.created_at,
                        and_(
                            Ticket.created_at == cursor_ticket.created_at,
                            Ticket.id < cursor_ticket.id,
                        ),
                    )
                )
            result = await session.scalars(
                query.order_by(Ticket.created_at.desc(), Ticket.id.desc()).limit(limit + 1)
            )
            rows = list(result)
        has_more = len(rows) > limit
        items = rows[:limit]
        return TicketList(
            items=[TicketResponse.model_validate(item) for item in items],
            next_cursor=items[-1].id if has_more and items else None,
        )

    @app.post(
        "/api/v1/tickets/{ticket_id}/evaluate",
        response_model=EvaluationResponse,
    )
    async def evaluate(ticket_id: str) -> EvaluationResponse:
        # Resolve an existing result before calling adapters. The ticket is
        # immutable after creation, so one durable evaluation per ticket makes
        # retries idempotent and avoids repeated external work.
        async with database.sessions() as session:
            ticket = await session.get(Ticket, ticket_id)
            if ticket is None:
                raise HTTPException(status_code=404, detail={"code": "ticket_not_found"})
            existing_query = (
                select(Evaluation)
                .options(selectinload(Evaluation.citation_rows))
                .where(Evaluation.ticket_id == ticket_id)
            )
            existing = (await session.scalars(existing_query)).one_or_none()
            if existing is not None:
                return evaluation_response(existing)
            ticket_input = snapshot_ticket(ticket)

        # Do not hold a database transaction or connection while independent
        # context adapters wait on I/O.
        decision, latency_ms = await evaluate_with_context(ticket_input, provider)
        evaluation = Evaluation(
            ticket_id=ticket_id,
            route=decision["route"],
            reason=decision["reason"],
            draft=decision.get("draft"),
            confidence=decision.get("confidence"),
            automatic_send_allowed=False,
            human_review_status="pending",
            external_action_state="blocked",
            latency_ms=latency_ms,
        )
        evaluation.citation_rows = [
            EvaluationCitation(source_id=source_id)
            for source_id in decision.get("citations", [])
        ]

        try:
            async with database.sessions() as session:
                persisted_ticket = await session.get(Ticket, ticket_id)
                if persisted_ticket is None:
                    raise HTTPException(
                        status_code=404,
                        detail={"code": "ticket_not_found"},
                    )
                existing = (await session.scalars(existing_query)).one_or_none()
                if existing is not None:
                    return evaluation_response(existing)
                persisted_ticket.status = "evaluated"
                session.add(evaluation)
                await session.commit()
                await session.refresh(evaluation, attribute_names=["citation_rows"])
        except IntegrityError:
            # A concurrent retry may win the unique ticket constraint after the
            # initial lookup. Return that durable result rather than a 500.
            async with database.sessions() as session:
                existing = (await session.scalars(existing_query)).one_or_none()
                if existing is None:
                    raise
                return evaluation_response(existing)
        return evaluation_response(evaluation)

    @app.post(
        "/api/v1/evaluations/{evaluation_id}/review",
        response_model=EvaluationResponse,
    )
    async def review(
        evaluation_id: str,
        payload: ReviewRequest,
    ) -> EvaluationResponse:
        async with database.sessions() as session:
            query = (
                select(Evaluation)
                .options(selectinload(Evaluation.citation_rows))
                .where(Evaluation.id == evaluation_id)
            )
            evaluation = (await session.scalars(query)).one_or_none()
            if evaluation is None:
                raise HTTPException(
                    status_code=404,
                    detail={"code": "evaluation_not_found"},
                )
            reviewed = reviewed_decision(evaluation, payload.status, payload.note)
            evaluation.human_review_status = reviewed["human_review_status"]
            evaluation.human_review_note = reviewed["human_review_note"]
            evaluation.external_action_state = reviewed["external_action_state"]
            evaluation.automatic_send_allowed = False
            await session.commit()
        return evaluation_response(evaluation)

    @app.get("/api/v1/metrics", response_model=MetricsResponse)
    async def metrics() -> MetricsResponse:
        async with database.sessions() as session:
            tickets_total = await session.scalar(select(func.count(Ticket.id)))
            evaluations_total = await session.scalar(select(func.count(Evaluation.id)))
            route_rows = await session.execute(
                select(Evaluation.route, func.count(Evaluation.id)).group_by(Evaluation.route)
            )
            automatic_sends = await session.scalar(
                select(func.count(Evaluation.id)).where(
                    Evaluation.automatic_send_allowed.is_(True)
                )
            )
        return MetricsResponse(
            tickets_total=tickets_total or 0,
            evaluations_total=evaluations_total or 0,
            routes={route: count for route, count in route_rows},
            automatic_sends=automatic_sends or 0,
        )

    return app


app = create_app()
