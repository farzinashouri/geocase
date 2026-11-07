#!/usr/bin/env python3
"""Build a private sandbox holding ``geocase`` for read-only exploring (Plan 56).

Standard library only; never imports ``geocase``.

    sandbox.py status
    sandbox.py create [--upgrade]

Both print one JSON object: ``exists``, ``python``, ``geocase_version``.
``create`` runs ``<this python> -m venv <sandbox>`` then
``<sandbox python> -m pip install geocase``; a second run does nothing.
``GEOCASE_SANDBOX_SPEC`` overrides the pip requirement (tests install from the
checkout so CI does not need PyPI).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def sandbox_dir(env: Mapping[str, str], home: Path | None = None) -> Path:
    data = env.get("CLAUDE_PLUGIN_DATA")
    if data:
        return Path(data) / "sandbox"
    return (home or Path.home()) / ".cache" / "geocase-claude-plugin" / "sandbox"


def sandbox_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _version(python: Path) -> str | None:
    if not python.is_file():
        return None
    code = "import importlib.metadata as m; print(m.version('geocase'))"
    proc = subprocess.run(
        [str(python), "-c", code], capture_output=True, text=True, check=False
    )
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def status(env: Mapping[str, str]) -> dict[str, Any]:
    python = sandbox_python(sandbox_dir(env))
    version = _version(python)
    return {
        "exists": version is not None,
        "python": str(python),
        "geocase_version": version,
    }


def _check(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(proc.returncode)


def create(env: Mapping[str, str], upgrade: bool = False) -> dict[str, Any]:
    root = sandbox_dir(env)
    python = sandbox_python(root)
    current = status(env)
    if current["exists"] and not upgrade:
        return current
    if not python.is_file():
        root.parent.mkdir(parents=True, exist_ok=True)
        _check([sys.executable, "-m", "venv", str(root)])
    spec = env.get("GEOCASE_SANDBOX_SPEC") or "geocase"
    cmd = [str(python), "-m", "pip", "install", "--quiet"]
    if upgrade:
        cmd += ["--upgrade", "--force-reinstall"]
    _check([*cmd, spec])
    return status(env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    make = commands.add_parser("create")
    make.add_argument("--upgrade", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "status":
        result = status(os.environ)
    else:
        result = create(os.environ, upgrade=args.upgrade)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
