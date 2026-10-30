#!/usr/bin/env python3
"""Formatea el archivo editado con ruff (Python) o prettier (TS/JS/CSS)."""
import json
import subprocess
import sys
from pathlib import Path

data = json.load(sys.stdin)
file_path = data.get("tool_input", {}).get("file_path", "")

if not file_path:
    sys.exit(0)

path = Path(file_path)
if not path.exists() or path.is_dir():
    sys.exit(0)

try:
    if path.suffix == ".py":
        subprocess.run(["ruff", "format", str(path)], check=False)
        subprocess.run(["ruff", "check", "--fix", str(path)], check=False)
    elif path.suffix in {".ts", ".tsx", ".js", ".jsx", ".css", ".json"}:
        subprocess.run(
            ["npx", "--prefix", "frontend", "prettier", "--write", str(path)],
            check=False,
        )
except FileNotFoundError:
    pass  # formatter not installed yet; skip silently
