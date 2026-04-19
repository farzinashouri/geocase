# GeoTIFF Float64 Small

## Purpose

Single-band `float64` raster for validating high-precision floating-point dtype handling.

## What to expect

- CRS is `EPSG:32633`.
- One band (`float64`).
- NoData is `-9999.0`.
- Pixel values include decimal precision that would be lossy if narrowed.
