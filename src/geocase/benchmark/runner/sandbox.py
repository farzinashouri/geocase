"""Soft sandboxing for model-generated code (Plan 15, trap 5).

One venv per run from ``configs/sandbox-requirements.txt`` (pinned to the
Step 0 environment), fresh temp workdir per task, subprocess with a timeout,
environment scrubbed of ``*_KEY``/``*_TOKEN``. This is *soft* isolation; the
methodology docs must say so and offer a ``docker run --network none`` recipe
for stronger isolation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
REQUIREMENTS = REPO_ROOT / "configs" / "sandbox-requirements.txt"


def scrubbed_env(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    return {
        k: v for k, v in env.items() if not (k.endswith("_KEY") or k.endswith("_TOKEN"))
    }


def ensure_sandbox(run_dir: Path, requirements: Path = REQUIREMENTS) -> Path:
    """Create (or reuse) the run's venv; returns its python executable."""
    venv = run_dir / "venv"
    python = venv / "bin" / "python"
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        subprocess.run(
            [str(python), "-m", "pip", "install", "-q", "-r", str(requirements)],
            check=True,
        )
    return python


def run_python(
    code_path: Path,
    *,
    python: Path,
    cwd: Path,
    timeout_s: float = 60.0,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(python), str(code_path)],
        cwd=cwd,
        env=scrubbed_env(),
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
