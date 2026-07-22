import asyncio
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from .database import DEFAULT_DATABASE_URL


ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = ROOT / "apps" / "api" / "alembic.ini"


def _upgrade(database_url: str) -> None:
    configuration = Config(str(ALEMBIC_INI))
    configuration.set_main_option("script_location", str(ALEMBIC_INI.parent / "migrations"))
    configuration.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(configuration, "head")


async def run_migrations(database_url: str) -> None:
    await asyncio.to_thread(_upgrade, database_url)


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    asyncio.run(run_migrations(database_url))
    print("Database migration completed at Alembic head.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
