# Local verification evidence

Build host: Apple M5 / macOS arm64. Verification performed 2026-09-27 local time (2026-09-28 UTC).

| Check | Result |
|---|---|
| Python lint and format | pass |
| Python tests | 47 passed, 1 PostgreSQL integration skipped |
| Coverage | 92% aggregate; forecasting core 98% |
| Frontend lint / typecheck | pass |
| Vitest | 5 passed |
| Vite production bundle | pass; chart size advisory retained |
| Browser workflow | 3 passed against real local API/database |
| Python dependency audit | no reported vulnerabilities |
| Frontend dependency audit | 0 low/moderate/high/critical after patching Vitest |
| Installed local model | qwen3:8b, successful structured explanation, unchanged forecast state |
| Docker / PostgreSQL / GitHub CI | not executed on this host; see release checklist |

The machine-readable forecasts and local AI measurements live in `docs/benchmarks`. Screenshots are in `docs/screenshots`. Do not treat this document as CI status or a portable performance guarantee.
