# Performance testing

The official objective is ≥1,000 requests/second for at least 15 minutes after a two-minute warm-up,
with error rate <1%, ingestion ACK p95 <200 ms, and read API p95 <500 ms. The benchmark dataset must
contain at least one million synthetic GPS points. No acknowledged event may be lost and queue lag
must recover after load stops.

Representative traffic is 50% GPS ingestion, 30% heatmap query by time/resolution, 10%
driver-filtered heatmap, and 10% trip/route detail. The environment, compute, database size,
versions, routing snapshot, cold/warm behavior, and results must be recorded.

Health-only traffic, static responses, mock repositories, empty datasets, or warm-cache-only runs
cannot establish acceptance. The current `smoke.js` only checks reachability; the official benchmark
cannot exist until the business endpoints do.

