"""Phase 1 port pin: the refactored graders change no expected value.

Grades the committed Step 0 modules through the new CLI and asserts every
(op, check) status matches the committed ``agent_baseline/results.json``.
"""

import json
import subprocess
import sys
from pathlib import Path

BASELINE = Path(__file__).parent / "agent_baseline"


def test_cli_reproduces_committed_step0_results(tmp_path):
    out = tmp_path / "results.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "geocase.benchmark",
            "grade",
            "--generated",
            str(BASELINE / "generated"),
            "--json",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    got = {(r["op"], r["check"]): r["status"] for r in json.loads(out.read_text())}
    committed = {
        (r["op"], r["check"]): r["status"]
        for r in json.loads((BASELINE / "results.json").read_text())
    }
    # The new registry also grades plan15 tasks (MISSING here); compare only
    # the step0 keys, which must match the committed run exactly.
    assert {k: v for k, v in got.items() if k in committed} == committed
