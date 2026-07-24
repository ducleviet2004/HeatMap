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

## GPS gap handling

GPS points remain immutable and no synthetic point is inserted. Gaps below 15 seconds stay in the
same trace. Gaps from 15 through 120 seconds remain matchable but carry `gps_gap_medium` metadata
for audit and confidence gating. Gaps over 120 seconds split the trace before OSRM; the following
matched segment has `gap_before=true` and `reason_code=gps_gap_long_split`, so rendering never draws
a straight connector across the missing interval. Planned edges fully inside a gap are marked
unobserved and Bypass Detection returns `gps_gap` instead of a confirmed bypass.

## OSRM map matching

Offline cleaned traces are sent only to the pinned, self-hosted OSRM Match API. Each OSRM sub-trace
remains a separate matched segment so GPS gaps are not bridged. The ordered road-edge sequence is
derived from directed consecutive OSM node pairs returned by `annotations=nodes`; duplicate
annotation overlap at leg boundaries is removed. Each segment retains OSRM's confidence, while the
trace-level `match_confidence` is the minimum segment confidence. Results always carry routing-data
and algorithm versions because edge identity is snapshot-dependent.

## Ordered-edge bypass detection

Planned and actual edge sequences are aligned with longest common subsequence rather than set
subtraction, preserving order and repeated edge occurrences. Contiguous missing planned-edge runs
are candidates only. A candidate is confirmed after routing-version, map-match confidence, minimum
length, GPS-gap, and corridor-distance gates pass. A missing edge run that remains within the
configured corridor is labeled `same_corridor` instead of bypass to reduce GPS-drift false
positives. Missing corridor evidence never produces a confirmed bypass.

## Bypass to H3 grid

Only confirmed bypass LineStrings are converted to H3 cells at resolutions 9–12. The
converter samples each line using at most half an H3 edge length and connects adjacent
sample cells, avoiding gaps along the route. Records are deduplicated by H3 resolution and
cell before persistence. Database inserts use `ON CONFLICT DO NOTHING`, so overlapping
segments and worker retries contribute at most once per trip/route/hex/algorithm version.

## Data model

`drivers` own `trips`; each trip has versioned `planned_routes` and immutable `gps_events`.
Coordinates use SRID 4326 and spatial columns have GiST indexes. `event_id` and
`(trip_id, sequence_no)` are idempotency constraints. Application schema is owned exclusively by
Alembic; database init only enables PostGIS.
