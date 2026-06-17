You are taking over an orders and refunds API for channel partners. After the most recent emergency launch, partners reported that this service is no longer suitable as a stable external interface: the order list behavior is unstable, the response shape is inconsistent over time, error responses are not machine-friendly, refund creation risks duplicate requests being created, and traffic-protection signals are missing. You need to fix the existing service without changing the business scope so it again meets production integration requirements.

Input data is under `/app/workspace/`:
- `service/`: the existing Node.js / Express service code, including partner-facing endpoints for order listing, order details, refund request creation, refund request details, etc.
- `data/orders_snapshot.json`: an orders snapshot including orders, line items, amounts, statuses, timestamps, and more.
- `data/customers_snapshot.json`: a customers snapshot including customers, emails, addresses, countries, and more.
- `data/refund_requests.json`: existing refund requests, processing status, and history records.
- `data/partner_keys.json`: partner API keys, access tiers, and baseline rate-limit configuration.
- `scripts/`: service startup, seeding, and basic self-check scripts.

Your tasks:
1. Fix the existing external HTTP API so that the order list, order details, refund request creation, and refund request details endpoints are consistent in URL structure, HTTP methods, status codes, and response body shape; do not evade issues in the existing interface by adding a parallel set of endpoints.
2. Make the order list support stable pagination, and support common filtering and sorting. The returned results must be computed from the real dataset; do not return a fixed, hard-coded sample.
3. Fix the refund request creation flow to correctly handle duplicate submissions, invalid fields, missing resources, state conflicts, and similar scenarios; the same retried request must not cause duplicate writes or duplicate creations.
4. Preserve and fix the authentication and traffic-protection flow so clients can distinguish authentication failure, insufficient permissions, request throttling, and normal business errors via status codes, response bodies, and required response headers.
5. Keep the service startup method and business boundaries unchanged, and continue using the existing data files and persistence approach as the system-of-record sources.

Output:
- Directly modify the existing service code under `/app/workspace/service/`.
- Keep the existing startup entrypoints; validation will start the service using the repository's default startup method.

Notes:
- After the service starts, it must continue to provide external order query and refund request capabilities; do not rewrite the task into an offline script or static file generation.
- You may add necessary validation, pagination, error handling, middleware, persistence logic, and test helper code, but do not change the task's business goals.
- You may add a small number of dependencies, but do not introduce components that require external private accounts, external cloud permissions, or extra manual logins.
- Do not modify any input data under `/app/workspace/data/` to evade issues.
- Do not evade issues by replacing real flows, removing functionality, removing authentication, removing rate limiting, or removing refund state checks.
- Do not spin up a second service, reverse proxy, or return pure mocks to bypass the existing implementation.
- Do not hard-code return values so they only work for a fixed sample, and do not special-case only a single order ID or a single request parameter.
- Do not collapse all failures into a single status code or a single error object shape.
