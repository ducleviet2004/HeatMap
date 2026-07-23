# Local routing graph

This directory intentionally contains no routing data. Pin an OSM snapshot URL, checksum, extract
date, and geographic boundary in an internal change record. Use OSRM `v5.27.1` tooling to run
`osrm-extract`, `osrm-partition`, and `osrm-customize`, then name the graph `region.osrm`.

Set `OSRM_URL=http://osrm:5000` and a meaningful `ROUTING_DATA_VERSION` only after the graph is
present. Start the optional service with `docker compose --profile routing up --build`.
Never commit `.osm.pbf` or generated `.osrm*` files.

