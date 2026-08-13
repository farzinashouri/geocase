"""Corpus cases as INPUT, never as ORACLE (Plan 17 Phase 3).

135 curated cases sit in the wheel unreferenced by the benchmark, because
Plan 15's **trap 2** says "never grade against the fixture corpus". Read
carefully, that forbids corpus *expected values*. It says nothing about corpus
*input bytes* — and the distinction is the whole of this module:

* A **fixture** is a file path handed to the model's function. It carries no
  expectation.
* An **oracle** is a value computed from first principles (``pyproj.Geod``, a
  format spec) inside ``grader.py``.

The rule that keeps them apart, and the reason this module exists:

    **A grader may read a fixture's bytes; it may never read the fixture's
    ``case.yaml``.**

Every leak vector lives in that one file — ``assertions.expected_epsg``,
``risk_types``, ``params.crosses_dateline``. A grader that read it would be
asserting what the corpus author believed rather than what is true, which is
Plan 15's trap 1: *a wrong oracle would be the exact failure this project is
named after*.

Three enforcement points turn that from a promise into a test:

1. :func:`stage_fixtures` carries an explicit denylist and raises on any
   attempt to copy metadata.
2. ``tests/benchmark/test_fixture_isolation.py`` greps every ``grader.py`` for
   the leak vectors.
3. This module is the **only** one under ``benchmark/`` permitted to import
   ``geocase.catalog`` — it needs ``case_roots_by_id()``. The same test asserts
   that, so the permission cannot quietly spread.

Trap 3 (prompt contamination) is avoided by construction on both tracks. Bare:
the model receives only ``bare_prompt(task)``; fixtures are staged grader-side
at grading time, so nothing about the corpus reaches the model and **no prompt
hash changes**. Agentic: fixtures are staged into ``workdir/data``, where the
agent sees a ``.geojson``, not a case directory.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from geocase.benchmark.registry import TaskMeta

#: Files that carry the corpus author's *expectations* rather than data. Copying
#: any of these into a grading directory would put an oracle within a grader's
#: reach, which is precisely what trap 2 forbids.
DENIED_FILENAMES = frozenset(
    {
        "case.yaml",  # assertions, risk_types, params — every leak vector
        "notes.md",  # prose that names the trap outright
        "checksums.sha256",
    }
)


class FixtureError(RuntimeError):
    """A declared fixture is missing, altered, or forbidden."""


def _case_root(case_id: str) -> Path:
    # The single permitted catalog import in the whole benchmark package.
    from geocase.catalog.roots import case_roots_by_id

    try:
        return case_roots_by_id()[case_id]
    except KeyError as exc:
        raise FixtureError(
            f"unknown case id {case_id!r}; it is not in the bundled case index"
        ) from exc


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_fixture(case_id: str, filename: str) -> Path:
    """Absolute path to one corpus *data* file. Refuses metadata outright."""
    if filename in DENIED_FILENAMES:
        raise FixtureError(
            f"refusing to stage {filename!r} from case {case_id!r}: it carries "
            f"the corpus author's expectations, and a grader that read it "
            f"would be checking a belief rather than computing an oracle "
            f"(Plan 15, trap 2)"
        )
    # A nested path could escape the case root or reach a sibling case's
    # case.yaml, so only plain filenames are accepted.
    if Path(filename).name != filename or filename in ("", ".", ".."):
        raise FixtureError(f"fixture file must be a plain filename, got {filename!r}")
    path = _case_root(case_id) / filename
    if not path.is_file():
        raise FixtureError(f"case {case_id!r} has no file {filename!r} at {path}")
    return path


def stage_fixtures(task: TaskMeta, dest: Path) -> dict[str, Path]:
    """Copy a task's declared fixture files into ``dest``, verifying sha256.

    Data bytes ONLY — never ``case.yaml``, ``notes.md``, ``checksums.sha256``.
    Returns ``{fixture name: staged path}``; a task declaring no fixtures gets
    an empty dict and no directory is created.
    """
    declared = task.fixtures or []
    if not declared:
        return {}
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    staged: dict[str, Path] = {}
    for fixture in declared:
        src = resolve_fixture(fixture.case_id, fixture.file)
        actual = _sha256(src)
        if fixture.sha256 and actual != fixture.sha256:
            # Pinned because the oracle is stated against *these* bytes: a
            # corpus file edited underneath the task would silently change what
            # the benchmark measures.
            raise FixtureError(
                f"fixture {fixture.name!r} ({fixture.case_id}/{fixture.file}) "
                f"has sha256 {actual}, but {task.name}/task.yaml pins "
                f"{fixture.sha256}. Re-pin it only after confirming the new "
                f"bytes still make the task's oracle true."
            )
        target = dest / fixture.file
        shutil.copyfile(src, target)
        staged[fixture.name] = target
    return staged
