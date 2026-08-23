# Plan 19: Spec table as a separate, zero-dependency package

*Written before the rename; `geospatial-spec` is now `geofacts`.*

## Context

Three honest-evaluation runs against raster codebases all returned "wouldn't adopt," but all
three were pixel-*moving* repos — the wrong population for geocase's radiometry thesis. The
decision record's conclusion: freeze the fixture/edge-case framework pending a confirmed
compute-side user, but **ship the standalone constants table regardless**, because it is cheap,
pure-Python, vendorable, and useful independent of the untested premise.

This plan extends that decision to vector data **as a new, separate distribution**, not a
geocase subpackage. The vendorable/dependency-light constraint is locked by three evals and 
cannot be met inside geocase itself — the fixture catalog pulls in 4.2 MB and 572 files just to 
add `import` of the constants.

The deliverable's audience is explicit: an **AI coding agent writing unit tests**, which imports 
the table to enumerate the cases it must cover. Agents reliably know the *shape* of geospatial 
code and reliably miss the *lookup facts* (Plan 14 Step 0: 9/10 operations correct; the one 
silent failure was an antimeridian fact). A table of facts-with-citations plus a coverage API 
targets exactly that gap — and depends on no premise that the three evals left untested.

**Why separate:** An agent installing `pip install geospatial-spec` to get a constants table 
should receive exactly that — zero dependencies, a 50 KB package, nothing else. Bundling it 
in geocase means installing `pydantic`, `pyyaml`, and 572 fixture files as side effects. The 
import-level purity (pure stdlib inside geocase, guarded by a test) doesn't solve the 
distribution-level problem. A fresh package solves both.

## Scope

**New package:** `geospatial-spec` (PyPI). Zero dependencies, pure Python 3.11+.

**Content:** Vector-first, raster second, one shared shape. Three deliverables per domain:
- Lookup facts (constants, format limits) with inline citations
- Enumerable edge-case catalog with inline WKT
- Coverage API for agent test-suite completeness checking

**Not in scope:**
- The fixture catalog (`geocase.data/`) stays in geocase
- `geocase.synth` (fixture generation) stays frozen
- Fixture-linking `case_id` field: can be `None` in the separate package; soft reference only

## Design: `geospatial_spec` package structure

**Pure stdlib (`dataclasses`, `typing`), zero outside imports.**

### Core types (`src/geospatial_spec/_types.py`)

```python
@dataclass(frozen=True, slots=True)
class SpecFact:
    id: str                    # e.g. "s2_boa_offset"
    value: str | float | int   # the constant
    summary: str               # short description
    source: str                # "Sentinel-2 PSD 14.9, §Radiometric offset"

@dataclass(frozen=True, slots=True)
class FormatLimit:
    id: str                    # e.g. "shapefile_field_name_bytes"
    format: str                # "Shapefile" | "GeoJSON" | etc.
    limit: int | str           # the constraint value
    summary: str               # what happens when violated
    source: str                # specification reference
    symptom: str               # "silent truncation" | "exception" | etc.

@dataclass(frozen=True, slots=True)
class EdgeCase:
    id: str                    # e.g. "antimeridian_crossing_line"
    group: str                 # "antimeridian" | "poles" | "validity" | etc.
    wkt: str                   # the geometry as WKT
    crs: str | None            # optional EPSG code or None for generic
    summary: str               # one-line description
    breaks: str                # *what silently goes wrong*: the reason agents need to know about this
    source: str                # specification reference
    severity: Literal["silent", "error"]  # does it fail or silently misbehave?
    case_id: str | None        # optional: matches geocase fixture id if exists
```

### Vector module (`src/geospatial_spec/vector.py`)

