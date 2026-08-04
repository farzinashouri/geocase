"""Tests for geocase.catalog.registry — in-memory case lookup."""

from pathlib import Path

import pytest

from geocase.catalog.loader import load_case_index
from geocase.catalog.models import CaseMetadata
from geocase.catalog.registry import CaseRegistry, get_registry, reset_registry

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_METADATA = _SRC / "metadata"
_CASE_INDEX = _METADATA / "case-index.yaml"
_EXPECTED_CASE_COUNT = len(load_case_index(_CASE_INDEX))


# ===================================================================
# CaseRegistry.from_index
# ===================================================================


class TestCaseRegistryFromIndex:
    """Build a registry from the bundled case-index.yaml."""

    def test_loads_all_indexed_cases(self):
        """Test loads all indexed cases."""
        reg = CaseRegistry.from_index(_CASE_INDEX)
        assert len(reg) == _EXPECTED_CASE_COUNT

    def test_all_entries_are_case_metadata(self):
        """Test all entries are case metadata."""
        reg = CaseRegistry.from_index(_CASE_INDEX)
        for case in reg:
            assert isinstance(case, CaseMetadata)

    def test_ids_are_sorted(self):
        """Test ids are sorted."""
        reg = CaseRegistry.from_index(_CASE_INDEX)
        ids = reg.list_ids()
        assert ids == sorted(ids)

    def test_missing_index_raises(self):
        """Test missing index raises."""
        with pytest.raises(FileNotFoundError):
            CaseRegistry.from_index(Path("/nonexistent/case-index.yaml"))


# ===================================================================
# CaseRegistry.get / lookup
# ===================================================================


