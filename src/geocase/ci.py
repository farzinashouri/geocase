"""Turn a pytest JUnit XML report into a GeoCase Markdown summary.

Run as ``python -m geocase.ci report <junit.xml> [--out summary.md]``.

Only tests parametrized by a GeoCase case are reported. The plugin uses the
bare case id as the parameter id, so a test is ``test_x[<case_id>]``; a bracket
suffix that is not a registered case id is ignored. Not part of ``__all__``:
a submodule import, like :mod:`geocase.differential`.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from geocase.api.public import get_case

_ID_RE = re.compile(r"\[([^\[\]]+)\]$")


def case_id_from_test_name(name: str) -> str | None:
    """Return the registered case id a test name is parametrized by, else None."""
    match = _ID_RE.search(name)
    if match is None:
        return None
    try:
        get_case(match.group(1))
    except KeyError:
        return None
    return match.group(1)


@dataclass(frozen=True)
class _Result:
    case_id: str
    test: str
    failure: str | None


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _results(path: Path) -> list[_Result]:
    out: list[_Result] = []
    for tc in ET.parse(path).getroot().iter("testcase"):
        name = tc.get("name", "")
        case_id = case_id_from_test_name(name)
        if case_id is None:
            continue
        bad = tc.find("failure")
        if bad is None:
            bad = tc.find("error")
        failure = None
        if bad is not None:
            failure = _first_line(bad.get("message") or bad.text or "") or "failed"
        out.append(_Result(case_id, name.split("[", 1)[0], failure))
    return out


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def build_report(junit_path: Path) -> str:
    """Return the Markdown summary for the JUnit report at *junit_path*."""
    results = _results(junit_path)
    if not results:
        return "No GeoCase cases were exercised in this run.\n"
    failed = [r for r in results if r.failure is not None]
    lines = [
        f"**{len(results) - len(failed)} of {len(results)} GeoCase cases pass.**",
        "",
    ]
    if failed:
        lines += [
            "| Case | What it tests | Risk types | Test | Failure |",
            "| --- | --- | --- | --- | --- |",
        ]
        for r in failed:
            meta = get_case(r.case_id)
            risks = _cell(", ".join(meta.risk_types))
            lines.append(
                f"| `{r.case_id}` | {_cell(meta.title)} | {risks} "
                f"| `{r.test}` | {_cell(r.failure or '')} |"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m geocase.ci")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="summarize a pytest JUnit XML file")
    rep.add_argument("junit_xml", type=Path)
    rep.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    text = build_report(args.junit_xml)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
