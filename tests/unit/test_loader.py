"""Tests for geocase.catalog.loader — YAML loading utilities."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from geocase.catalog.loader import (
    load_case_index,
    load_case_metadata,
    load_suite_index,
    load_suite_metadata,
)
from geocase.catalog.models import CaseMetadata, SuiteMetadata


# ---------------------------------------------------------------------------
# Resolve paths relative to the package source tree
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_DATA = _SRC / "data"
_VEC = _DATA / "core" / "vector"
_METADATA = _SRC / "metadata"
_SUITES = _SRC / "catalog" / "suites"

_CASE_INDEX = _METADATA / "case-index.yaml"
_SUITE_INDEX = _METADATA / "suite-index.yaml"

_DATELINE_CASE = (
    _VEC / "special" / "dateline" / "dateline_crossing_polygon" / "case.yaml"
)
_SIMPLE_CASE = _VEC / "polygon" / "geojson" / "simple_valid_polygon" / "case.yaml"
_NODATA_CASE = _DATA / "core" / "raster" / "geotiff_nodata_small" / "case.yaml"
_NETCDF_CASE = _DATA / "core" / "netcdf" / "latlon_small" / "case.yaml"

_CORE_VECTOR_SUITE = _SUITES / "core-vector.yaml"
_CRS_SUITE = _SUITES / "crs-edge-cases.yaml"


# ===================================================================
# load_case_metadata — happy paths
# ===================================================================


class TestLoadCaseMetadata:
    """Load real case.yaml files from the bundled data directory."""

    def test_load_dateline_case(self):
        """Loads the dateline case metadata with its expected loader and EPSG hints."""
        case = load_case_metadata(_DATELINE_CASE)
        assert isinstance(case, CaseMetadata)
        assert case.id == "dateline_crossing_polygon"
        assert case.category == "vector"
        assert case.format == "GeoJSON"
        assert case.loader_hint == "geopandas"
        assert case.files.primary == "geometry.geojson"
        assert case.assertions.expected_epsg == 4326

    def test_load_simple_valid_polygon(self):
        """Loads validated vector metadata from a real bundled case file."""
        case = load_case_metadata(_SIMPLE_CASE)
        assert case.id == "simple_valid_polygon"
        assert case.category == "vector"
        assert case.status == "validated"

    def test_load_raster_case(self):
        """Loads raster metadata with GeoTIFF and NoData assertion hints."""
        case = load_case_metadata(_NODATA_CASE)
        assert case.id == "geotiff_nodata_small"
        assert case.category == "raster"
        assert case.format == "GeoTIFF"
        assert case.loader_hint == "rasterio"
        assert case.assertions.expect_nodata is True

    def test_load_netcdf_case(self):
        """Loads NetCDF metadata with the xarray loader hint."""
        case = load_case_metadata(_NETCDF_CASE)
        assert case.id == "latlon_small"
        assert case.category == "netcdf"
        assert case.loader_hint == "xarray"


class TestLoadCaseMetadataAllCases:
    """Every case.yaml listed in case-index.yaml must load without error."""

    def test_all_indexed_cases_load(self):
        """Loads every case referenced by the bundled case index."""
        paths = load_case_index(_CASE_INDEX)
        assert len(paths) >= 8, f"Expected at least 8 cases, got {len(paths)}"

        for rel_path in paths:
            full_path = _SRC / rel_path
            case = load_case_metadata(full_path)
            assert isinstance(case, CaseMetadata), f"Failed for {rel_path}"
            assert case.id, f"Empty id in {rel_path}"


# ===================================================================
# load_case_metadata — error paths
# ===================================================================


class TestLoadCaseMetadataErrors:
    def test_missing_file(self):
        """Raises `FileNotFoundError` for a missing case metadata file."""
        with pytest.raises(FileNotFoundError):
            load_case_metadata(Path("/nonexistent/case.yaml"))

    def test_empty_yaml_file(self, tmp_path):
        """Rejects an empty case YAML file."""
        empty = tmp_path / "case.yaml"
        empty.write_text("")
        with pytest.raises(ValueError, match="Empty YAML"):
            load_case_metadata(empty)

    def test_invalid_schema(self, tmp_path):
        """Rejects case YAML that fails model validation."""
        bad = tmp_path / "case.yaml"
        bad.write_text("id: BAD_CASE\ntitle: Bad\n")
        with pytest.raises(ValidationError):
            load_case_metadata(bad)


# ===================================================================
# load_suite_metadata
# ===================================================================


class TestLoadSuiteMetadata:
    def test_load_core_vector_suite(self):
        """Loads the core vector suite with its bundled filters and case order."""
        suite = load_suite_metadata(_CORE_VECTOR_SUITE)
        assert isinstance(suite, SuiteMetadata)
        assert suite.suite_key == "core-vector"
        assert suite.selection.category == "vector"
        assert suite.selection.storage_class == "bundled"
        assert "simple_valid_polygon" in suite.case_order

    def test_load_crs_edge_cases_suite(self):
        """Loads the CRS edge-case suite with its `crs` tag filter."""
        suite = load_suite_metadata(_CRS_SUITE)
        assert suite.suite_key == "crs-edge-cases"
        assert "crs" in suite.selection.tags_any

    def test_missing_suite_file(self):
        """Raises `FileNotFoundError` for a missing suite metadata file."""
        with pytest.raises(FileNotFoundError):
            load_suite_metadata(Path("/nonexistent/suite.yaml"))

    def test_empty_suite_file(self, tmp_path):
        """Rejects an empty suite YAML file."""
        empty = tmp_path / "suite.yaml"
        empty.write_text("")
        with pytest.raises(ValueError, match="Empty YAML"):
            load_suite_metadata(empty)


# ===================================================================
# load_case_index
# ===================================================================


class TestLoadCaseIndex:
    def test_load_real_index(self):
        """Loads the bundled case index into a list of case metadata paths."""
        paths = load_case_index(_CASE_INDEX)
        assert isinstance(paths, list)
        assert len(paths) >= 8
        assert all(p.endswith(".yaml") for p in paths)

    def test_missing_index(self):
        """Raises `FileNotFoundError` for a missing case index path."""
        with pytest.raises(FileNotFoundError):
            load_case_index(Path("/nonexistent/case-index.yaml"))

    def test_empty_index(self, tmp_path):
        """Treats an empty case index file as an empty list."""
        empty = tmp_path / "case-index.yaml"
        empty.write_text("")
        result = load_case_index(empty)
        assert result == []

    def test_index_without_cases_key(self, tmp_path):
        """Treats a case index without a `cases` key as empty."""
        no_key = tmp_path / "case-index.yaml"
        no_key.write_text("schema_version: '1.0'\n")
        result = load_case_index(no_key)
        assert result == []


# ===================================================================
# load_suite_index
# ===================================================================


class TestLoadSuiteIndex:
    def test_load_real_index(self):
        """Loads the bundled suite index into a list of suite metadata paths."""
        paths = load_suite_index(_SUITE_INDEX)
        assert isinstance(paths, list)
        assert len(paths) >= 3
        assert any("core-vector" in p for p in paths)

    def test_missing_index(self):
        """Raises `FileNotFoundError` for a missing suite index path."""
        with pytest.raises(FileNotFoundError):
            load_suite_index(Path("/nonexistent/suite-index.yaml"))
