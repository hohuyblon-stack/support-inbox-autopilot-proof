FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv==0.10.9

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY readiness.py ./readiness.py
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api/__init__.py ./apps/api/__init__.py
COPY apps/api/alembic.ini ./apps/api/alembic.ini
COPY apps/api/app ./apps/api/app
COPY apps/api/migrations ./apps/api/migrations

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /app/.state \
    && chown -R app:app /app

USER app
EXPOSE 8000

CMD [".venv/bin/uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
