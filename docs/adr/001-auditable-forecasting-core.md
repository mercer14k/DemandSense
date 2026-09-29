# ADR 001 — NumPy and scikit-learn for the first forecasting core

Status: accepted for 0.1.

StatsForecast and MLForecast are strong options for a broader model zoo and high-throughput panels. This release instead implements a small, auditable set of statistical methods in NumPy and uses scikit-learn for ridge regression. The choice keeps the selected-model/calibration/test chronology explicit, limits compiler/runtime dependencies, supports native macOS/Windows development, and makes edge-case tests easy to inspect.

Tradeoffs: no AutoARIMA/ETS optimizer, no global tree model, no optimized panel fitting, no hierarchical reconciliation, and no validated probabilistic sampling distribution. We do not claim equivalent functionality to StatsForecast or MLForecast. The model adapter is `predict_all`; a future library backend must preserve its training-only inputs and pass the leakage/zero-demand tests before comparison.
