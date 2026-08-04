# Multispectral Sentinel-2-like Small

## Purpose

Multispectral baseline for validating four-band uint16 reflectance handling.

## What to expect

- CRS is `EPSG:32633`.
- Four `uint16` bands named `blue`, `green`, `red`, `nir`.
- 16×16 pixels, DEFLATE compressed.
- NoData sentinel is `0`.

## Typical checks

- `assert_band_count(src, 4)`
- `assert_dtype(src, "uint16")`
- `assert_nodata_value(src, 0)`
- `assert_band_names(src, ["blue", "green", "red", "nir"])`

## Common failure modes

- NIR band dropped, leaving an RGB-only stack.
- Band order assumed to be RGB rather than BGR-NIR.
- Sentinel NoData treated as a valid reflectance value.

## Regenerate

`python scripts/generate_raster_fixtures.py`
