# Foundation architecture

```text
Browser → React status console → FastAPI /api/v1
                                  ├─ readiness service → PostgreSQL/PostGIS
                                  ├─ readiness service → Redis Streams
                                  └─ OSRM adapter → optional local OSRM graph
Future ingestion → transaction in PostgreSQL → publish versioned event → future workers
```

The repository is a modular monolith. HTTP routers validate and map responses; services coordinate
use cases; repositories own SQL; adapters isolate Redis and OSRM. API schemas and future ORM models
remain separate. Async connections are pooled and closed during application shutdown.

PostgreSQL/PostGIS is the system of record. Redis Streams is transport, never the sole durable copy.
OSRM uses a pinned, self-hosted image and versioned routing data; absence of a graph degrades only
routing capability.

The pool and async seams prepare the platform for the ≥1,000 req/s objective, but do not prove it.
Only the representative benchmark described in `performance-testing.md` can support that claim.

## GPS cleaning

GPS cleaning is a non-mutating service over immutable `gps_events`. It rejects points whose
reported accuracy or speed exceeds environment-configured thresholds and records the threshold
configuration version in every decision. Filtering returns references to accepted events without
updating raw geometry or measurements. Persisting cleaning decisions is outside this slice and
would require a new Alembic migration.

## Data model

`drivers` own `trips`; each trip has versioned `planned_routes` and immutable `gps_events`.
Coordinates use SRID 4326 and spatial columns have GiST indexes. `event_id` and
`(trip_id, sequence_no)` are idempotency constraints. Application schema is owned exclusively by
Alembic; database init only enables PostGIS.
