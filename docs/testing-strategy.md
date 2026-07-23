# Testing strategy

The test pyramid emphasizes fast unit tests for services/adapters and semantic API/component tests,
then focused integration tests with real PostgreSQL/PostGIS and Redis. Tests must inspect response
meaning, not only HTTP status.

Foundation coverage includes liveness, degraded readiness, version configuration, CORS validation,
Redis envelope publishing, UI loading/degraded/error states, type checks, and production build.
Integration CI should next add: empty-database migration, PostGIS geometry round trip, Redis
publish/read, database idempotency constraints, and latest migration downgrade/upgrade.

Use synthetic, deterministic coordinates only. Never commit customer or real driver GPS. A failing
external dependency should produce an explicit unavailable state; it must not be hidden with mocks
in end-to-end tests.

Definition of Done requires relevant unit, integration, contract, and UI tests plus evidence for
operational behavior and rollback.

