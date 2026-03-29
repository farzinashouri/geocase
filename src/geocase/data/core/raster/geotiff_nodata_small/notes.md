# GeoTIFF NoData Small

## Purpose

Single-band raster with explicit NoData sentinel (`-9999`) for masking and
statistics validation.

## What to expect

- CRS is `EPSG:32633`.
- One band (`float32`).
- NoData is set and present in pixel values.

## Typical checks

- `assert_band_count(src, 1)`
- `assert_dtype(src, "float32")`
- `assert_nodata_value(src, -9999)`
- `assert_nodata_masked(data, nodata)`

## Common failure modes

- NoData ignored in mean/min/max computations.
- NoData converted to valid values during type casting.
