# Dateline Crossing Polygon

## Purpose

Antimeridian stress case for longitude wrapping and bounds logic.

## What to expect

- Geometry is valid and in `EPSG:4326`.
- Naive min/max longitude assumptions may break.
- Reprojection/bounds operations can reveal dateline handling bugs.

## Typical checks

- `assert_valid_geometry(gdf)`
- `assert_epsg(gdf, 4326)`
- `assert_geometry_type(gdf, "Polygon")`
- Compare bounds before/after reprojection for sanity.

## Common failure modes

- Incorrect bbox crossing interpretation.
- Longitude normalization bugs around `-180`/`180`.
