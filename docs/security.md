# Threat model and security boundaries

## Assets and trust

Assets are demand history, dataset lineage, immutable forecast/scenario state, access credentials, and the user's local machine. Trust boundaries are browser→API, imported CSV→validated records, API→database, and evidence/text→local inference. This is one trusted workspace, not a multi-tenant SaaS.

| Threat | Implemented control | Residual limitation |
|---|---|---|
| Unauthorized mutation | Router-wide write token, constant-time comparison; separate optional read token | Demo publishes a local-only demo token. It is not a user login system. |
| Data exfiltration | No cloud AI default; local runtime host allowlist; no redirects or proxy inheritance | An administrator can configure a local proxy that forwards remotely. Verify the runtime. |
| Prompt injection | Treat text as data; structured schema; cite allowlisted evidence IDs; no shell/SQL/agent tools | Semantically misleading prose can still pass schema validation. |
| Malformed/oversized uploads | MIME/extension allowlist, UTF-8 parsing, strict schemas, 10 MiB file cap; 11 MiB ASGI streamed body cap | Memory buffers are bounded but concurrent local requests still consume resources. |
| Path traversal | Original filename reduced to basename for display; never used as a storage path | Import error text is displayed as escaped text. |
| SQL injection | SQLAlchemy bound queries; fixed SQL only for setup/readiness | Database administrators retain normal administrator power. |
| Cross-site browser attacks | No permissive CORS; mutations require custom header token; trusted host allowlist; CSP in container frontend | Native Vite is a development server, not a hardened public host. |
| XSS and unsafe output | React text rendering; no raw model HTML; CSV export contains only generated dates/numbers | CSP permits inline styles for ECharts, but not inline script/eval. |
| Corrupted forecast from AI | AI reads evidence only; snapshots and KPIs are computed independently | No automatic numerical hallucination verifier for prose. |
| Retry/double apply | Request fingerprints + idempotency ledger + immutable content IDs | One API process; documented import crash window. |
| Resource exhaustion | Bounded horizons, upload limits, DB pagination, nginx rate limit, API concurrency limit in Compose | No distributed rate limiting, queue, or per-user quotas. |

## Demo versus private mode

Compose binds the API and web ports to 127.0.0.1 and does not publish the database port. Native development also binds loopback. `DEMO_MODE=true` makes synthetic data and a clearly non-secret demo write credential available for the first-run experience. Never expose this mode to a shared network or put real customer data into an untrusted demo host.

For a private shared deployment, set `DEMO_MODE=false`, unique `WRITE_TOKEN` and `READ_TOKEN`, configure `ALLOWED_HOSTS`, and use a private authenticated ingress with appropriate TLS. The API refuses the known demo token in private mode. Read-only callers cannot mutate or obtain the write token. OpenAPI/docs routes are disabled in private mode. Access tokens stay in browser memory, not local storage or URLs. For internet or multi-tenant use, add an identity provider, user/object authorization, audit policy, quotas, and database migrations first.

Compose provisions a SELECT-only `demandsense_reader` role; mutations use the owner connection. SQLAlchemy read calls use `DATABASE_READ_URL` where configured. The initial application user creates tables; a production deployment should separate migration and runtime credentials. `.env.example` contains only obvious local placeholders. `.env`, local databases, logs, caches, generated large data, and model files are ignored.

## Logging and model telemetry

Requests log a generated trace ID, method, path, status, and latency. Errors expose a consistent public envelope without stack traces. Do not place secrets in path identifiers. LLM events record runtime/model, model digest when exposed, template version, run IDs, settings, token usage when exposed, latency, retries (zero), and structured validation failures. Forecast snapshots record algorithm settings and data lineage. Raw prompts, uploaded CSV bodies, tokens, and private hidden reasoning are not logged.

## Verification and dependency hygiene

Tests cover read/write authorization, unknown schemas, SQL-shaped search input, chunked body size, invalid MIME/encoding, duplicate records, atomic rollback, unrecognized model/citation IDs, cloud-backed tags, and local model failure isolation. CI includes pip-audit and pnpm audit; advisory state changes over time. See the release checklist for actual checks run versus pending checks.

Both API and web containers run as non-root users. The API filesystem is read-only with a temporary writable /tmp. Container images and transitive dependencies still need regular patching and scanning. A full third-party penetration test and container-image vulnerability audit are not claimed.
