"""Tests for geocase.catalog.suites — suite resolution logic."""

from pathlib import Path

import pytest

from geocase.catalog.loader import load_suite_index
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
_EXPECTED_SUITE_COUNT = len(load_suite_index(_SUITE_INDEX))

_CORE_VECTOR_SUITE = _SUITES / "core-vector.yaml"
_CRS_SUITE = _SUITES / "crs-edge-cases.yaml"
_NODATA_SUITE = _SUITES / "raster-nodata.yaml"
_VECTOR_SCHEMA_SUITE = _SUITES / "vector-schema-encoding.yaml"


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
    """Exercises `resolve_suite()` with programmatically constructed suite metadata."""

    def test_select_all_vectors(self, registry: CaseRegistry):
        """Resolves a programmatic suite into all vector cases."""
        suite_meta = SuiteMetadata(
            suite_key="test-vectors",
            title="Test Vectors",
            description="All vector cases.",
            schema_version="1.0",
            selection=SuiteSelection(category="vector"),
        )
        resolved = resolve_suite(suite_meta, registry)
        assert isinstance(resolved, ResolvedSuite)
        expected = [case for case in registry.list_cases() if case.category == "vector"]
        assert len(resolved) == len(expected)
        assert all(c.category == "vector" for c in resolved.cases)

    def test_suite_key_propagates(self, registry: CaseRegistry):
        """Preserves the suite key on the resolved suite."""
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
        """Exposes resolved case ids through the `case_ids` helper."""
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
        """Applies explicit case order after selection."""
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
        """Treats an empty programmatic selection as all registry cases."""
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
        """Includes the suite key and case count in the resolved suite representation."""
        suite_meta = SuiteMetadata(
            suite_key="repr-test",
            title="T",
            description="D",
            schema_version="1.0",
            selection=SuiteSelection(category="netcdf"),
        )
        resolved = resolve_suite(suite_meta, registry)
        assert "repr-test" in repr(resolved)
        assert f"{len(resolved)} cases" in repr(resolved)


# ===================================================================
# load_and_resolve_suite — from YAML files
# ===================================================================

class TestLoadAndResolveSuite:
    """Exercises loading and resolving real suite YAML files."""

    def test_core_vector_suite(self, registry: CaseRegistry):
        """Resolves the core vector suite to its expected ordered vector cases."""
        resolved = load_and_resolve_suite(_CORE_VECTOR_SUITE, registry)
        assert resolved.suite_key == "core-vector"
        expected_order = [
            "simple_valid_polygon",
            "polygon_with_hole",
            "self_intersecting_polygon",
            "dateline_crossing_polygon",
            "mixed_encoding_attributes",
        ]
        assert len(resolved) == len(expected_order)
        assert all(c.category == "vector" for c in resolved.cases)

    def test_core_vector_order(self, registry: CaseRegistry):
        """Keeps the declared case order from the core vector suite file."""
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
        """Resolves the CRS edge-case suite to cases tagged for CRS-related behavior."""
        resolved = load_and_resolve_suite(_CRS_SUITE, registry)
        assert resolved.suite_key == "crs-edge-cases"
        # Must include cases tagged with crs, antimeridian, utm, or reprojection
        ids = set(resolved.case_ids)
        assert "dateline_crossing_polygon" in ids
        assert "geotiff_utm_boundary" in ids

    def test_crs_suite_order(self, registry: CaseRegistry):
        """Preserves the declared order of the CRS edge-case suite."""
        resolved = load_and_resolve_suite(_CRS_SUITE, registry)
        assert resolved.case_ids[0] == "dateline_crossing_polygon"
        assert resolved.case_ids[1] == "geotiff_utm_boundary"

    def test_raster_nodata_suite(self, registry: CaseRegistry):
        """Resolves the raster NoData suite to the expected NoData-related cases."""
        resolved = load_and_resolve_suite(_NODATA_SUITE, registry)
        assert resolved.suite_key == "raster-nodata"
        ids = set(resolved.case_ids)
        assert "geotiff_nodata_small" in ids
        assert "latlon_small" in ids

    def test_raster_nodata_order(self, registry: CaseRegistry):
        """Keeps the declared order of the raster NoData suite."""
        resolved = load_and_resolve_suite(_NODATA_SUITE, registry)
        assert resolved.case_ids[0] == "geotiff_nodata_small"
        assert resolved.case_ids[1] == "latlon_small"

    def test_missing_suite_file_raises(self, registry: CaseRegistry):
        """Raises `FileNotFoundError` when resolving a missing suite file."""
        with pytest.raises(FileNotFoundError):
            load_and_resolve_suite(
                Path("/nonexistent/suite.yaml"), registry
            )

    def test_vector_schema_encoding_suite_includes_step2_format_cases(
        self, registry: CaseRegistry
    ):
        """Resolves the schema-and-encoding suite with the step 2 format-specific cases."""
        resolved = load_and_resolve_suite(_VECTOR_SCHEMA_SUITE, registry)
        ids = set(resolved.case_ids)
        assert "parquet_mixed_schema_attributes" in ids
        assert "format_limited_kml_case" in ids

    def test_vector_crs_edge_suite_includes_step3_polar_equator_cases(
        self, registry: CaseRegistry
    ):
        """Resolves the CRS edge suite with the step 3 polar and equatorial polygons."""
        resolved = load_and_resolve_suite(
            _SUITES / "vector-crs-edge.yaml", registry
        )
        ids = set(resolved.case_ids)
        assert "north_pole_polygon" in ids
        assert "south_pole_polygon" in ids
        assert "equator_polygon" in ids


# ===================================================================
# load_all_suites — bulk resolution from suite-index.yaml
# ===================================================================

class TestLoadAllSuites:
    """Exercises loading every bundled suite from the suite index."""

    def test_loads_three_suites(self, registry: CaseRegistry):
        """Loads every suite referenced by the bundled suite index."""
        suites = load_all_suites(_SUITE_INDEX, registry)
        assert len(suites) == _EXPECTED_SUITE_COUNT

    def test_all_are_resolved_suites(self, registry: CaseRegistry):
        """Returns non-empty `ResolvedSuite` objects for every indexed suite."""
        suites = load_all_suites(_SUITE_INDEX, registry)
        for s in suites:
            assert isinstance(s, ResolvedSuite)
            assert len(s) > 0

    def test_suite_keys(self, registry: CaseRegistry):
        """Loads the expected suite keys from the bundled suite index."""
        suites = load_all_suites(_SUITE_INDEX, registry)
        keys = {s.suite_key for s in suites}
        assert keys == {
            "core-vector",
            "crs-edge-cases",
            "raster-nodata",
            "vector-topology",
            "vector-crs-edge",
            "vector-schema-encoding",
        }

    def test_no_empty_suites(self, registry: CaseRegistry):
        """Ensures no indexed suite resolves to zero cases."""
        suites = load_all_suites(_SUITE_INDEX, registry)
        for s in suites:
            assert len(s.cases) > 0, f"Suite {s.suite_key} has no cases"

    def test_default_index_path(self, registry: CaseRegistry):
        """load_all_suites() with no path uses the bundled index."""
        suites = load_all_suites(registry=registry)
        assert len(suites) == _EXPECTED_SUITE_COUNT
