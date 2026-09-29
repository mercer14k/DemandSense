# Repository tree

Generated from delivered source and artifacts; runtime caches, virtual environments, databases, and build outputs are omitted.

```text
demandsense/
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   └── dependabot.yml
├── apps/
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── web/
│   │   ├── public/
│   │   │   └── favicon.svg
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── Chart.tsx
│   │   │   ├── Panels.test.tsx
│   │   │   ├── Panels.tsx
│   │   │   ├── api.test.ts
│   │   │   ├── api.ts
│   │   │   ├── main.tsx
│   │   │   ├── style.css
│   │   │   ├── test-setup.ts
│   │   │   └── types.ts
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── eslint.config.js
│   │   ├── index.html
│   │   ├── nginx.conf
│   │   ├── package.json
│   │   ├── playwright.config.ts
│   │   ├── pnpm-lock.yaml
│   │   ├── pnpm-workspace.yaml
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   └── vitest.config.ts
│   └── __init__.py
├── data/
│   ├── sample/
│   │   ├── anomalies.csv
│   │   └── demand.csv
│   └── schemas/
│       ├── InventoryForecast.schema.json
│       ├── Narrative.schema.json
│       ├── Observation.schema.json
│       ├── RunRequest.schema.json
│       └── ScenarioInput.schema.json
├── docs/
│   ├── adr/
│   │   ├── 001-auditable-forecasting-core.md
│   │   └── 002-storage-and-local-ai.md
│   ├── benchmarks/
│   │   ├── example/
│   │   │   ├── metrics.csv
│   │   │   ├── per-series.csv
│   │   │   ├── results.json
│   │   │   └── summary.md
│   │   └── local-ai.json
│   ├── screenshots/
│   │   ├── README.md
│   │   ├── backtests.png
│   │   ├── mobile.png
│   │   ├── scenario.png
│   │   └── workspace.png
│   ├── ai-design.md
│   ├── architecture-diagram.md
│   ├── architecture.diagram.json
│   ├── architecture.md
│   ├── data-model.md
│   ├── dependency-inventory.json
│   ├── evaluation.md
│   ├── local-verification.md
│   ├── open-source-licenses.md
│   ├── release-checklist.md
│   ├── repository-tree.md
│   ├── roadmap.md
│   └── security.md
├── packages/
│   └── demandsense/
│       ├── __init__.py
│       ├── ai.py
│       ├── forecasting.py
│       ├── generator.py
│       ├── http_security.py
│       ├── schemas.py
│       ├── services.py
│       └── storage.py
├── scripts/
│   ├── postgres/
│   │   └── 01-reader.sh
│   ├── benchmark.py
│   ├── benchmark_ai.py
│   ├── dev.py
│   ├── license_inventory.py
│   └── performance.py
├── tests/
│   ├── benchmarks/
│   ├── e2e/
│   │   └── workflow.spec.ts
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_postgres.py
│   ├── unit/
│   │   ├── test_ai.py
│   │   ├── test_forecasting.py
│   │   └── test_runtime_protocols.py
│   └── conftest.py
├── .dockerignore
├── .env.example
├── .gitattributes
├── .gitignore
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── Dockerfile
├── LICENSE
├── README.md
├── SECURITY.md
├── docker-compose.yml
├── pyproject.toml
└── requirements.lock
```
