"""Tests for geocase.assertions — reusable geospatial checks (Wave 4).

Exercises all assertion functions against the real bundled test data.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest

from geocase.assertions.crs import assert_crs_units, assert_epsg, assert_has_crs
from geocase.assertions.footprint import (
    assert_footprint_no_holes,
    assert_footprint_rectangularity,
    assert_footprint_similar_to_expected,
)
from geocase.assertions.geometry import (
    assert_feature_count,
    assert_geometry_type,
    assert_has_holes,
    assert_invalid_geometry,
    assert_no_holes,
    assert_valid_geometry,
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
from geocase.cases.factory import create_case
from geocase.cases.raster import RasterCase
from geocase.cases.vector import VectorCase
from geocase.catalog.loader import load_case_metadata

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_DATA = _SRC / "data"
_VEC = _DATA / "core" / "vector"

_SIMPLE = _VEC / "polygon" / "geojson" / "simple_valid_polygon"
_HOLE = _VEC / "special" / "holes" / "polygon_with_hole"
_SELF_INTER = _VEC / "special" / "invalid" / "self_intersecting_polygon"
_DATELINE = _VEC / "special" / "dateline" / "dateline_crossing_polygon"
_ENCODING = _VEC / "special" / "encoding" / "mixed_encoding_attributes"
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
        """Does not raise for a valid polygon geometry."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_valid_geometry(gdf)  # should not raise

    def test_self_intersecting_fails(self):
        """Raises when a self-intersecting polygon is validated as valid."""
        gdf = gpd.read_file(_SELF_INTER / "geometry.geojson")
        with pytest.raises(AssertionError, match="invalid"):
            assert_valid_geometry(gdf)

    def test_custom_message(self):
        """Propagates a custom assertion message on geometry validation failure."""
        gdf = gpd.read_file(_SELF_INTER / "geometry.geojson")
        with pytest.raises(AssertionError, match="custom msg"):
            assert_valid_geometry(gdf, msg="custom msg")


class TestAssertInvalidGeometry:
    def test_self_intersecting_passes(self):
        """Does not raise when invalid-geometry sees a self-intersecting polygon."""
        gdf = gpd.read_file(_SELF_INTER / "geometry.geojson")
        assert_invalid_geometry(gdf)  # should not raise

    def test_valid_polygon_fails(self):
        """Raises when invalid-geometry assertion receives only valid features."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="all are valid"):
            assert_invalid_geometry(gdf)


class TestAssertGeometryType:
    def test_polygon_type_passes(self):
        """Accepts a GeoDataFrame whose geometry type matches the expected type."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_geometry_type(gdf, "Polygon")

    def test_polygon_type_with_list(self):
        """Accepts a geometry type when it matches any allowed type."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_geometry_type(gdf, ["Polygon", "MultiPolygon"])

    def test_wrong_type_fails(self):
        """Raises when the geometry type does not match the expected type."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="Unexpected"):
            assert_geometry_type(gdf, "Point")

    def test_point_type_for_encoding_case(self):
        """Detects point geometry in the encoding edge-case fixture."""
        gdf = gpd.read_file(_ENCODING / "mixed_attrs.gpkg")
        assert_geometry_type(gdf, "Point")


class TestAssertHasHoles:
    def test_polygon_with_hole_passes(self):
        """Detects interior rings in the polygon-with-hole fixture."""
        gdf = gpd.read_file(_HOLE / "geometry.geojson")
        assert_has_holes(gdf)

    def test_simple_polygon_fails(self):
        """Raises when no polygon holes are present."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="hole"):
            assert_has_holes(gdf)


class TestAssertNoHoles:
    def test_simple_polygon_passes(self):
        """Passes when a polygon has no interior rings."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_no_holes(gdf)

    def test_polygon_with_hole_fails(self):
        """Raises when interior rings are present."""
        gdf = gpd.read_file(_HOLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="interior rings"):
            assert_no_holes(gdf)


class TestAssertFeatureCount:
    def test_single_feature(self):
        """Validates a one-feature GeoDataFrame."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_feature_count(gdf, 1)

    def test_three_features(self):
        """Validates the expected three-feature encoding fixture."""
        gdf = gpd.read_file(_ENCODING / "mixed_attrs.gpkg")
        assert_feature_count(gdf, 3)

    def test_wrong_count_fails(self):
        """Raises when the feature count differs from the expected count."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="Expected 5"):
            assert_feature_count(gdf, 5)


# ===================================================================
# CRS assertions
# ===================================================================


