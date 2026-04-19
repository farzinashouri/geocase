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
_VEC = _DATA / "core" / "vector"
_RASTER = _DATA / "core" / "raster"

# Vector cases - organized by geometry_type/format/case_name
# Point
_POINT = _VEC / "point" / "geojson" / "simple_valid_point"
_SHAPEFILE_POINT = _VEC / "point" / "shapefile" / "point_shapefile_baseline"
_GPKG_POINT = _VEC / "point" / "geopackage" / "point_geopackage_baseline"
_CSV_WKT_POINT = _VEC / "point" / "csv_wkt" / "point_csv_wkt_baseline"
_WKT_POINT = _VEC / "point" / "wkt" / "point_wkt_baseline"
_WKB_POINT = _VEC / "point" / "wkb" / "point_wkb_baseline"
_SQLITE_POINT = _VEC / "point" / "sqlite" / "point_sqlite_baseline"
_FLATGEOBUF_POINT = _VEC / "point" / "flatgeobuf" / "point_flatgeobuf_baseline"
_KML = _VEC / "point" / "kml" / "point_kml_baseline"
_GML = _VEC / "point" / "gml" / "point_gml_baseline"
_FEATHER = _VEC / "point" / "feather" / "point_feather_baseline"
_ARROW_POINT = _VEC / "point" / "arrow" / "point_arrow_baseline"

# Raster
_NODATA = _RASTER / "geotiff_nodata_small"
_UTM = _RASTER / "geotiff_utm_boundary"
_MULTIBAND = _RASTER / "geotiff_multiband_small"
_INT8_RASTER = _RASTER / "geotiff_int8_small"
_INT16_RASTER = _RASTER / "geotiff_int16_small"
_INT32_RASTER = _RASTER / "geotiff_int32_small"
_FLOAT64_RASTER = _RASTER / "geotiff_float64_small"

# LineString
_LINESTRING = _VEC / "linestring" / "geojson" / "simple_valid_linestring"
_SHAPEFILE_LINE = _VEC / "linestring" / "shapefile" / "linestring_shapefile_baseline"
_GPKG_LINE = _VEC / "linestring" / "geopackage" / "linestring_geopackage_baseline"
_CSV_WKT = _VEC / "linestring" / "csv_wkt" / "linestring_csv_wkt_baseline"
_WKT_LINE = _VEC / "linestring" / "wkt" / "linestring_wkt_baseline"
_WKB_LINE = _VEC / "linestring" / "wkb" / "linestring_wkb_baseline"
_SQLITE_LINE = _VEC / "linestring" / "sqlite" / "linestring_sqlite_baseline"
_FLATGEOBUF_LINE = _VEC / "linestring" / "flatgeobuf" / "linestring_flatgeobuf_baseline"
_KML_LINE = _VEC / "linestring" / "kml" / "linestring_kml_baseline"
_GML_LINE = _VEC / "linestring" / "gml" / "linestring_gml_baseline"
_GEOARROW = _VEC / "linestring" / "geoarrow" / "linestring_geoarrow_baseline"

# Polygon
_SIMPLE = _VEC / "polygon" / "geojson" / "simple_valid_polygon"
_SHAPEFILE = _VEC / "polygon" / "shapefile" / "polygon_shapefile_baseline"
_GPKG_POLY = _VEC / "polygon" / "geopackage" / "polygon_geopackage_baseline"
_CSV_WKT_POLY = _VEC / "polygon" / "csv_wkt" / "polygon_csv_wkt_baseline"
_WKT = _VEC / "polygon" / "wkt" / "polygon_wkt_baseline"
_WKB = _VEC / "polygon" / "wkb" / "polygon_wkb_baseline"
_SQLITE = _VEC / "polygon" / "sqlite" / "polygon_sqlite_baseline"
_FLATGEOBUF = _VEC / "polygon" / "flatgeobuf" / "polygon_flatgeobuf_baseline"
_KML_POLYGON = _VEC / "polygon" / "kml" / "polygon_kml_baseline"
_GML_POLYGON = _VEC / "polygon" / "gml" / "polygon_gml_baseline"
_PARQUET = _VEC / "polygon" / "parquet" / "polygon_parquet_baseline"

