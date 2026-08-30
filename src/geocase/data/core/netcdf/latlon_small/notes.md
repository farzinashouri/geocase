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

- Fill value ignored during analysis.
- Inconsistent coordinate metadata handling.

## History

**The primary file was replaced in plan 34 (2026-08-29).** The original
`latlon_sample.nc` arrived in a single commit carrying unseeded random
temperature values, which made it the only fixture in the repository that could
not be regenerated — 400 seed and distribution combinations were searched
without recovering them. Since every NetCDF gate depends on comparing the
committed bytes against a fresh build, the file is now emitted by
`scripts/generate_netcdf_fixtures.py` from a deterministic ramp.

Shape `(5, 8)`, `float64`, `_FillValue = -9999.0` and both fill positions
(row 0 column 0, row 3 column 5) are preserved exactly, so every assertion the
case declared still holds. **Only the temperature values differ.** Anyone who
pinned an earlier release and asserted against specific temperatures will see a
change; nothing in this repository does, because the case's own assertions are
structural.

Three declarations were also removed as undemonstrable:

- `coordinate_order` and `dimension_mismatch` risk types — this is conventional
  `(latitude, longitude)` rectilinear data, which exercises neither.
- `expect_crs` / `expected_epsg` — the file has no `grid_mapping` attribute and
  no `crs` variable, so there is nothing in the bytes for a CRS check to read.

The dimension-ordering risk is carried instead by `cf_time_ordering_netcdf`,
against a file whose dimensions are genuinely non-conventional.
