# Reproduce the screenshots

All images here are captured from the real local UI against the generated 500-SKU demo, not design mockups.

1. Start the app (Compose or native) at `http://127.0.0.1:5187`.
2. In `apps/web`, run `pnpm exec playwright install chromium` once.
3. Run `pnpm e2e`. This traverses the real browser→API→database workflow, tests CSV rejection and mobile layout, and replaces the screenshots.

Desktop capture is 1440 × 1050 with full-page output. Mobile is 390 × 844. The workflow captures `workspace.png`, `backtests.png`, `scenario.png`, and `mobile.png`. It creates a real immutable 25% promotion scenario. If using a different dataset or seed, numbers and screenshots will change.

Manual capture: open the forecast workspace for SKU-0001 at CHI, horizon 14; capture. Open Backtesting; capture. Open Scenarios, enter 25% uplift across days 1–14, apply, and capture. Never edit numeric values into screenshots.
