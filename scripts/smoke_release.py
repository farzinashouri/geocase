"""Smoke-test an installed geocase before and after a PyPI upload (Plan 50).

    python scripts/smoke_release.py --version 1.2.0 --mode core|array [--summary FILE]

Run it in a clean environment where geocase was installed from an index
(TestPyPI or PyPI), never from this checkout: it checks the *published*
package. It imports only the installed ``geocase``.

Modes:
- ``core``: plain ``pip install geocase``. numpy must NOT be installed, and
  ``import geocase.raster`` must fail with the message naming ``geocase[array]``.
- ``array``: ``pip install geocase[array]``. ``geocase.raster`` must import.

Prints a Markdown report (appended to ``--summary``, e.g. ``$GITHUB_STEP_SUMMARY``)
and exits 1 if any check fails.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata as metadata
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def _check(name: str, fn: Callable[[], tuple[bool, str]]) -> Check:
    try:
        ok, detail = fn()
    except Exception as exc:  # a crash is a failed check, not a crashed report
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    return Check(name, ok, detail)


def _installed(dist: str) -> bool:
    try:
        metadata.version(dist)
    except metadata.PackageNotFoundError:
        return False
    return True


def run_checks(expected_version: str, mode: str) -> list[Check]:
    import geocase

    def version() -> tuple[bool, str]:
        return geocase.__version__ == expected_version, geocase.__version__

    def cases() -> tuple[bool, str]:
        from importlib.resources import files

        from geocase.catalog.loader import load_case_index

        index = Path(str(files("geocase") / "metadata" / "case-index.yaml"))
        n_index = len(load_case_index(index))
        n_listed = len(geocase.list_cases())
        return n_listed == n_index and n_listed > 0, f"{n_listed} (index: {n_index})"

    def data_file() -> tuple[bool, str]:
        case_id = geocase.list_cases()[0].id
        path = geocase.load_case(case_id).primary_path
        return path.exists(), f"{case_id}: {path.name}"

    def plugin() -> tuple[bool, str]:
        points = [e.value for e in metadata.entry_points(group="pytest11")]
        return "geocase.pytest_plugin" in points, ", ".join(points) or "none"

    checks = [
        _check("version", version),
        _check(
            "public API",
            lambda: (len(geocase.__all__) > 0, f"{len(geocase.__all__)} names"),
        ),
        _check("cases", cases),
        _check("data file", data_file),
        _check("pytest plugin", plugin),
    ]

    if mode == "core":

        def no_numpy() -> tuple[bool, str]:
            present = _installed("numpy")
            return not present, "numpy installed" if present else "not installed"

        def raster_message() -> tuple[bool, str]:
            try:
                importlib.import_module("geocase.raster")
            except ImportError as exc:
                return "geocase[array]" in str(exc), str(exc)
            return False, "imported without numpy"

        checks += [
            _check("no numpy in core", no_numpy),
            _check("geocase.raster message", raster_message),
        ]
    elif mode == "array":

        def raster() -> tuple[bool, str]:
            module = importlib.import_module("geocase.raster")
            return hasattr(module, "raster_fixture"), "raster_fixture importable"

        checks.append(_check("geocase.raster", raster))
    else:
        raise ValueError(f"unknown mode {mode!r}; use core or array")
    return checks


def report(checks: list[Check], version: str, mode: str) -> str:
    lines = [
        f"### Smoke test: geocase {version} ({mode})",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for c in checks:
        detail = c.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {c.name} | {'✅' if c.ok else '❌'} | {detail} |")
    return "\n".join(lines) + "\n"


def exit_code(checks: list[Check]) -> int:
    return 0 if all(c.ok for c in checks) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", required=True)
    parser.add_argument("--mode", required=True, choices=["core", "array"])
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)

    checks = run_checks(args.version, args.mode)
    text = report(checks, args.version, args.mode)
    print(text)
    if args.summary:
        with args.summary.open("a") as fh:
            fh.write(text + "\n")
    return exit_code(checks)


if __name__ == "__main__":
    sys.exit(main())
