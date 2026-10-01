#!/usr/bin/env python
"""Scaffold a draft blog post from the catalog (Plan 47 phase 3).

    python scripts/scaffold_post.py --pillar spotlight --case geotiff_nodata_small --date 2026-10-05
    python scripts/scaffold_post.py --pillar failure-mode --risk nodata/ignored --date 2026-10-06

Writes ``docs/posts/<date>-<slug>.md`` with the front matter and the numbers
prefilled from the registry, and ``TODO:`` markers where a person has to write.
A scaffolded post is ``draft: true``; remove that (and every ``TODO:``) to
publish. A pure registry read: no GDAL, no data files opened.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from geocase.catalog.registry import get_registry  # noqa: E402
from geocase.catalog.risk_types import RISK_TYPE_DESCRIPTIONS  # noqa: E402

POSTS_DIR = REPO_ROOT / "docs" / "posts"
PREVIEW_PATH = "../_generated/catalog/previews"
CASE_PAGE_PATH = "../_generated/catalog/cases"
RISK_PAGE_PATH = "../_generated/catalog/risk"

GROUND_TRUTH_FIELDS = ("expected_mean_masked", "expected_mean_naive", "nodata_pixel_count")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _quote(text: str) -> str:
    """Quote a string as a YAML double-quoted scalar."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _front_matter(
    *, title: str, description: str, when: date, risk_types: list[str], cases: list[str]
) -> list[str]:
    return [
        "---",
        f"title: {_quote(title)}",
        f"description: {_quote(description)}",
        f"date: {when.isoformat()}",
        "draft: true",
        f"risk_types: [{', '.join(risk_types)}]",
        f"cases: [{', '.join(cases)}]",
        "---",
        "",
    ]


def _where(case: Any) -> str | None:
    """The extent / region line; ``None`` when the case has neither."""
    parts: list[str] = []
    if case.region:
        parts.append(str(case.region))
    extent = case.extent
    if extent is not None:
        box = (
            f"{extent.west:.2f}°E, {extent.south:.2f}°N → "
            f"{extent.east:.2f}°E, {extent.north:.2f}°N"
        )
        if extent.crosses_antimeridian:
            box += " (crosses the antimeridian)"
        parts.append(box)
    return " — ".join(parts) or None


def _ground_truth_table(case: Any) -> list[str]:
    rows = [
        (field, getattr(case.assertions, field))
        for field in GROUND_TRUTH_FIELDS
        if getattr(case.assertions, field, None) is not None
    ]
    if not rows:
        return []
    lines = ["| Ground truth | Value |", "|---|---|"]
    lines.extend(f"| `{field}` | {value} |" for field, value in rows)
    lines.append("")
    return lines


def spotlight(case_id: str, when: date) -> tuple[str, str]:
    """Return ``(filename, text)`` for a one-case spotlight post."""
    case = get_registry().get(case_id)
    description = " ".join((case.description or case.title).split())
    risk_types = sorted(case.risk_types)

    lines = _front_matter(
        title=case.title, description=description, when=when, risk_types=risk_types, cases=[case.id]
    )
    lines += [f"# {case.title}", "", f"TODO: one-sentence hook for `{case.id}`.", ""]
    lines += [f"![{case.title}]({PREVIEW_PATH}/{case.id}.png)", ""]
    where = _where(case)
    if where:
        lines += [f"**Where:** {where}", ""]
    lines += _ground_truth_table(case)
    lines += [
        "## The failing call",
        "",
        "TODO: the call that returns a plausible wrong answer, and the right one.",
        "",
        "## Try it",
        "",
        f"The case page: [`{case.id}`]({CASE_PAGE_PATH}/{case.id}.md).",
        "",
    ]
    return f"{when.isoformat()}-{_slug(case.id)}.md", "\n".join(lines)


def failure_mode(risk: str, when: date) -> tuple[str, str]:
    """Return ``(filename, text)`` for a failure-mode post on one risk type."""
    if risk not in RISK_TYPE_DESCRIPTIONS:
        raise KeyError(risk)
    description = RISK_TYPE_DESCRIPTIONS[risk]
    declaring = sorted(c.id for c in get_registry().list_cases() if risk in c.risk_types)

    lines = _front_matter(
        title=f"Failure mode: {risk}",
        description=description,
        when=when,
        risk_types=[risk],
        cases=declaring,
    )
    lines += [f"# TODO: title for `{risk}`", "", description, ""]
    lines += ["## Cases that exercise it", ""]
    lines += [f"- [`{case_id}`]({CASE_PAGE_PATH}/{case_id}.md)" for case_id in declaring]
    lines += [
        "",
        "## What goes wrong",
        "",
        "TODO: the failing call and the number it gets wrong.",
        "",
        "## The risk hub",
        "",
        f"All cases: [`{risk}`]({RISK_PAGE_PATH}/{_slug(risk)}.md).",
        "",
    ]
    return f"{when.isoformat()}-{_slug(risk)}.md", "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pillar", choices=("spotlight", "failure-mode"), required=True)
    parser.add_argument("--case", help="case id (spotlight)")
    parser.add_argument("--risk", help="risk type, e.g. nodata/ignored (failure-mode)")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output-dir", type=Path, default=POSTS_DIR)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.pillar == "spotlight":
            if not args.case:
                print("--case is required for --pillar spotlight", file=sys.stderr)
                return 2
            filename, text = spotlight(args.case, args.date)
        else:
            if not args.risk:
                print("--risk is required for --pillar failure-mode", file=sys.stderr)
                return 2
            filename, text = failure_mode(args.risk, args.date)
    except KeyError as exc:
        print(f"unknown case or risk type: {exc}", file=sys.stderr)
        return 1

    target = args.output_dir / filename
    if target.exists():
        print(f"{target} already exists; not overwriting", file=sys.stderr)
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