class TestAssertHasCrs:
    def test_geodataframe_with_crs(self):
        """Accepts vector data that carries a CRS."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_has_crs(gdf)

    def test_no_crs_fails(self):
        """Raises when vector data has no CRS."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        gdf = gdf.set_crs(None, allow_override=True)
        with pytest.raises(AssertionError, match="no CRS"):
            assert_has_crs(gdf)

    def test_rasterio_dataset(self):
        """Accepts raster datasets that carry a CRS."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_has_crs(src)


class TestAssertEpsg:
    def test_epsg_4326(self):
        """Accepts vector data with EPSG:4326."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_epsg(gdf, 4326)

    def test_wrong_epsg_fails(self):
        """Raises when the dataset EPSG does not match the expected value."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="EPSG:32633"):
            assert_epsg(gdf, 32633)

    def test_rasterio_epsg_32633(self):
        """Accepts the raster fixture with EPSG:32633."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_epsg(src, 32633)

    def test_no_crs_fails(self):
        """Raises when EPSG is checked on data without a CRS."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        gdf = gdf.set_crs(None, allow_override=True)
        with pytest.raises(AssertionError, match="no CRS"):
            assert_epsg(gdf, 4326)


class TestAssertCrsUnits:
    def test_degree_units(self):
        """Accepts geographic CRS units expressed in degrees."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_crs_units(gdf, "degree")

    def test_metre_units(self):
        """Accepts projected CRS units expressed in metres."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_crs_units(src, "metre")

    def test_wrong_unit_fails(self):
        """Raises when CRS units do not match the expected unit."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        with pytest.raises(AssertionError, match="metre"):
            assert_crs_units(gdf, "metre")


# ===================================================================
# Raster assertions
# ===================================================================


class TestAssertBandCount:
    def test_single_band(self):
        """Accepts a single-band raster."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_band_count(src, 1)

    def test_wrong_band_count_fails(self):
        """Raises when the raster band count does not match."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            with pytest.raises(AssertionError, match="3 band"):
                assert_band_count(src, 3)


class TestAssertNodataValue:
    def test_nodata_present(self):
        """Accepts a raster that defines any NoData value."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_nodata_value(src)

    def test_nodata_exact_value(self):
        """Accepts a raster whose NoData value matches the expected value."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_nodata_value(src, -9999.0)

    def test_wrong_nodata_fails(self):
        """Raises when the raster NoData value differs from the expected one."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            with pytest.raises(AssertionError, match="NoData=0"):
                assert_nodata_value(src, 0)

    def test_no_nodata_fails(self):
        """Raises when a raster has no NoData value."""
        case = RasterCase(_meta(_UTM), _UTM)
        with case.open() as src:
            with pytest.raises(AssertionError, match="no NoData"):
                assert_nodata_value(src)


class TestAssertDtype:
    def test_float32(self):
        """Accepts a raster whose dtype is `float32`."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_dtype(src, "float32")

    def test_wrong_dtype_fails(self):
        """Raises when the raster dtype differs from the expected dtype."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            with pytest.raises(AssertionError, match="uint8"):
                assert_dtype(src, "uint8")


class TestAssertShape:
    def test_correct_shape(self):
        """Accepts a raster with the expected width and height."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            assert_shape(src, 10, 10)

    def test_wrong_shape_fails(self):
        """Raises when the raster shape differs from the expected shape."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        with case.open() as src:
            with pytest.raises(AssertionError, match="100, 100"):
                assert_shape(src, 100, 100)


class TestAssertNodataMasked:
    def test_nodata_pixels_present(self):
        """Accepts arrays that contain pixels equal to the NoData sentinel."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        data, _, nodata = case.read(1)
        assert_nodata_masked(data, nodata)

    def test_no_nodata_pixels_fails(self):
        # Create an array with no nodata pixels
        """Raises when no pixels use the expected NoData value."""
        data = np.ones((10, 10), dtype=np.float32)
        with pytest.raises(AssertionError, match="No pixels"):
            assert_nodata_masked(data, -9999.0)


class TestAssertNoNodataPixels:
    def test_clean_array_passes(self):
        """Accepts arrays without any NoData pixels."""
        data = np.ones((10, 10), dtype=np.float32)
        assert_no_nodata_pixels(data, -9999.0)

    def test_array_with_nodata_fails(self):
        """Raises when an array expected to be clean still contains NoData pixels."""
        case = RasterCase(_meta(_NODATA), _NODATA)
        data, _, nodata = case.read(1)
        with pytest.raises(AssertionError, match="pixel"):
            assert_no_nodata_pixels(data, nodata)


# ===================================================================
# Topology assertions
# ===================================================================


