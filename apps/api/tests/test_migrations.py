from contextlib import redirect_stdout
import io
from pathlib import Path
import os
import subprocess
import sys

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from apps.api.app.migrations import run_migrations


@pytest.mark.asyncio
async def test_initial_migration_creates_relations_constraints_and_query_index(
    tmp_path: Path,
):
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'migration.sqlite3'}"
    await run_migrations(database_url)
    engine = create_async_engine(database_url)

    async with engine.connect() as connection:
        tables = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
        ticket_indexes = await connection.run_sync(
            lambda sync: inspect(sync).get_indexes("tickets")
        )
        evaluation_foreign_keys = await connection.run_sync(
            lambda sync: inspect(sync).get_foreign_keys("evaluations")
        )
        evaluation_unique_constraints = await connection.run_sync(
            lambda sync: inspect(sync).get_unique_constraints("evaluations")
        )

    await engine.dispose()

    assert {"tickets", "evaluations", "evaluation_citations", "alembic_version"} <= tables
    index_by_name = {item["name"]: item for item in ticket_indexes}
    assert index_by_name["ix_tickets_status_created_at_id"]["column_names"] == [
        "status",
        "created_at",
        "id",
    ]
    assert any(key["referred_table"] == "tickets" for key in evaluation_foreign_keys)
    assert "uq_evaluations_ticket" in {
        item["name"] for item in evaluation_unique_constraints
    }


def test_migration_module_is_a_cross_driver_cli(tmp_path: Path):
    database_path = tmp_path / "cli.sqlite3"
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
    }

    completed = subprocess.run(
        [sys.executable, "-m", "apps.api.app.migrations"],
        cwd=Path(__file__).resolve().parents[3],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "completed at Alembic head" in completed.stdout
    with __import__("sqlite3").connect(database_path) as connection:
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert version == ("0001_initial",)


def test_postgres_dialect_can_compile_complete_offline_ddl():
    root = Path(__file__).resolve().parents[3]
    configuration = Config(str(root / "apps/api/alembic.ini"))
    configuration.set_main_option(
        "script_location",
        str(root / "apps/api/migrations"),
    )
    configuration.set_main_option(
        "sqlalchemy.url",
        "postgresql+asyncpg://user:pass@db:5432/support_readiness",
    )
    output = io.StringIO()

    with redirect_stdout(output):
        command.upgrade(configuration, "head", sql=True)

    ddl = output.getvalue()
    assert "CREATE TABLE tickets" in ddl
    assert "CREATE TABLE evaluations" in ddl
    assert "ix_tickets_status_created_at_id" in ddl
    assert "CONSTRAINT uq_evaluations_ticket UNIQUE (ticket_id)" in ddl
