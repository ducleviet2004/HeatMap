# ADR 0004: Self-hosted OSRM and routing data versioning

Status: Accepted

Use pinned OSRM `v5.27.1` with a locally prepared, checksum-pinned OSM snapshot. The graph is not
stored in Git. Every derived route records `routing_data_version`.

Public routing services are forbidden because they make availability, privacy, reproducibility, and
capacity uncontrollable. OSRM remains an optional Compose profile until a graph is installed;
readiness then reports `not_configured` instead of returning fabricated matches.

