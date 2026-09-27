"""Print one version's section of CHANGELOG.md (the GitHub release notes).

    python scripts/changelog_section.py 1.2.0 > notes.md

Prints the body under ``## [1.2.0] — <date>`` up to the next ``## [`` heading,
without the heading itself. Exits 1 if the version has no section.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def section(changelog: str, version: str) -> str:
    pattern = re.compile(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", re.M | re.S
    )
    match = pattern.search(changelog)
    if not match:
        raise ValueError(f"CHANGELOG.md has no section for {version}")
    return match.group(1).strip()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: changelog_section.py VERSION", file=sys.stderr)
        return 2
    try:
        print(section((REPO_ROOT / "CHANGELOG.md").read_text(), args[0]))
    except ValueError as exc:
        print(f"changelog_section: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
