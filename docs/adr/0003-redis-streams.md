# ADR 0003: Redis Streams for asynchronous processing

Status: Accepted

Use Redis 7 Streams for versioned work notifications and future consumer groups. Messages carry an
event ID, correlation ID, type, timestamp, payload version, and compact payload. Durable business
state is committed to PostgreSQL before it is eligible for asynchronous work.

Streams offer sufficient foundation throughput and low operating cost for this team. Delivery,
retry, pending-entry recovery, dead-letter behavior, and the transactional publication pattern must
be completed and tested in the ingestion slice.

