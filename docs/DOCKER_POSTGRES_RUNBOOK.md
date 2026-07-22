# Docker and PostgreSQL runbook

The Compose path joins the Next.js UI, FastAPI, an Alembic migration job and
PostgreSQL 17. It is a local deployment path, not evidence of a deployed cloud
environment.

## Start

1. Copy `.env.example` to `.env`.
2. Set a URL-safe, local-only `POSTGRES_PASSWORD`; do not commit `.env`.
3. Run `docker compose up --build`.
4. Open `http://127.0.0.1:3000`.
5. Check API readiness at `http://127.0.0.1:8000/readyz`.

The database has no host port. The migration container must reach Alembic head
before the API starts, and the web container waits for API readiness. Both
public development ports bind only to loopback. The API and web images run as
non-root users. The API filesystem is read-only except for `/tmp`.

## Stop and recover

`docker compose down` stops containers and retains the named PostgreSQL volume.
`docker compose down --volumes` deletes the local demo data and should only be
used when that destructive reset is intended. Re-running `docker compose up`
retries the idempotent migration job.

Inspect `postgres`, then `migrate`, then `api` health when startup fails. A
failed migration blocks API startup instead of silently creating tables from
ORM metadata.

## Verification status

The Python migration CLI and SQLite migration behavior are automated and pass
locally. Alembic also generated the complete PostgreSQL 17-compatible offline
DDL without connecting to a server, and the Compose file has structural tests.
Docker was not installed on the 2026-07-22 verification machine, so image
builds, PostgreSQL runtime migration, container health checks and the integrated
container journey remain
`UNVERIFIED`. Run the commands above on a Docker-capable machine before calling
the container path ready.