class TestAssertNoSelfIntersections:
    def test_valid_polygon_passes(self):
        """Accepts geometries without self-intersections."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_no_self_intersections(gdf)

    def test_self_intersecting_fails(self):
        """Raises when a geometry self-intersects."""
        gdf = gpd.read_file(_SELF_INTER / "geometry.geojson")
        with pytest.raises(AssertionError, match="self-intersect"):
            assert_no_self_intersections(gdf)


class TestAssertNoDuplicates:
    def test_unique_geometries_passes(self):
        """Accepts fixtures without duplicate geometries."""
        gdf = gpd.read_file(_ENCODING / "mixed_attrs.gpkg")
        assert_no_duplicates(gdf)

    def test_duplicate_fails(self):
        """Raises when duplicate geometries are present."""
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
        """Accepts fixtures without null geometries."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        assert_no_null_geometries(gdf)

    def test_null_geometry_fails(self):
        """Raises when a null geometry is present."""
        gdf = gpd.read_file(_SIMPLE / "geometry.geojson")
        gdf.loc[len(gdf)] = {"name": "empty", "geometry": None}
        with pytest.raises(AssertionError, match="null or empty"):
            assert_no_null_geometries(gdf)


# ===================================================================
# Metadata assertions (high-level)
# ===================================================================


class TestAssertCaseLoadable:
    def test_existing_case_passes(self):
        """Accepts a case whose primary file exists and is loadable."""
        meta = _meta(_SIMPLE)
        case = create_case(meta, _SIMPLE)
        assert_case_loadable(case)

    def test_missing_file_fails(self):
        """Raises when a case points to a missing primary file."""
        meta = _meta(_SIMPLE)
        case = create_case(meta, Path("/tmp/nonexistent_geocase"))
        with pytest.raises(AssertionError, match="primary file not found"):
            assert_case_loadable(case)


class TestAssertMatchesVectorHints:
    def test_simple_valid_passes_all_hints(self):
        """Matches vector assertion hints for the simple polygon fixture."""
        meta = _meta(_SIMPLE)
        case = VectorCase(meta, _SIMPLE)
        gdf = case.load()
        assert_matches_vector_hints(case, gdf)

    def test_polygon_with_hole_passes(self):
        """Matches vector assertion hints for the polygon-with-hole fixture."""
        meta = _meta(_HOLE)
        case = VectorCase(meta, _HOLE)
        gdf = case.load()
        assert_matches_vector_hints(case, gdf)

    def test_self_intersecting_passes(self):
        # expect_valid_geometry is False — so this should pass
        """Matches vector assertion hints when invalid geometry is expected."""
        meta = _meta(_SELF_INTER)
        case = VectorCase(meta, _SELF_INTER)
        gdf = case.load()
        assert_matches_vector_hints(case, gdf)

    def test_dateline_crossing_passes(self):
        """Matches vector assertion hints for the dateline-crossing fixture."""
        meta = _meta(_DATELINE)
        case = VectorCase(meta, _DATELINE)
        gdf = case.load()
        assert_matches_vector_hints(case, gdf)

    def test_encoding_case_passes(self):
        """Matches vector assertion hints for the encoding edge-case fixture."""
        meta = _meta(_ENCODING)
        case = VectorCase(meta, _ENCODING)
        gdf = case.load()
        assert_matches_vector_hints(case, gdf)


class TestAssertMatchesRasterHints:
    def test_nodata_raster_passes(self):
        """Matches raster assertion hints for the NoData raster fixture."""
        meta = _meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        with case.open() as src:
            assert_matches_raster_hints(case, src)

    def test_utm_boundary_passes(self):
        """Matches raster assertion hints for the UTM boundary raster fixture."""
        meta = _meta(_UTM)
        case = RasterCase(meta, _UTM)
        with case.open() as src:
            assert_matches_raster_hints(case, src)


# ===================================================================
# Footprint assertions
# ===================================================================


class TestFootprintAssertions:
    def test_no_holes_passes_on_expected_footprint(self):
        """Accepts an expected footprint polygon without holes."""
        expected = gpd.read_file(
            _EDGE / "all_valid_rectangular_footprint_truth.geojson"
        )
        assert_footprint_no_holes(expected)

    def test_rectangularity_strict_can_fail_on_complex_shape(self):
        """Raises when a complex footprint fails a strict rectangularity threshold."""
        complex_fp = gpd.read_file(
            _EDGE / "rotated_two_islands_footprint_truth.geojson"
        )
        with pytest.raises(AssertionError, match="rectangularity ratio"):
            assert_footprint_rectangularity(complex_fp, min_ratio=0.999)

    def test_similarity_against_expected_fixture(self):
        """Accepts identical footprint fixtures with zero allowed difference."""
        expected = gpd.read_file(_EDGE / "hole_center_nodata_footprint_truth.geojson")
        actual = gpd.read_file(_EDGE / "hole_center_nodata_footprint_truth.geojson")
        assert_footprint_similar_to_expected(actual, expected, max_diff_ratio=0.0)
