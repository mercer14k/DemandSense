#!/usr/bin/env python3
"""Start the native app using installed dependencies; never installs or downloads models."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
if (root / ".env").exists():
    for line in (root / ".env").read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
node = shutil.which("node")
if not node or not (root / "apps/web/node_modules/vite/bin/vite.js").exists():
    raise SystemExit("Install Node.js 24 LTS and run 'pnpm install' in apps/web first. See README.")
commands = [
    ([sys.executable, "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", "8027"], root),
    (
        [node, "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5187", "--strictPort"],
        root / "apps/web",
    ),
]
processes = []
try:
    for command, cwd in commands:
        processes.append(subprocess.Popen(command, cwd=cwd))
    print("DemandSense: http://127.0.0.1:5187  |  API: http://127.0.0.1:8027/docs", flush=True)
    while all(p.poll() is None for p in processes):
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
