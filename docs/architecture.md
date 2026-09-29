# Architecture

DemandSense is a single-workspace local planning system. The API owns authorization and schemas; the service layer owns workflows; forecasting functions are pure numerical code. The browser never computes authoritative planning KPIs.

| Layer | Responsibility | Implementation |
|---|---|---|
| Web | Series search, charts, backtests, scenarios, evidence, validation | React, Vite, ECharts |
| HTTP | Versioned contracts, trace IDs, error envelope, read/write boundaries | FastAPI + Pydantic |
| Services | Immutable forecast snapshots, stable run IDs, scenario lineage | `services.py` |
| Domain | Six models, calibration bands, rolling origins, metrics, scenario arithmetic | `forecasting.py` |
| Data | Atomic imports, source identifiers, versioned datasets, persistence | SQLAlchemy |
| Local AI | Model discovery, structured explanation/draft adapters, abstention/fallback | Ollama or local OpenAI-compatible protocol |
| Evaluation | Reproducible synthetic benchmark and local model adapter benchmark | `scripts/benchmark*.py` |

## Main workflow

1. Generate or upload a dataset. Invalid imports are rejected atomically and produce a persisted validation report.
2. Search SKU/location series. Daily gaps must be repaired explicitly, never silently filled with zero.
3. `POST /api/v1/runs` checks minimum history, evaluates six candidates, freezes the pre-test winner, scores held-out origins, then refits the selected model on all available history.
4. Store the forecast, metrics, source-ID digest, algorithm settings, and evidence ledger as one immutable JSON snapshot.
5. A scenario creates a new immutable child snapshot; it cannot overwrite the baseline.
6. Explanations read a small evidence bundle. Runtime failure or invalid citations yield a deterministic template and observable failure telemetry.
7. Inventory callers read the versioned daily forecast contract, with explicit warnings against summing marginal bounds into service quantiles.

## Persistence and concurrency

PostgreSQL is the Compose store; SQLite is the native default. SQLAlchemy creates the initial schema at startup. This initial release does not include online schema migrations: back up the database before adopting a future schema revision.

A process lock serializes mutations and prevents duplicate run/scenario creation. An idempotency ledger replays identical requests and rejects key reuse with different payloads. Run/scenario content IDs also make a crash between snapshot commit and idempotency insertion safe for those operations. Import reports have a smaller crash window: after import commit but before idempotency recording, a retry rejects an existing dataset instead of duplicating records. This is documented rather than claimed to be exactly-once processing.

Use **one API worker** in this release. Multi-process/distributed job coordination, cancellation, retention, and an asynchronous job queue are future work. Read requests use a SELECT-only PostgreSQL role in Compose. SQLite has no equivalent database role split; HTTP authorization still applies.

No cloud services are required. The browser calls its same-origin API proxy. Native inference endpoints must use configured local hosts; no arbitrary endpoint can be supplied by a request. A malicious administrator can still configure a local proxy to forward elsewhere; deployment control remains a trust boundary.
