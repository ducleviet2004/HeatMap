# Local routing graph

This directory intentionally contains no routing data in Git. The repository pins the Vietnam
snapshot and build metadata in [`../vietnam-snapshot.json`](../vietnam-snapshot.json).

On Windows, run `.\scripts\setup-osrm.ps1` from the repository root. The script downloads and
checksum-verifies the pinned snapshot, uses OSRM `v5.27.1` to run `osrm-extract`,
`osrm-partition`, and `osrm-customize`, creates the local `.env`, starts the routing profile, and
checks a route plus application readiness. It reuses valid local data on subsequent runs; pass
`-Force` to rebuild the graph.

For manual operation, the generated graph basename must be `region.osrm`. Set
`OSRM_URL=http://osrm:5000` and a meaningful `ROUTING_DATA_VERSION`, then start the optional service:

```sh
docker compose --profile routing up --build
```

Never commit `.osm.pbf` or generated `.osrm*` files.
