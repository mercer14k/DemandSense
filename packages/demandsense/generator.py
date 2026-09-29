"""Seeded synthetic daily demand. Latent expectations are evaluation-only."""

import argparse
import csv
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

GENERATOR_VERSION = "synthetic-1.0"
LOCATIONS = ("CHI", "DAL", "SEA")


def generate(skus=500, days=196, seed=42, locations=LOCATIONS):
    if skus < 1 or days < 28 or skus > 100_000:
        raise ValueError("skus must be 1..100000; days must be >=28")
    dataset = f"demo-v1-seed{seed}"
    start = date(2025, 1, 6)
    for s in range(skus):
        for li, location in enumerate(locations):
            rng = np.random.default_rng(np.random.SeedSequence([seed, s, li]))
            family = ("regular", "seasonal", "intermittent", "lumpy", "trending")[s % 5]
            level = 12 + (s % 73) * 1.3 + li * 7
            for t in range(days):
                promotion = (t + s * 3) % 63 in range(7, 14)
                seasonal = 1 + (0.48 if family == "seasonal" else 0.12) * np.sin(2 * np.pi * t / 7)
                trend = 1 + (0.004 * t if family == "trending" else 0)
                shock = 0.58 if s % 17 == 0 and days - 45 <= t < days - 31 else 1.0
                expected = max(0, level * seasonal * trend * (1.65 if promotion else 1) * shock)
                occurrence = 0.19 if family == "intermittent" else 0.36 if family == "lumpy" else 1
                amount = float(rng.poisson(expected)) if rng.random() < occurrence else 0.0
                if family == "lumpy" and amount:
                    amount *= float(rng.choice([1, 2, 8]))
                stockout = s % 29 == 0 and t in (60, 61)
                if stockout or s == 499:
                    amount = 0.0
                day = (start + timedelta(days=t)).isoformat()
                rid = hashlib.sha256(f"{dataset}|SKU-{s + 1:04d}|{location}|{day}".encode()).hexdigest()[:24]
                yield {
                    "record_id": rid,
                    "dataset_id": dataset,
                    "sku": f"SKU-{s + 1:04d}",
                    "location": location,
                    "date": day,
                    "demand": amount,
                    "promotion": promotion,
                    "stockout": stockout,
                    # Fixed logical source time makes fixture byte-for-byte reproducible.
                    "ingested_at": "2025-07-21T00:00:00+00:00",
                    "validation_status": "warning" if stockout else "valid",
                    "provenance": {
                        "generator": GENERATOR_VERSION,
                        "seed": seed,
                        "family": family,
                        "expected_uncensored": round(
                            (0 if s == 499 else expected) * occurrence * (11 / 3 if family == "lumpy" else 1),
                            4,
                        ),
                        "shock_multiplier": shock,
                    },
                }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--skus", type=int, default=500)
    p.add_argument("--days", type=int, default=196)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dataset-id", default=None)
    p.add_argument("--output", default="data/generated/demand.csv")
    args = p.parse_args()
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with target.open("w", newline="") as f:
        writer = None
        for row in generate(args.skus, args.days, args.seed):
            if args.dataset_id:
                row["dataset_id"] = args.dataset_id
                row["record_id"] = hashlib.sha256(
                    f"{args.dataset_id}|{row['sku']}|{row['location']}|{row['date']}".encode()
                ).hexdigest()[:24]
            row["provenance"] = json.dumps(row["provenance"], sort_keys=True)
            if writer is None:
                writer = csv.DictWriter(f, fieldnames=list(row), lineterminator="\n")
                writer.writeheader()
            writer.writerow(row)
            count += 1
    print(
        json.dumps(
            {
                "path": str(target),
                "records": count,
                "seed": args.seed,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    )


if __name__ == "__main__":
    main()
