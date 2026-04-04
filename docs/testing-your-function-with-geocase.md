# Testing your geospatial function with GeoCase

This guide shows how to test an existing geospatial function using GeoCase cases.

Assumption: `geocase` is already installed and available in your test environment.

## What GeoCase gives you

GeoCase provides:

- curated vector/raster/NetCDF test cases,
- pytest markers to select cases,
- pytest fixtures that materialize cases for your test function.

In practice, you write normal `pytest` tests and let GeoCase feed realistic cases into them.

## Quick workflow

1. Pick a function to test (vector, raster, or NetCDF).
2. Select relevant GeoCase cases by id, suite, or metadata filter.
3. Load case data through the GeoCase fixture.
4. Run your function.
5. Assert expected behavior (including edge-case behavior).

---

## Pytest integration model

GeoCase plugin markers:

- `@pytest.mark.geocase_case("id1", "id2")` → explicit case IDs
- `@pytest.mark.geocase_suite("suite_key")` → named suite
- `@pytest.mark.geocase_select(...)` → metadata-based filtering

`geocase_select(...)` supports filters such as:

- `category` (e.g., `"vector"`, `"raster"`)
- `geometry_type` (e.g., `"Polygon"`, `"Point"`)
- `tags_any`, `tags_all`, `risk_types_any`
- `format`, `test_tier`, `storage_class`, `size_class`

GeoCase fixtures:

- `geocase` → auto-parameterized case object (one invocation per selected case)
- `geocase_case` → single case object (expects exactly one resolved case)
- `geocase_cases` → list of resolved case objects

---

## How to use selectors (`geocase_select`)

If you do not want to hardcode case IDs, use selectors.

`@pytest.mark.geocase_select(...)` picks matching cases from metadata, then runs your test once per match.

### Common selector patterns

```python
import pytest


@pytest.mark.geocase_select(category="raster")
def test_all_rasters(geocase) -> None:
    data, _, _ = geocase.read(1)
    assert data.size > 0


@pytest.mark.geocase_select(category="vector")
def test_all_vectors(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0


@pytest.mark.geocase_select(format="GeoJSON")
def test_geojson_only(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0


@pytest.mark.geocase_select(category="vector", format="GPKG")
def test_vector_gpkg_only(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0


@pytest.mark.geocase_select(category="raster", format="GeoTIFF")
def test_raster_geotiff_only(geocase) -> None:
    data, _, _ = geocase.read(1)
    assert data.size > 0


@pytest.mark.geocase_select(category="vector", geometry_type="Polygon")
def test_all_polygon_vectors(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0


@pytest.mark.geocase_select(category="vector", tags_any=["polygon", "hole"])
def test_vectors_with_any_tag(geocase) -> None:
    assert geocase.category == "vector"


@pytest.mark.geocase_select(category="vector", tags_all=["vector", "polygon"])
def test_vectors_with_all_tags(geocase) -> None:
    assert geocase.category == "vector"


@pytest.mark.geocase_select(risk_types_any=["coordinate_wrapping"])
def test_coordinate_wrapping_cases(geocase) -> None:
    assert "coordinate_wrapping" in geocase.metadata.risk_types
```

### Selector fields you can use

- `category`: `"vector" | "raster" | "netcdf" | "satellite"`
- `geometry_type`: e.g. `"Polygon"`, `"Point"`
- `format`: e.g. `"GeoJSON"`, `"GeoTIFF"`, `"NetCDF"`
- `test_tier`, `storage_class`, `size_class`
- `tags_any`, `tags_all`
- `risk_types_any`

### Quick lookup: goal → selector

| Goal | Selector |
|---|---|
| All vector cases | `@pytest.mark.geocase_select(category="vector")` |
| All raster cases | `@pytest.mark.geocase_select(category="raster")` |
| All polygon vectors | `@pytest.mark.geocase_select(category="vector", geometry_type="Polygon")` |
| All point vectors | `@pytest.mark.geocase_select(category="vector", geometry_type="Point")` |
| Only GeoJSON cases | `@pytest.mark.geocase_select(format="GeoJSON")` |
| Only GeoTIFF rasters | `@pytest.mark.geocase_select(category="raster", format="GeoTIFF")` |
| Any nodata-related cases | `@pytest.mark.geocase_select(tags_any=["nodata"])` |
| Any coordinate-wrapping risk | `@pytest.mark.geocase_select(risk_types_any=["coordinate_wrapping"])` |

### Copy-paste template

```python
@pytest.mark.geocase_select(
    category="vector",
    geometry_type="Polygon",
    tags_any=["polygon"],
)
def test_your_function_on_selected_cases(geocase) -> None:
    data = geocase.load()  # or geocase.read(1) for raster
    result = your_function(data)
    assert result is not None
```

---

## Example edge-case fixtures for interview-style helpers

