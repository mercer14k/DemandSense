"""Small auditable forecasting engine. No database, HTTP, or LLM dependencies."""

import math
from datetime import date, timedelta

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

VERSION = "forecast-engine-1.0"
MODEL_NAMES = ("seasonal_naive", "seasonal_mean", "croston_sba", "tsb", "ridge", "ensemble")


def classify(y):
    y = np.asarray(y, dtype=float)
    positive = y[y > 0]
    if not len(positive):
        return {"class": "all_zero", "adi": None, "cv2": None, "zero_fraction": 1.0}
    adi = len(y) / len(positive)
    cv2 = float((positive.std() / positive.mean()) ** 2)
    label = (
        ("lumpy" if cv2 >= 0.49 else "intermittent")
        if adi >= 1.32
        else ("erratic" if cv2 >= 0.49 else "smooth")
    )
    return {
        "class": label,
        "adi": round(adi, 3),
        "cv2": round(cv2, 3),
        "zero_fraction": float(np.mean(y == 0)),
    }


def features(t, promo):
    t = np.asarray(t, dtype=float)
    return np.column_stack(
        [
            t / 365,
            np.sin(2 * np.pi * t / 7),
            np.cos(2 * np.pi * t / 7),
            np.sin(4 * np.pi * t / 7),
            np.cos(4 * np.pi * t / 7),
            promo,
        ]
    )


def predict_all(y, h, promo=None, future_promo=None):
    y = np.asarray(y, dtype=float)
    if len(y) < 14 or not np.isfinite(y).all() or (y < 0).any():
        raise ValueError("Need >=14 finite, nonnegative observations")
    if h < 1:
        raise ValueError("horizon must be positive")
    n = len(y)
    promo = np.zeros(n) if promo is None else np.asarray(promo, dtype=float)
    future_promo = np.zeros(h) if future_promo is None else np.asarray(future_promo, dtype=float)
    if len(promo) != n or len(future_promo) != h:
        raise ValueError("Promotion features must match the time axis")
    preds = {
        "seasonal_naive": np.array([y[n - 7 + i % 7] for i in range(h)]),
        "seasonal_mean": np.array(
            [np.mean(y[max(0, n - 56) :][np.arange(max(0, n - 56), n) % 7 == (n + i) % 7]) for i in range(h)]
        ),
    }
    positive = np.flatnonzero(y > 0)
    if not len(positive):
        preds["croston_sba"] = np.zeros(h)
        preds["tsb"] = np.zeros(h)
    else:
        alpha = 0.15
        z, interval, last = y[positive[0]], float(positive[0] + 1), int(positive[0])
        probability = 1 / interval
        for t in range(last + 1, n):
            probability += alpha * (float(y[t] > 0) - probability)
            if y[t] > 0:
                z += alpha * (y[t] - z)
                interval += alpha * ((t - last) - interval)
                last = t
        preds["croston_sba"] = np.full(h, (1 - alpha / 2) * z / interval)
        preds["tsb"] = np.full(h, probability * z)
    ridge = make_pipeline(StandardScaler(), Ridge(alpha=10))
    ridge.fit(features(np.arange(n), promo), y)
    preds["ridge"] = np.maximum(0, ridge.predict(features(np.arange(n, n + h), future_promo)))
    preds["ensemble"] = np.mean(np.stack(list(preds.values())), axis=0)
    return {k: np.maximum(0, np.asarray(v, dtype=float)) for k, v in preds.items()}


def finite_quantile(residuals, coverage):
    values = np.sort(np.asarray(residuals, dtype=float))
    if not len(values):
        raise ValueError("No calibration evidence")
    rank = min(len(values), math.ceil((len(values) + 1) * coverage))
    return float(values[rank - 1])


