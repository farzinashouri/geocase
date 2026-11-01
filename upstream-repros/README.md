# Upstream repros: GDAL

One standalone script per GDAL defect found by the GeoCase corpus. Each script
builds its own input, does not import `geocase`, and can be given to a GDAL
maintainer as is.

Each script prints what it saw and ends with one line:

- `RESULT: REPRODUCED`: the defect is present in this environment (exit code 0);
- `RESULT: did not reproduce`: the defect is gone, for example fixed upstream (exit code 1).

Every script also runs a **control**: the same operation on an input where GDAL
behaves correctly. A script reports `REPRODUCED` only when the control passes,
so a broken environment does not look like a reproduced bug.

## Run

```bash
conda activate geocase              # GDAL 3.12.2; the gpkg script also needs pyogrio + geopandas
python run_all.py                   # every script, one line each
cd gdal && python -I repro_warp_zero_height.py   # one script, full output
```

Last full run: 2026-11-01. All three reproduce on GDAL 3.12.2; the two filed
ones also reproduce on the 3.13.3 release (their fixes are on master only).

## Findings

| Script | Defect | Status (2026-11-01) |
|---|---|---|
| `gdal/repro_small_coordinates_zeroed.py` | WKT and GeoJSON writers write `\|v\|` in `[1e-15, 1e-13)` as `0`, with no warning | [#15317](https://github.com/OSGeo/gdal/issues/15317), fixed on master by [#15369](https://github.com/OSGeo/gdal/pull/15369) |
| `gdal/repro_warp_zero_height.py` | `AutoCreateWarpedVRT` returns a `23x0` dataset for an antimeridian-crossing source, and reports success | [#15266](https://github.com/OSGeo/gdal/issues/15266), fixed on master by [#15274](https://github.com/OSGeo/gdal/pull/15274) |
| `gdal/repro_gpkg_arrow_spatial_filter_null_geometry.py` | GPKG: under a spatial filter, `OGR_L_GetArrowStream` returns the NULL-geometry row that the feature iterator excludes (3 rows vs 2) | [#15465](https://github.com/OSGeo/gdal/issues/15465), open; found through pyogrio (Plan 43 queue #10) |

## Sources

- `issues/`: the GDAL issue texts as filed.
- `docs/geocase_validate/pyogrio-bug-report.md`: the GPKG / Arrow draft.
- `~/projects/geocase_validation/findings/gdal/REPORT.md`: the GDAL round.
