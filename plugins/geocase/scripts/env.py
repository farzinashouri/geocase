#!/usr/bin/env python3
"""Detect how the user's project manages its Python environment (Plan 56).

Standard library only; reads env vars and files, never installs anything.

    env.py detect [--version V] [--project DIR]

prints one JSON object: ``manager``, ``python``, ``installable``, ``command``,
``reason``, ``edits_manifest``. Exit 0 always: "not installable" is a result.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import sysconfig
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _pin(version: str | None) -> str:
    return f"geocase=={version}" if version else "geocase"


def _is_pixi(env: Mapping[str, str], project: Path) -> bool:
    if env.get("PIXI_PROJECT_MANIFEST") or (project / "pixi.toml").is_file():
        return True
    pyproject = project / "pyproject.toml"
    if pyproject.is_file():
        try:
            return "[tool.pixi" in pyproject.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
    return False


def _result(
    manager: str | None,
    python: str,
    command: str | None,
    reason: str | None = None,
    edits_manifest: bool = False,
) -> dict[str, Any]:
    return {
        "manager": manager,
        "python": python,
        "installable": command is not None,
        "command": command,
        "reason": reason,
        "edits_manifest": edits_manifest,
    }


def detect(
    *,
    env: Mapping[str, str],
    project: Path,
    version: str | None,
    python: str,
    prefix: str,
    base_prefix: str,
    stdlib: Path,
) -> dict[str, Any]:
    pin = _pin(version)
    pip = f"{python} -m pip install {pin}"
    in_venv = prefix != base_prefix

    if _is_pixi(env, project):
        return _result("pixi", python, f"pixi add --pypi {pin}", edits_manifest=True)
    if (project / "uv.lock").is_file():
        return _result("uv", python, f"uv add --dev {pin}", edits_manifest=True)
    if (project / "poetry.lock").is_file():
        return _result(
            "poetry", python, f"poetry add --group dev {pin}", edits_manifest=True
        )
    if env.get("CONDA_PREFIX") and not in_venv:
        name = env.get("CONDA_DEFAULT_ENV") or Path(env["CONDA_PREFIX"]).name
        if name == "base":
            return _result(
                None,
                python,
                None,
                "The active environment is conda 'base'; installing into it can "
                "break conda. Create or activate another environment first.",
            )
        return _result("conda", python, pip)
    if in_venv:
        return _result("venv", python, pip)
    if (stdlib / "EXTERNALLY-MANAGED").is_file():
        return _result(
            None,
            python,
            None,
            "This Python is marked EXTERNALLY-MANAGED (PEP 668, a system "
            "Python). Create or activate a virtual environment first.",
        )
    return _result("pip", python, pip)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect", help="print the environment as JSON")
    d.add_argument("--version", default=None)
    d.add_argument("--project", default=".")
    args = parser.parse_args(argv)
    result = detect(
        env=os.environ,
        project=Path(args.project),
        version=args.version,
        python=sys.executable,
        prefix=sys.prefix,
        base_prefix=sys.base_prefix,
        stdlib=Path(sysconfig.get_path("stdlib")),
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
