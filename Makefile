.PHONY: setup check backend-check frontend-check compose-config up down smoke

setup:
	cd backend && python -m pip install -e ".[dev]"
	cd frontend && npm ci

backend-check:
	cd backend && ruff format --check .
	cd backend && ruff check .
	cd backend && mypy app
	cd backend && pytest

frontend-check:
	cd frontend && npm run format:check
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm test
	cd frontend && npm run build

compose-config:
	docker compose config --quiet

check: backend-check frontend-check compose-config

up:
	docker compose up --build

down:
	docker compose down

smoke:
	k6 run load-tests/scenarios/smoke.js

