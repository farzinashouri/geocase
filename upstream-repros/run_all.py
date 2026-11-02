"""Run every repro in this folder and print one line per finding.

    python run_all.py                 # all of them
    python run_all.py gdal pyogrio    # only these library folders

Each repro prints a line starting with ``RESULT:``:

    RESULT: REPRODUCED          the defect is still there in this environment
    RESULT: did not reproduce   the defect is gone (fixed, or a different version)
    RESULT: SKIPPED (reason)    the environment cannot exercise this repro

A script that prints neither (for example, a missing import) is reported as
ERROR with the last line of its output. Each script runs in its own process,
from its own folder, with ``python -I`` so nothing on the current path leaks in.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TIMEOUT_S = 300


def run(script: Path) -> tuple[str, str]:
    try:
        proc = subprocess.run(
            [sys.executable, "-I", script.name],
            cwd=script.parent,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return "ERROR", f"timed out after {TIMEOUT_S}s"
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT:"):
            verdict = line.removeprefix("RESULT:").strip()
            if verdict == "REPRODUCED":
                return "REPRODUCED", ""
            if verdict.startswith("SKIPPED"):
                return "SKIPPED", verdict.removeprefix("SKIPPED").strip(" ()")
            return "not reproduced", ""
    tail = (proc.stderr or proc.stdout).strip().splitlines()
    return "ERROR", tail[-1] if tail else f"exit code {proc.returncode}"


def main(argv: list[str]) -> int:
    folders = argv or sorted(p.name for p in HERE.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))
    counts: dict[str, int] = {}
    for folder in folders:
        for script in sorted((HERE / folder).glob("repro_*.py")):
            status, detail = run(script)
            counts[status] = counts.get(status, 0) + 1
            name = f"{folder}/{script.name}"
            print(f"{status:<15} {name}" + (f"   ({detail})" if detail else ""), flush=True)
    print("\n" + ", ".join(f"{n} {s}" for s, n in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
