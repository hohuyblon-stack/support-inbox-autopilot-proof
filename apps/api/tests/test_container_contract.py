from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_compose_requires_migrations_and_keeps_postgres_private():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert 'command: [".venv/bin/python", "-m", "apps.api.app.migrations"]' in compose
    assert "condition: service_completed_successfully" in compose
    assert "AUTO_CREATE_SCHEMA: \"false\"" in compose
    assert "127.0.0.1:8000:8000" in compose
    assert "127.0.0.1:3000:3000" in compose
    postgres_section = compose.split("  postgres:", 1)[1].split("\n  migrate:", 1)[0]
    assert "ports:" not in postgres_section


def test_images_run_application_processes_as_non_root_users():
    api_image = (ROOT / "apps/api/Dockerfile").read_text(encoding="utf-8")
    web_image = (ROOT / "apps/web/Dockerfile").read_text(encoding="utf-8")

    assert "USER app" in api_image
    assert "USER node" in web_image