```python
FACTS: tuple[SpecFact, ...] = (
    SpecFact("utm_zone_1_to_60", (1, 60), "UTM zones", "EPSG:4326 definition"),
    SpecFact("utm_epsg_north", 32600, "Northern hemisphere base EPSG", "OGC EPSG:326xx series"),
    SpecFact("utm_epsg_south", 32700, "Southern hemisphere base EPSG", "OGC EPSG:327xx series"),
    SpecFact("utm_norway_32v_exception", (56, 64, 3, 12), "Norway 32V zone", 
             "EPSG:3046 et al, OGC recommendations"),
    SpecFact("svalbard_31x_33x_35x_37x", True, "Svalbard zones", 
             "EPSG:3031–3037, OGC recommendations 72–84°N"),
    SpecFact("epsg_3857_latitude_limit", 85.0511287798066, "Web Mercator max latitude", 
             "EPSG:3857 definition, RFC 3857"),
    SpecFact("epsg_4326_axis_order", ("latitude", "longitude"), 
             "OGC:CRS84 axis order (not GeoJSON order)", "EPSG:4326 authority definition"),
    # ... etc
)

LIMITS: tuple[FormatLimit, ...] = (
    FormatLimit("shapefile_field_name_bytes", "Shapefile", 10, 
                "Field names truncated silently to 10 ASCII bytes", "ESRI Shapefile spec",
                "silent truncation"),
    FormatLimit("shapefile_field_count", "Shapefile", 255, 
                "Maximum fields per file", "ESRI Shapefile spec", "exception on exceed"),
    FormatLimit("shapefile_file_size", "Shapefile", "2 GB",
                "Maximum file size per .shp/.dbf", "ESRI Shapefile spec", "silent data loss"),
    FormatLimit("geojson_coordinate_precision", "GeoJSON", 6,
                "Practical decimal precision guidance", "RFC 7946, §11.2", "information"),
    # ... etc
)

EDGE_CASES: tuple[EdgeCase, ...] = (
    EdgeCase("antimeridian_crossing_line", "antimeridian",
             "LINESTRING(170 -10, -170 10)",
             None, "Line crossing antimeridian",
             "RFC 7946 §3.1.9: geometries crossing antimeridian MUST be split; "
             "unsplit versions silently produce wrong bounds and comparison results",
             "RFC 7946", "silent", "antimeridian_crossing_line"),
    EdgeCase("null_island_point", "validity",
             "POINT(0 0)",
             "EPSG:4326", "Point at (0, 0) lat/lon",
             "Silently collides with null/unknown placeholders in poorly-designed schemas; "
             "exact coordinates are valid but become ambiguous under lossy serialization",
             "ESRI, OGC GIS folklore", "silent", "null_island_point"),
    EdgeCase("svalbard_utm_polygon", "poles",
             "POLYGON((16 73, 16 81, 35 81, 35 73, 16 73))",
             "EPSG:4326", "Polygon covering Svalbard (72–84°N)",
             "EPSG:3857 (Web Mercator) cannot render (exceeds latitude limit); "
             "standard UTM zone formula picks wrong zone; agents silently write wrong CRS codes",
             "EPSG:3857, OGC UTM", "silent", "svalbard_special_zone_polygon"),
    # ... ~30 entries total
)

def by_id(id: str, cases=EDGE_CASES) -> EdgeCase:
    """Lookup single case by id; raises KeyError if not found."""
    
def in_group(group: str, cases=EDGE_CASES) -> tuple[EdgeCase, ...]:
    """Return all cases in a group, or empty tuple if group unknown."""
```

### Raster module (`src/geospatial_spec/raster.py`)

Same shape as vector. Seeds from grader.py provenance:

```python
FACTS: tuple[SpecFact, ...] = (
    SpecFact("s2_boa_add_offset", -1000.0, "Sentinel-2 L2A BOA reflectance offset",
             "Sentinel-2 Products Specification Document, PSD 14.9, "
             "§Radiometric offset; ESA baseline 04.00 change notice (2022-01-25)"),
    SpecFact("s2_quantification_value", 10000, "Sentinel-2 L2A reflectance scaling factor",
             "Sentinel-2 PSD 14.9, same section"),
    SpecFact("s2_nodata_sentinel", 0, "Sentinel-2 L2A NODATA and saturation marker",
             "Sentinel-2 PSD 14.9, §Product metadata"),
    SpecFact("s2_nodata_saturation", 65535, "Sentinel-2 L1C saturation marker (uint16)",
             "Sentinel-2 PSD 14.9, §Radiometric quality"),
    SpecFact("s2_scl_classes", tuple(range(12)), "Scene Classification (SCL) class codes 0–11",
             "Sentinel-2 PSD 14.9, §SCL product specification"),
    # ... S1 GRD calibration, band resolutions, etc.
)
```

### Coverage API (`src/geospatial_spec/coverage.py`)

```python
def missing(
    covered: Iterable[str],
    cases: tuple[EdgeCase, ...] = vector.EDGE_CASES,
    *,
    group: str | None = None,
    severity: Literal["silent", "error"] | None = None,
) -> tuple[EdgeCase, ...]:
    """Return uncovered cases. Raises KeyError on unknown covered id."""

def report(
    covered: Iterable[str],
    cases: tuple[EdgeCase, ...] = vector.EDGE_CASES,
    *,
    group: str | None = None,
) -> str:
    """Human-readable gap report."""

def require_coverage(
    covered: Iterable[str],
    cases: tuple[EdgeCase, ...] = vector.EDGE_CASES,
    *,
    group: str | None = None,
) -> None:
    """Raise AssertionError naming gaps; agent-facing entry point."""
```

### Package init (`src/geospatial_spec/__init__.py`)

```python
from geospatial_spec._types import EdgeCase, FormatLimit, SpecFact
from geospatial_spec import coverage, raster, vector

__all__ = ["SpecFact", "FormatLimit", "EdgeCase", "coverage", "raster", "vector"]
__version__ = "0.1.0"
```

## Integration with geocase (future, optional)

Once this package ships and stabilizes:
- geocase can optionally depend on `geospatial-spec` to avoid maintaining its own spec table
- grader.py can import from the spec package instead of defining constants locally
- No urgent action; this is a separate product

## Verification

- `pytest` with only `pytest` and stdlib available (no `pydantic`, `shapely`, `geopandas`, 
  `rasterio`). Tests `import geospatial_spec` and run coverage API.
- Optional: `pytest[vector]` when `shapely` is installed — validates WKT parsing and 
  `is_valid` checks on edge cases.
- Linting: `ruff check/format`, mypy strict on all modules.

## Not in scope

- Fixture catalog/data stays in geocase
- Fixture generation (`geocase.synth`) stays frozen
- This is **not** a replacement for geocase; it's a companion product for a different use case
