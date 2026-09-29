# ADR 002 — Portable persistence and optional local inference

Status: accepted for 0.1.

PostgreSQL is the standard container store; SQLite removes a database-server prerequisite from native development. SQLAlchemy provides bound queries and a common repository API. Immutable JSON snapshots capture evidence and lineage without exposing HTTP handlers to numerical implementation details. The cost is coarse snapshot storage and no migration framework in this first release.

Local AI uses a protocol interface with Ollama and local OpenAI-compatible adapters. The chosen model is request-scoped and discovered from the user's runtime. A deterministic explanation path is always available. No provider SDK, remote key, or model download is part of startup.

Single-process mutation serialization is acceptable for a local workbench. Horizontal scaling requires database-backed jobs and transaction-safe idempotency; adding workers alone is unsupported.
