# Contributing to DemandSense

We welcome small, evidence-backed improvements to forecasting, data quality, accessibility, and local AI reliability.

1. Follow the native setup in README and create a branch.
2. Keep forecasting math in `packages/demandsense`, orchestration in services, and presentation in the web app. HTTP handlers validate and delegate.
3. Add regression tests for numerical changes. Show that training never reads its future and that no LLM output changes computed state.
4. Run `ruff check packages apps/api tests scripts`, `ruff format --check packages apps/api tests scripts`, and `pytest`.
5. In `apps/web`, run `pnpm lint`, `pnpm typecheck`, `pnpm test`, and `pnpm build`. Run `pnpm e2e` against a running full demo for workflow changes.
6. Benchmark model changes with fixed seeds. Include configuration, hardware, accuracy, coverage, and difficult demand classes. A worse result is useful evidence.
7. Explain the operational problem, resulting behavior, and validation in the PR. Attach screenshots for UI changes.

Never submit customer data, credentials, licensed model weights, or unverifiable accuracy/performance claims. Keep dependencies open source and update the license inventory and lockfiles. New cloud integrations must be optional and must not enter the default demo.

The release has an explicit acceptance checklist in `docs/release-checklist.md`; passing local checks is not evidence that GitHub Actions has run.