# MultiPoint
_MULTIPOINT = _VEC / "multipoint" / "geojson" / "simple_valid_multipoint"
_SHAPEFILE_MULTIPOINT = _VEC / "multipoint" / "shapefile" / "multipoint_shapefile_baseline"
_GPKG_MULTIPOINT = _VEC / "multipoint" / "geopackage" / "multipoint_geopackage_baseline"
_CSV_WKT_MULTIPOINT = _VEC / "multipoint" / "csv_wkt" / "multipoint_csv_wkt_baseline"
_WKT_MULTIPOINT = _VEC / "multipoint" / "wkt" / "multipoint_wkt_baseline"
_WKB_MULTIPOINT = _VEC / "multipoint" / "wkb" / "multipoint_wkb_baseline"
_SQLITE_MULTIPOINT = _VEC / "multipoint" / "sqlite" / "multipoint_sqlite_baseline"
_FLATGEOBUF_MULTIPOINT = _VEC / "multipoint" / "flatgeobuf" / "multipoint_flatgeobuf_baseline"
_KML_MULTIPOINT = _VEC / "multipoint" / "kml" / "multipoint_kml_baseline"
_GML_MULTIPOINT = _VEC / "multipoint" / "gml" / "multipoint_gml_baseline"
_FEATHER_MULTIPOINT = _VEC / "multipoint" / "feather" / "multipoint_feather_baseline"

# MultiLineString
_MULTILINESTRING = _VEC / "multilinestring" / "geojson" / "simple_valid_multilinestring"
_SHAPEFILE_MULTILINE = _VEC / "multilinestring" / "shapefile" / "multilinestring_shapefile_baseline"
_GPKG_MULTILINE = _VEC / "multilinestring" / "geopackage" / "multilinestring_geopackage_baseline"
_CSV_WKT_MULTILINE = _VEC / "multilinestring" / "csv_wkt" / "multilinestring_csv_wkt_baseline"
_WKT_MULTILINE = _VEC / "multilinestring" / "wkt" / "multilinestring_wkt_baseline"
_WKB_MULTILINE = _VEC / "multilinestring" / "wkb" / "multilinestring_wkb_baseline"
_SQLITE_MULTILINE = _VEC / "multilinestring" / "sqlite" / "multilinestring_sqlite_baseline"
_FLATGEOBUF_MULTILINE = _VEC / "multilinestring" / "flatgeobuf" / "multilinestring_flatgeobuf_baseline"
_KML_MULTILINE = _VEC / "multilinestring" / "kml" / "multilinestring_kml_baseline"
_GML_MULTILINE = _VEC / "multilinestring" / "gml" / "multilinestring_gml_baseline"
_PARQUET_MULTILINE = _VEC / "multilinestring" / "parquet" / "multilinestring_parquet_baseline"

# MultiPolygon
_MULTIPOLYGON = _VEC / "multipolygon" / "geojson" / "simple_valid_multipolygon"
_SHAPEFILE_MULTIPOLY = _VEC / "multipolygon" / "shapefile" / "multipolygon_shapefile_baseline"
_GPKG_MULTIPOLY = _VEC / "multipolygon" / "geopackage" / "multipolygon_geopackage_baseline"
_CSV_WKT_MULTIPOLY = _VEC / "multipolygon" / "csv_wkt" / "multipolygon_csv_wkt_baseline"
_WKT_MULTIPOLY = _VEC / "multipolygon" / "wkt" / "multipolygon_wkt_baseline"
_WKB_MULTIPOLY = _VEC / "multipolygon" / "wkb" / "multipolygon_wkb_baseline"
_SQLITE_MULTIPOLY = _VEC / "multipolygon" / "sqlite" / "multipolygon_sqlite_baseline"
_FLATGEOBUF_MULTIPOLY = _VEC / "multipolygon" / "flatgeobuf" / "multipolygon_flatgeobuf_baseline"
_KML_MULTIPOLY = _VEC / "multipolygon" / "kml" / "multipolygon_kml_baseline"
_GML_MULTIPOLY = _VEC / "multipolygon" / "gml" / "multipolygon_gml_baseline"

# Special cases
_HOLE = _VEC / "special" / "holes" / "polygon_with_hole"
_SELF_INTER = _VEC / "special" / "invalid" / "self_intersecting_polygon"
_DATELINE = _VEC / "special" / "dateline" / "dateline_crossing_polygon"
_ENCODING = _VEC / "special" / "encoding" / "mixed_encoding_attributes"

