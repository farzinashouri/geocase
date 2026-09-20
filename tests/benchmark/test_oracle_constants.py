"""Hand-typed oracle constants carry a citation (Plan 46 §0.4).

Every oracle is either computed from a library or typed in by hand. The
hand-typed ones — the ``utm_epsg_for`` zone table, ``s2_fixture``'s
``BOA_ADD_OFFSET`` and ``QUANTIFICATION_VALUE`` — were checked by nothing but
review, and the repo has already been wrong about one of them once (the Plan
14 prior-art table for ``utm_epsg_for``, corrected in ``RESULTS.md``).

This is a **completeness** check, not a network check: every public numeric
module-level constant in a grader must appear in that grader's ``SOURCES``
dict, either as a ``(document, section)`` citation or as a string beginning
``author-chosen`` that says the value is a parameter of the oracle rather than
a published fact. A new constant therefore cannot arrive unclassified.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from geocase.benchmark.grading import load_module
from geocase.benchmark.registry import all_tasks

AUTHOR_CHOSEN = "author-chosen"


def _is_numeric_literal(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _is_numeric_literal(node.operand)
    return False


def _has_numeric_leaf(node: ast.AST) -> bool:
    """True for a numeric literal, or a dict/list/tuple containing one."""
    if _is_numeric_literal(node):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return any(_has_numeric_leaf(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return any(_has_numeric_leaf(v) for v in node.values if v is not None)
    return False


def hand_typed_constants(grader_path: Path) -> list[str]:
    """Public ALL_CAPS module-level names bound to numeric literals."""
    tree = ast.parse(grader_path.read_text())
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if name.startswith("_") or name != name.upper() or name == "SOURCES":
                continue
            if _has_numeric_leaf(value):
                names.append(name)
    return names


GRADERS = {t.name: t.grader_path for t in all_tasks()}
WITH_CONSTANTS = sorted(n for n, p in GRADERS.items() if hand_typed_constants(p))


def test_the_scan_finds_the_constants_this_phase_is_about():
    """Guards the guard: a scan that found nothing would pass vacuously."""
    assert "s2_fixture" in WITH_CONSTANTS
    assert "utm_epsg_for" in WITH_CONSTANTS
    assert set(hand_typed_constants(GRADERS["s2_fixture"])) >= {
        "BOA_ADD_OFFSET",
        "QUANTIFICATION_VALUE",
    }


@pytest.mark.parametrize("name", WITH_CONSTANTS)
def test_every_hand_typed_constant_is_cited_or_declared_chosen(name):
    grader = load_module(GRADERS[name])
    sources = getattr(grader, "SOURCES", None)
    assert isinstance(sources, dict), (
        f"{name}/grader.py has hand-typed constants but no SOURCES dict"
    )
    for const in hand_typed_constants(GRADERS[name]):
        assert const in sources, (
            f"{name}/grader.py: {const} is hand-typed and uncited — add it to "
            f"SOURCES as (document, section) or as an 'author-chosen: ...' note"
        )
        entry = sources[const]
        if isinstance(entry, str):
            assert entry.startswith(AUTHOR_CHOSEN), (
                f"{name}/grader.py: SOURCES[{const!r}] is a string but does not "
                f"begin {AUTHOR_CHOSEN!r}; a citation is a (document, section) tuple"
            )
        else:
            assert (
                isinstance(entry, tuple)
                and len(entry) == 2
                and all(isinstance(s, str) and s.strip() for s in entry)
            ), f"{name}/grader.py: SOURCES[{const!r}] must be (document, section)"


@pytest.mark.parametrize("name", WITH_CONSTANTS)
def test_sources_names_only_constants_that_exist(name):
    """A stale SOURCES entry is a citation for nothing."""
    grader = load_module(GRADERS[name])
    for key in grader.SOURCES:
        assert hasattr(grader, key), f"{name}/grader.py: SOURCES cites {key!r}, absent"


def test_the_published_facts_are_cited_not_declared_chosen():
    """The two constants that motivated this test cannot be waved through."""
    s2 = load_module(GRADERS["s2_fixture"])
    for key in ("BOA_ADD_OFFSET", "QUANTIFICATION_VALUE"):
        assert isinstance(s2.SOURCES[key], tuple), f"s2_fixture: {key} needs a citation"
    utm = load_module(GRADERS["utm_epsg_for"])
    assert isinstance(utm.SOURCES["ZONE_EXCEPTIONS"], tuple)
