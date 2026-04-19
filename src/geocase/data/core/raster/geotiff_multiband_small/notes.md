# GeoTIFF Multi-Band Small

## Purpose

Three-band raster baseline for validating multi-band read behavior.

## What to expect

- CRS is `EPSG:32633`.
- Three bands (`float32`).
- NoData is set to `-9999` and present in all bands.
- Each band contains different values so band order mistakes are visible.

## Typical checks

- `assert_band_count(src, 3)`
- `assert_dtype(src, "float32")`
- `assert_nodata_value(src, -9999)`
- `src.read(1)`, `src.read(2)`, and `src.read(3)` return distinct arrays

## Common failure modes

- Multi-band rasters read as a single band.
- Band order swapped during processing.
- NoData lost in one or more bands.
