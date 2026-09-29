# Evaluation methodology

Run from the repository root after native installation:

```sh
python scripts/benchmark.py --skus 500 --days 196 --seed 42 --horizon 14
```

Outputs are JSON metadata/summary, aggregate CSV, per-series CSV, and Markdown under `docs/benchmarks/example`. Use another `--output` directory to preserve the committed example. A large workload is `python scripts/performance.py --skus 5000 --days 365 --output data/generated/performance`.

## Time split

For n observations and horizon h, the first origin is n−6h. A minimum 56-day initial training history is required. Three non-overlapping forecast windows calibrate absolute residuals and select the smallest MAE candidate. The winner is frozen. The next three windows are held out, with an expanding training set for every origin. Later test observations can train a later origin but never an earlier one. Final operational predictions refit on all available observations.

Candidates are seasonal naïve (period 7), trailing eight-week weekday mean, Croston-SBA (alpha .15), TSB (alpha .15 for both processes), standardized ridge regression (alpha 10), and a fixed equal-weight ensemble of the five. Ridge features are linear time, two weekly Fourier harmonics, and promotion flags. Historical future promotion flags are treated as scheduled features known at the forecast origin. Real datasets must preserve that knowledge-time assumption; retrospective campaign labels can leak information.

There is no automatic tuning on held-out scores. The ensemble's equal weights are fixed before evaluation. Model selection uses MAE, rather than WAPE with an unstable denominator on zero-demand windows. The primary UI may rank a selected model ahead of a better test performer, correctly, because selection is pre-test.

## Intervals

For each model, pool absolute errors from 3h calibration predictions. For nominal coverage c, use sorted residual rank min(m, ceil((m+1)c)). Bands are max(0, point−radius) and point+radius at 80% and 95%. The same pre-test radius is used for all held-out origins and final predictions.

These are **empirical marginal calibration bands**, not a fully specified predictive distribution. Time dependence, pooled lead times, distribution shifts, and selecting a winner using the same calibration windows prevent a general exchangeability-based coverage guarantee. Clipping at zero further changes symmetry. Coverage is measured and displayed; low coverage is not hidden. All-zero series produce zero-width bands and carry an explicit unseen-arrival warning. No daily band should be summed into a lead-time service-level quantile.

## Metrics

- **WAPE**: sum(abs(prediction−actual)) / sum(actual). Undefined when total actual demand is zero.
- **MASE**: mean absolute error divided by mean abs(y[t]−y[t−7]) from that origin's training history. Undefined for zero seasonal scale. Per-series MASE averages defined origins; aggregate MASE averages defined series and reports the denominator.
- **RMSE**: sqrt(mean((prediction−actual)²)).
- **Bias**: sum(prediction−actual) / sum(actual). Positive means overforecasting; undefined at zero actual volume.
- **Interval coverage**: fraction of actuals within inclusive bounds, at both levels.
- **Demand class**: ADI n/nonzero_count and positive-size CV², with thresholds 1.32 and .49; all-zero history receives its own class. Classes are descriptive over the available full series, not inputs to winner selection.

Aggregate WAPE/bias are volume-weighted. RMSE and coverage pool observations. Class performance and undefined metrics remain visible. Intermittent demand can have WAPE above 100% even with a sensible expected-demand forecast; evaluate inventory decisions separately before operational adoption.

## Reproducibility and limits

The generator has fixed seeds and stable per-series streams. Forecasts are deterministic for pinned libraries; no claim of bit-identical cross-platform floating point is made. Timing includes generation and all forecast/evaluation loops but excludes imports, database I/O, HTTP, and artifact writes. Peak RSS is process high-water memory, not incremental model allocation; it is unavailable on some Windows environments. CPU, platform, Python, package versions, dataset size, and configuration accompany results.

The benchmark is synthetic, with a known generating process that favors models matching weekly harmonics and promotions. It is not a retail production dataset and does not prove improved availability, working capital, or real-world ROI. A global ridge model can beat the automatic selection policy; that result is published. The evaluation should guide hypotheses, not marketing claims.

References: [rolling-origin evaluation](https://otexts.com/fpp3/tscv.html), [forecast accuracy](https://otexts.com/fpp3/accuracy.html), [distributional accuracy](https://otexts.com/fpp3/distaccuracy.html).
