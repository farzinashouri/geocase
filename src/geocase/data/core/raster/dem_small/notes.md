# DEM Small

## Purpose

Elevation baseline for validating float32 continuous-surface handling and
NaN NoData semantics.

## What to expect

- CRS is `EPSG:32633`.
- One `float32` band named `elevation`.
- 16×16 pixels, DEFLATE compressed.
- NoData is `NaN` (one pixel).

## Typical checks

- `assert_band_count(src, 1)`
- `assert_dtype(src, "float32")`
- `assert_nan_nodata(src)`

## Common failure modes

- NaN pixels included in min/max/mean statistics.
- NoData convention assumed to be a numeric sentinel.

## Regenerate

`python scripts/generate_raster_fixtures.py`
