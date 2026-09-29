#!/usr/bin/env python3
"""Record installed package metadata, not a substitute for reviewing upstream licenses."""

import importlib.metadata as metadata
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
python = []
for dist in metadata.distributions():
    m = dist.metadata
    if m.get("Name", "").lower() in {"demandsense", "pip", "setuptools"}:
        continue
    classifiers = [s.split(" :: ")[-1] for s in m.get_all("Classifier", []) if s.startswith("License ::")]
    license_text = (
        m.get("License-Expression") or (", ".join(classifiers)) or m.get("License") or "Review upstream"
    )
    python.append(
        {
            "name": m["Name"],
            "version": dist.version,
            "license_metadata": license_text[:500],
            "source": "installed distribution metadata",
        }
    )
javascript = []
root_package = ROOT / "apps/web/package.json"
root_data = json.loads(root_package.read_text())
pending = [
    (root_package.parent, name)
    for category in ("dependencies", "devDependencies")
    for name in root_data.get(category, {})
]
visited = set()
while pending:
    base, name = pending.pop()
    target = next(
        (
            folder / "node_modules" / name / "package.json"
            for folder in [base, *base.parents]
            if (folder / "node_modules" / name / "package.json").is_file()
        ),
        None,
    )
    if target is None:
        continue
    target = target.resolve()
    if target in visited:
        continue
    visited.add(target)
    data = json.loads(target.read_text())
    javascript.append(
        {
            "name": data["name"],
            "version": data["version"],
            "license_metadata": data.get("license", "Review upstream"),
        }
    )
    for category in ("dependencies", "optionalDependencies", "peerDependencies"):
        pending.extend((target.parent, child) for child in data.get(category, {}))
unique = {f"{p['name']}@{p['version']}": p for p in javascript}
result = {
    "note": "Build-host inventory. Platform-specific optional packages may differ in Linux containers. Upstream notices remain authoritative.",
    "python": sorted(python, key=lambda p: p["name"].lower()),
    "javascript": sorted(unique.values(), key=lambda p: p["name"].lower()),
}
(ROOT / "docs/dependency-inventory.json").write_text(json.dumps(result, indent=2) + "\n")
print(f"Recorded {len(python)} Python and {len(unique)} JavaScript distributions")
