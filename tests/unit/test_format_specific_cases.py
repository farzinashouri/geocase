"""Tests for format-specific vector edge cases.

These tests exercise format-specific behaviors that can cause data loss
or corruption during cross-format conversion:

- Shapefile field name truncation (10-character limit)
- Shapefile legacy DBF encoding (Windows-1252 code pages)
- GeoJSON precision loss during text serialization roundtrips
- GeoPackage NULL vs EMPTY geometry distinction
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_DATA = _SRC / "data"
_VEC = _DATA / "core" / "vector"
_SPECIAL = _VEC / "special"

# Format-specific special cases
_SHAPEFILE_TRUNCATION = _SPECIAL / "encoding" / "shapefile_field_truncation"
_SHAPEFILE_ENCODING = _SPECIAL / "encoding" / "shapefile_encoding_legacy"
_GEOJSON_PRECISION = _SPECIAL / "precision" / "precision_loss_geojson_roundtrip"
_GPKG_EMPTY = _SPECIAL / "empty" / "empty_geometry_gpkg"


# ---------------------------------------------------------------------------
# Shapefile field name truncation tests
# ---------------------------------------------------------------------------


class TestShapefileFieldTruncation:
    """Exercises Shapefile field-name truncation and collision handling."""

    @pytest.fixture
    def shapefile_path(self) -> Path:
        return _SHAPEFILE_TRUNCATION / "truncated_fields.shp"

    def test_shapefile_loads_successfully(self, shapefile_path: Path) -> None:
        """Loads the truncated-field Shapefile and preserves its CRS."""
        gdf = gpd.read_file(shapefile_path)
        assert len(gdf) == 3
        assert gdf.crs.to_epsg() == 4326

    def test_field_names_are_truncated(self, shapefile_path: Path) -> None:
        """Preserves truncated and collision-resolved column names instead of the original long names."""
        gdf = gpd.read_file(shapefile_path)
        columns = [c for c in gdf.columns if c != "geometry"]

        # Original names were: temperature_celsius, temperature_fahrenheit,
        # precipitation_mm, wind_speed_knots
        # Expected truncated: temperatur, temperat_1, precipitat, wind_speed
        assert "temperatur" in columns
        assert "temperat_1" in columns  # Renamed to avoid collision
        assert "precipitat" in columns
        assert "wind_speed" in columns

        # Original long names should NOT be present
        assert "temperature_celsius" not in columns
        assert "temperature_fahrenheit" not in columns

    def test_all_field_names_within_limit(self, shapefile_path: Path) -> None:
        """Keeps every non-geometry field name within the Shapefile 10-character limit."""
        gdf = gpd.read_file(shapefile_path)
        for col in gdf.columns:
            if col != "geometry":
                assert len(col) <= 10, f"Field '{col}' exceeds 10 characters"

    def test_data_values_preserved(self, shapefile_path: Path) -> None:
        """Preserves representative numeric attribute values after field-name truncation."""
        gdf = gpd.read_file(shapefile_path)
        # Check that values are present and reasonable
        assert gdf["temperatur"].iloc[0] == pytest.approx(20.5, rel=0.01)
        assert gdf["wind_speed"].iloc[0] == 15


# ---------------------------------------------------------------------------
# Shapefile legacy encoding tests
# ---------------------------------------------------------------------------


class TestShapefileEncodingLegacy:
    """Exercises legacy DBF encoding behavior for Shapefile text attributes."""

    @pytest.fixture
    def shapefile_path(self) -> Path:
        return _SHAPEFILE_ENCODING / "legacy_encoding.shp"

    def test_shapefile_loads_successfully(self, shapefile_path: Path) -> None:
        """Loads the legacy-encoded Shapefile with the expected feature count and CRS."""
        gdf = gpd.read_file(shapefile_path, encoding="windows-1252")
        assert len(gdf) == 4
        assert gdf.crs.to_epsg() == 4326

    def test_special_characters_preserved_with_correct_encoding(
        self, shapefile_path: Path
    ) -> None:
        """Preserves accented city names when the correct Windows-1252 encoding is supplied."""
        gdf = gpd.read_file(shapefile_path, encoding="windows-1252")
        cities = list(gdf["city"])

        assert "Zürich" in cities
        assert "Köln" in cities
        assert "Malmö" in cities
        assert "São Paulo" in cities

    def test_cpg_file_exists(self, shapefile_path: Path) -> None:
        """Ships a `.cpg` sidecar that advertises the legacy code page."""
        cpg_path = shapefile_path.with_suffix(".cpg")
        assert cpg_path.exists()

        with open(cpg_path) as f:
            encoding = f.read().strip()
        assert encoding.lower() in ("windows-1252", "cp1252")

    def test_geometry_coordinates_valid(self, shapefile_path: Path) -> None:
        """Keeps decoded point geometries valid and within WGS84 coordinate bounds."""
        gdf = gpd.read_file(shapefile_path, encoding="windows-1252")
        for geom in gdf.geometry:
            assert geom.is_valid
            # Check coordinates are in reasonable WGS84 range
            assert -180 <= geom.x <= 180
            assert -90 <= geom.y <= 90


# ---------------------------------------------------------------------------
# GeoJSON precision loss tests
# ---------------------------------------------------------------------------


class TestGeoJSONPrecisionLoss:
    """Exercises GeoJSON precision retention during text serialization roundtrips."""

    @pytest.fixture
    def geojson_path(self) -> Path:
        return _GEOJSON_PRECISION / "high_precision_points.geojson"

    def test_geojson_loads_successfully(self, geojson_path: Path) -> None:
        """Loads the high-precision GeoJSON fixture successfully."""
        gdf = gpd.read_file(geojson_path)
        assert len(gdf) == 3

    def test_coordinates_have_high_precision(self, geojson_path: Path) -> None:
        """Preserves high-precision coordinate values when reading the fixture."""
        gdf = gpd.read_file(geojson_path)

        # First point should have ~15 significant digits
        point1 = gdf.geometry.iloc[0]
        # Allow small floating-point representation differences
        assert point1.x == pytest.approx(10.123456789012344, rel=1e-14)
        assert point1.y == pytest.approx(50.987654321098766, rel=1e-14)

    def test_very_small_coordinates_preserved(self, geojson_path: Path) -> None:
        """Preserves very small coordinate values near zero."""
        gdf = gpd.read_file(geojson_path)

        # Third point has very small values
        point3 = gdf.geometry.iloc[2]
        assert point3.x == pytest.approx(1e-14, rel=0.1)
        assert point3.y == pytest.approx(1e-14, rel=0.1)

    def test_roundtrip_maintains_precision(
        self, geojson_path: Path, tmp_path: Path
    ) -> None:
        """Keeps coordinate precision within tolerance across a GeoJSON write-read roundtrip."""
        gdf_original = gpd.read_file(geojson_path)
        original_coords = [(g.x, g.y) for g in gdf_original.geometry]

        # Write and read back
        output_path = tmp_path / "roundtrip.geojson"
        gdf_original.to_file(output_path, driver="GeoJSON")
        gdf_roundtrip = gpd.read_file(output_path)

        roundtrip_coords = [(g.x, g.y) for g in gdf_roundtrip.geometry]

        # Check precision is maintained within tolerance
        for orig, rt in zip(original_coords, roundtrip_coords):
            assert orig[0] == pytest.approx(rt[0], rel=1e-12)
            assert orig[1] == pytest.approx(rt[1], rel=1e-12)


# ---------------------------------------------------------------------------
# GeoPackage NULL vs EMPTY geometry tests
# ---------------------------------------------------------------------------


class TestGeoPackageNullEmptyGeometry:
    """Exercises GeoPackage handling of NULL geometries versus EMPTY geometries."""

    @pytest.fixture
    def gpkg_path(self) -> Path:
        return _GPKG_EMPTY / "empty_geom.gpkg"

    def test_gpkg_loads_successfully(self, gpkg_path: Path) -> None:
        """Loads the GeoPackage fixture containing valid, NULL, and EMPTY geometries."""
        gdf = gpd.read_file(gpkg_path)
        assert len(gdf) == 4

    def test_valid_geometries_present(self, gpkg_path: Path) -> None:
        """Loads the valid rows as non-empty, valid geometry objects."""
        gdf = gpd.read_file(gpkg_path)

        valid_rows = gdf[gdf["id"].isin(["valid_1", "valid_2"])]
        for geom in valid_rows.geometry:
            assert geom is not None
            assert not pd.isna(geom)
            assert geom.is_valid
            assert not geom.is_empty

    def test_null_geometry_detected(self, gpkg_path: Path) -> None:
        """Represents the NULL geometry row as `None` or `NaN`."""
        gdf = gpd.read_file(gpkg_path)

        null_row = gdf[gdf["id"] == "null_row"].iloc[0]
        # NULL geometry should be NaN or None
        assert pd.isna(null_row.geometry) or null_row.geometry is None

    def test_empty_geometry_detected(self, gpkg_path: Path) -> None:
        """Represents the EMPTY geometry row as an empty geometry object."""
        gdf = gpd.read_file(gpkg_path)

        empty_row = gdf[gdf["id"] == "empty_row"].iloc[0]
        # EMPTY geometry should be a geometry object that is_empty
        assert empty_row.geometry is not None
        assert not pd.isna(empty_row.geometry)
        assert empty_row.geometry.is_empty

    def test_null_and_empty_are_distinguishable(self, gpkg_path: Path) -> None:
        """Keeps NULL and EMPTY geometry states distinguishable after loading."""
        gdf = gpd.read_file(gpkg_path)

        null_row = gdf[gdf["id"] == "null_row"].iloc[0]
        empty_row = gdf[gdf["id"] == "empty_row"].iloc[0]

        # They should be different states
        is_null = pd.isna(null_row.geometry) or null_row.geometry is None
        is_empty = (
            empty_row.geometry is not None
            and not pd.isna(empty_row.geometry)
            and empty_row.geometry.is_empty
        )

        assert is_null, "NULL row should have NaN/None geometry"
        assert is_empty, "EMPTY row should have empty geometry object"

    def test_spatial_filtering_excludes_null_and_empty(self, gpkg_path: Path) -> None:
        """Filters out NULL and EMPTY geometries while retaining valid rows."""
        gdf = gpd.read_file(gpkg_path)

        # Filter to only valid (non-null, non-empty) geometries
        valid_gdf = gdf[
            gdf.geometry.apply(
                lambda geometry: (
                    geometry is not None
                    and not pd.isna(geometry)
                    and not geometry.is_empty
                )
            )
        ]

        assert len(valid_gdf) == 2
        assert set(valid_gdf["id"]) == {"valid_1", "valid_2"}
