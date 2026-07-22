# Verification

Run commands from the repository root unless a block changes directory. The
application and CI require Python 3.11–3.14, uv, Node.js 20.9+, and npm.

## 1. Deterministic control engine and static evidence

```bash
python3 -m unittest discover -s tests -v
python3 evaluate.py --output /tmp/evaluation-results.json
diff -u evaluation/results.json /tmp/evaluation-results.json
python3 -m compileall -q readiness.py evaluate.py tests
```

This covers deterministic routes, provider-output structure, source/confidence
gates, failure fallback, human review, page links/truth boundaries, and 20
committed expected-versus-observed cases with zero automatic sends.

## 2. FastAPI, relational, async, and migration contracts

```bash
uv sync --python 3.13 --frozen
uv run --python 3.13 pytest -q apps/api/tests
uv run --python 3.13 python -m apps.api.app.migrations
uv run --python 3.13 python -m compileall -q apps/api
```

The suite covers the complete API operator journey, conflicts, validation,
bounded pagination, health/readiness, aggregate metrics, human review, an async
rendezvous proof, schema migration, foreign keys, constraints and queue index.

## 3. Reproducible async and SQL evidence

Run the exact commands documented by the committed evidence files:

```bash
uv run --python 3.13 python apps/api/scripts/benchmark_context.py --verify
uv run --python 3.13 python apps/api/scripts/explain_queue_query.py --verify
```

The benchmark measures deterministic local adapter scheduling. The SQL script
creates its declared synthetic workload in a temporary local database and
records the actual query plan. Both are engineering regression artifacts, not
production latency, capacity, scale, or cost claims.

## 4. Strict frontend and production build

```bash
cd apps/web
npm ci
npm run typecheck
npm test
npm run build
npm audit --audit-level=high
```

This covers strict TypeScript, loading/empty/error/ticket/evaluation state,
absence of a send control, production compilation and currently known npm
advisories. The exact dependency tree is locked. `postcss` and `sharp` overrides
are present because the initial current dependency tree produced one moderate
and two high advisories; the final audited tree reports zero.

## 5. Real browser-to-API-to-database flow

```bash
cd apps/web
npx playwright install chromium
npm run test:e2e
```

Playwright starts the real FastAPI application and Next.js development server,
creates and persists a synthetic ticket, evaluates it, records approval, asserts
zero send control, and checks mobile page overflow. The test uses a local SQLite
file and deterministic recorded context; it makes no external provider call.

## 6. Render evidence

Production-build renders were inspected at 1440px desktop and 390px mobile for
the populated decision state, plus loading, empty and API-error states. The reviewed files
are stored only in the local internal workbench:

- `screenshots/flagship-desktop-decision-v3.png`
- `screenshots/flagship-mobile-decision-v3.png`
- `screenshots/flagship-loading-v3.png`
- `screenshots/flagship-empty-v3.png`
- `screenshots/flagship-error-v3.png`

These images prove local rendering at one commit; they do not prove a public
deployment.

## 7. Docker/PostgreSQL path

```bash
docker compose config
docker compose up --build
```

The current execution machine did not provide Docker, so the files can be
structurally reviewed but the PostgreSQL container path is `UNVERIFIED_RUNTIME`.
Do not convert a successful SQLite run into a PostgreSQL or cloud claim.

## 8. Security and source hygiene

```bash
git diff --check
git grep -n -I -E '-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|sk_live_[0-9A-Za-z]{16,}' -- .
```

No match is the expected result for the high-confidence pattern check. GitHub
secret scanning and push protection remain separate remote controls. No scanner
was installed or executed from an untrusted source.

## What these checks do not prove

- live LLM/retrieval quality, provider cost, latency, rate limits, or availability;
- Gorgias, Shopify, carrier, order, refund, email, or shopper-send behavior;
- PostgreSQL runtime, distributed workers, AWS operation, production security,
  traffic, SLOs, observability, or incident response;
- buyer demand, client delivery, support impact, revenue, or collected cash; or
- full assistive-technology, cross-browser, penetration, supply-chain, or load
  testing beyond the exact checks listed above.
