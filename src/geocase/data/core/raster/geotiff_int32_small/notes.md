# GeoTIFF Int32 Small

## Purpose

Single-band `int32` raster for validating wide integer raster dtype handling.

## What to expect

- CRS is `EPSG:32633`.
- One band (`int32`).
- NoData is `-9999`.
- Pixel values exceed `int16` range to make accidental narrowing visible.
