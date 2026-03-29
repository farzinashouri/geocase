# GeoTIFF UTM Boundary

## Purpose

Raster near a UTM zone boundary used to expose reprojection and alignment
issues in zone-edge workflows.

## What to expect

- CRS is `EPSG:32633`.
- Single band raster.
- No explicit NoData requirement in metadata hints.

## Typical checks

- `assert_band_count(src, 1)`
- `assert_has_crs(src)`
- `assert_epsg(src, 32633)`
- Reproject and verify bounds/pixel alignment remain coherent.

## Common failure modes

- Pixel shifts near zone boundaries.
- Mosaicking artifacts caused by wrong zone assumptions.
