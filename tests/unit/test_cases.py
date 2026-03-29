"""Tests for geocase.cases — runtime case wrappers (Wave 3).

Covers BaseCase, VectorCase, RasterCase, NetCDFCase, and create_case
factory, exercising real bundled data files.
"""

from pathlib import Path

import pytest

from geocase.catalog.loader import load_case_metadata
from geocase.catalog.models import CaseMetadata
from geocase.cases.base import BaseCase
from geocase.cases.factory import create_case
from geocase.cases.netcdf import NetCDFCase
from geocase.cases.raster import RasterCase
from geocase.cases.vector import VectorCase


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_DATA = _SRC / "data"

# Vector cases
_SIMPLE = _DATA / "core" / "vector" / "simple_valid_polygon"
_HOLE = _DATA / "core" / "vector" / "polygon_with_hole"
_SELF_INTER = _DATA / "core" / "vector" / "self_intersecting_polygon"
_DATELINE = _DATA / "core" / "vector" / "dateline_crossing_polygon"
_ENCODING = _DATA / "core" / "vector" / "mixed_encoding_attributes"

# Raster cases
_NODATA = _DATA / "core" / "raster" / "geotiff_nodata_small"
_UTM = _DATA / "core" / "raster" / "geotiff_utm_boundary"

# NetCDF cases
_LATLON = _DATA / "core" / "netcdf" / "latlon_small"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_meta(case_dir: Path) -> CaseMetadata:
    return load_case_metadata(case_dir / "case.yaml")


# ===================================================================
# BaseCase
# ===================================================================

