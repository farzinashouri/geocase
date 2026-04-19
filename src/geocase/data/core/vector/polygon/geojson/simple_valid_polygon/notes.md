# Simple Valid Polygon

## Purpose

Baseline vector case for the "happy path": valid polygon geometry, no holes,
and standard CRS (`EPSG:4326`).

## What to expect

- Loads cleanly with GeoPandas.
- Geometry validity checks should pass.
- No interior rings are present.
- Reprojection (`to_crs(...)`) should behave normally.

## Typical checks

- `assert_valid_geometry(gdf)`
- `assert_geometry_type(gdf, "Polygon")`
- `assert_no_holes(gdf)`
- `assert_epsg(gdf, 4326)`

## Why this case matters

Use this case to confirm your test harness and pipeline are healthy before
running edge-case scenarios.
