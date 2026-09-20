"""`trap_category` maps onto the catalog's `risk_types` (Plan 46 §2.3).

The two vocabularies were disjoint, which is how `transform/*`, `dtype/*` and
`precision/*` came to have purpose-built corpus cases and zero benchmark
coverage without anyone noticing. The mapping lives in ``taxonomy.py`` and
imports **nothing** from ``geocase.catalog`` — this test does the cross-check,
so ``test_fixture_isolation.py``'s sole-importer rule is untouched.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from geocase.benchmark.registry import all_tasks
from geocase.benchmark.runner.report import uncovered_risk_families
from geocase.benchmark.taxonomy import (
    TRAP_CATEGORIES_BY_DOMAIN,
    TRAP_TO_RISK,
    UNMAPPED_TRAPS,
)
from geocase.catalog.risk_types import (
    RISK_TYPE_ALIASES,
    RISK_TYPES,
    risk_type_family,
)

ALL_CATEGORIES = {c for cats in TRAP_CATEGORIES_BY_DOMAIN.values() for c in cats}


def test_every_trap_category_has_a_mapping_entry():
    assert set(TRAP_TO_RISK) == ALL_CATEGORIES, (
        f"missing: {ALL_CATEGORIES - set(TRAP_TO_RISK)}; "
        f"stale: {set(TRAP_TO_RISK) - ALL_CATEGORIES}"
    )


@pytest.mark.parametrize("category", sorted(TRAP_CATEGORIES_BY_DOMAIN["geo"]))
def test_every_geo_category_maps_to_at_least_one_risk_type(category):
    if category in UNMAPPED_TRAPS:
        assert not TRAP_TO_RISK[category]
        assert UNMAPPED_TRAPS[category].strip(), "an unmapped trap needs a reason"
        return
    assert TRAP_TO_RISK[category], f"{category!r} maps to nothing"


@pytest.mark.parametrize("category", sorted(ALL_CATEGORIES))
def test_every_mapped_term_is_canonical(category):
    """An unaliased rename in risk_types.py must fail loudly here."""
    for term in TRAP_TO_RISK[category]:
        assert term in RISK_TYPES, f"{category!r} -> {term!r} is not a risk type"
        assert term not in RISK_TYPE_ALIASES, (
            f"{category!r} -> {term!r} is a deprecated spelling; use "
            f"{RISK_TYPE_ALIASES[term]!r}"
        )
        assert risk_type_family(term) is not None, f"{term!r} has no family"


def test_unmapped_traps_are_a_subset_of_the_mapping():
    assert set(UNMAPPED_TRAPS) <= set(TRAP_TO_RISK)
    for category in UNMAPPED_TRAPS:
        assert TRAP_TO_RISK[category] == (), f"{category!r} is both mapped and unmapped"


def test_report_restates_the_catalog_families_exactly():
    """report.py keeps its own family list so it stays catalog-free; this is
    what keeps that list from drifting."""
    from geocase.benchmark.runner.report import RISK_FAMILIES
    from geocase.catalog.risk_types import families

    assert RISK_FAMILIES == frozenset(families())


def test_taxonomy_still_imports_nothing_from_the_catalog():
    src = Path(__file__).resolve().parents[2] / "src" / "geocase" / "benchmark"
    text = (src / "taxonomy.py").read_text()
    assert not re.search(r"^\s*(from|import)\s+geocase\.(catalog|cases)", text, re.M)


def test_the_gap_the_plan_names_is_visible():
    """Plan 46 §2.3: transform, dtype and precision have no geo task today.

    This pins the *finding*, so that Phase 4 closing it is a measured change
    to this test rather than an assertion in a document.
    """
    geo = [t for t in all_tasks() if t.domain == "geo"]
    gaps = uncovered_risk_families(geo)
    assert {"transform", "dtype", "precision"} <= set(gaps), gaps
