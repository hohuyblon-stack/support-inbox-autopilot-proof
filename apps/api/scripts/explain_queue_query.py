"""Compatibility entry point for the ticket-list SQL investigation."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.sql.investigate_ticket_query import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