def metrics(actual, predicted, train, lower=None, upper=None):
    a, p, t = (np.asarray(x, dtype=float) for x in (actual, predicted, train))
    err = p - a
    denom = float(a.sum())
    scale = float(np.mean(np.abs(t[7:] - t[:-7]))) if len(t) > 7 else 0
    return {
        "wape": float(np.abs(err).sum() / denom) if denom else None,
        "mase": float(np.abs(err).mean() / scale) if scale > 1e-12 else None,
        "rmse": float(np.sqrt(np.mean(err**2))),
        "bias": float(err.sum() / denom) if denom else None,
        "mae": float(np.abs(err).mean()),
        "coverage_80": float(np.mean((a >= lower) & (a <= upper))) if lower is not None else None,
    }


def analyze(observations, horizon=14):
    """3 calibration origins then 3 untouched test origins; no shuffled time split."""
    if not 7 <= horizon <= 28:
        raise ValueError("horizon must be 7..28 days")
    rows = sorted(observations, key=lambda r: str(r["date"]))
    y = np.asarray([r["demand"] for r in rows], dtype=float)
    dates = [date.fromisoformat(str(r["date"])) for r in rows]
    if len(set(dates)) != len(dates) or any((b - a).days != 1 for a, b in zip(dates, dates[1:])):
        raise ValueError("Daily series has duplicate dates or gaps; repair explicitly before forecasting")
    if len(y) < 56 + 6 * horizon:
        raise ValueError(f"Need at least {56 + 6 * horizon} daily observations for this horizon")
    promo = np.asarray([r.get("promotion", False) for r in rows], dtype=float)
    first = len(y) - 6 * horizon
    residuals = {m: [] for m in MODEL_NAMES}
    calibration = []
    # Future promotion flags are scheduled exogenous inputs, never latent ground truth.
    for cut in range(first, first + 3 * horizon, horizon):
        preds = predict_all(y[:cut], horizon, promo[:cut], promo[cut : cut + horizon])
        for m, p in preds.items():
            residuals[m].extend(np.abs(y[cut : cut + horizon] - p).tolist())
        calibration.append({"train_end": str(dates[cut - 1]), "forecast_start": str(dates[cut])})
    selected = min(MODEL_NAMES, key=lambda m: float(np.mean(residuals[m])))
    radii = {
        m: {"80": finite_quantile(residuals[m], 0.8), "95": finite_quantile(residuals[m], 0.95)}
        for m in MODEL_NAMES
    }
    aggregate = {
        m: {"actual": [], "predicted": [], "lower": [], "upper": [], "low95": [], "up95": []}
        for m in MODEL_NAMES
    }
    origins, plot = [], []
    for cut in range(first + 3 * horizon, len(y), horizon):
        preds = predict_all(y[:cut], horizon, promo[:cut], promo[cut : cut + horizon])
        actual = y[cut : cut + horizon]
        origin = {"train_end": str(dates[cut - 1]), "start": str(dates[cut]), "models": {}}
        for m, p in preds.items():
            r80, r95 = radii[m]["80"], radii[m]["95"]
            lower, upper = np.maximum(0, p - r80), p + r80
            for k, vals in {
                "actual": actual,
                "predicted": p,
                "lower": lower,
                "upper": upper,
                "low95": np.maximum(0, p - r95),
                "up95": p + r95,
            }.items():
                aggregate[m][k].extend(vals.tolist())
            origin["models"][m] = metrics(actual, p, y[:cut], lower, upper)
            if m == selected:
                plot.extend(
                    {
                        "date": str(dates[cut + i]),
                        "actual": float(a),
                        "point": float(p[i]),
                        "lower80": float(lower[i]),
                        "upper80": float(upper[i]),
                    }
                    for i, a in enumerate(actual)
                )
        origins.append(origin)
    scores = []
    for m, a in aggregate.items():
        score = metrics(
            a["actual"], a["predicted"], y[: first + 3 * horizon], np.array(a["lower"]), np.array(a["upper"])
        )
        # Macro MASE uses each origin's training-only seasonal scale.
        scales = [o["models"][m]["mase"] for o in origins if o["models"][m]["mase"] is not None]
        score["mase"] = float(np.mean(scales)) if scales else None
        score["coverage_95"] = float(
            np.mean((np.array(a["actual"]) >= a["low95"]) & (np.array(a["actual"]) <= a["up95"]))
        )
        scores.append(
            {"model": m, "selected": m == selected, "selection_mae": float(np.mean(residuals[m])), **score}
        )
    forecasts = predict_all(y, horizon, promo)
    future = []
    for i, p in enumerate(forecasts[selected]):
        future.append(
            {
                "date": str(dates[-1] + timedelta(days=i + 1)),
                "point": float(p),
                "lower80": max(0.0, float(p - radii[selected]["80"])),
                "upper80": float(p + radii[selected]["80"]),
                "lower95": max(0.0, float(p - radii[selected]["95"])),
                "upper95": float(p + radii[selected]["95"]),
            }
        )
    chosen = next(s for s in scores if s["selected"])
    warnings = [
        "Intervals are marginal empirical calibration bands, not joint lead-time guarantees.",
        "Future baseline assumes no scheduled promotions. Scenario bands are conditional on the entered uplift.",
    ]
    if any(r.get("stockout", False) for r in rows):
        warnings.append("Stockout flags are present: observed sales may understate unconstrained demand.")
    if not np.any(y):
        warnings.append("All-zero history: zero-width bands cannot represent unseen demand arrivals.")
    evidence = [
        {
            "id": "E1",
            "label": "Model selection",
            "value": selected,
            "detail": "Lowest MAE on three pre-test calibration origins; frozen before evaluation.",
        },
        {
            "id": "E2",
            "label": "Held-out WAPE",
            "value": chosen["wape"],
            "detail": "Three untouched rolling origins.",
        },
        {
            "id": "E3",
            "label": "80% interval coverage",
            "value": chosen["coverage_80"],
            "detail": "Realized held-out marginal coverage.",
        },
        {
            "id": "E4",
            "label": "Demand class",
            "value": classify(y)["class"],
            "detail": "ADI and positive-demand CV² thresholds.",
        },
        {
            "id": "E5",
            "label": "Recent level change",
            "value": float(y[-28:].mean() - y[-56:-28].mean()),
            "detail": "Mean units/day, recent 28 days minus preceding 28 days. Association, not causation.",
        },
    ]
    return {
        "engine_version": VERSION,
        "selected_model": selected,
        "horizon": horizon,
        "classification": classify(y),
        "metrics": chosen,
        "leaderboard": sorted(scores, key=lambda s: s["selection_mae"]),
        "history": [
            {
                "date": str(d),
                "demand": float(a),
                "promotion": bool(p),
                "stockout": bool(r.get("stockout", False)),
            }
            for d, a, p, r in zip(dates, y, promo, rows)
        ],
        "forecast": future,
        "forecast_total": float(sum(p["point"] for p in future)),
        "backtest": plot,
        "origins": origins,
        "calibration_origins": calibration,
        "evidence": evidence,
        "warnings": warnings,
        "config": {
            "season_length": 7,
            "seed": 42,
            "calibration_origins": 3,
            "test_origins": 3,
            "ridge_alpha": 10,
            "croston_alpha": 0.15,
            "interval_method": "pooled_absolute_residual_order_statistic",
        },
    }


def apply_scenario(result, scenario):
    if scenario.end_day > result["horizon"]:
        raise ValueError("Scenario exceeds the forecast horizon")
    adjusted = []
    for i, row in enumerate(result["forecast"], 1):
        multiplier = 1 + scenario.uplift_pct / 100 if scenario.start_day <= i <= scenario.end_day else 1
        adjusted.append(
            {"date": row["date"], **{k: float(v * multiplier) for k, v in row.items() if k != "date"}}
        )
    baseline = sum(r["point"] for r in result["forecast"])
    total = sum(r["point"] for r in adjusted)
    return {
        "assumptions": scenario.model_dump(),
        "forecast": adjusted,
        "baseline_total": baseline,
        "scenario_total": total,
        "delta_units": total - baseline,
        "interval_note": "Conditional scale transformation. Does not include uncertainty in assumed uplift; not causally estimated.",
    }
