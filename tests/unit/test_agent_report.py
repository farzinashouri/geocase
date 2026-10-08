"""`scripts/agent_run_report.py` (Plan 52 Phase 1, issue #83).

The report turns a claude-code-action execution file (a JSON list of messages
ending in a `result` object) into a Markdown verdict, so a run that failed or
was blocked is visible without opening the Actions log.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "agent_run_report", ROOT / "scripts" / "agent_run_report.py"
)
assert spec and spec.loader
report = importlib.util.module_from_spec(spec)
sys.modules["agent_run_report"] = report
spec.loader.exec_module(report)


def _result(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "num_turns": 40,
        "duration_ms": 125000,
        "total_cost_usd": 1.5,
        "permission_denials": [],
        "result": "Opened PR #90.",
    }
    base.update(over)
    return base


def _log(tmp_path: Path, result: dict[str, Any] | None) -> Path:
    msgs: list[dict[str, Any]] = [{"type": "system", "subtype": "init"}]
    if result is not None:
        msgs.append(result)
    path = tmp_path / "exec.json"
    path.write_text(json.dumps(msgs))
    return path


def _run(path: Path, outcome: str = "success", max_turns: int = 250) -> Any:
    return report.build_report(
        report.load_result(path), outcome=outcome, max_turns=max_turns
    )


def test_extracts_the_result_fields(tmp_path: Path) -> None:
    rep = _run(_log(tmp_path, _result()))
    assert rep.turns == 40
    assert rep.duration_s == 125
    assert rep.cost == 1.5
    assert rep.final_text == "Opened PR #90."
    assert rep.healthy


def test_healthy_header(tmp_path: Path) -> None:
    md = report.render(_run(_log(tmp_path, _result())), run_url="u", mode="full")
    assert md.splitlines()[0].startswith("✅ healthy")
    assert "Opened PR #90." in md


def test_permission_denials_are_listed_and_unhealthy(tmp_path: Path) -> None:
    denial = {"tool_name": "Bash", "tool_input": {"command": "curl x"}}
    rep = _run(_log(tmp_path, _result(permission_denials=[denial])))
    md = report.render(rep, run_url="u", mode="full")
    assert not rep.healthy
    assert md.splitlines()[0].startswith("⚠️ needs attention")
    assert "Bash" in md and "curl x" in md


@pytest.mark.parametrize(
    "over, reason",
    [
        ({"is_error": True}, "is_error"),
        ({"num_turns": 250}, "turn cap"),
    ],
)
def test_unhealthy_reasons(tmp_path: Path, over: dict[str, Any], reason: str) -> None:
    rep = _run(_log(tmp_path, _result(**over)))
    assert not rep.healthy
    assert any(reason in r for r in rep.reasons)


def test_no_result_object_is_unhealthy(tmp_path: Path) -> None:
    rep = _run(_log(tmp_path, None))
    assert not rep.healthy
    assert any("no result" in r for r in rep.reasons)


def test_missing_file_is_unhealthy(tmp_path: Path) -> None:
    assert report.load_result(tmp_path / "absent.json") is None
    assert not _run(tmp_path / "absent.json").healthy


def test_failed_action_step_is_unhealthy(tmp_path: Path) -> None:
    rep = _run(_log(tmp_path, _result()), outcome="failure")
    assert not rep.healthy
    assert any("step" in r for r in rep.reasons)


def test_main_writes_github_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    code = report.main(
        [
            "--execution-file",
            str(_log(tmp_path, _result())),
            "--outcome",
            "success",
            "--run-url",
            "https://example/run/1",
            "--mode",
            "full",
            "--max-turns",
            "250",
        ]
    )
    assert code == 0
    assert "healthy=true" in out.read_text()
    assert "https://example/run/1" in capsys.readouterr().out


def _issue(number: int, comment: str) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Issue {number}",
        "url": f"https://github.com/o/r/issues/{number}",
        "comments": [{"body": "older"}, {"body": comment}],
    }


def test_needs_human_lines_quote_the_last_comment() -> None:
    lines = report.needs_human_lines(
        [_issue(67, "@farzinashouri Should I drop Qwen?\n\nDetails below.")]
    )
    assert lines == [
        "- [#67](https://github.com/o/r/issues/67) Issue 67: Should I drop Qwen?"
    ]


def test_needs_human_lines_without_comments() -> None:
    issue = _issue(5, "x")
    issue["comments"] = []
    assert report.needs_human_lines([issue]) == [
        "- [#5](https://github.com/o/r/issues/5) Issue 5"
    ]


def test_needs_you_section_is_rendered() -> None:
    rep = report.build_report(_result(), outcome="success", max_turns=250)
    md = report.render(
        rep, run_url="u", mode="triage", needs_human=["- [#67](x) Issue 67: q?"]
    )
    assert "**Needs you**" in md
    assert "- [#67](x) Issue 67: q?" in md
    assert md.index("**Needs you**") < md.index("**Final message**")
    assert "Needs you" in md.splitlines()[0]


def _pr(number: int, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "number": number,
        "headRefName": f"agent/{number}-x",
        "statusCheckRollup": checks,
    }


def _check(name: str, conclusion: str, status: str = "COMPLETED") -> dict[str, Any]:
    return {"name": name, "conclusion": conclusion, "status": status}


def test_red_pr_lines_name_the_failing_check() -> None:
    prs = [
        _pr(91, [_check("lint", "SUCCESS"), _check("catalog", "FAILURE")]),
        _pr(92, [_check("lint", "SUCCESS")]),
    ]
    lines = report.red_pr_lines(prs)
    assert len(lines) == 1
    assert "#91" in lines[0] and "catalog" in lines[0]


def test_red_pr_lines_flag_a_pr_without_checks() -> None:
    lines = report.red_pr_lines([_pr(93, [])])
    assert len(lines) == 1
    assert "#93" in lines[0] and "no checks" in lines[0]


def test_red_pr_lines_ignore_pending_and_non_agent_prs() -> None:
    pending = _pr(94, [_check("lint", "", status="IN_PROGRESS")])
    other = {"number": 5, "headRefName": "feature", "statusCheckRollup": []}
    assert report.red_pr_lines([pending, other]) == []


def test_red_pr_lines_read_status_contexts() -> None:
    ctx = {"context": "ci/legacy", "state": "FAILURE"}
    lines = report.red_pr_lines([_pr(95, [ctx])])
    assert "ci/legacy" in lines[0]


def test_limit_line_when_three_agent_prs_are_open() -> None:
    prs = [_pr(n, [_check("lint", "SUCCESS")]) for n in (1, 2, 3)]
    assert "limit" in report.limit_line(prs)
    assert report.limit_line(prs[:2]) == ""


def test_red_prs_are_part_of_needs_you() -> None:
    rep = report.build_report(_result(), outcome="success", max_turns=250)
    md = report.render(rep, run_url="u", mode="full", needs_human=["- red #91"])
    assert "- red #91" in md
    assert "Needs you: 1" in md.splitlines()[0]


def test_main_reads_the_prs_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    prs = tmp_path / "prs.json"
    prs.write_text(json.dumps([_pr(91, [_check("catalog", "FAILURE")])]))
    report.main(
        ["--execution-file", str(_log(tmp_path, _result())), "--prs-file", str(prs)]
    )
    out = capsys.readouterr().out
    assert "#91" in out and "catalog" in out


def test_no_needs_you_section_when_nothing_waits() -> None:
    rep = report.build_report(_result(), outcome="success", max_turns=250)
    md = report.render(rep, run_url="u", mode="full", needs_human=[])
    assert "Needs you" not in md
