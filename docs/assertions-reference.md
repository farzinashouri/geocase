# Assertions Reference

GeoCase provides reusable assertion helpers for common geospatial expectations.

Import them from `geocase.assertions`:

```python
from geocase.assertions import assert_has_crs, assert_valid_geometry
```

---

## Geometry assertions

### `assert_valid_geometry(geom)`

Checks that a geometry is valid.

### `assert_invalid_geometry(geom)`

Checks that a geometry is invalid.

### `assert_geometry_type(data, expected_type)`

Checks that the geometry type matches the expected type.

### `assert_has_holes(geom)`

Checks that a polygon contains interior rings.

### `assert_no_holes(geom)`

Checks that a polygon does not contain interior rings.

### `assert_feature_count(data, expected_count)`

Checks the number of vector features.

### `assert_footprint_no_holes(geom)`

Checks that a raster footprint has no interior holes.

### `assert_footprint_rectangularity(geom, min_ratio=...)`

Checks that a raster footprint is sufficiently rectangular.

### `assert_footprint_similar_to_expected(observed, expected, tolerance=...)`

Checks that a footprint is similar to an expected geometry.

---

## CRS assertions

### `assert_has_crs(data)`

Checks that CRS metadata is present.

### `assert_epsg(data, expected_epsg)`

Checks that the CRS resolves to a specific EPSG code.

### `assert_crs_units(data, expected_units)`

Checks CRS unit expectations, such as degrees or metres.

---

## Extent assertions

### `assert_bounds(observed, expected, tolerance=1e-4)`

Checks that a `(west, south, east, north)` WGS84 envelope matches a declared
`SpatialExtent` (the case's `extent` field). `observed` is a raw envelope as a reader hands it over --
`gdf.total_bounds`, or `rasterio.warp.transform_bounds(...)` for a projected
raster -- so it may carry unwrapped longitudes past 180.

Those are folded to the catalog's convention before the comparison, which
matters for the antimeridian cases: `dateline_crossing_polygon` really does
store coordinates at 190, while its declared extent is the wrapped
`west=170, east=-170`. Those are the same box, and comparing them without
folding first would report a 340-degree error on a case that is correct.

This is the same function the content gate runs, so a case that passes
`validate_case_content.py` passes this assertion in your own test too.

```python
from geocase import get_case
from geocase.assertions import assert_bounds
import geocase

case = get_case("simple_valid_polygon")
gdf = geocase.load_case("simple_valid_polygon").load()

assert_bounds(tuple(gdf.total_bounds), case.extent)
```

---

## Raster assertions

### `assert_band_count(dataset, expected_count)`

Checks the raster band count.

### `assert_nodata_value(dataset, expected_value)`

Checks the raster NoData value.

### `assert_dtype(dataset, expected_dtype)`

Checks raster dtype.

### `assert_shape(dataset, expected_height, expected_width)`

Checks raster dimensions.

### `assert_nodata_masked(data)`

Checks that NoData values are masked in a read array.

### `assert_no_nodata_pixels(data)`

Checks that the raster array contains no NoData pixels.

---

## Topology assertions

### `assert_no_self_intersections(data)`

Checks that geometries do not self-intersect.

### `assert_no_duplicates(data)`

Checks that duplicate geometries or rows are not present.

### `assert_no_null_geometries(data)`

Checks that vector data contains no null geometries.

---

## Format compliance assertions

### `assert_format_compliance(path, declared_format)`

Validates that a file truly matches its declared format using magic-byte
inspection, structural parsing, or schema reads. Covers all 14 vector
format types: GeoJSON, Parquet, GPKG, Shapefile, KML, GML, SQLite,
FlatGeobuf, Feather, Arrow, GeoArrow, CSV_WKT, WKT, WKB.

### `assert_geoparquet_metadata(path)`

Verifies that a Parquet file contains valid GeoParquet metadata — the
`geo` key exists, is valid JSON, and includes `primary_column` and
`columns` per the GeoParquet 1.0/1.1 spec.

### `registered_format_validators()`

Returns the set of format names that have a registered validator.
Useful for testing that the dispatch table stays in sync with
`FormatType`.

---

## Metadata-aware assertions

### `assert_case_loadable(case)`

Checks that a case can be loaded successfully.

### `assert_matches_vector_hints(case, data)`

Checks that loaded vector data matches metadata hints.

### `assert_matches_raster_hints(case, dataset)`

Checks that loaded raster data matches metadata hints.

---

## Typical usage

### Vector example

```python
import pytest
from geocase.assertions import assert_has_crs, assert_valid_geometry


@pytest.mark.geocase_case("simple_valid_polygon")
def test_polygon_case(geocase_case) -> None:
    gdf = geocase_case.load()
    assert_has_crs(gdf)
    assert_valid_geometry(gdf.geometry.iloc[0])
```

### Raster example

```python
import pytest
from geocase.assertions import assert_band_count, assert_nodata_value


@pytest.mark.geocase_case("geotiff_nodata_small")
def test_raster_case(geocase_case) -> None:
    with geocase_case.open() as src:
        assert_band_count(src, 1)
        assert_nodata_value(src, -9999)
```

---

## Related docs

- [`getting-started.md`](getting-started.md)
- [`testing-your-function-with-geocase.md`](testing-your-function-with-geocase.md)
- [`case-discovery.md`](case-discovery.md)
