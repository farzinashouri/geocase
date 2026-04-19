# GeoTIFF Int16 Small

## Purpose

Single-band `int16` raster for validating signed integer raster dtype handling.

## What to expect

- CRS is `EPSG:32633`.
- One band (`int16`).
- NoData is `-9999`.
- Pixel values exceed `int8` range to make accidental narrowing visible.
