#!/usr/bin/env python3
"""Benchmark a selected, already-installed local model without touching forecast state."""

import argparse
import hashlib
import json
import platform
from pathlib import Path

from demandsense.ai import discover, explain
from demandsense.forecasting import analyze
from demandsense.generator import generate
from demandsense.schemas import AIRequest
from demandsense.storage import Repository


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runtime", choices=["none", "ollama", "openai-local"], default="none")
    p.add_argument("--model", default="")
    p.add_argument("--list", action="store_true")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--output", default="docs/benchmarks/local-ai.json")
    args = p.parse_args()
    if args.list:
        print(json.dumps(discover(), indent=2))
        return
    if not 1 <= args.repeats <= 20:
        raise SystemExit("repeats must be 1..20")
    run = {"id": "ai-benchmark-seed42", **analyze([r for r in generate(1) if r["location"] == "CHI"])}
    original = hashlib.sha256(json.dumps(run, sort_keys=True).encode()).hexdigest()
    repo = Repository("sqlite:///:memory:")
    repo.initialize()
    results = []
    for _ in range(args.repeats):
        output = explain(repo, run, AIRequest(runtime=args.runtime, model=args.model))
        assert original == hashlib.sha256(json.dumps(run, sort_keys=True).encode()).hexdigest()
        results.append(
            {
                "telemetry": output["telemetry"],
                "mode": output["mode"],
                "claims": len(output["narrative"]["claims"]),
                "abstained": output["narrative"]["abstained"],
                "deterministic_state_unchanged": True,
            }
        )
    data = {
        "hardware": platform.platform(),
        "python": platform.python_version(),
        "config": vars(args),
        "results": results,
        "limitation": "Schema and citation validation only; this is not a semantic faithfulness or model-quality benchmark.",
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
