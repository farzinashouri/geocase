# CRS Family Pair

The same ground written twice: once in a **projected** CRS (EPSG:32633, metres)
and once in a **geographic** one (EPSG:4326, degrees). A declared pair, in the
manner of `utm_zone_33n_to_32n_pair` and `crs_mismatch_overlay_pair` — a
divergence that is a *relationship between two inputs* is not expressible by two
independently selectable cases.

## Why this exists

31 of the catalog's 34 rasters were EPSG:32633. That made any "same case, two
CRSs" assertion untestable, and left reprojection sweeps leaning entirely on the
**target** CRS for variation.

It matters because the unit change is what pays. Round 2's odc-stac HIGH defect
needed nothing more exotic than `crs=` set to a target whose linear unit differs
from the source's — a single option value, and the one a consumer author is
least likely to think of testing. Until this pair, that axis was reachable only
from *outside* the corpus, through an external consumer's option.

## How the two halves relate

`crs_family_pair_projected.tif` is authored: a 16×16 float32 ramp at 30 m with a
`-9999.0` nodata cell in the top-left corner.

`crs_family_pair_geographic.tif` is **derived** from it by reprojection
(`scripts/generate_raster_fixtures.py`, `_write_geographic_twin`), which is why
it is 14×18 rather than 16×16 — a reprojected grid is not the same grid.

Deriving rather than authoring is deliberate, and follows
`rotated_two_islands_warped_reference`: a hand-authored twin drifts away from
the file it is the twin of, and that drift is what broke `hole_center_nodata`.
The two halves only mean anything together if they describe the same ground, so
the guarantee has to be structural rather than a promise in a comment.

`tests/unit/test_raster_groups.py` gates both directions: that the two are in
different CRS families with different linear units, and that their footprints
agree in WGS 84 to within a millidegree.
