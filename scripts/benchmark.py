#!/usr/bin/env python3
"""Reproducible sequential evaluation, including generation time and process peak RSS."""

import argparse
import csv
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path

from demandsense.forecasting import VERSION, analyze
from demandsense.generator import generate


def aggregate(rows):
    out = []
    for key, group in groupby(
        sorted(rows, key=lambda r: (r["group"], r["model"])), key=lambda r: (r["group"], r["model"])
    ):
        group = list(group)
        actual = sum(r["actual_total"] for r in group)
        n = sum(r["test_points"] for r in group)
        mase = [r["mase"] for r in group if r["mase"] is not None]
        out.append(
            {
                "class": key[0],
                "model": key[1],
                "series": len(group),
                "test_points": n,
                "wape": sum(r["mae"] * r["test_points"] for r in group) / actual if actual else None,
                "mase": sum(mase) / len(mase) if mase else None,
                "mase_defined_series": len(mase),
                "rmse": math.sqrt(sum(r["rmse"] ** 2 * r["test_points"] for r in group) / n),
                "bias": sum((r["bias"] or 0) * r["actual_total"] for r in group) / actual if actual else None,
                "coverage_80": sum(r["coverage_80"] * r["test_points"] for r in group) / n,
                "coverage_95": sum(r["coverage_95"] * r["test_points"] for r in group) / n,
            }
        )
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--skus", type=int, default=500)
    p.add_argument("--days", type=int, default=196)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--horizon", type=int, default=14)
    p.add_argument("--output", default="docs/benchmarks/example")
    args = p.parse_args()
    start = time.perf_counter()
    rows, counts, total = [], defaultdict(int), 0
    for (sku, location), stream in groupby(
        generate(args.skus, args.days, args.seed), key=lambda r: (r["sku"], r["location"])
    ):
        records = list(stream)
        result = analyze(records, args.horizon)
        total += len(records)
        counts[result["selected_model"]] += 1
        actual = sum(r["actual"] for r in result["backtest"])
        cls = result["classification"]["class"]
        for score in [*result["leaderboard"], {**result["metrics"], "model": "selected_policy"}]:
            for group in ("all", cls):
                rows.append(
                    {
                        "sku": sku,
                        "location": location,
                        "group": group,
                        "test_points": args.horizon * 3,
                        "actual_total": actual,
                        **score,
                    }
                )
    elapsed = time.perf_counter() - start
    peak = None
    try:
        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak = rss / (1024**2 if sys.platform == "darwin" else 1024)
    except ImportError:
        pass
    cpu = platform.processor() or platform.machine()
    if sys.platform == "darwin":
        try:
            cpu = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            cpu += " (CPU brand unavailable)"
    summary = aggregate(rows)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": VERSION,
        "hardware": {
            "os": platform.platform(),
            "cpu": cpu,
            "logical_cpus": os.cpu_count(),
            "machine": platform.machine(),
        },
        "python": platform.python_version(),
        "dependencies": {d: importlib.metadata.version(d) for d in ("numpy", "scikit-learn", "scipy")},
        "config": vars(args),
        "dataset_records": total,
        "series": args.skus * 3,
        "runtime_seconds": elapsed,
        "peak_process_rss_mib": peak,
        "llm": "disabled",
        "selected_model_counts": dict(counts),
        "timing_scope": "Synthetic generation, model fitting, calibration, evaluation; excludes interpreter/library imports and artifact writes.",
        "metric_aggregation": "WAPE and bias volume-weighted; RMSE observation-weighted; MASE macro over defined series; coverage pooled.",
    }
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=True)
    (target / "results.json").write_text(
        json.dumps({"metadata": metadata, "summary": summary}, indent=2, allow_nan=False) + "\n"
    )
    with (target / "metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)
    with (target / "per-series.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows([r for r in rows if r["group"] == "all"])

    def fmt(v):
        return "undefined" if v is None else f"{v:.3f}"

    lines = [
        "# Measured synthetic benchmark",
        "",
        f"Measured {metadata['generated_at']}. Engine `{VERSION}`. LLM disabled.",
        "",
        f"Hardware: **{cpu}**, {metadata['hardware']['os']}, Python {metadata['python']}.",
        f"Dataset: **{args.skus} SKUs × 3 locations × {args.days} days = {total:,} observations**; seed {args.seed}.",
        f"Wall time: **{elapsed:.2f} seconds**. Peak process RSS: **{peak:.1f} MiB**."
        if peak
        else f"Wall time: {elapsed:.2f} seconds; RSS unavailable.",
        "",
        "Three calibration origins select each series' model. Three later origins are held out. Percentages below are proportions. Synthetic results do not establish real-world accuracy.",
        "",
        "| Model | WAPE | MASE | RMSE | Bias | 80% coverage | 95% coverage |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        if r["class"] == "all":
            lines.append(
                f"| {r['model']} | "
                + " | ".join(
                    fmt(r[k]) for k in ("wape", "mase", "rmse", "bias", "coverage_80", "coverage_95")
                )
                + " |"
            )
    lines += [
        "",
        "## Selected policy by demand class",
        "",
        "| Class | Series | WAPE | MASE | 80% coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in summary:
        if r["model"] == "selected_policy" and r["class"] != "all":
            lines.append(
                f"| {r['class']} | {r['series']} | {fmt(r['wape'])} | {fmt(r['mase'])} | {fmt(r['coverage_80'])} |"
            )
    lines += [
        "",
        metadata["timing_scope"],
        "",
        metadata["metric_aggregation"],
        "",
        "Intervals use absolute errors pooled across forecast leads. Time dependence and regime shifts invalidate a blanket finite-sample coverage guarantee. All-zero history produces zero bands and is separately reported.",
        "",
    ]
    (target / "summary.md").write_text("\n".join(lines))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