# Raster cases
_NODATA = _DATA / "core" / "raster" / "geotiff_nodata_small"
_UTM = _DATA / "core" / "raster" / "geotiff_utm_boundary"
_RASTER_EDGE = _DATA / "core" / "raster" / "footprint_edge_cases"

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
        """Test metadata accessible."""
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.metadata is meta
        assert case.id == "simple_valid_polygon"
        assert case.title == "Simple Valid Polygon"

    def test_category(self):
        """Test category."""
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.category == "vector"

    def test_tags(self):
        """Test tags."""
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert "polygon" in case.tags

    def test_primary_path(self):
        """Test primary path."""
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.primary_path == _SIMPLE / "geometry.geojson"

    def test_primary_exists(self):
        """Test primary exists."""
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.primary_exists() is True

    def test_notes_path(self):
        """Test notes path."""
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.notes_path == _SIMPLE / "notes.md"

    def test_notes_path_none_when_absent(self):
        """Test notes path none when absent."""
        meta = _load_meta(_SIMPLE)
        meta_dict = meta.model_dump()
        meta_dict["files"]["notes"] = None
        meta2 = CaseMetadata.model_validate(meta_dict)
        case = BaseCase(meta2, _SIMPLE)
        assert case.notes_path is None

    def test_sidecar_paths_empty(self):
        """Test sidecar paths empty."""
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.sidecar_paths() == []

    def test_root_dir(self):
        """Test root dir."""
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.root_dir == _SIMPLE.resolve()

    def test_assertions(self):
        """Test assertions."""
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.assertions.expect_loadable is True

    def test_params(self):
        """Test params."""
        meta = _load_meta(_HOLE)
        case = BaseCase(meta, _HOLE)
        assert case.params["has_holes"] is True

    def test_files(self):
        """Test files."""
        meta = _load_meta(_SIMPLE)
        case = BaseCase(meta, _SIMPLE)
        assert case.files.primary == "geometry.geojson"

    def test_repr(self):
        """Test repr."""
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
        """Test construct from vector metadata."""
        meta = _load_meta(_SIMPLE)
        case = VectorCase(meta, _SIMPLE)
        assert case.id == "simple_valid_polygon"

    def test_reject_non_vector_metadata(self):
        """Test reject non vector metadata."""
        meta = _load_meta(_NODATA)  # raster case
        with pytest.raises(ValueError, match="category='vector'"):
            VectorCase(meta, _NODATA)

    def test_load_simple_polygon(self):
        """Test load simple polygon."""
        meta = _load_meta(_SIMPLE)
        case = VectorCase(meta, _SIMPLE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None

    def test_load_simple_point(self):
        """Test load simple point."""
        meta = _load_meta(_POINT)
        case = VectorCase(meta, _POINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_polygon_with_hole(self):
        """Test load polygon with hole."""
        meta = _load_meta(_HOLE)
        case = VectorCase(meta, _HOLE)
        gdf = case.load()
        geom = gdf.geometry.iloc[0]
        # Polygon with hole has at least one interior ring
        assert len(list(geom.interiors)) == 1

    def test_load_self_intersecting(self):
        """Test load self intersecting."""
        meta = _load_meta(_SELF_INTER)
        case = VectorCase(meta, _SELF_INTER)
        gdf = case.load()
        geom = gdf.geometry.iloc[0]
        # Self-intersecting polygon is not valid by OGC standards
        assert geom.is_valid is False

    def test_load_dateline_crossing(self):
        """Test load dateline crossing."""
        meta = _load_meta(_DATELINE)
        case = VectorCase(meta, _DATELINE)
        gdf = case.load()
        assert len(gdf) == 1
        # Bounding box should span across 170-190 longitude
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        assert bounds[0] >= 170.0

    def test_load_gpkg(self):
        """Test load gpkg."""
        meta = _load_meta(_ENCODING)
        case = VectorCase(meta, _ENCODING)
        gdf = case.load()
        assert len(gdf) == 3
        assert "Café" in gdf["name"].values

    def test_load_shapefile(self):
        """Test load shapefile."""
        meta = _load_meta(_SHAPEFILE)
        case = VectorCase(meta, _SHAPEFILE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_load_shapefile_point(self):
        """Test load shapefile point."""
        meta = _load_meta(_SHAPEFILE_POINT)
        case = VectorCase(meta, _SHAPEFILE_POINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_shapefile_linestring(self):
        """Test load shapefile linestring."""
        meta = _load_meta(_SHAPEFILE_LINE)
        case = VectorCase(meta, _SHAPEFILE_LINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "LineString"

    def test_load_shapefile_multipoint(self):
        """Test load shapefile multipoint."""
        meta = _load_meta(_SHAPEFILE_MULTIPOINT)
        case = VectorCase(meta, _SHAPEFILE_MULTIPOINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPoint"

    def test_load_shapefile_multilinestring(self):
        """Test load shapefile multilinestring."""
        meta = _load_meta(_SHAPEFILE_MULTILINE)
        case = VectorCase(meta, _SHAPEFILE_MULTILINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiLineString"

    def test_load_shapefile_multipolygon(self):
        """Test load shapefile multipolygon."""
        meta = _load_meta(_SHAPEFILE_MULTIPOLY)
        case = VectorCase(meta, _SHAPEFILE_MULTIPOLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPolygon"

    def test_load_geopackage_point(self):
        """Test load geopackage point."""
        meta = _load_meta(_GPKG_POINT)
        case = VectorCase(meta, _GPKG_POINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_geopackage_linestring(self):
        """Test load geopackage linestring."""
        meta = _load_meta(_GPKG_LINE)
        case = VectorCase(meta, _GPKG_LINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "LineString"

    def test_load_geopackage_polygon(self):
        """Test load geopackage polygon."""
        meta = _load_meta(_GPKG_POLY)
        case = VectorCase(meta, _GPKG_POLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_load_geopackage_multipoint(self):
        """Test load geopackage multipoint."""
        meta = _load_meta(_GPKG_MULTIPOINT)
        case = VectorCase(meta, _GPKG_MULTIPOINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPoint"

    def test_load_geopackage_multilinestring(self):
        """Test load geopackage multilinestring."""
        meta = _load_meta(_GPKG_MULTILINE)
        case = VectorCase(meta, _GPKG_MULTILINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiLineString"

    def test_load_geopackage_multipolygon(self):
        """Test load geopackage multipolygon."""
        meta = _load_meta(_GPKG_MULTIPOLY)
        case = VectorCase(meta, _GPKG_MULTIPOLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPolygon"

    def test_load_csv_wkt_point(self):
        """Test load csv wkt point."""
        meta = _load_meta(_CSV_WKT_POINT)
        case = VectorCase(meta, _CSV_WKT_POINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_csv_wkt_polygon(self):
        """Test load csv wkt polygon."""
        meta = _load_meta(_CSV_WKT_POLY)
        case = VectorCase(meta, _CSV_WKT_POLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_load_csv_wkt_multipoint(self):
        """Test load csv wkt multipoint."""
        meta = _load_meta(_CSV_WKT_MULTIPOINT)
        case = VectorCase(meta, _CSV_WKT_MULTIPOINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiPoint"

    def test_load_csv_wkt_multilinestring(self):
        """Test load csv wkt multilinestring."""
        meta = _load_meta(_CSV_WKT_MULTILINE)
        case = VectorCase(meta, _CSV_WKT_MULTILINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiLineString"

    def test_load_csv_wkt_multipolygon(self):
        """Test load csv wkt multipolygon."""
        meta = _load_meta(_CSV_WKT_MULTIPOLY)
        case = VectorCase(meta, _CSV_WKT_MULTIPOLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiPolygon"

    def test_load_gml(self):
        """Test load gml."""
        meta = _load_meta(_GML)
        case = VectorCase(meta, _GML)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_gml_polygon(self):
        """Test load gml polygon."""
        meta = _load_meta(_GML_POLYGON)
        case = VectorCase(meta, _GML_POLYGON)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_load_gml_linestring(self):
        """Test load gml linestring."""
        meta = _load_meta(_GML_LINE)
        case = VectorCase(meta, _GML_LINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "LineString"

    def test_load_gml_multipoint(self):
        """Test load gml multipoint."""
        meta = _load_meta(_GML_MULTIPOINT)
        case = VectorCase(meta, _GML_MULTIPOINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPoint"

    def test_load_gml_multilinestring(self):
        """Test load gml multilinestring."""
        meta = _load_meta(_GML_MULTILINE)
        case = VectorCase(meta, _GML_MULTILINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiLineString"

    def test_load_gml_multipolygon(self):
        """Test load gml multipolygon."""
        meta = _load_meta(_GML_MULTIPOLY)
        case = VectorCase(meta, _GML_MULTIPOLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPolygon"

    def test_load_csv_wkt(self):
        """Test load csv wkt."""
        meta = _load_meta(_CSV_WKT)
        case = VectorCase(meta, _CSV_WKT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "LineString"

    def test_load_sqlite(self):
        """Test load sqlite."""
        meta = _load_meta(_SQLITE)
        case = VectorCase(meta, _SQLITE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_load_kml(self):
        """Test load kml."""
        meta = _load_meta(_KML)
        case = VectorCase(meta, _KML)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_kml_polygon(self):
        """Test load kml polygon."""
        meta = _load_meta(_KML_POLYGON)
        case = VectorCase(meta, _KML_POLYGON)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_load_kml_linestring(self):
        """Test load kml linestring."""
        meta = _load_meta(_KML_LINE)
        case = VectorCase(meta, _KML_LINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "LineString"

    def test_load_kml_multipoint(self):
        """Test load kml multipoint."""
        meta = _load_meta(_KML_MULTIPOINT)
        case = VectorCase(meta, _KML_MULTIPOINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPoint"

    def test_load_kml_multilinestring(self):
        """Test load kml multilinestring."""
        meta = _load_meta(_KML_MULTILINE)
        case = VectorCase(meta, _KML_MULTILINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiLineString"

    def test_load_kml_multipolygon(self):
        """Test load kml multipolygon."""
        meta = _load_meta(_KML_MULTIPOLY)
        case = VectorCase(meta, _KML_MULTIPOLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPolygon"

    def test_load_wkt(self):
        """Test load wkt."""
        meta = _load_meta(_WKT)
        case = VectorCase(meta, _WKT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_load_wkt_point(self):
        """Test load wkt point."""
        meta = _load_meta(_WKT_POINT)
        case = VectorCase(meta, _WKT_POINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_wkt_linestring(self):
        """Test load wkt linestring."""
        meta = _load_meta(_WKT_LINE)
        case = VectorCase(meta, _WKT_LINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "LineString"

    def test_load_wkt_multipoint(self):
        """Test load wkt multipoint."""
        meta = _load_meta(_WKT_MULTIPOINT)
        case = VectorCase(meta, _WKT_MULTIPOINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiPoint"

    def test_load_wkt_multilinestring(self):
        """Test load wkt multilinestring."""
        meta = _load_meta(_WKT_MULTILINE)
        case = VectorCase(meta, _WKT_MULTILINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiLineString"

    def test_load_wkt_multipolygon(self):
        """Test load wkt multipolygon."""
        meta = _load_meta(_WKT_MULTIPOLY)
        case = VectorCase(meta, _WKT_MULTIPOLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiPolygon"

    def test_load_wkb(self):
        """Test load wkb."""
        meta = _load_meta(_WKB)
        case = VectorCase(meta, _WKB)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_load_wkb_point(self):
        """Test load wkb point."""
        meta = _load_meta(_WKB_POINT)
        case = VectorCase(meta, _WKB_POINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_wkb_linestring(self):
        """Test load wkb linestring."""
        meta = _load_meta(_WKB_LINE)
        case = VectorCase(meta, _WKB_LINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "LineString"

    def test_load_wkb_multipoint(self):
        """Test load wkb multipoint."""
        meta = _load_meta(_WKB_MULTIPOINT)
        case = VectorCase(meta, _WKB_MULTIPOINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiPoint"

    def test_load_wkb_multilinestring(self):
        """Test load wkb multilinestring."""
        meta = _load_meta(_WKB_MULTILINE)
        case = VectorCase(meta, _WKB_MULTILINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiLineString"

    def test_load_wkb_multipolygon(self):
        """Test load wkb multipolygon."""
        meta = _load_meta(_WKB_MULTIPOLY)
        case = VectorCase(meta, _WKB_MULTIPOLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiPolygon"

    def test_load_sqlite_point(self):
        """Test load sqlite point."""
        meta = _load_meta(_SQLITE_POINT)
        case = VectorCase(meta, _SQLITE_POINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_sqlite_linestring(self):
        """Test load sqlite linestring."""
        meta = _load_meta(_SQLITE_LINE)
        case = VectorCase(meta, _SQLITE_LINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "LineString"

    def test_load_sqlite_multipoint(self):
        """Test load sqlite multipoint."""
        meta = _load_meta(_SQLITE_MULTIPOINT)
        case = VectorCase(meta, _SQLITE_MULTIPOINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiPoint"

    def test_load_sqlite_multilinestring(self):
        """Test load sqlite multilinestring."""
        meta = _load_meta(_SQLITE_MULTILINE)
        case = VectorCase(meta, _SQLITE_MULTILINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiLineString"

    def test_load_sqlite_multipolygon(self):
        """Test load sqlite multipolygon."""
        meta = _load_meta(_SQLITE_MULTIPOLY)
        case = VectorCase(meta, _SQLITE_MULTIPOLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.geometry.iloc[0].geom_type == "MultiPolygon"

    def test_load_flatgeobuf(self):
        """Test load flatgeobuf."""
        meta = _load_meta(_FLATGEOBUF)
        case = VectorCase(meta, _FLATGEOBUF)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_load_flatgeobuf_point(self):
        """Test load flatgeobuf point."""
        meta = _load_meta(_FLATGEOBUF_POINT)
        case = VectorCase(meta, _FLATGEOBUF_POINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_flatgeobuf_linestring(self):
        """Test load flatgeobuf linestring."""
        meta = _load_meta(_FLATGEOBUF_LINE)
        case = VectorCase(meta, _FLATGEOBUF_LINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "LineString"

    def test_load_flatgeobuf_multipoint(self):
        """Test load flatgeobuf multipoint."""
        meta = _load_meta(_FLATGEOBUF_MULTIPOINT)
        case = VectorCase(meta, _FLATGEOBUF_MULTIPOINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPoint"

    def test_load_flatgeobuf_multilinestring(self):
        """Test load flatgeobuf multilinestring."""
        meta = _load_meta(_FLATGEOBUF_MULTILINE)
        case = VectorCase(meta, _FLATGEOBUF_MULTILINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiLineString"

    def test_load_flatgeobuf_multipolygon(self):
        """Test load flatgeobuf multipolygon."""
        meta = _load_meta(_FLATGEOBUF_MULTIPOLY)
        case = VectorCase(meta, _FLATGEOBUF_MULTIPOLY)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPolygon"

    def test_load_parquet(self):
        """Test load parquet."""
        meta = _load_meta(_PARQUET)
        case = VectorCase(meta, _PARQUET)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Polygon"

    def test_load_feather(self):
        """Test load feather."""
        meta = _load_meta(_FEATHER)
        case = VectorCase(meta, _FEATHER)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_load_geoarrow(self):
        """Test load geoarrow."""
        meta = _load_meta(_GEOARROW)
        case = VectorCase(meta, _GEOARROW)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "LineString"

    def test_load_parquet_multilinestring(self):
        """Test load parquet multilinestring."""
        meta = _load_meta(_PARQUET_MULTILINE)
        case = VectorCase(meta, _PARQUET_MULTILINE)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiLineString"

    def test_load_feather_multipoint(self):
        """Test load feather multipoint."""
        meta = _load_meta(_FEATHER_MULTIPOINT)
        case = VectorCase(meta, _FEATHER_MULTIPOINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "MultiPoint"

    def test_load_arrow_point(self):
        """Test load arrow point."""
        meta = _load_meta(_ARROW_POINT)
        case = VectorCase(meta, _ARROW_POINT)
        gdf = case.load()
        assert len(gdf) == 1
        assert gdf.crs is not None
        assert gdf.geometry.iloc[0].geom_type == "Point"

    def test_crs_preserved(self):
        """Test crs preserved."""
        meta = _load_meta(_SIMPLE)
        case = VectorCase(meta, _SIMPLE)
        gdf = case.load()
        assert gdf.crs.to_epsg() == 4326

    def test_missing_file_raises(self):
        """Test missing file raises."""
        meta = _load_meta(_SIMPLE)
        # Point to a non-existent directory
        fake_dir = Path("/tmp/geocase_nonexistent_case")
        case = VectorCase(meta, fake_dir)
        with pytest.raises(FileNotFoundError):
            case.load()

    def test_repr(self):
        """Test repr."""
        meta = _load_meta(_SIMPLE)
        case = VectorCase(meta, _SIMPLE)
        assert "VectorCase" in repr(case)


# ===================================================================
# RasterCase
# ===================================================================

class TestRasterCase:
    """Test RasterCase construction and loading."""

    def test_construct_from_raster_metadata(self):
        """Test construct from raster metadata."""
        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        assert case.id == "geotiff_nodata_small"

    def test_reject_non_raster_metadata(self):
        """Test reject non raster metadata."""
        meta = _load_meta(_SIMPLE)  # vector case
        with pytest.raises(ValueError, match="category='raster'"):
            RasterCase(meta, _SIMPLE)

    def test_open_nodata_raster(self):
        """Test open nodata raster."""
        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        with case.open() as src:
            assert src.count == 1
            assert src.width == 10
            assert src.height == 10
            assert src.nodata == -9999.0

    def test_open_crs(self):
        """Test open crs."""
        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        with case.open() as src:
            assert src.crs.to_epsg() == 32633

    def test_open_utm_boundary(self):
        """Test open utm boundary."""
        meta = _load_meta(_UTM)
        case = RasterCase(meta, _UTM)
        with case.open() as src:
            assert src.count == 1
            assert src.width == 20
            assert src.height == 20

    def test_open_rotated_raster_preserves_affine_terms(self):
        """Test open rotated raster preserves affine terms."""
        meta = load_case_metadata(_RASTER_EDGE / "case_rotated_two_islands.yaml")
        case = RasterCase(meta, _RASTER_EDGE)
        with case.open() as src:
            assert src.count == 1
            assert src.width == 8
            assert src.height == 8
            assert src.transform.b != 0.0
            assert src.transform.d != 0.0
            assert src.nodata == -9999.0

    def test_read_rotated_raster_profile_keeps_non_axis_aligned_transform(self):
        """Test read rotated raster profile keeps non axis aligned transform."""
        meta = load_case_metadata(_RASTER_EDGE / "case_rotated_two_islands.yaml")
        case = RasterCase(meta, _RASTER_EDGE)
        data, profile, nodata = case.read(1)
        transform = profile["transform"]

        assert data.shape == (8, 8)
        assert nodata == -9999.0
        assert transform.b != 0.0
        assert transform.d != 0.0
        assert profile["driver"] == "GTiff"

    def test_open_multiband_raster(self):
        """Test open multiband raster."""
        meta = _load_meta(_MULTIBAND)
        case = RasterCase(meta, _MULTIBAND)
        with case.open() as src:
            assert src.count == 3
            assert src.width == 10
            assert src.height == 10

    def test_read_multiband_raster_bands_are_distinct(self):
        """Test read multiband raster bands are distinct."""
        meta = _load_meta(_MULTIBAND)
        case = RasterCase(meta, _MULTIBAND)

        band1, profile1, nodata1 = case.read(1)
        band2, profile2, nodata2 = case.read(2)
        band3, profile3, nodata3 = case.read(3)

        assert band1.shape == (10, 10)
        assert band2.shape == (10, 10)
        assert band3.shape == (10, 10)
        assert profile1["count"] == 3
        assert profile2["count"] == 3
        assert profile3["count"] == 3
        assert nodata1 == nodata2 == nodata3 == -9999.0
        assert (band1 != band2).any()
        assert (band2 != band3).any()
        assert (band1 != band3).any()

    @pytest.mark.parametrize(
        ("case_dir", "expected_dtype"),
        [
            (_INT8_RASTER, "int8"),
            (_INT16_RASTER, "int16"),
            (_INT32_RASTER, "int32"),
            (_FLOAT64_RASTER, "float64"),
        ],
    )
    def test_open_dtype_specific_raster(self, case_dir: Path, expected_dtype: str):
        """Test open dtype specific raster."""
        meta = _load_meta(case_dir)
        case = RasterCase(meta, case_dir)
        with case.open() as src:
            assert src.count == 1
            assert src.width == 10
            assert src.height == 10
            assert src.dtypes == (expected_dtype,)

    @pytest.mark.parametrize(
        ("case_dir", "expected_dtype"),
        [
            (_INT8_RASTER, "int8"),
            (_INT16_RASTER, "int16"),
            (_INT32_RASTER, "int32"),
            (_FLOAT64_RASTER, "float64"),
        ],
    )
    def test_read_dtype_specific_raster_preserves_profile_dtype(
        self, case_dir: Path, expected_dtype: str
    ):
        """Test read dtype specific raster preserves profile dtype."""
        meta = _load_meta(case_dir)
        case = RasterCase(meta, case_dir)
        data, profile, _ = case.read(1)

        assert data.shape == (10, 10)
        assert profile["dtype"] == expected_dtype
        assert profile["driver"] == "GTiff"

    def test_read_band(self):
        """Test read band."""
        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        data, profile, nodata = case.read(1)
        assert data.shape == (10, 10)
        assert nodata == -9999.0
        assert profile["driver"] == "GTiff"

    def test_nodata_pixels_present(self):
        """Test nodata pixels present."""
        import numpy as np

        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        data, _, nodata = case.read(1)
        # We injected NoData at (0,0) and (5,5)
        assert data[0, 0] == nodata
        assert data[5, 5] == nodata

    def test_missing_file_raises(self):
        """Test missing file raises."""
        meta = _load_meta(_NODATA)
        fake_dir = Path("/tmp/geocase_nonexistent_raster")
        case = RasterCase(meta, fake_dir)
        with pytest.raises(FileNotFoundError):
            with case.open():
                pass

    def test_repr(self):
        """Test repr."""
        meta = _load_meta(_NODATA)
        case = RasterCase(meta, _NODATA)
        assert "RasterCase" in repr(case)


# ===================================================================
# NetCDFCase
# ===================================================================

class TestNetCDFCase:
    """Test NetCDFCase construction and loading."""

    def test_construct_from_netcdf_metadata(self):
        """Test construct from netcdf metadata."""
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        assert case.id == "latlon_small"

    def test_reject_non_netcdf_metadata(self):
        """Test reject non netcdf metadata."""
        meta = _load_meta(_SIMPLE)  # vector case
        with pytest.raises(ValueError, match="category='netcdf'"):
            NetCDFCase(meta, _SIMPLE)

    def test_load_dataset(self):
        """Test load dataset."""
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        ds = case.load()
        assert "temperature" in ds.data_vars
        ds.close()

    def test_dimensions(self):
        """Test dimensions."""
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        ds = case.load()
        assert "latitude" in ds.sizes
        assert "longitude" in ds.sizes
        assert ds.sizes["latitude"] == 5
        assert ds.sizes["longitude"] == 8
        ds.close()

    def test_coordinates(self):
        """Test coordinates."""
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        ds = case.load()
        assert ds["latitude"].values[0] == 40.0
        assert ds["latitude"].values[-1] == 50.0
        ds.close()

    def test_fill_value(self):
        """Test fill value."""
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        ds = case.load()
        temp = ds["temperature"]
        # xarray consumes _FillValue into encoding during open_dataset
        assert temp.encoding.get("_FillValue") == -9999.0
        ds.close()

    def test_cf_conventions(self):
        """Test cf conventions."""
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        ds = case.load()
        assert ds.attrs.get("Conventions") == "CF-1.8"
        ds.close()

    def test_missing_file_raises(self):
        """Test missing file raises."""
        meta = _load_meta(_LATLON)
        fake_dir = Path("/tmp/geocase_nonexistent_nc")
        case = NetCDFCase(meta, fake_dir)
        with pytest.raises(FileNotFoundError):
            case.load()

    def test_repr(self):
        """Test repr."""
        meta = _load_meta(_LATLON)
        case = NetCDFCase(meta, _LATLON)
        assert "NetCDFCase" in repr(case)


# ===================================================================
# Factory — create_case
# ===================================================================

class TestCreateCase:
    """Test the create_case() factory dispatch."""

    def test_creates_vector_case(self):
        """Test creates vector case."""
        meta = _load_meta(_SIMPLE)
        case = create_case(meta, _SIMPLE)
        assert isinstance(case, VectorCase)

    def test_creates_raster_case(self):
        """Test creates raster case."""
        meta = _load_meta(_NODATA)
        case = create_case(meta, _NODATA)
        assert isinstance(case, RasterCase)

    def test_creates_netcdf_case(self):
        """Test creates netcdf case."""
        meta = _load_meta(_LATLON)
        case = create_case(meta, _LATLON)
        assert isinstance(case, NetCDFCase)

    def test_all_are_base_case(self):
        """Test all are base case."""
        for case_dir in [_SIMPLE, _NODATA, _LATLON]:
            meta = _load_meta(case_dir)
            case = create_case(meta, case_dir)
            assert isinstance(case, BaseCase)

    def test_unsupported_category_raises(self):
        """Test unsupported category raises."""
        meta = _load_meta(_SIMPLE)
        # Force an unsupported category
        meta_dict = meta.model_dump()
        meta_dict["category"] = "satellite"
        meta2 = CaseMetadata.model_validate(meta_dict)
        with pytest.raises(ValueError, match="satellite"):
            create_case(meta2, _SIMPLE)

    def test_factory_produces_loadable_vector(self):
        """Test factory produces loadable vector."""
        meta = _load_meta(_DATELINE)
        case = create_case(meta, _DATELINE)
        assert isinstance(case, VectorCase)
        gdf = case.load()
        assert len(gdf) == 1

    def test_factory_produces_loadable_raster(self):
        """Test factory produces loadable raster."""
        meta = _load_meta(_NODATA)
        case = create_case(meta, _NODATA)
        assert isinstance(case, RasterCase)
        with case.open() as src:
            assert src.count == 1

    def test_factory_produces_loadable_netcdf(self):
        """Test factory produces loadable netcdf."""
        meta = _load_meta(_LATLON)
        case = create_case(meta, _LATLON)
        assert isinstance(case, NetCDFCase)
        ds = case.load()
        assert "temperature" in ds.data_vars
        ds.close()
