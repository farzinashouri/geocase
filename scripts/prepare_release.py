"""Prepare a release: bump the version and date the changelog (Plan 50).

    python scripts/prepare_release.py 1.2.0 [--date YYYY-MM-DD]

Sets ``project.version`` in ``pyproject.toml`` and renames ``## [Unreleased]``
in ``CHANGELOG.md`` to ``## [1.2.0] — <date>``. Refuses a version that is not
greater than the current one, and an ``[Unreleased]`` section that is missing
or empty: a release with no changelog entry is the thing this guards against.

Run ``scripts/generate_changelog_page.py`` afterwards to regenerate
``docs/changelog.md``; ``prepare-release.yml`` does both.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:rc(\d+))?$")
_PROJECT_VERSION = re.compile(r'(\[project\][^\[]*?\nversion = ")([^"]+)(")', re.S)
_UNRELEASED = re.compile(r"^## \[Unreleased\][^\n]*\n(.*?)(?=^## \[|\Z)", re.M | re.S)


def _key(version: str) -> tuple[int, int, int, float]:
    match = _VERSION.match(version)
    if not match:
        raise ValueError(f"not a release version (X.Y.Z or X.Y.ZrcN): {version!r}")
    major, minor, patch, rc = match.groups()
    # A final release sorts after all of its release candidates.
    return int(major), int(minor), int(patch), float(rc) if rc else float("inf")


def bump_version(pyproject: str, version: str) -> str:
    match = _PROJECT_VERSION.search(pyproject)
    if not match:
        raise ValueError("no version in the [project] table of pyproject.toml")
    current = match.group(2)
    if _key(version) <= _key(current):
        raise ValueError(f"{version} is not greater than the current {current}")
    return pyproject[: match.start(2)] + version + pyproject[match.end(2) :]


def release_changelog(changelog: str, version: str, date: str) -> str:
    match = _UNRELEASED.search(changelog)
    if not match:
        raise ValueError("CHANGELOG.md has no '## [Unreleased]' section")
    if not match.group(1).strip():
        raise ValueError("the [Unreleased] section is empty; nothing to release")
    heading = f"## [{version}] — {date}\n"
    end_of_heading = changelog.index("\n", match.start()) + 1
    return changelog[: match.start()] + heading + changelog[end_of_heading:]


def main(argv: list[str] | None = None, root: Path = REPO_ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version")
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    args = parser.parse_args(argv)

    pyproject = root / "pyproject.toml"
    changelog = root / "CHANGELOG.md"
    try:
        new_pyproject = bump_version(pyproject.read_text(), args.version)
        new_changelog = release_changelog(
            changelog.read_text(), args.version, args.date
        )
    except ValueError as exc:
        print(f"prepare_release: {exc}", file=sys.stderr)
        return 1
    pyproject.write_text(new_pyproject)
    changelog.write_text(new_changelog)
    print(f"prepared {args.version} ({args.date})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
