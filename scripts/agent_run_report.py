"""Summarise one nightly agent run as Markdown (Plan 52 Phase 1, issue #83).

    python scripts/agent_run_report.py --execution-file out.json \
        --outcome success --run-url URL --mode full --max-turns 250 \
        [--prs-file prs.json]

Reads the claude-code-action execution file (a JSON list of messages ending in
a ``result`` object), prints a Markdown report to stdout and writes
``healthy=true|false`` to ``$GITHUB_OUTPUT``. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class Report:
    turns: int | None = None
    duration_s: int | None = None
    cost: float | None = None
    final_text: str = ""
    denials: list[dict[str, Any]] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return not self.reasons


def load_result(path: Path) -> dict[str, Any] | None:
    """Return the trailing ``result`` message, or None if there is none."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    for msg in reversed(data):
        if isinstance(msg, dict) and msg.get("type") == "result":
            return msg
    return None


def build_report(
    result: dict[str, Any] | None, *, outcome: str, max_turns: int
) -> Report:
    rep = Report()
    if outcome != "success":
        rep.reasons.append(f"action step {outcome}")
    if result is None:
        rep.reasons.append("no result object in the execution file")
        return rep
    rep.turns = result.get("num_turns")
    ms = result.get("duration_ms")
    rep.duration_s = round(ms / 1000) if isinstance(ms, (int, float)) else None
    rep.cost = result.get("total_cost_usd")
    rep.final_text = str(result.get("result") or "")
    rep.denials = list(result.get("permission_denials") or [])
    if result.get("is_error"):
        rep.reasons.append(f"is_error ({result.get('subtype', 'unknown')})")
    if rep.denials:
        rep.reasons.append(f"{len(rep.denials)} permission denial(s)")
    if rep.turns is not None and rep.turns >= max_turns:
        rep.reasons.append(f"hit the turn cap ({rep.turns}/{max_turns})")
    return rep


def touched(since: datetime) -> list[str]:
    """PRs and issues the agent opened in the run window (best effort)."""
    day = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = []
    for kind in ("pr", "issue"):
        cmd = ["gh", kind, "list", "--state", "all", "--author", "@me"]
        cmd += ["--search", f"created:>={day}", "--json", "number,title,url"]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, check=True)
            for item in json.loads(out.stdout):
                lines.append(
                    f"- {kind} [#{item['number']}]({item['url']}) {item['title']}"
                )
        except (OSError, subprocess.CalledProcessError, ValueError):
            continue
    return lines


def needs_human_lines(issues: list[dict[str, Any]]) -> list[str]:
    """One line per waiting issue: link, title and the question's first line.

    The agent asks with the owner's token, and GitHub emails nobody about
    their own comments, so the question has to travel in this report.
    """
    lines = []
    for item in issues:
        line = f"- [#{item['number']}]({item['url']}) {item['title']}"
        comments = item.get("comments") or []
        if comments:
            first = str(comments[-1].get("body") or "").strip().splitlines()
            question = first[0].removeprefix("@farzinashouri").strip() if first else ""
            if question:
                line += f": {question}"
        lines.append(line)
    return lines


_RED = {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "STARTUP_FAILURE"}
PR_LIMIT = 3


def _agent_prs(prs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p for p in prs if str(p.get("headRefName", "")).startswith("agent/")]


def red_pr_lines(prs: list[dict[str, Any]]) -> list[str]:
    """One line per open agent PR that is red or has no checks (Plan 53).

    ``prs`` is ``gh pr list --json number,headRefName,statusCheckRollup``.
    Pending checks are not red. A check run carries ``name``/``conclusion``;
    a legacy status carries ``context``/``state``.
    """
    lines = []
    for pr in _agent_prs(prs):
        checks = pr.get("statusCheckRollup") or []
        failed = [
            str(c.get("name") or c.get("context") or "?")
            for c in checks
            if str(c.get("conclusion") or c.get("state") or "").upper() in _RED
        ]
        label = f"- PR #{pr['number']} (`{pr.get('headRefName')}`)"
        if failed:
            lines.append(f"{label} is red: {', '.join(failed)}")
        elif not checks:
            lines.append(f"{label} has no checks")
    return lines


def limit_line(prs: list[dict[str, Any]]) -> str:
    """A sentence when the open-PR limit stops the agent, else an empty string."""
    n = len(_agent_prs(prs))
    if n < PR_LIMIT:
        return ""
    return f"- {n} agent PRs are open: the limit of {PR_LIMIT} stops new work"


def load_prs(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def waiting_issues() -> list[dict[str, Any]]:
    """Open issues labelled ``agent:needs-human`` (best effort)."""
    cmd = ["gh", "issue", "list", "--state", "open", "--label", "agent:needs-human"]
    cmd += ["--json", "number,title,url,comments"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(out.stdout)
    except (OSError, subprocess.CalledProcessError, ValueError):
        return []
    return data if isinstance(data, list) else []


def render(
    rep: Report,
    *,
    run_url: str,
    mode: str,
    touched_lines: list[str] | None = None,
    needs_human: list[str] | None = None,
) -> str:
    if rep.healthy:
        head = "✅ healthy"
    else:
        head = "⚠️ needs attention: " + "; ".join(rep.reasons)
    if needs_human:
        head += f" · 🙋 Needs you: {len(needs_human)} issue(s)"
    cost = f"${rep.cost:.2f}" if rep.cost is not None else "n/a"
    out = [
        head,
        "",
        f"- Run: {run_url}",
        f"- Mode: {mode}",
        f"- Turns: {rep.turns if rep.turns is not None else 'n/a'}",
        f"- Duration: {rep.duration_s if rep.duration_s is not None else 'n/a'} s",
        f"- Cost (list price): {cost}",
    ]
    if rep.denials:
        out += ["", "**Permission denials**", ""]
        for d in rep.denials:
            cmd = (d.get("tool_input") or {}).get("command", "")
            out.append(f"- `{d.get('tool_name', '?')}` `{cmd}`".rstrip())
    if needs_human:
        out += ["", "**Needs you**", "", *needs_human]
    if touched_lines:
        out += ["", "**Touched in this run**", "", *touched_lines]
    if rep.final_text:
        out += ["", "**Final message**", "", rep.final_text]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execution-file", type=Path, required=True)
    ap.add_argument("--outcome", default="success")
    ap.add_argument("--run-url", default="")
    ap.add_argument("--mode", default="full")
    ap.add_argument("--max-turns", type=int, default=250)
    ap.add_argument("--prs-file", type=Path, default=None)
    args = ap.parse_args(argv)

    rep = build_report(
        load_result(args.execution_file),
        outcome=args.outcome,
        max_turns=args.max_turns,
    )
    since = datetime.now(UTC) - timedelta(seconds=(rep.duration_s or 0) + 600)
    has_gh = bool(os.environ.get("GH_TOKEN"))
    lines = touched(since) if has_gh else []
    waiting = needs_human_lines(waiting_issues()) if has_gh else []
    prs = load_prs(args.prs_file)
    waiting += red_pr_lines(prs)
    if limit := limit_line(prs):
        waiting.append(limit)
    sys.stdout.write(
        render(
            rep,
            run_url=args.run_url,
            mode=args.mode,
            touched_lines=lines,
            needs_human=waiting,
        )
    )
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as fh:
            fh.write(f"healthy={'true' if rep.healthy else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
