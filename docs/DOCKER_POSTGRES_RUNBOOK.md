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
locally. Docker was not installed on the 2026-07-22 local verification machine.
The draft-PR `docker-postgres-smoke` job supplied the independent runtime gate:
it built both images, started PostgreSQL 17, ran Alembic before API startup,
reached the API and web health paths, and verified one create/evaluate/metrics
journey with zero automatic sends.

That disposable CI result verifies the narrow container path only. It does not
prove production networking, secrets, backup/restore, traffic, observability,
managed PostgreSQL or cloud operation.

## Reviewable cloud path — design only

The validated infrastructure artifact in this repository is the non-root
Dockerfiles plus `docker-compose.yml`; CI runs `docker compose config`, builds the
images, orders migration before API readiness, and exercises PostgreSQL. There is
no AWS Terraform/CloudFormation module and no deployed environment.

If a validated pilot justifies cloud work, the smallest AWS-shaped mapping would
be one private PostgreSQL/RDS database, one migration task, one FastAPI container
service, one Next.js container service, TLS ingress, a registry, secret storage,
and centralized logs/alarms. That is an architecture decision to review—not
infrastructure that currently exists. Authentication, tenancy, retention,
backups, restore tests, alert ownership, and lawful data boundaries must be
defined before provisioning.

## Rollback requirements

1. Publish immutable image digests and retain the last known-good API/web pair.
2. Take and verify a database backup before a schema change.
3. Run migrations as a separately observed job; a failure must keep the new API
   revision out of service.
4. Shift traffic only after readiness and one sanitized smoke journey pass.
5. Roll application traffic back to the previous image digests on behavioral or
   health regression.
6. Never reverse a data migration blindly. Restore or apply a reviewed forward
   repair according to the migration's compatibility plan.

None of these production steps has been executed here, so recovery remains a
market-quality blocker.

## Cost notes

The billable drivers would be container CPU/memory and runtime hours, load
balancing/data transfer, registry storage, managed PostgreSQL size/IO/backups,
logs/metrics retention, secrets, and any external model/platform usage. No dollar
estimate is recorded because region, traffic, retention, availability target,
database shape, and provider contract are unknown. Refresh an official provider
calculator with the approved pilot assumptions before any spend authorization.
