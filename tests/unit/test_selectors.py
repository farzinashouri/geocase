"""Tests for geocase.catalog.selectors — case filtering logic."""

from pathlib import Path

import pytest

from geocase.catalog.models import CaseMetadata, SuiteSelection
from geocase.catalog.registry import CaseRegistry
from geocase.catalog.selectors import matches_selection, select_cases


# ---------------------------------------------------------------------------
# Fixtures — registry & full case list
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_CASE_INDEX = _SRC / "metadata" / "case-index.yaml"


@pytest.fixture()
def all_cases() -> list[CaseMetadata]:
    """All indexed cases from the bundled catalog."""
    reg = CaseRegistry.from_index(_CASE_INDEX)
    return reg.list_cases()


# ===================================================================
# matches_selection — individual case vs. selection
# ===================================================================

class TestMatchesSelection:
    """Test the low-level single-case matcher."""

    @pytest.fixture()
    def vector_case(self, all_cases: list[CaseMetadata]) -> CaseMetadata:
        return next(c for c in all_cases if c.id == "simple_valid_polygon")

    @pytest.fixture()
    def raster_case(self, all_cases: list[CaseMetadata]) -> CaseMetadata:
        return next(c for c in all_cases if c.id == "geotiff_nodata_small")

    # -- empty selection matches everything --
    def test_empty_selection_matches_any(self, vector_case: CaseMetadata):
        sel = SuiteSelection()
        assert matches_selection(vector_case, sel) is True

    # -- category filter --
    def test_category_match(self, vector_case: CaseMetadata):
        sel = SuiteSelection(category="vector")
        assert matches_selection(vector_case, sel) is True

    def test_category_mismatch(self, vector_case: CaseMetadata):
        sel = SuiteSelection(category="raster")
        assert matches_selection(vector_case, sel) is False

    # -- test_tier filter --
    def test_geometry_type_match(self, vector_case: CaseMetadata):
        sel = SuiteSelection(geometry_type="Polygon")
        assert matches_selection(vector_case, sel) is True

    def test_geometry_type_mismatch(self, vector_case: CaseMetadata):
        sel = SuiteSelection(geometry_type="Point")
        assert matches_selection(vector_case, sel) is False

    def test_tier_match(self, vector_case: CaseMetadata):
        sel = SuiteSelection(test_tier="unit")
        assert matches_selection(vector_case, sel) is True

    def test_tier_mismatch(self, vector_case: CaseMetadata):
        sel = SuiteSelection(test_tier="slow")
        assert matches_selection(vector_case, sel) is False

    # -- storage_class filter --
    def test_storage_class_match(self, raster_case: CaseMetadata):
        sel = SuiteSelection(storage_class="bundled")
        assert matches_selection(raster_case, sel) is True

    def test_storage_class_mismatch(self, raster_case: CaseMetadata):
        sel = SuiteSelection(storage_class="remote")
        assert matches_selection(raster_case, sel) is False

    # -- format filter --
    def test_format_match(self, raster_case: CaseMetadata):
        sel = SuiteSelection(format="GeoTIFF")
        assert matches_selection(raster_case, sel) is True

    def test_format_mismatch(self, raster_case: CaseMetadata):
        sel = SuiteSelection(format="NetCDF")
        assert matches_selection(raster_case, sel) is False

    # -- size_class filter --
    def test_size_class_match(self, vector_case: CaseMetadata):
        sel = SuiteSelection(size_class="tiny")
        assert matches_selection(vector_case, sel) is True

    def test_size_class_mismatch(self, vector_case: CaseMetadata):
        sel = SuiteSelection(size_class="large")
        assert matches_selection(vector_case, sel) is False

    # -- tags_any --
    def test_tags_any_match(self, vector_case: CaseMetadata):
        sel = SuiteSelection(tags_any=["polygon", "nonexistent"])
        assert matches_selection(vector_case, sel) is True

    def test_tags_any_no_match(self, vector_case: CaseMetadata):
        sel = SuiteSelection(tags_any=["satellite", "cloud"])
        assert matches_selection(vector_case, sel) is False

    # -- tags_all --
    def test_tags_all_match(self, vector_case: CaseMetadata):
        sel = SuiteSelection(tags_all=["vector", "polygon"])
        assert matches_selection(vector_case, sel) is True

    def test_tags_all_partial_mismatch(self, vector_case: CaseMetadata):
        sel = SuiteSelection(tags_all=["vector", "raster"])
        assert matches_selection(vector_case, sel) is False

    # -- risk_types_any --
    def test_risk_types_any_match(self):
        reg = CaseRegistry.from_index(_CASE_INDEX)
        dateline = reg.get("dateline_crossing_polygon")
        sel = SuiteSelection(risk_types_any=["coordinate_wrapping"])
        assert matches_selection(dateline, sel) is True

    def test_risk_types_any_no_match(self, vector_case: CaseMetadata):
        sel = SuiteSelection(risk_types_any=["coordinate_wrapping"])
        assert matches_selection(vector_case, sel) is False

    # -- include_case_ids --
    def test_include_ids_match(self, vector_case: CaseMetadata):
        sel = SuiteSelection(include_case_ids=["simple_valid_polygon"])
        assert matches_selection(vector_case, sel) is True

    def test_include_ids_excludes_other(self, raster_case: CaseMetadata):
        sel = SuiteSelection(include_case_ids=["simple_valid_polygon"])
        assert matches_selection(raster_case, sel) is False

    # -- exclude_case_ids --
    def test_exclude_ids(self, vector_case: CaseMetadata):
        sel = SuiteSelection(exclude_case_ids=["simple_valid_polygon"])
        assert matches_selection(vector_case, sel) is False

    def test_exclude_ids_allows_other(self, raster_case: CaseMetadata):
        sel = SuiteSelection(exclude_case_ids=["simple_valid_polygon"])
        assert matches_selection(raster_case, sel) is True

    # -- combined filters --
    def test_combined_category_and_tags(self, all_cases: list[CaseMetadata]):
        sel = SuiteSelection(category="vector", tags_any=["hole"])
        matched = [c for c in all_cases if matches_selection(c, sel)]
        assert len(matched) == 1
        assert matched[0].id == "polygon_with_hole"


