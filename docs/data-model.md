# Data model and data dictionary

Daily unit demand is indexed by an immutable dataset version, SKU, location, and date. `data/schemas` contains exported Pydantic JSON Schemas.

| Observation field | Type | Meaning / validation |
|---|---|---|
| record_id | string, 1–100 | Stable source record identifier; unique across the store |
| dataset_id | string, 1–100 | Immutable dataset version; ASCII-like word/dot/hyphen identifier |
| sku / location | string, 1–80 | Business keys; no arbitrary HTML/path names |
| date | ISO date | One daily record per series/date |
| demand | finite float, 0–1e9 | Units observed; zero is explicit and is not a missing value |
| promotion | boolean | Historical scheduled promotion feature; false by default |
| stockout | boolean | Censoring warning retained in history; false by default |
| ingested_at | timestamp | Actual UTC ingestion time set by the importer; source fixture timestamps are deterministic |
| validation_status | valid / warning | Stockouts receive warning status; invalid rows prevent atomic dataset commit |
| provenance | JSON object | Optional source metadata; synthetic family, seed, latent mean, generator version, shock multiplier |

CSV requires record_id, dataset_id, sku, location, date, demand. Extra columns are rejected. Boolean fields accept Pydantic boolean representations; prefer `true`/`false`. CSV provenance must be a JSON-encoded object. Uploads are UTF-8, at most 10 MiB and 250,000 records. Use the generator and startup seed for larger synthetic datasets.

Each import has exactly one dataset_id. Existing dataset versions cannot be overwritten. A new version must use new record IDs. Duplicate keys, invalid dates, NaN, infinite/negative demand, invalid CSV structure, and invalid encoding appear in a persisted report. Rows are committed together or not at all. Daily continuity and sufficient history are checked before forecasting; an otherwise valid short or gapped series may import but cannot produce a run. No imputation occurs.

## Tables

- `datasets`: version ID, source, timestamp, row count, content SHA-256, generation/import metadata.
- `observations`: validated daily records; unique composite series/date index.
- `validation_reports`: every accepted/rejected attempt and row-level issue descriptions.
- `forecast_runs`: content-addressed input/config identity and immutable forecast/evaluation JSON.
- `scenarios`: immutable assumptions and computed deltas linked to a baseline run ID.
- `idempotency`: request key, input fingerprint, and replayable response.
- `ai_telemetry`: runtime, model/digest, template version, input run IDs, token counts if available, latency, validation outcomes.

The initial schema uses application-enforced relationships and SQL unique keys. There are no cascade-delete workflows or multi-tenant ownership rules.

## Synthetic truth and anomalies

The generator uses an independent NumPy SeedSequence per SKU/location. Increasing assortment size preserves existing series. The demo includes 500 SKUs × CHI/DAL/SEA × 196 days (294,000 records). The committed small fixture contains five SKUs across the same three locations (2,940 records).

Families rotate through regular, weekly seasonal, intermittent, lumpy, and trending demand. Promotions recur on a seven-day schedule within a 63-day cycle. Some series have a temporary negative shock; stockout days are marked explicitly; SKU-0500 has all-zero history. Lumpy positive demand scales Poisson arrivals by one of 1, 2, or 8. Latent `expected_uncensored` incorporates occurrence and size multipliers; the structural-zero SKU has zero expected demand. It does not set censored sales to the latent mean.

`provenance.family` is a generating mechanism. The computed ADI/CV² class is a descriptive statistic and may differ because of finite samples. Ground-truth fields are never forecast inputs, verified by regression tests. `data/sample/anomalies.csv` deliberately contains negative demand, NaN, invalid dates, and duplicate keys for rejection demos.
