# API conventions

- Public foundation endpoints live under `/api/v1`; OpenAPI is served by FastAPI.
- JSON uses snake_case and UTC timestamps use ISO 8601 with an explicit offset.
- Clients may send `X-Correlation-ID`; every response returns it.
- Validation and unexpected errors use
  `{"error":{"code":"…","message":"…","correlation_id":"…"}}`.
- Unexpected exceptions are logged server-side without exposing stack traces or settings.
- Liveness only proves that the process runs. Readiness reports each dependency separately and may
  be `healthy`, `degraded`, or `unavailable`.
- Adding breaking fields or semantics requires a new API version or an approved compatibility plan.

