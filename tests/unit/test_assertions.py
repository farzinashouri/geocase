"""Tests for geocase.assertions — reusable geospatial checks (Wave 4).

Exercises all assertion functions against the real bundled test data.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest

from geocase.assertions.crs import assert_crs_units, assert_epsg, assert_has_crs
from geocase.assertions.geometry import (
    assert_feature_count,
    assert_geometry_type,
    assert_has_holes,
    assert_invalid_geometry,
    assert_no_holes,
    assert_valid_geometry,
)
from geocase.assertions.footprint import (
    assert_footprint_no_holes,
    assert_footprint_rectangularity,
    assert_footprint_similar_to_expected,
)
from geocase.assertions.metadata import (
    assert_case_loadable,
    assert_matches_raster_hints,
    assert_matches_vector_hints,
)
from geocase.assertions.raster import (
    assert_band_count,
    assert_dtype,
    assert_no_nodata_pixels,
    assert_nodata_masked,
    assert_nodata_value,
    assert_shape,
)
from geocase.assertions.topology import (
    assert_no_duplicates,
    assert_no_null_geometries,
    assert_no_self_intersections,
)
from geocase.catalog.loader import load_case_metadata
from geocase.cases.factory import create_case
from geocase.cases.raster import RasterCase
from geocase.cases.vector import VectorCase


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_DATA = _SRC / "data"

_SIMPLE = _DATA / "core" / "vector" / "simple_valid_polygon"
_HOLE = _DATA / "core" / "vector" / "polygon_with_hole"
_SELF_INTER = _DATA / "core" / "vector" / "self_intersecting_polygon"
_DATELINE = _DATA / "core" / "vector" / "dateline_crossing_polygon"
_ENCODING = _DATA / "core" / "vector" / "mixed_encoding_attributes"
_NODATA = _DATA / "core" / "raster" / "geotiff_nodata_small"
_UTM = _DATA / "core" / "raster" / "geotiff_utm_boundary"
_EDGE = _DATA / "core" / "raster" / "footprint_edge_cases"


def _meta(case_dir):
    return load_case_metadata(case_dir / "case.yaml")


# ===================================================================
# Geometry assertions
# ===================================================================

class TestAssertValidGeometry:

    def test_valid_polygon_passes(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_valid_geometry(gdf)  # should not raise

    def test_self_intersecting_fails(self):
        gdf = gpd.read_file(_SELF_INTER / "geometry.geojson")
        with pytest.raises(AssertionError, match="invalid"):
            assert_valid_geometry(gdf)

    def test_custom_message(self):
        gdf = gpd.read_file(_SELF_INTER / "geometry.geojson")
        with pytest.raises(AssertionError, match="custom msg"):
            assert_valid_geometry(gdf, msg="custom msg")


class TestAssertInvalidGeometry:

    def test_self_intersecting_passes(self):
        gdf = gpd.read_file(_SELF_INTER / "geometry.geojson")
        assert_invalid_geometry(gdf)  # should not raise

    def test_valid_polygon_fails(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="all are valid"):
            assert_invalid_geometry(gdf)


class TestAssertGeometryType:

    def test_polygon_type_passes(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_geometry_type(gdf, "Polygon")

    def test_polygon_type_with_list(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_geometry_type(gdf, ["Polygon", "MultiPolygon"])

    def test_wrong_type_fails(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="Unexpected"):
            assert_geometry_type(gdf, "Point")

    def test_point_type_for_encoding_case(self):
        gdf = gpd.read_file(_ENCODING / "mixed_attrs.gpkg")
        assert_geometry_type(gdf, "Point")


class TestAssertHasHoles:

    def test_polygon_with_hole_passes(self):
        gdf = gpd.read_file(_HOLE / "geometry.geojson")
        assert_has_holes(gdf)

    def test_simple_polygon_fails(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="hole"):
            assert_has_holes(gdf)


class TestAssertNoHoles:

    def test_simple_polygon_passes(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_no_holes(gdf)

    def test_polygon_with_hole_fails(self):
        gdf = gpd.read_file(_HOLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="interior rings"):
            assert_no_holes(gdf)


class TestAssertFeatureCount:

    def test_single_feature(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_feature_count(gdf, 1)

    def test_three_features(self):
        gdf = gpd.read_file(_ENCODING / "mixed_attrs.gpkg")
        assert_feature_count(gdf, 3)

    def test_wrong_count_fails(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="Expected 5"):
            assert_feature_count(gdf, 5)


# ===================================================================
# CRS assertions
# ===================================================================

class TestAssertHasCrs:

    def test_geodataframe_with_crs(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_has_crs(gdf)

    def test_no_crs_fails(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        gdf = gdf.set_crs(None, allow_override=True)
        with pytest.raises(AssertionError, match="no CRS"):
            assert_has_crs(gdf)

    def test_rasterio_dataset(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_has_crs(src)


class TestAssertEpsg:

    def test_epsg_4326(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_epsg(gdf, 4326)

    def test_wrong_epsg_fails(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="EPSG:32633"):
            assert_epsg(gdf, 32633)

    def test_rasterio_epsg_32633(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_epsg(src, 32633)

    def test_no_crs_fails(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        gdf = gdf.set_crs(None, allow_override=True)
        with pytest.raises(AssertionError, match="no CRS"):
            assert_epsg(gdf, 4326)


class TestAssertCrsUnits:

    def test_degree_units(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_crs_units(gdf, "degree")

    def test_metre_units(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_crs_units(src, "metre")

    def test_wrong_unit_fails(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="metre"):
            assert_crs_units(gdf, "metre")


# ===================================================================
# Raster assertions
# ===================================================================

class TestAssertBandCount:

    def test_single_band(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_band_count(src, 1)

    def test_wrong_band_count_fails(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            with pytest.raises(AssertionError, match="3 band"):
                assert_band_count(src, 3)


class TestAssertNodataValue:

    def test_nodata_present(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_nodata_value(src)

    def test_nodata_exact_value(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_nodata_value(src, -9999.0)

    def test_wrong_nodata_fails(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            with pytest.raises(AssertionError, match="NoData=0"):
                assert_nodata_value(src, 0)

    def test_no_nodata_fails(self):
        case = RasterCase(_meta(_UTM), _UTM)
        with case.open() as src:
            with pytest.raises(AssertionError, match="no NoData"):
                assert_nodata_value(src)


class TestAssertDtype:

    def test_float32(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_dtype(src, "float32")

    def test_wrong_dtype_fails(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            with pytest.raises(AssertionError, match="uint8"):
                assert_dtype(src, "uint8")


class TestAssertShape:

    def test_correct_shape(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_shape(src, 10, 10)

    def test_wrong_shape_fails(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            with pytest.raises(AssertionError, match="100, 100"):
                assert_shape(src, 100, 100)


class TestAssertNodataMasked:

    def test_nodata_pixels_present(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        data, _, nodata = case.read(1)
        assert_nodata_masked(data, nodata)

    def test_no_nodata_pixels_fails(self):
        # Create an array with no nodata pixels
        data = np.ones((10, 10), dtype=np.float32)
        with pytest.raises(AssertionError, match="No pixels"):
            assert_nodata_masked(data, -9999.0)


class TestAssertNoNodataPixels:

    def test_clean_array_passes(self):
        data = np.ones((10, 10), dtype=np.float32)
        assert_no_nodata_pixels(data, -9999.0)

    def test_array_with_nodata_fails(self):
        case = RasterCase(_meta(_NODATA), _NODATA)
        data, _, nodata = case.read(1)
        with pytest.raises(AssertionError, match="pixel"):
            assert_no_nodata_pixels(data, nodata)


# ===================================================================
# Topology assertions
# ===================================================================

class TestAssertNoSelfIntersections:

    def test_valid_polygon_passes(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_no_self_intersections(gdf)

    def test_self_intersecting_fails(self):
        gdf = gpd.read_file(_SELF_INTER / "geometry.geojson")
        with pytest.raises(AssertionError, match="self-intersect"):
            assert_no_self_intersections(gdf)


class TestAssertNoDuplicates:

    def test_unique_geometries_passes(self):
        gdf = gpd.read_file(_ENCODING / "mixed_attrs.gpkg")
        assert_no_duplicates(gdf)

    def test_duplicate_fails(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        # Stack the same feature twice
        gdf2 = gpd.GeoDataFrame(
            data={"name": ["a", "b"]},
            geometry=[gdf.geometry.iloc[0], gdf.geometry.iloc[0]],
            crs=gdf.crs,
        )
        with pytest.raises(AssertionError, match="Duplicate"):
            assert_no_duplicates(gdf2)


class TestAssertNoNullGeometries:

    def test_no_nulls_passes(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_no_null_geometries(gdf)

    def test_null_geometry_fails(self):
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        gdf.loc[len(gdf)] = {"name": "empty", "geometry": None}
        with pytest.raises(AssertionError, match="null or empty"):
            assert_no_null_geometries(gdf)


# ===================================================================
# Metadata assertions (high-level)
# ===================================================================

class TestAssertCaseLoadable:

    def test_existing_case_passes(self):
        meta = _meta(_SIMPLE)
        case = create_case(meta, _SIMPLE)
        assert_case_loadable(case)

    def test_missing_file_fails(self):
        meta = _meta(_SIMPLE)
        case = create_case(meta, Path("/tmp/nonexistent_geocase"))
        with pytest.raises(AssertionError, match="primary file not found"):
            assert_case_loadable(case)


class TestAssertMatchesVectorHints:

    def test_simple_valid_passes_all_hints(self):
        meta = _meta(_SIMPLE)
        case = VectorCase(meta, _SIMPLE)
        gdf = case.load()
        assert_matches_vector_hints(case, gdf)

    def test_polygon_with_hole_passes(self):
        meta = _meta(_HOLE)
        case = VectorCase(meta, _HOLE)
        gdf = case.load()
        assert_matches_vector_hints(case, gdf)

    def test_self_intersecting_passes(self):
        # expect_valid_geometry is False — so this should pass
        meta = _meta(_SELF_INTER)
        case = VectorCase(meta, _SELF_INTER)
        gdf = case.load()
        assert_matches_vector_hints(case, gdf)

    def test_dateline_crossing_passes(self):
        meta = _meta(_DATELINE)
        case = VectorCase(meta, _DATELINE)
        gdf = case.load()
        assert_matches_vector_hints(case, gdf)

    def test_encoding_case_passes(self):
        meta = _meta(_ENCODING)
        case = VectorCase(meta, _ENCODING)
        gdf = case.load()
        assert_matches_vector_hints(case, gdf)


class TestAssertMatchesRasterHints:

    def test_nodata_raster_passes(self):
        meta = _meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        with case.open() as src:
            assert_matches_raster_hints(case, src)

    def test_utm_boundary_passes(self):
        meta = _meta(_UTM)
        case = RasterCase(meta, _UTM)
        with case.open() as src:
            assert_matches_raster_hints(case, src)


# ===================================================================
# Footprint assertions
# ===================================================================

class TestFootprintAssertions:

    def test_no_holes_passes_on_expected_footprint(self):
        expected = gpd.read_file(_EDGE / "all_valid_rectangular_footprint.geojson")
        assert_footprint_no_holes(expected)

    def test_rectangularity_strict_can_fail_on_complex_shape(self):
        complex_fp = gpd.read_file(_EDGE / "rotated_two_islands_footprint.geojson")
        with pytest.raises(AssertionError, match="rectangularity ratio"):
            assert_footprint_rectangularity(complex_fp, min_ratio=0.999)

    def test_similarity_against_expected_fixture(self):
        expected = gpd.read_file(_EDGE / "hole_center_nodata_footprint.geojson")
        actual = gpd.read_file(_EDGE / "hole_center_nodata_footprint.geojson")
        assert_footprint_similar_to_expected(actual, expected, max_diff_ratio=0.0)
