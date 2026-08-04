# NDVI Small

## Purpose

Derived-index baseline for validating float32 NDVI-style raster handling.

## What to expect

- CRS is `EPSG:32633`.
- One `float32` band named `ndvi` with values in `[-1, 1]`.
- 16×16 pixels, DEFLATE compressed.
- No NoData value.

## Typical checks

- `assert_band_count(src, 1)`
- `assert_dtype(src, "float32")`
- values within `[-1, 1]`

## Common failure modes

- NDVI values clipped or scaled outside the valid range.
- dtype downcast to an integer type, destroying precision.

## Regenerate

`python scripts/generate_raster_fixtures.py`
