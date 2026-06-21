# Water Mask Small

## Purpose

Binary mask baseline for validating mask-style raster handling and nodata logic.

## What to expect

- CRS is `EPSG:32633`.
- One `uint8` band named `water` (0 = land, 1 = water).
- 16×16 pixels, DEFLATE compressed.
- NoData sentinel is `255` (one pixel).

## Typical checks

- `assert_band_count(src, 1)`
- `assert_dtype(src, "uint8")`
- `assert_nodata_value(src, 255)`

## Common failure modes

- NoData `255` counted as water/land.
- Mask promoted to a float dtype.

## Regenerate

`python scripts/generate_raster_fixtures.py`
