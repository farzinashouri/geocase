"""Canonical raster integration suite (Step 6 of the raster action plan).

This suite is registry-driven: it resolves bundled raster cases from the live
``CaseRegistry`` rather than hard-coded file paths, opens each via the rasterio
loader, and dispatches typed expectations from the case metadata through
``assert_matches_raster_hints``.

Edge-case behaviours (NaN nodata, masking, derived indices) are covered by
targeted unit tests; this suite enforces catalog-wide consistency.

See: docs/plans/08-raster-action-plan.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from geocase.assertions.metadata import assert_matches_raster_hints
from geocase.cases.factory import create_case
from geocase.catalog.loader import load_case_index, load_case_metadata
from geocase.catalog.registry import get_registry
from geocase.loaders.rasterio_loader import open_raster

pytest.importorskip("rasterio")


_PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "geocase"


def _case_roots_by_id() -> dict[str, Path]:
    """Map every indexed case id to its on-disk case directory."""
    case_index_path = _PACKAGE_ROOT / "metadata" / "case-index.yaml"
    roots: dict[str, Path] = {}
    for rel in load_case_index(case_index_path):
        case_yaml = _PACKAGE_ROOT / rel
        meta = load_case_metadata(case_yaml)
        roots[meta.id] = case_yaml.parent
    return roots


def _bundled_raster_case_ids() -> list[str]:
    """Return sorted ids of all bundled GeoTIFF raster cases in the registry."""
    registry = get_registry(reload=True)
    return sorted(
        case.id
        for case in registry
        if case.category == "raster"
        and case.format == "GeoTIFF"
        and case.storage_class == "bundled"
    )


_RASTER_CASE_IDS = _bundled_raster_case_ids()


@pytest.fixture(scope="module")
def case_roots() -> dict[str, Path]:
    return _case_roots_by_id()


@pytest.mark.parametrize("case_id", _RASTER_CASE_IDS)
def test_bundled_raster_case_matches_typed_hints(case_id, case_roots):
    """Every bundled raster case opens and satisfies its typed metadata hints."""
    registry = get_registry()
    meta = registry.get(case_id)
    case = create_case(meta, case_roots[case_id])

    assert case.primary_exists(), f"Missing primary file for '{case_id}'"

    with open_raster(case.primary_path) as src:
        assert_matches_raster_hints(case, src)


def test_registry_exposes_bundled_raster_cases():
    """Sanity guard: the bundled raster catalog is non-empty."""
    assert _RASTER_CASE_IDS, "No bundled raster cases resolved from registry"