The bundled catalog now includes several tiny cases that are useful when you
want realistic inputs for "simple but imperfect" geospatial helpers.

These cases are especially handy for side-by-side tests where:

- the original helper is expected to fail or behave naively, and
- a `*_perfect` variant is expected to handle the case correctly.

### Vector fixtures

| Case ID | What it is for | Typical helper gap it exposes |
|---|---|---|
| `wrapped_longitude_point` | Point stored as `190°` longitude in EPSG:4326 | Geographic reprojection that fails to normalize longitude back into `[-180, 180]` |
| `dateline_chain_cluster` | Three-point transitive cluster around the antimeridian | Projection-based clustering that splits a geodesically connected chain |
| `spike_invalid_polygon` | Invalid polygon that repairs to mixed polygon + line output | Geometry repair helpers that return `GeometryCollection` instead of polygon-only output |
| `svalbard_special_zone_polygon` | Polygon representative point in a Svalbard special UTM zone | Naive UTM zone lookup that ignores Svalbard exceptions |
| `classic_antimeridian_polygon` | Polygon encoded across the classic `-180/180` seam | Bounding-box or antimeridian logic that uses raw bounds instead of minimal wrapped span |
| `dateline_points_pair` | Two points on opposite sides of the antimeridian but close in reality | Distance, clustering, or UTM logic that treats wrapped longitudes as far apart |

### Raster fixtures

| Case ID | What it is for | Typical helper gap it exposes |
|---|---|---|
| `geotiff_nodata_small` | Small single-band raster with explicit NoData | Sampling helpers that return the sentinel instead of masking NoData |
| `geotiff_nodata_small_shifted` | Same raster shifted exactly one pixel east | Alignment logic that is too strict about matching extents |
| `geotiff_utm_boundary` | Projected raster with UTM coordinates | Raster clipping or rasterization helpers that assume WGS84 bounds already match raster CRS |

### How to use them quickly

For explicit case IDs:

```python
@pytest.mark.geocase_case("wrapped_longitude_point", "spike_invalid_polygon")
def test_specific_edge_cases(geocase) -> None:
    data = geocase.load()
    assert data is not None
```

For metadata-driven selection:

```python
@pytest.mark.geocase_select(risk_types_any=["coordinate_wrapping"])
def test_coordinate_wrapping_cases(geocase) -> None:
    assert geocase is not None
```

---

## What is `geocase.id`?

`geocase.id` is the unique case identifier from the case metadata (`case.yaml`).

When your test is parameterized by GeoCase markers, each test invocation gets one case object,
and `geocase.id` tells you exactly which scenario is currently running.

Typical use:

- branch expectations per case,
- produce readable assertion messages,
- keep one test function that validates several edge scenarios.

Example:

```python
@pytest.mark.geocase_case("geotiff_nodata_small", "geotiff_utm_boundary")
def test_something(geocase) -> None:
    if geocase.id == "geotiff_nodata_small":
        ...  # expectations for nodata case
    elif geocase.id == "geotiff_utm_boundary":
        ...  # expectations for UTM boundary case
```

---

## Example A: real function (`geotiff_footprint_to_geojson`) on raster cases

This uses the real function in `examples/gdal_footprint.py`:

```python
# tests/test_gdal_footprint_real_raster.py
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pytest

from gdal_footprint import geotiff_footprint_to_geojson
from geocase.assertions import assert_footprint_no_holes


@pytest.mark.geocase_case("geotiff_nodata_small", "geotiff_utm_boundary")
def test_gdal_footprint_raster_cases(geocase, tmp_path: Path) -> None:
    out_path = tmp_path / f"{geocase.id}_footprint.geojson"

    created = geotiff_footprint_to_geojson(geocase.primary_path, out_path)
    assert created == out_path
    assert out_path.exists()

    footprint = gpd.read_file(out_path)
    assert len(footprint) >= 1
    assert_footprint_no_holes(footprint)
```

Why this is useful: your function is validated on realistic raster cases without hardcoded `src/geocase/data/...` paths.

---

## Complete example: write function first, then unit test it

This repository now includes a concrete function module:

- `examples/real_geospatial_function.py`

It defines two real utilities:

- `compute_projected_shape_metrics(gdf, target_epsg=3857)`
- `compute_masked_raster_stats(data, nodata)`

And unit tests for both using GeoCase fixtures:

- `examples/test_real_geospatial_function.py`

### Function code (real implementation)

