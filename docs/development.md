# Development and onboarding

## Toolchain

Use Python 3.12, Node 22.13+, npm, Docker Desktop/Compose v2, and optionally k6. Do not use the
host's Python 3.11 for the backend.

## Services

Run `docker compose up --build`. Migrations execute before Uvicorn starts. Named volumes preserve
PostgreSQL and Redis data; `docker compose down` does not remove them. Use `docker compose down -v`
only when intentionally deleting local data.

Backend-only setup:

```sh
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
mypy app
pytest
```

Frontend setup:

```sh
cd frontend
npm ci
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

Configuration is environment-only; `.env.example` documents all variables. Never log raw GPS,
secrets, or the full environment. Add a migration for every schema change and exercise upgrade from
empty plus the latest downgrade/upgrade cycle.

