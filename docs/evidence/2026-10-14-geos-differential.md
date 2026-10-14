# GEOS differential round: shapely vs `osgeo.ogr` (#48)

**Result: clean.** 84 vector cases compared, 84 agreed. No `known_divergences` were added
and no corpus case changed. Nothing to file upstream.

Harness: `examples/test_differential_geos.py`, built on `geocase.differential.run_round` /
`render_report`, comparing with `compare_geometry_ops`. Neither side is the oracle.

| | |
|---|---|
| shapely | 2.1.2 |
| GEOS (shapely) | 3.14.1 |
| GEOS (GDAL) | 3.14.1 |
| GDAL | 3.12.2 |

**Same GEOS version on both sides** (conda-forge ships one `libgeos`), so a clean result
mostly shows the two front ends' defaults agree. It cannot show a GEOS version difference.
A run with a pip shapely wheel against conda GDAL would.

## What was compared

Both sides parse the **same ISO WKB** (read once with `osgeo.ogr`), so reading is out of
the picture. Per feature: `is_valid`, `is_empty`, `area`, `length`, `buffer(0)` area,
centroid, envelope, `make_valid` (validity, type, area), `simplify(0.01)` area; per case:
area and type of the union of all features. Floats agree within relative 1e-9.

| | |
|---|---|
| compared | 84 |
| agree | 84 |
| diverged / known / errored | 0 / 0 / 0 |

## Left out

41 of 125 vector cases: OGR cannot open them here (WKB/WKT blobs, Arrow/Parquet without
`libgdal-arrow-parquet`) or they hold no geometry (CSV text columns). Counting them would pad
`agree` with cases that compared nothing. OGR exposes no `is_valid` reason, so only the
boolean is compared.

## Harness artifacts fixed along the way (not findings)

The first run showed 2 diverged and 1 errored; all three were the harness, not GEOS:

- `empty_polygon`: shapely's `union_all` of one empty polygon is `GEOMETRYCOLLECTION EMPTY`;
  the first harness never called OGR's union for a single feature. Now both use a unary union.
- `unclosed_ring_polygon`: both sides refused with the same GEOS message but different
  exception types. Parse failures are now normalised to one type.
- `geometrycollection_mixed_valid`: OGR `Length()` is 0 for areal parts, so the harness used
  `Boundary().Length()`, which GEOS does not support on a collection. Now summed per part.

`Length()` for a polygon is a definition difference (OGR: 0, shapely: perimeter), handled by
using the boundary on the OGR side.
