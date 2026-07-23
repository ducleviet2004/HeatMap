# Load-test foundation

`smoke.js` verifies only reachability and the health response contract. It is not the official
performance workload and must never be used to claim the 1,000 req/s target.

Run against a local stack with `k6 run load-tests/scenarios/smoke.js`. Override the target with
`BASE_URL`.

