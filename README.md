# Route Deviation Heatmap Analytics

Foundation monorepo for a six-week, three-developer delivery. It provides a FastAPI status API,
PostgreSQL/PostGIS schema, Redis Streams adapter, optional self-hosted OSRM, and a React operations
console. Route deviation analytics are deliberately **not implemented yet**.

The official product source is [PRD V4](docs/PRD_V4_ROUTE_DEVIATION_HEATMAP.md). The checked-in PRD
is currently empty; obtain the approved content from the Product Owner before product behavior is
implemented. The foundation brief was used only to establish the development platform.

## Quick start

Prerequisites: Docker Desktop with Compose v2. Copy `.env.example` to `.env` only when overrides are
needed; the Compose defaults are safe for local development.

```sh
docker compose config --quiet
docker compose up --build
```

Open the System Status console at <http://localhost:5173/status>, API docs at
<http://localhost:8000/docs>, and health at <http://localhost:8000/api/v1/health>. With no routing
graph, readiness is intentionally `degraded` and OSRM is `not_configured`.

To enable a prepared local graph, follow [OSRM data instructions](osrm/data/README.md), set
`OSRM_URL=http://osrm:5000`, and run:

```sh
docker compose --profile routing up --build
```

## Local checks

Python 3.12 and Node 22 are required outside Docker.

```sh
make setup
make check
```

Windows developers can run the commands listed in [development.md](docs/development.md) directly.
See [architecture](docs/architecture.md), [testing strategy](docs/testing-strategy.md), and
[team ownership](docs/team-ownership.md) before starting a slice.

## Scope status

Available: schema migration, health/readiness/version endpoints, PostGIS and Redis checks, generic
versioned Stream publishing, status UI, CI, and a k6 reachability smoke test.

Not available: GPS ingestion, cleaning/windowing, map matching, ordered road-edge comparison,
bypass detection, H3 aggregation, heatmap/query APIs, production authentication, or the real
performance benchmark. No 1,000 req/s claim has been made.

