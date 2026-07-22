"""Compatibility entry point for the async context benchmark."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.benchmarks.async_context_benchmark import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
