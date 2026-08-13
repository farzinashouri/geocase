"""Pin the Step 0 grading outcome (Plan 14).

Re-grades the committed agent-generated modules against the inline oracles and
asserts the result matches the committed ``results.json``. This is a
reproducibility pin, not a quality gate: the recorded outcome *includes* the
``buffer_m`` silent failure, and a drift in either direction (a failure
disappearing or a new one appearing) means the graded artifacts or the oracles
changed and the results table must be regenerated deliberately.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def test_grading_matches_committed_results(tmp_path):
    out = tmp_path / "results.json"
    subprocess.run(
        [sys.executable, str(HERE / "grade.py"), "--json", str(out)],
        check=True,
        capture_output=True,
    )
    got = {(r["op"], r["check"]): r["status"] for r in json.loads(out.read_text())}
    committed = {
        (r["op"], r["check"]): r["status"]
        for r in json.loads((HERE / "results.json").read_text())
    }
    assert got == committed