class TestBaseCase:
    """Test the base case wrapper (path resolution, metadata access)."""

    def test_metadata_accessible(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.metadata is meta
        assert case.id == "simple_valid_polygon"
        assert case.title == "Simple Valid Polygon"

    def test_category(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.category == "vector"

    def test_tags(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert "polygon" in case.tags

    def test_primary_path(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.primary_path == _SIMPLE / "geometry.geojson"

    def test_primary_exists(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.primary_exists() is True

    def test_notes_path(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.notes_path == _SIMPLE / "notes.md"

    def test_notes_path_none_when_absent(self):
        meta = _load_meta(_SIMPLE)
        meta_dict = meta.model_dump()
        meta_dict["files"]["notes"] = None
        meta2 = CaseMetadata.model_validate(meta_dict)
        case = BaseCase(meta2, _SIMPLE)
        assert case.notes_path is None

    def test_sidecar_paths_empty(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.sidecar_paths() == []

    def test_root_dir(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.root_dir == _SIMPLE.resolve()

    def test_assertions(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.assertions.expect_loadable is True

    def test_params(self):
        meta = _load_meta(_HOLE)
        case = BaseCase(meta, _HOLE)
        assert case.params["has_holes"] is True

    def test_files(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.files.primary == "geometry.geojson"

    def test_repr(self):
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert "BaseCase" in repr(case)
        assert "simple_valid_polygon" in repr(case)


# ===================================================================
# VectorCase
# ===================================================================

class TestVectorCase:
    """Test VectorCase construction and loading."""

    def test_construct_from_vector_metadata(self):
        meta = _load_meta(_SIMPLE)
        case = VectorCase(meta, _SIMPLE)
        assert case.id == "simple_valid_polygon"

    def test_reject_non_vector_metadata(self):
        meta = _load_meta(_NODATA)  # raster case
        with pytest.raises(ValueError, match="category='vector'"):
            VectorCase(meta, _NODATA)

    def test_load_simple_polygon(self):
        meta = _load_meta(_SIMPLE)
        case = VectorCase(meta, _SIMPLE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None

    def test_load_polygon_with_hole(self):
        meta = _load_meta(_HOLE)
        case = VectorCase(meta, _HOLE)
        gdf = case.load()
        geom = gdf.geometry.iloc[0]
        # Polygon with hole has at least one interior ring
        assert len(list(geom.interiors)) == 1

    def test_load_self_intersecting(self):
        meta = _load_meta(_SELF_INTER)
        case = VectorCase(meta, _SELF_INTER)
        gdf = case.load()
        geom = gdf.geometry.iloc[0]
        # Self-intersecting polygon is not valid by OGC standards
        assert geom.is_valid is False

    def test_load_dateline_crossing(self):
        meta = _load_meta(_DATELINE)
        case = VectorCase(meta, _DATELINE)
        gdf = case.load()
        assert len(gdf) == 1
        # Bounding box should span across 170-190 longitude
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        assert bounds[0] >= 170.0

    def test_load_gpkg(self):
        meta = _load_meta(_ENCODING)
        case = VectorCase(meta, _ENCODING)
        gdf = case.load()
        assert len(gdf) == 3
        assert "Café" in gdf["name"].values

    def test_crs_preserved(self):
        meta = _load_meta(_SIMPLE)
        case = VectorCase(meta, _SIMPLE)
        gdf = case.load()
        assert gdf.crs.to_epsg() == 4326

    def test_missing_file_raises(self):
        meta = _load_meta(_SIMPLE)
        # Point to a non-existent directory
        fake_dir = Path("/tmp/geocase_nonexistent_case")
        case = VectorCase(meta, fake_dir)
        with pytest.raises(FileNotFoundError):
            case.load()

    def test_repr(self):
        meta = _load_meta(_SIMPLE)
        case = VectorCase(meta, _SIMPLE)
        assert "VectorCase" in repr(case)


# ===================================================================
# RasterCase
# ===================================================================

class TestRasterCase:
    """Test RasterCase construction and loading."""

    def test_construct_from_raster_metadata(self):
        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        assert case.id == "geotiff_nodata_small"

    def test_reject_non_raster_metadata(self):
        meta = _load_meta(_SIMPLE)  # vector case
        with pytest.raises(ValueError, match="category='raster'"):
            RasterCase(meta, _SIMPLE)

    def test_open_nodata_raster(self):
        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        with case.open() as src:
            assert src.count == 1
            assert src.width == 10
            assert src.height == 10
            assert src.nodata == -9999.0

    def test_open_crs(self):
        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        with case.open() as src:
            assert src.crs.to_epsg() == 32633

    def test_open_utm_boundary(self):
        meta = _load_meta(_UTM)
        case = RasterCase(meta, _UTM)
        with case.open() as src:
            assert src.count == 1
            assert src.width == 20
            assert src.height == 20

    def test_read_band(self):
        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        data, profile, nodata = case.read(1)
        assert data.shape == (10, 10)
        assert nodata == -9999.0
        assert profile["driver"] == "GTiff"

    def test_nodata_pixels_present(self):
        import numpy as np

        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        data, _, nodata = case.read(1)
        # We injected NoData at (0,0) and (5,5)
        assert data[0, 0] == nodata
        assert data[5, 5] == nodata

    def test_missing_file_raises(self):
        meta = _load_meta(_NODATA)
        fake_dir = Path("/tmp/geocase_nonexistent_raster")
        case = RasterCase(meta, fake_dir)
        with pytest.raises(FileNotFoundError):
            with case.open():
                pass

    def test_repr(self):
        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        assert "RasterCase" in repr(case)


# ===================================================================
# NetCDFCase
# ===================================================================

class TestNetCDFCase:
    """Test NetCDFCase construction and loading."""

    def test_construct_from_netcdf_metadata(self):
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        assert case.id == "latlon_small"

    def test_reject_non_netcdf_metadata(self):
        meta = _load_meta(_SIMPLE)  # vector case
        with pytest.raises(ValueError, match="category='netcdf'"):
            NetCDFCase(meta, _SIMPLE)

    def test_load_dataset(self):
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        ds = case.load()
        assert "temperature" in ds.data_vars
        ds.close()

    def test_dimensions(self):
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        ds = case.load()
        assert "latitude" in ds.sizes
        assert "longitude" in ds.sizes
        assert ds.sizes["latitude"] == 5
        assert ds.sizes["longitude"] == 8
        ds.close()

    def test_coordinates(self):
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        ds = case.load()
        assert ds["latitude"].values[0] == 40.0
        assert ds["latitude"].values[-1] == 50.0
        ds.close()

    def test_fill_value(self):
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        ds = case.load()
        temp = ds["temperature"]
        # xarray consumes _FillValue into encoding during open_dataset
        assert temp.encoding.get("_FillValue") == -9999.0
        ds.close()

    def test_cf_conventions(self):
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        ds = case.load()
        assert ds.attrs.get("Conventions") == "CF-1.8"
        ds.close()

    def test_missing_file_raises(self):
        meta = _load_meta(_LATLON)
        fake_dir = Path("/tmp/geocase_nonexistent_nc")
        case = NetCDFCase(meta, fake_dir)
        with pytest.raises(FileNotFoundError):
            case.load()

    def test_repr(self):
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        assert "NetCDFCase" in repr(case)


# ===================================================================
# Factory — create_case
# ===================================================================

class TestCreateCase:
    """Test the create_case() factory dispatch."""

    def test_creates_vector_case(self):
        meta = _load_meta(_SIMPLE)
        case = create_case(meta, _SIMPLE)
        assert isinstance(case, VectorCase)

    def test_creates_raster_case(self):
        meta = _load_meta(_NODATA)
        case = create_case(meta, _NODATA)
        assert isinstance(case, RasterCase)

    def test_creates_netcdf_case(self):
        meta = _load_meta(_LATLON)
        case = create_case(meta, _LATLON)
        assert isinstance(case, NetCDFCase)

    def test_all_are_base_case(self):
        for case_dir in [_SIMPLE, _NODATA, _LATLON]:
            meta = _load_meta(case_dir)
            case = create_case(meta, case_dir)
            assert isinstance(case, BaseCase)

    def test_unsupported_category_raises(self):
        meta = _load_meta(_SIMPLE)
        # Force an unsupported category
        meta_dict = meta.model_dump()
        meta_dict["category"] = "satellite"
        meta2 = CaseMetadata.model_validate(meta_dict)
        with pytest.raises(ValueError, match="satellite"):
            create_case(meta2, _SIMPLE)

    def test_factory_produces_loadable_vector(self):
        meta = _load_meta(_DATELINE)
        case = create_case(meta, _DATELINE)
        assert isinstance(case, VectorCase)
        gdf = case.load()
        assert len(gdf) == 1

    def test_factory_produces_loadable_raster(self):
        meta = _load_meta(_NODATA)
        case = create_case(meta, _NODATA)
        assert isinstance(case, RasterCase)
        with case.open() as src:
            assert src.count == 1

    def test_factory_produces_loadable_netcdf(self):
        meta = _load_meta(_LATLON)
        case = create_case(meta, _LATLON)
        assert isinstance(case, NetCDFCase)
        ds = case.load()
        assert "temperature" in ds.data_vars
        ds.close()
