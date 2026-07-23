# ADR 0001: Technology stack

Status: Accepted for foundation

Use Python 3.12/FastAPI/SQLAlchemy/Alembic for the async API and React/TypeScript/Vite with Router,
TanStack Query, MapLibre, and Deck.gl for the UI. Use Docker Compose and GitHub Actions.

This matches the mandated stack, supports typed contracts and geospatial work, and keeps one
deployable modular monolith for a three-person team. Kafka, Kubernetes, Celery, microservices, and
additional frameworks are excluded until a measured need and new ADR exist.

