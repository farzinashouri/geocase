"""Tests for geocase.catalog.suites — suite resolution logic."""

from pathlib import Path

import pytest

from geocase.catalog.models import CaseMetadata, SuiteMetadata, SuiteSelection
from geocase.catalog.registry import CaseRegistry
from geocase.catalog.suites import (
    ResolvedSuite,
    load_all_suites,
    load_and_resolve_suite,
    resolve_suite,
)


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_METADATA = _SRC / "metadata"
_CASE_INDEX = _METADATA / "case-index.yaml"
_SUITE_INDEX = _METADATA / "suite-index.yaml"
_SUITES = _SRC / "catalog" / "suites"

_CORE_VECTOR_SUITE = _SUITES / "core-vector.yaml"
_CRS_SUITE = _SUITES / "crs-edge-cases.yaml"
_NODATA_SUITE = _SUITES / "raster-nodata.yaml"


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> CaseRegistry:
    return CaseRegistry.from_index(_CASE_INDEX)


# ===================================================================
# resolve_suite — from a SuiteMetadata object
# ===================================================================

class TestResolveSuite:
    """Test resolve_suite with programmatic SuiteMetadata."""

    def test_select_all_vectors(self, registry: CaseRegistry):
        suite_meta = SuiteMetadata(
            suite_key="test-vectors",
            title="Test Vectors",
            description="All vector cases.",
            schema_version="1.0",
            selection=SuiteSelection(category="vector"),
        )
        resolved = resolve_suite(suite_meta, registry)
        assert isinstance(resolved, ResolvedSuite)
        assert len(resolved) == 5
        assert all(c.category == "vector" for c in resolved.cases)

    def test_suite_key_propagates(self, registry: CaseRegistry):
        suite_meta = SuiteMetadata(
            suite_key="my-key",
            title="T",
            description="D",
            schema_version="1.0",
            selection=SuiteSelection(),
        )
        resolved = resolve_suite(suite_meta, registry)
        assert resolved.suite_key == "my-key"

    def test_case_ids_property(self, registry: CaseRegistry):
        suite_meta = SuiteMetadata(
            suite_key="rasters",
            title="Rasters",
            description="Raster cases.",
            schema_version="1.0",
            selection=SuiteSelection(
                include_case_ids=[
                    "geotiff_nodata_small",
                    "geotiff_utm_boundary",
                ],
            ),
        )
        resolved = resolve_suite(suite_meta, registry)
        assert set(resolved.case_ids) == {
            "geotiff_nodata_small",
            "geotiff_utm_boundary",
        }

    def test_case_order_respected(self, registry: CaseRegistry):
        suite_meta = SuiteMetadata(
            suite_key="ordered",
            title="Ordered",
            description="Explicit order.",
            schema_version="1.0",
            selection=SuiteSelection(
                include_case_ids=[
                    "geotiff_nodata_small",
                    "geotiff_utm_boundary",
                ],
            ),
            case_order=["geotiff_utm_boundary", "geotiff_nodata_small"],
        )
        resolved = resolve_suite(suite_meta, registry)
        assert resolved.case_ids == [
            "geotiff_utm_boundary",
            "geotiff_nodata_small",
        ]

    def test_empty_selection_returns_all(self, registry: CaseRegistry):
        suite_meta = SuiteMetadata(
            suite_key="all",
            title="All",
            description="Everything.",
            schema_version="1.0",
            selection=SuiteSelection(),
        )
        resolved = resolve_suite(suite_meta, registry)
        assert len(resolved) == len(registry)

    def test_repr(self, registry: CaseRegistry):
        suite_meta = SuiteMetadata(
            suite_key="repr-test",
            title="T",
            description="D",
            schema_version="1.0",
            selection=SuiteSelection(category="netcdf"),
        )
        resolved = resolve_suite(suite_meta, registry)
        assert "repr-test" in repr(resolved)
        assert "1 cases" in repr(resolved)


# ===================================================================
# load_and_resolve_suite — from YAML files
# ===================================================================

class TestLoadAndResolveSuite:
    """Test loading real suite YAML files and resolving them."""

    def test_core_vector_suite(self, registry: CaseRegistry):
        resolved = load_and_resolve_suite(_CORE_VECTOR_SUITE, registry)
        assert resolved.suite_key == "core-vector"
        assert len(resolved) == 5
        assert all(c.category == "vector" for c in resolved.cases)

    def test_core_vector_order(self, registry: CaseRegistry):
        resolved = load_and_resolve_suite(_CORE_VECTOR_SUITE, registry)
        expected_order = [
            "simple_valid_polygon",
            "polygon_with_hole",
            "self_intersecting_polygon",
            "dateline_crossing_polygon",
            "mixed_encoding_attributes",
        ]
        assert resolved.case_ids == expected_order

    def test_crs_edge_cases_suite(self, registry: CaseRegistry):
        resolved = load_and_resolve_suite(_CRS_SUITE, registry)
        assert resolved.suite_key == "crs-edge-cases"
        # Must include cases tagged with crs, antimeridian, utm, or reprojection
        ids = set(resolved.case_ids)
        assert "dateline_crossing_polygon" in ids
        assert "geotiff_utm_boundary" in ids

    def test_crs_suite_order(self, registry: CaseRegistry):
        resolved = load_and_resolve_suite(_CRS_SUITE, registry)
        assert resolved.case_ids[0] == "dateline_crossing_polygon"
        assert resolved.case_ids[1] == "geotiff_utm_boundary"

    def test_raster_nodata_suite(self, registry: CaseRegistry):
        resolved = load_and_resolve_suite(_NODATA_SUITE, registry)
        assert resolved.suite_key == "raster-nodata"
        ids = set(resolved.case_ids)
        assert "geotiff_nodata_small" in ids
        assert "latlon_small" in ids

    def test_raster_nodata_order(self, registry: CaseRegistry):
        resolved = load_and_resolve_suite(_NODATA_SUITE, registry)
        assert resolved.case_ids[0] == "geotiff_nodata_small"
        assert resolved.case_ids[1] == "latlon_small"

    def test_missing_suite_file_raises(self, registry: CaseRegistry):
        with pytest.raises(FileNotFoundError):
            load_and_resolve_suite(
                Path("/nonexistent/suite.yaml"), registry
            )


# ===================================================================
# load_all_suites — bulk resolution from suite-index.yaml
# ===================================================================

class TestLoadAllSuites:
    """Test loading all suites from the suite-index."""

    def test_loads_three_suites(self, registry: CaseRegistry):
        suites = load_all_suites(_SUITE_INDEX, registry)
        assert len(suites) == 3

    def test_all_are_resolved_suites(self, registry: CaseRegistry):
        suites = load_all_suites(_SUITE_INDEX, registry)
        for s in suites:
            assert isinstance(s, ResolvedSuite)
            assert len(s) > 0

    def test_suite_keys(self, registry: CaseRegistry):
        suites = load_all_suites(_SUITE_INDEX, registry)
        keys = {s.suite_key for s in suites}
        assert keys == {"core-vector", "crs-edge-cases", "raster-nodata"}

    def test_no_empty_suites(self, registry: CaseRegistry):
        suites = load_all_suites(_SUITE_INDEX, registry)
        for s in suites:
            assert len(s.cases) > 0, f"Suite {s.suite_key} has no cases"

    def test_default_index_path(self, registry: CaseRegistry):
        """load_all_suites() with no path uses the bundled index."""
        suites = load_all_suites(registry=registry)
        assert len(suites) == 3
