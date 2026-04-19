# Polygon with Hole

## Purpose

Exercises interior-ring handling. The polygon is valid but contains one hole.

## What to expect

- Geometry validity checks pass.
- Exactly one polygon hole is present.
- Area-sensitive workflows should subtract the interior ring area.

## Typical checks

- `assert_valid_geometry(gdf)`
- `assert_has_holes(gdf)`
- `assert_geometry_type(gdf, "Polygon")`
- `assert_epsg(gdf, 4326)`

## Common failure modes

- Inner ring dropped during load/serialization.
- Incorrect area if hole is ignored.
- Ring orientation assumptions causing geometry rewrites.
