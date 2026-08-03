# Plan: Universal Format & Geometry Compliance Gate

> **Archived — superseded. Retained as an implementation log.** The compliance gate shipped as `tests/unit/test_format_compliance.py` (211 tests).
>
> The single active roadmap is [`docs/plans/development-plan.md`](../development-plan.md).

> Created: April 2026
> Status: Complete (April 2026)
> Depends on: Phase 2 Step 2 (format-specific cases)

---

## Objective

Add a single parametrized test that auto-discovers every vector case in the catalog and validates that:

1. the file on disk actually **is** the format its `case.yaml` claims,
2. the loaded geometries match the declared `geometry_type`.

Any future case added by anyone that lies about its format or geometry type will fail CI automatically — no one has to remember to write a new test.

---

## Motivation

The project currently has **zero format-level validation tests**. Every vector format case only checks "loads into GeoDataFrame, CRS present, geometry type correct." No test inspects Parquet metadata, KML XML structure, GeoPackage SQLite internals, or Shapefile magic bytes.

The whole point of GeoCase is providing trusted test fixtures. A Parquet file that isn't actually Parquet, or a "Polygon" case that contains Points, undermines the entire premise. This plan closes that gap permanently.

---

## Implementation Steps

### Step 1: Create `src/geocase/assertions/format_compliance.py`

A module with one validator per format family, each doing the cheapest reliable "is this file really this format?" check.

#### Format validation strategies

| Format | Validation strategy |
|---|---|
| **GeoJSON** | Parse with `json.load()`; assert top-level `type` is a GeoJSON type (`Feature`, `FeatureCollection`, `GeometryCollection`, `Point`, `MultiPoint`, `LineString`, `MultiLineString`, `Polygon`, `MultiPolygon`) |
| **Parquet** | Read first 4 bytes = `PAR1`; then `pyarrow.parquet.read_schema()` succeeds; check for `geo` key in metadata (GeoParquet) |
| **GPKG** | First 16 bytes contain `SQLite format 3`; then `sqlite3.connect()` + query `gpkg_contents` table exists |
| **Shapefile** | File starts with magic bytes `0x0000270a` (big-endian int `9994`); `.shx` and `.dbf` sidecars exist |
| **KML** | Parse with `xml.etree.ElementTree`; root tag contains `kml` (namespace-aware) |
| **GML** | Parse with `xml.etree.ElementTree`; root tag is in OGC GML namespace or contains `FeatureCollection` |
| **SQLite** | First 16 bytes = `SQLite format 3`; not a GeoPackage (no `gpkg_contents`) |
| **FlatGeobuf** | First 8 bytes match FlatGeobuf magic (`0x6667620366676203`) |
| **Feather / Arrow / GeoArrow** | `pyarrow.ipc.open_file()` succeeds (IPC format magic) |
| **CSV_WKT** | `csv.Sniffer` or header row parse; at least one column named `wkt`, `geometry_wkt`, or `geometry` |
| **WKT** | File is text; `shapely.wkt.loads()` succeeds on content |
| **WKB** | `shapely.wkb.loads()` succeeds on raw bytes or hex-decoded content |

#### Entry point

Expose a single dispatch function:

```python
def assert_format_compliance(path: Path, declared_format: str) -> None:
    """Validate that the file at *path* truly matches *declared_format*.

    Raises AssertionError with a clear message on mismatch.
    """
```

#### GeoParquet-specific deeper check

Add a focused helper for Parquet specifically:

```python
def assert_geoparquet_metadata(path: Path) -> None:
    """Verify the Parquet file contains valid GeoParquet metadata.

    Checks that the ``geo`` metadata key exists in the Parquet schema
    metadata, is valid JSON, and contains ``primary_column`` and
    ``columns`` per the GeoParquet 1.0/1.1 spec.
    """
```

### Step 2: Create `tests/unit/test_format_compliance.py`

A single parametrized test that:

