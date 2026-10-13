# PROJ differential round: pyproj vs GDAL `osr` (#47)

**Result: clean.** Every compared case agreed in all four passes. No `known_divergences`
were added and no corpus case changed.

Harness: `examples/test_differential_proj.py`, built on `geocase.differential.run_round` /
`render_report`, comparing with `compare_crs_facts`. Neither side is the oracle.

| | |
|---|---|
| pyproj | 3.7.2 |
| PROJ (pyproj) | 9.7.1 |
| GDAL (`osgeo.osr`) | 3.12.2 |

Both bindings wrap PROJ, so a disagreement would have been in a binding or its defaults
(axis order, authority lookup, pipeline choice), not in PROJ itself. Had one appeared, the
repro would need `projinfo` / `cs2cs` before anything was said about PROJ.

## What was compared

Per case: authority code, axis directions, units, `is_geographic`, `is_projected`; the
case's `extent` corners transformed from EPSG:4326 into the CRS and back (tolerance 1e-9 deg
for degrees, 1e-6 m otherwise); a WKT2 export/re-parse on each side (must not raise). Four
passes: CRS from the case's declared `crs` or from the file's own WKT, each with traditional
GIS axis order (`always_xy=True` / `OAMS_TRADITIONAL_GIS_ORDER`) and authority axis order.

| pass | compared | agree | diverged | errored |
|---|---|---|---|---|
| declared, traditional | 164 | 164 | 0 | 0 |
| declared, authority | 164 | 164 | 0 | 0 |
| file, traditional | 138 | 138 | 0 | 0 |
| file, authority | 138 | 138 | 0 | 0 |

## What was left out, and why

- 5 cases with `crs: None`: nothing to parse.
- 6 cases with no computed extent (netcdf): no corners to transform.
- File passes only: 20 cases GDAL cannot open here (WKB/WKT blobs; Arrow/Parquet without
  `libgdal-arrow-parquet`) and 6 CSV cases, which carry no CRS. The harness counts two
  identical failures as `agree`, so leaving these in would have padded the count with
  cases that compared nothing.
- The file passes extract the WKT with GDAL on both sides, so a difference there would be
  in the parse, not the file reading.

## Environment finding (not a corpus finding)

In this checkout, `osr` could not open `proj.db` from the conda env
(`proj_create_from_database: Open of .../share/proj failed`) while pyproj, using the same
directory, could. Calling `osr.SetPROJSearchPaths([pyproj.datadir.get_data_dir()])` fixed
it, and the example does that so both bindings read one database. Without it, 148 of 164
cases reported `errored` for a reason that is not about any case. Cause not investigated;
not filed.

## Limits of a clean result

164 of 175 cases is the declared-CRS coverage, and the CRS set is small (EPSG:4326, 32633,
3995, 32601, 32756, 32632, 3857). A clean round on these says the two bindings agree here,
not that they agree on every CRS.
