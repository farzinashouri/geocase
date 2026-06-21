# Optical RGB Small

## Purpose

True-colour optical baseline for validating multi-band uint8 raster handling.

## What to expect

- CRS is `EPSG:32633`.
- Three `uint8` bands named `red`, `green`, `blue`.
- 16×16 pixels, DEFLATE compressed.
- No NoData value.

## Typical checks

- `assert_band_count(src, 3)`
- `assert_dtype(src, "uint8")`
- `assert_band_names(src, ["red", "green", "blue"])`

## Common failure modes

- RGB bands collapsed to a single band.
- Band order swapped during processing.
- dtype promoted to a wider integer type.

## Regenerate

`python scripts/generate_raster_fixtures.py`
