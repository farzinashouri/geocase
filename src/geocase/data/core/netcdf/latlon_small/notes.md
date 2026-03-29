# LatLon Small

## Purpose

Minimal CF-style NetCDF baseline with latitude/longitude dimensions and one
primary data variable (`temperature`).

## What to expect

- Loads via `xarray` without decoding failures.
- Coordinate dimensions include latitude and longitude.
- Fill value (`-9999.0`) is present for masking workflows.

## Typical checks

- Dataset opens and variable exists (`temperature`).
- Dimension sizes are non-zero and consistent.
- Fill value is detected via encoding/attrs.
- Basic slicing over lat/lon returns expected shapes.

## Common failure modes

- Latitude/longitude dimension swap.
- Fill value ignored during analysis.
- Inconsistent coordinate metadata handling.
