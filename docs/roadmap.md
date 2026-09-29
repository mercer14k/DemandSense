# Next five meaningful improvements

1. **Calibrate by forecast lead and demand regime.** Add nested selection/calibration splits, asymmetric count-aware intervals, proper scoring rules, and block-bootstrap coverage diagnostics. Compare with the current simple bands before adoption.
2. **Model joint lead-time demand.** Generate temporally dependent forecast paths and evaluate inventory service/cost outcomes. Daily marginal intervals are not enough for safety stock.
3. **Censoring and event knowledge-time.** Introduce availability observations, lost-sales treatment, and promotion snapshots as known at each origin. Evaluate on a licensed real-world retail dataset alongside the synthetic benchmark.
4. **Scale model fitting and durable jobs.** Add StatsForecast/MLForecast adapters, global models, a database-backed job queue, durable cancellation, migration tooling, and transaction-safe idempotency before multiple API workers.
5. **Measure explanation faithfulness.** Build an adversarial evidence suite and human-reviewed claim annotations across installed local models. Report unsupported-claim rate, abstention quality, latency, and memory independently of forecasting accuracy.

After those foundations: hierarchical reconciliation, explicit cold-start fallbacks, forecast value-add tracking, and probabilistic ensemble research. These are not implemented capabilities of 0.1.