class TestCaseRegistryLookup:
    """Test lookup operations on a pre-built registry."""

    @pytest.fixture()
    def registry(self) -> CaseRegistry:
        return CaseRegistry.from_index(_CASE_INDEX)

    def test_get_existing_case(self, registry: CaseRegistry):
        """Test get existing case."""
        case = registry.get("dateline_crossing_polygon")
        assert case.id == "dateline_crossing_polygon"
        assert case.category == "vector"

    def test_get_raster_case(self, registry: CaseRegistry):
        """Test get raster case."""
        case = registry.get("geotiff_nodata_small")
        assert case.id == "geotiff_nodata_small"
        assert case.category == "raster"

    def test_get_rotated_raster_case(self, registry: CaseRegistry):
        """Test get rotated raster case."""
        case = registry.get("rotated_two_islands")
        assert case.id == "rotated_two_islands"
        assert case.category == "raster"
        assert case.format == "GeoTIFF"
        assert "rotated" in case.tags

    def test_step3_raster_multiband_case_is_indexed(self, registry: CaseRegistry):
        """Test step3 raster multiband case is indexed."""
        case = registry.get("geotiff_multiband_small")
        assert case.id == "geotiff_multiband_small"
        assert case.category == "raster"
        assert case.format == "GeoTIFF"
        assert case.params.get("band_count") == 3

    @pytest.mark.parametrize(
        ("case_id", "expected_dtype"),
        [
            ("geotiff_int8_small", "int8"),
            ("geotiff_int16_small", "int16"),
            ("geotiff_int32_small", "int32"),
            ("geotiff_float64_small", "float64"),
        ],
    )
    def test_step3_raster_dtype_cases_are_indexed(
        self, registry: CaseRegistry, case_id: str, expected_dtype: str
    ):
        """Test step3 raster dtype cases are indexed."""
        case = registry.get(case_id)
        assert case.id == case_id
        assert case.category == "raster"
        assert case.format == "GeoTIFF"
        assert case.params.get("dtype") == expected_dtype

    def test_get_netcdf_case(self, registry: CaseRegistry):
        """Test get netcdf case."""
        case = registry.get("latlon_small")
        assert case.category == "netcdf"

    def test_get_missing_raises_key_error(self, registry: CaseRegistry):
        """Test get missing raises key error."""
        with pytest.raises(KeyError, match="no_such_case"):
            registry.get("no_such_case")

    @pytest.mark.parametrize(
        "case_id",
        [
            "parquet_mixed_schema_attributes",
            "format_limited_kml_case",
        ],
    )
    def test_step2_format_specific_cases_are_indexed(
        self, registry: CaseRegistry, case_id: str
    ):
        """Test step2 format specific cases are indexed."""
        case = registry.get(case_id)
        assert case.id == case_id
        assert case.category == "vector"

    @pytest.mark.parametrize(
        "case_id",
        [
            "north_pole_polygon",
            "south_pole_polygon",
            "equator_polygon",
        ],
    )
    def test_step3_polar_equator_polygon_cases_are_indexed(
        self, registry: CaseRegistry, case_id: str
    ):
        """Test step3 polar equator polygon cases are indexed."""
        case = registry.get(case_id)
        assert case.id == case_id
        assert case.category == "vector"
        assert case.geometry_type == "Polygon"
        assert case.format == "GeoJSON"

    def test_step4_empty_geometry_gpkg_covers_null_semantics(
        self, registry: CaseRegistry
    ):
        """Step 4 decision: empty_geometry_gpkg already covers NULL vs EMPTY.

        No separate null_geometry_row_gpkg case is needed because the
        existing case contains both a SQL-NULL row and a WKB-EMPTY row,
        and its metadata explicitly tracks both.  This test codifies that
        decision so it cannot silently regress.
        """
        case = registry.get("empty_geometry_gpkg")
        assert case.format == "GPKG"
        # Must declare null-handling awareness in tags
        assert "null_handling" in case.tags
        assert "empty" in case.tags
        # Params must separately track null vs empty row counts
        assert case.params.get("null_geometry_rows", 0) >= 1
        assert case.params.get("empty_geometry_rows", 0) >= 1
        # No separate null_geometry_row_gpkg should exist
        assert "null_geometry_row_gpkg" not in registry

    def test_step5_matrix_completeness_baseline(self, registry: CaseRegistry):
        """Step 5 decision: full geometry×format matrix completeness is
        deferred past v1.0.

        This test documents the v1.0 coverage gate:
        - all 7 geometry types have at least one case,
        - the 10 core formats each cover at least 6 of 7 geometry types,
        - GeometryCollection and Arrow-family sparse cells are explicitly
          deferred.
        """
        from collections import Counter

        combos: Counter[tuple[str, str]] = Counter()
        geom_types: set[str] = set()

        for case in registry.list_cases():
            if case.category != "vector":
                continue
            gt = case.geometry_type or "Mixed"
            combos[(gt, case.format)] += 1
            if gt != "Mixed":
                geom_types.add(gt)

        # All 7 geometry families must have at least 1 case
        expected_families = {
            "Point",
            "MultiPoint",
            "LineString",
            "MultiLineString",
            "Polygon",
            "MultiPolygon",
            "GeometryCollection",
        }
        assert expected_families <= geom_types

        # Core formats must each cover >= 6 geometry types
        core_formats = [
            "GeoJSON",
            "GPKG",
            "Shapefile",
            "CSV_WKT",
            "FlatGeobuf",
            "GML",
            "KML",
            "SQLite",
            "WKB",
            "WKT",
        ]
        for fmt in core_formats:
            covered = sum(1 for gt in expected_families if combos.get((gt, fmt), 0) > 0)
            assert covered >= 6, f"{fmt} only covers {covered}/7 geometry types"

    def test_contains(self, registry: CaseRegistry):
        """Test contains."""
        assert "simple_valid_polygon" in registry
        assert "nonexistent" not in registry

    def test_list_cases_length(self, registry: CaseRegistry):
        """Test list cases length."""
        assert len(registry.list_cases()) == _EXPECTED_CASE_COUNT

    def test_list_ids_contains_known(self, registry: CaseRegistry):
        """Test list ids contains known."""
        ids = registry.list_ids()
        assert "dateline_crossing_polygon" in ids
        assert "polygon_with_hole" in ids
        assert "geotiff_utm_boundary" in ids

    def test_iter(self, registry: CaseRegistry):
        """Test iter."""
        cases = list(registry)
        assert len(cases) == _EXPECTED_CASE_COUNT
        assert all(isinstance(c, CaseMetadata) for c in cases)

    def test_repr(self, registry: CaseRegistry):
        """Test repr."""
        assert f"{_EXPECTED_CASE_COUNT} cases" in repr(registry)


# ===================================================================
# get_registry / reset_registry (singleton)
# ===================================================================


class TestDefaultRegistry:
    """Test the module-level singleton helpers."""

    def setup_method(self):
        reset_registry()

    def teardown_method(self):
        reset_registry()

    def test_get_registry_returns_registry(self):
        """Test get registry returns registry."""
        reg = get_registry()
        assert isinstance(reg, CaseRegistry)
        assert len(reg) == _EXPECTED_CASE_COUNT

    def test_get_registry_is_cached(self):
        """Test get registry is cached."""
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_reload_creates_new_instance(self):
        """Test reload creates new instance."""
        r1 = get_registry()
        r2 = get_registry(reload=True)
        assert r1 is not r2
        assert len(r2) == _EXPECTED_CASE_COUNT

    def test_reset_clears_cache(self):
        """Test reset clears cache."""
        r1 = get_registry()
        reset_registry()
        r2 = get_registry()
        assert r1 is not r2