1. scans `case-index.yaml` to discover every bundled vector case,
2. loads `case.yaml` for each,
3. resolves the primary file path,
4. calls `assert_format_compliance(primary_path, meta.format)`,
5. loads via `VectorCase` and calls `assert_geometry_type(gdf, meta.assertions.expected_geometry_types)` for every case that declares `expected_geometry_types`.

This is the **future-proof gate**: any new case that gets indexed automatically enters this test.

```python
@pytest.mark.parametrize("case_id", _ALL_VECTOR_CASE_IDS)
def test_format_matches_declared(case_id: str):
    """Every vector case's primary file must truly be the declared format."""
    ...

@pytest.mark.parametrize("case_id", _ALL_VECTOR_CASE_IDS)
def test_geometry_type_matches_declared(case_id: str):
    """Every vector case's loaded geometries must match declared geometry_type."""
    ...
```

### Step 3: Register in `src/geocase/assertions/__init__.py`

Export `assert_format_compliance` and `assert_geoparquet_metadata` alongside the existing public assertions so users and downstream tests can use them.

### Step 4: Wire geometry-type truthfulness

After format compliance, do `VectorCase(meta, root).load()` and call `assert_geometry_type(gdf, meta.assertions.expected_geometry_types)` for every case that declares `expected_geometry_types`.

This ensures the file contains what the metadata promises. An invalid polygon is still a `Polygon` — only the validity assertion is skipped, not the type check.

---

## Likely Files to Edit

| Area | Files |
|---|---|
| New assertion module | `src/geocase/assertions/format_compliance.py` |
| Assertion exports | `src/geocase/assertions/__init__.py` |
| New test | `tests/unit/test_format_compliance.py` |

---

## Performance

- All 103 current vector cases use tiny/small files.
- Format fingerprint checks (magic bytes, header parse) are sub-millisecond each.
- Full `VectorCase.load()` for geometry-type verification adds ~5 seconds total across all cases.
- No measurable CI slowdown.

---

## Scope Boundaries

### In scope

- All vector formats currently in the `FormatType` literal: `GeoJSON`, `GPKG`, `Shapefile`, `Parquet`, `GML`, `KML`, `CSV_WKT`, `Feather`, `Arrow`, `GeoArrow`, `WKB`, `WKT`, `SQLite`, `FlatGeobuf`.
- All geometry types currently in use: `Point`, `MultiPoint`, `LineString`, `MultiLineString`, `Polygon`, `MultiPolygon`, `GeometryCollection`.
- The deeper GeoParquet metadata check (JSON structure, `primary_column`, `columns`).

### Out of scope (for now)

- Raster format compliance (GeoTIFF magic bytes, COG structure).
- NetCDF format compliance.
- Full KML XSD schema validation (requires bundling the KML schema or network fetch).
- Full GeoParquet spec validation beyond key presence and JSON parseability.

---

## Edge Cases and Decisions

### Cases with `expect_valid_geometry: false`

The geometry-type check still applies. An invalid polygon is still a `Polygon`. Only the validity assertion is skipped for those cases, not the type check.

### Cases without `expected_geometry_types` in assertions

Fall back to `meta.geometry_type` if `expected_geometry_types` is empty but `geometry_type` is set. If neither is declared, skip the geometry-type check for that case (but still run format compliance).

### SQLite vs GPKG disambiguation

Both are SQLite files at the byte level. The validator distinguishes them by checking for the `gpkg_contents` table. A case declared as `SQLite` must not have that table; a case declared as `GPKG` must have it.

### Shapefile sidecar enforcement

A case declared as `Shapefile` must have `.shx` and `.dbf` sidecars alongside the `.shp` primary file. Missing sidecars will fail the check, since a Shapefile without them is not a valid Shapefile.

---

## Definition of Done

- `assert_format_compliance` exists and covers all 14 vector format types.
- `assert_geoparquet_metadata` provides deeper Parquet-specific validation.
- `test_format_compliance.py` parametrizes over every indexed vector case.
- All 103 current vector cases pass both format and geometry-type checks.
- Any future case added to `case-index.yaml` is automatically tested.
- Assertions are exported from `src/geocase/assertions/__init__.py`.
- Validator coverage is enforced so new vector formats must register a validator.
