# DemandSense 0.1 release checklist

This is a **locally verified release candidate**. It is not marked as a completed public GitHub release. The user requested local-only delivery.

## Verified on the build host

- [x] Native backend and frontend running on loopback (8027 / 5187).
- [x] Full default dataset: 500 SKUs, 3 locations, 196 days, 294,000 records.
- [x] Regular, seasonal, trending, intermittent, lumpy, promotional, shock, stockout, and all-zero cases.
- [x] Six numerical model candidates and empirical 80%/95% bands.
- [x] Selection/calibration precede untouched rolling evaluation.
- [x] Immutable scenarios, deterministic deltas, CSV export, inventory API.
- [x] Malformed data rejection is atomic and visible; source IDs and report lineage retained.
- [x] No-LLM mode works throughout the primary workflow.
- [x] Already-installed qwen3:8b discovered through Ollama and a real structured explanation completed.
- [x] Unit/integration suite: **47 passed, 1 skipped**, **92% aggregate coverage**; numerical engine **98%**.
- [x] PostgreSQL test skip is explicit when no disposable PostgreSQL URL is configured.
- [x] Frontend lint, TypeScript checking, **5 tests**, and production build pass.
- [x] **3 real browser E2E tests** pass: planner workflow, narrow viewport, malformed upload.
- [x] Screenshots are captured from the implementation and reproducible.
- [x] Full 1,500-series benchmark committed with JSON/CSV/Markdown and hardware/config metadata.
- [x] Python dependency audit: no known vulnerabilities reported at execution time.
- [x] Frontend dependency audit after Vitest upgrade: zero reported vulnerabilities, including moderate severity.
- [x] Source license, dependency/license inventory, threat model, ADRs, data dictionary, contribution guidance, and roadmap included.
- [x] Mermaid architecture source passed the Mermaid skill's static validation. Host rendering is not claimed.
- [x] Local database, environment, logs, caches, and model weights excluded from Git.

## Pending before public release

- [ ] Run `docker compose up --build --wait` on a host with a container engine. Docker is absent on this Mac.
- [ ] Run PostgreSQL integration and validate the Compose read-only role on that host.
- [ ] Run the committed GitHub Actions workflow and inspect all jobs. No GitHub run is claimed for local-only delivery.
- [ ] Execute native Windows instructions on Windows.
- [ ] Enable private vulnerability reporting and review repository/community settings when publishing.
- [ ] Scan built container images and review model-weight licenses for the exact deployment.

## Known limits, not hidden release claims

Single-workspace and single-process mutation coordination; no schema-migration framework; an import idempotency crash window; empirical marginal bands without universal coverage guarantees; assumed rather than causal scenario effects; stockout flags without lost-sales recovery; no joint lead-time distribution; no semantic proof of AI prose. See architecture, evaluation, and security docs.

The frontend chart chunk is approximately 522 kB minified (177 kB gzip) and Vite reports a size advisory. That is a build advisory, not a failed build; further chart splitting is an optimization opportunity. A Starlette test-client deprecation warning is visible in the backend test run; tests still pass.
