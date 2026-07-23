# ADR 0002: PostgreSQL/PostGIS as system of record

Status: Accepted

Persist authoritative routes, trips, drivers, and raw GPS events in PostgreSQL 16 with PostGIS.
Alembic alone manages application tables. Redis cannot contain the only copy of acknowledged data.

This provides transactions, idempotency constraints, time queries, and spatial indexing in one
operational store. Scale will be measured before partitioning or introducing another datastore.

