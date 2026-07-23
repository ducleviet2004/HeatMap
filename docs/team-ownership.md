# Team ownership and delivery

All three developers are full-stack and own vertical slices through schema, API/worker, UI,
observability, tests, and documentation. The PO/BA/QA coordinator protects scope, clarifies
acceptance examples, curates test evidence, and does not become the team's testing bottleneck.

## Definition of Ready

An issue has user/operational value, bounded scope, PRD reference, examples and acceptance criteria,
data/privacy classification, dependency and API/schema notes, observability expectation, test
approach, performance relevance, and an owner/reviewer. Open product ambiguities are resolved.

## Definition of Done

Acceptance criteria are demonstrated; architecture flow and API conventions are followed; migration
and rollback are safe; lint, format, types, tests, build, and relevant integration checks pass;
logs/metrics make failure diagnosable; docs and ADRs are current; no secrets or real GPS are added;
peer review is complete; and unfinished behavior is clearly disabled rather than simulated.

## Initial balanced slices and merge order

1. **A — Planned route lifecycle:** synthetic route fixture contract → route repository/API →
   read-only route summary UI. Depends on migration hardening.
2. **B — GPS event acceptance:** idempotent persistence → transaction-safe Stream publication →
   ACK/error UI diagnostics. Depends on route/trip fixture contract.
3. **C — Worker observability:** consumer group lifecycle → lag/retry/dead-letter policy → worker
   status UI. Depends on the event envelope.

Merge shared migration/contract changes first, then A route contract, B ingestion path, and C worker
runtime. Feature slices remain independently reviewable and must not expose incomplete analytics.

## Next 12 issues

1. **A:** Validate migration upgrade, downgrade, constraints, and PostGIS round trip in CI.
2. **A:** Add driver/trip/planned-route repositories and synthetic fixture factory.
3. **A:** Deliver planned-route create/read API plus route summary UI.
4. **A:** Add routing-snapshot provenance and route-version audit tests.
5. **B:** Define versioned GPS ingestion contract and PRD acceptance examples.
6. **B:** Persist idempotent GPS batches before returning ACK.
7. **B:** Publish committed event references to Redis Streams with recovery tests.
8. **B:** Add ingestion health/throughput telemetry and operator diagnostics UI.
9. **C:** Implement consumer-group runner, graceful shutdown, retry, and claim policy.
10. **C:** Deliver cleaning/windowing slice with deterministic synthetic cases.
11. **C:** Integrate self-hosted OSRM matching with graph/version compatibility checks.
12. **C:** Add worker lag/failure status API and status-console panels.

After these, sequence ordered road-edge comparison → bypass detection → H3 aggregation → GeoJSON
query → dashboard. Each requires the approved PRD before semantics are implemented.

