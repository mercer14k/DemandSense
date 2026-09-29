# Measured synthetic benchmark

Measured 2026-09-28T03:47:00.964195+00:00. Engine `forecast-engine-1.0`. LLM disabled.

Hardware: **Apple M5**, macOS-26.6.2-arm64-arm-64bit, Python 3.12.14.
Dataset: **500 SKUs × 3 locations × 196 days = 294,000 observations**; seed 42.
Wall time: **6.98 seconds**. Peak process RSS: **131.8 MiB**.

Three calibration origins select each series' model. Three later origins are held out. Percentages below are proportions. Synthetic results do not establish real-world accuracy.

| Model | WAPE | MASE | RMSE | Bias | 80% coverage | 95% coverage |
|---|---:|---:|---:|---:|---:|---:|
| croston_sba | 0.576 | 1.077 | 96.268 | -0.104 | 0.777 | 0.936 |
| ensemble | 0.533 | 0.871 | 96.797 | -0.041 | 0.796 | 0.935 |
| ridge | 0.480 | 0.678 | 93.793 | -0.012 | 0.806 | 0.948 |
| seasonal_mean | 0.530 | 0.849 | 97.698 | -0.034 | 0.810 | 0.937 |
| seasonal_naive | 0.642 | 1.085 | 131.707 | -0.011 | 0.795 | 0.923 |
| selected_policy | 0.491 | 0.693 | 99.922 | -0.018 | 0.776 | 0.943 |
| tsb | 0.578 | 1.056 | 96.920 | -0.045 | 0.767 | 0.936 |

## Selected policy by demand class

| Class | Series | WAPE | MASE | 80% coverage |
|---|---:|---:|---:|---:|
| all_zero | 3 | undefined | undefined | 1.000 |
| intermittent | 300 | 1.664 | 1.003 | 0.780 |
| lumpy | 300 | 1.384 | 0.903 | 0.725 |
| smooth | 897 | 0.103 | 0.519 | 0.791 |

Synthetic generation, model fitting, calibration, evaluation; excludes interpreter/library imports and artifact writes.

WAPE and bias volume-weighted; RMSE observation-weighted; MASE macro over defined series; coverage pooled.

Intervals use absolute errors pooled across forecast leads. Time dependence and regime shifts invalidate a blanket finite-sample coverage guarantee. All-zero history produces zero bands and is separately reported.