```python
from __future__ import annotations

from typing import Any

import numpy as np


def compute_projected_shape_metrics(
    geodataframe: Any,
    *,
    target_epsg: int = 3857,
) -> dict[str, float]:
    if getattr(geodataframe, "crs", None) is None:
        raise ValueError("Input GeoDataFrame must have a CRS")
    if len(geodataframe) == 0:
        raise ValueError("Input GeoDataFrame is empty")

    projected = geodataframe.to_crs(epsg=target_epsg)
    return {
        "feature_count": float(len(projected)),
        "area_sum": float(projected.area.sum()),
        "perimeter_sum": float(projected.length.sum()),
    }


def compute_masked_raster_stats(
    data: np.ndarray,
    nodata: float | int | None,
) -> dict[str, float]:
    finite_mask = np.isfinite(data)
    valid_mask = finite_mask if nodata is None else finite_mask & (data != nodata)

    valid_values = data[valid_mask]
    if valid_values.size == 0:
        raise ValueError("Raster has no valid pixels after nodata masking")

    nodata_ratio = 1.0 - (float(valid_values.size) / float(data.size))
    return {
        "valid_pixel_count": float(valid_values.size),
        "nodata_ratio": float(nodata_ratio),
        "min": float(valid_values.min()),
        "max": float(valid_values.max()),
        "mean": float(valid_values.mean()),
        "std": float(valid_values.std()),
    }
```

### Unit tests with GeoCase

```python
from __future__ import annotations

from typing import Any

import pytest

from real_geospatial_function import (
    compute_masked_raster_stats,
    compute_projected_shape_metrics,
)


@pytest.mark.geocase_case("simple_valid_polygon", "polygon_with_hole")
def test_compute_projected_shape_metrics(geocase: Any) -> None:
    gdf = geocase.load()
    metrics = compute_projected_shape_metrics(gdf, target_epsg=3857)

    assert metrics["feature_count"] == float(len(gdf))
    assert metrics["area_sum"] > 0.0
    assert metrics["perimeter_sum"] > 0.0


@pytest.mark.geocase_case("geotiff_nodata_small", "geotiff_utm_boundary")
def test_compute_masked_raster_stats(geocase: Any) -> None:
    data, _profile, nodata = geocase.read(1)
    stats = compute_masked_raster_stats(data, nodata)

    assert stats["valid_pixel_count"] > 0.0
    assert 0.0 <= stats["nodata_ratio"] <= 1.0

    if geocase.id == "geotiff_nodata_small":
        assert stats["nodata_ratio"] > 0.0
    if geocase.id == "geotiff_utm_boundary":
        assert stats["nodata_ratio"] == 0.0
```

Run this example:

```bash
pytest examples/test_real_geospatial_function.py -v
```

---

## Example B: real function (`geotiff_footprint_to_geojson`) rejects vector inputs

Same function, but tested against real vector cases:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from gdal_footprint import geotiff_footprint_to_geojson


@pytest.mark.geocase_case(
    "simple_valid_polygon",
    "polygon_with_hole",
    "self_intersecting_polygon",
)
def test_gdal_footprint_rejects_vector_inputs(geocase, tmp_path: Path) -> None:
    out_path = tmp_path / f"{geocase.id}_footprint.geojson"

    with pytest.raises(ValueError, match="no raster bands|Unable to open raster dataset"):
        geotiff_footprint_to_geojson(geocase.primary_path, out_path)
```

---

## Example C: one specific case via `geocase_case`

Use this when you want exactly one case object:

```python
from __future__ import annotations

import pytest


@pytest.mark.geocase_case("dateline_crossing_polygon")
def test_dateline_case(geocase_case) -> None:
    gdf = geocase_case.load()
    assert geocase_case.id == "dateline_crossing_polygon"
    assert gdf.crs is not None
```

---

## Assertions: what to check

A practical pattern is to combine:

- **invariants** (must always hold): CRS present, geometry validity, shape/dtype constraints,
- **case-specific expectations** (only for some case IDs),
- **regression checks** (expected output geometry/statistics).

If helpful, use reusable GeoCase assertions from `geocase.assertions`.

---

## Run tests

Run all tests:

```bash
pytest -v
```

Run only tests that use GeoCase markers:

```bash
pytest -m "geocase_case or geocase_suite or geocase_select" -v
```

Run one file:

```bash
pytest tests/test_normalize_geoms.py -v
```

---

## Tips

- Prefer markers and fixtures over hardcoded `src/geocase/data/...` paths.
- Start with a narrow selection (`geocase_case`) and broaden (`geocase_select`) once stable.
- Use `geocase.id` in assertions when behavior should differ by scenario.
- Keep tests deterministic: avoid network and random behavior unless explicitly needed.

## Test without naming case IDs

You can run against all matching cases by metadata only:

```python
import pytest


@pytest.mark.geocase_select(category="raster")
def test_all_rasters(geocase) -> None:
    data, _, _ = geocase.read(1)
    assert data.size > 0


@pytest.mark.geocase_select(category="vector", geometry_type="Polygon")
def test_all_polygon_vectors(geocase) -> None:
    gdf = geocase.load()
    assert len(gdf) > 0
```

That’s it: you can treat GeoCase as a realistic test-data layer on top of standard `pytest`.
