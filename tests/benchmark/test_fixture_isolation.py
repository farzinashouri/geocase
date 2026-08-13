"""Trap 2 enforced, not promised (Plan 17 §3.2).

Corpus files may be handed to a model's function as INPUT. Their ``case.yaml``
may never be read by a grader: it carries the corpus author's expectations
(``assertions.expected_epsg``, ``risk_types``, ``params.crosses_dateline``), and
a grader that read them would be checking a belief rather than computing an
oracle — Plan 15's trap 1, *"a wrong oracle would be the exact failure this
project is named after."*

These tests are the mechanism. If they are ever deleted, the corpus-as-input
distinction reverts to a promise in a document.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from geocase.benchmark.fixtures import DENIED_FILENAMES, FixtureError, stage_fixtures
from geocase.benchmark.registry import FixtureDecl, all_tasks, tasks_root

SRC_BENCHMARK = Path(__file__).resolve().parents[2] / "src" / "geocase" / "benchmark"

#: Every way a grader could reach an expectation instead of computing one.
LEAK_PATTERNS = (
    "case.yaml",
    "assertions",
    "risk_types",
    "list_cases",
    "get_case",
    "load_case",
    "geocase.catalog",
    "geocase.cases",
)


def _grader_paths() -> list[Path]:
    return sorted(tasks_root().glob("*/grader.py"))


def _code_only(source: str) -> str:
    """Source with comments and *docstrings* removed — other strings kept.

    The patterns must be matched against code, not prose: a docstring
    explaining why a grader never reads ``case.yaml`` is the opposite of a
    violation, and failing on it would push authors to delete the explanation
    rather than stop reading the file.

    Ordinary string literals are deliberately kept, because
    ``open("case.yaml")`` is a violation that lives entirely inside one.
    Only strings in docstring position (a bare expression statement) are
    dropped.
    """
    import ast

    tree = ast.parse(source)
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstrings.add(id(first))

    class Strip(ast.NodeTransformer):
        def generic_visit(self, node):
            node = super().generic_visit(node)
            if id(node) in docstrings:
                return None
            return node

    # ast.unparse drops comments for free.
    return ast.unparse(Strip().visit(tree))


@pytest.mark.parametrize("grader", _grader_paths(), ids=lambda p: p.parent.name)
def test_no_grader_reaches_for_an_expectation(grader: Path):
    text = _code_only(grader.read_text())
    hits = [p for p in LEAK_PATTERNS if p in text]
    assert not hits, (
        f"{grader} references {hits} — a grader may read a fixture's BYTES, "
        f"never the corpus's expectations. Compute the oracle from first "
        f"principles instead (Plan 15, trap 2)."
    )


def test_the_leak_check_still_catches_real_code():
    """Guards the guard: stripping prose must not blind the pattern match."""
    violation = _code_only(
        "import yaml\n"
        "def build_checks(f):\n"
        "    meta = yaml.safe_load(open(root / 'case.yaml').read())\n"
        "    return meta['assertions']['expected_epsg']\n"
    )
    # Both the quoted filename and the subscripted expectation are caught.
    assert set(p for p in LEAK_PATTERNS if p in violation) == {
        "case.yaml",
        "assertions",
    }

    # And a docstring naming the same terms is *not* a violation.
    prose = _code_only(
        '"""This grader never reads case.yaml, assertions, or risk_types."""\n'
        "def build_checks(f):\n"
        "    return []\n"
    )
    assert not [p for p in LEAK_PATTERNS if p in prose]


def test_fixtures_module_is_the_only_catalog_importer():
    """One module may import geocase.catalog, so the permission cannot spread."""
    offenders = []
    for path in sorted(SRC_BENCHMARK.rglob("*.py")):
        if path.name == "fixtures.py" and path.parent == SRC_BENCHMARK:
            continue
        text = path.read_text()
        if re.search(r"^\s*(from|import)\s+geocase\.(catalog|cases)", text, re.M):
            offenders.append(str(path.relative_to(SRC_BENCHMARK)))
    assert not offenders, (
        f"{offenders} import geocase.catalog/cases. Only benchmark/fixtures.py "
        f"may (it needs case_roots_by_id); every other reach into the corpus "
        f"is a path to an expected value."
    )


@pytest.mark.parametrize("denied", sorted(DENIED_FILENAMES))
def test_stage_fixtures_refuses_metadata(tmp_path, denied):
    """The denylist is load-bearing, not documentation."""

    class FakeTask:
        name = "fake"
        fixtures = [
            FixtureDecl(
                name="leak", case_id="classic_antimeridian_polygon", file=denied
            )
        ]

    with pytest.raises(FixtureError, match="refusing to stage"):
        stage_fixtures(FakeTask(), tmp_path)  # type: ignore[arg-type]


def test_stage_fixtures_refuses_a_path_escape(tmp_path):
    class FakeTask:
        name = "fake"
        fixtures = [
            FixtureDecl(
                name="escape",
                case_id="classic_antimeridian_polygon",
                file="../classic_antimeridian_polygon/case.yaml",
            )
        ]

    with pytest.raises(FixtureError):
        stage_fixtures(FakeTask(), tmp_path)  # type: ignore[arg-type]


def test_stage_fixtures_copies_only_the_declared_data_file(tmp_path):
    class FakeTask:
        name = "fake"
        fixtures = [
            FixtureDecl(
                name="poly",
                case_id="classic_antimeridian_polygon",
                file="geometry.geojson",
            )
        ]

    staged = stage_fixtures(FakeTask(), tmp_path)  # type: ignore[arg-type]
    assert staged["poly"].is_file()
    names = {p.name for p in tmp_path.iterdir()}
    assert names == {"geometry.geojson"}
    assert not names & DENIED_FILENAMES


def test_declared_fixture_hashes_still_match_the_corpus():
    """A corpus file edited underneath a task changes what it measures."""
    from geocase.benchmark.fixtures import _sha256, resolve_fixture

    checked = 0
    for task in all_tasks():
        for fixture in task.fixtures:
            if not fixture.sha256:
                continue
            path = resolve_fixture(fixture.case_id, fixture.file)
            assert _sha256(path) == fixture.sha256, (
                f"{task.name}: fixture {fixture.name} no longer matches its "
                f"pinned sha256 — re-verify the oracle before re-pinning"
            )
            checked += 1
    assert checked, "no pinned fixtures found; Phase 3 declares two"


def test_no_task_declares_a_fixture_it_cannot_stage(tmp_path):
    for task in all_tasks():
        if task.fixtures:
            stage_fixtures(task, tmp_path / task.name)