# ===================================================================
# select_cases — bulk selection
# ===================================================================

class TestSelectCases:
    """Test the top-level select_cases function."""

    def test_select_by_category_vector(self, all_cases: list[CaseMetadata]):
        result = select_cases(all_cases, category="vector")
        assert len(result) == 5
        assert all(c.category == "vector" for c in result)

    def test_select_by_category_raster(self, all_cases: list[CaseMetadata]):
        result = select_cases(all_cases, category="raster")
        assert len(result) == 7
        assert all(c.category == "raster" for c in result)

    def test_select_by_category_netcdf(self, all_cases: list[CaseMetadata]):
        result = select_cases(all_cases, category="netcdf")
        assert len(result) == 1
        assert result[0].id == "latlon_small"

    def test_select_all_bundled(self, all_cases: list[CaseMetadata]):
        result = select_cases(all_cases, storage_class="bundled")
        assert len(result) == len(all_cases)

    def test_select_by_format_geojson(self, all_cases: list[CaseMetadata]):
        result = select_cases(all_cases, format="GeoJSON")
        assert all(c.format == "GeoJSON" for c in result)

    def test_select_by_geometry_type_polygon(self, all_cases: list[CaseMetadata]):
        result = select_cases(
            all_cases,
            category="vector",
            geometry_type="Polygon",
        )
        assert len(result) == 4
        assert all(c.geometry_type == "Polygon" for c in result)

    def test_select_by_geometry_type_point(self, all_cases: list[CaseMetadata]):
        result = select_cases(
            all_cases,
            category="vector",
            geometry_type="Point",
        )
        assert len(result) == 1
        assert result[0].id == "mixed_encoding_attributes"

    def test_select_by_tags_any(self, all_cases: list[CaseMetadata]):
        result = select_cases(all_cases, tags_any=["nodata", "masking"])
        ids = {c.id for c in result}
        assert "geotiff_nodata_small" in ids
        assert "latlon_small" in ids

    def test_select_with_suite_selection_object(
        self, all_cases: list[CaseMetadata]
    ):
        sel = SuiteSelection(
            category="vector",
            storage_class="bundled",
            test_tier="unit",
        )
        result = select_cases(all_cases, sel)
        assert len(result) == 5

    def test_select_empty_when_nothing_matches(
        self, all_cases: list[CaseMetadata]
    ):
        result = select_cases(all_cases, category="satellite")
        assert result == []

    def test_select_with_exclude(self, all_cases: list[CaseMetadata]):
        result = select_cases(
            all_cases,
            category="vector",
            exclude_ids=["simple_valid_polygon", "polygon_with_hole"],
        )
        ids = {c.id for c in result}
        assert "simple_valid_polygon" not in ids
        assert "polygon_with_hole" not in ids
        assert len(result) == 3

    def test_select_with_include(self, all_cases: list[CaseMetadata]):
        result = select_cases(
            all_cases,
            include_ids=["dateline_crossing_polygon", "latlon_small"],
        )
        assert len(result) == 2
        assert {c.id for c in result} == {
            "dateline_crossing_polygon",
            "latlon_small",
        }
