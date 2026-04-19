# Mixed Encoding Attributes

## Purpose

Valid point geometries with multilingual text attributes to test encoding
robustness (`UTF-8`, `Latin-1`, `Windows-1252` style content).

## What to expect

- Geometry loads as `Point` in `EPSG:4326`.
- Attribute strings should preserve accents/special characters.
- Column-level parsing should not introduce mojibake.

## Typical checks

- `assert_geometry_type(gdf, "Point")`
- `assert_valid_geometry(gdf)`
- `assert_epsg(gdf, 4326)`
- Verify representative strings remain unchanged after round-trips.

## Common failure modes

- Silent text corruption during decode/encode.
- Attribute truncation in export/import steps.
