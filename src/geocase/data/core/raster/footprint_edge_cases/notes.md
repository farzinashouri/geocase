# Footprint Edge Cases

Bundled raster fixtures used to stress-test GDAL footprint generation.

## Files

- `all_valid_rectangular.tif`: Full-valid rectangular tile (baseline).
- `hole_center_nodata.tif`: Valid pixels form a donut-like shape around an
  interior NoData void (a 4x4 block at the centre of a 12x12 scene). The outer
  border is deliberately *valid*, which is what makes footprint extraction that
  ignores NoData visibly wrong: it returns the solid rectangle instead of a ring.
- `rotated_two_islands.tif`: Rotated/skewed transform with disconnected valid islands.
- `nonsquare_diagonal_sparse.tif`: Non-square pixel transform with sparse diagonal valid cells.
- `thin_corridor_shape.tif`: Narrow corridor geometry sensitive to simplification/shape artifacts.

## Intent

These scenes are intentionally small but geometrically tricky, so footprint code
can be validated against edge conditions without requiring external datasets.

## Two kinds of footprint fixture

Each raster ships a footprint sidecar, and until Plan 32 they did not all mean
the same thing while all being named as if they did. They are now split by
filename, because the name is what a reader trusts:

- `<case>_footprint_truth.geojson` — **ground truth.** Derived from the
  raster's own valid-pixel mask by `scripts/generate_raster_fixtures.py`, from
  the same array that writes the GeoTIFF, so it cannot drift by construction.
  This is what `params.expected_footprint` points at, and what the content gate
  (`scripts/validate_case_content.py`) checks against on part count, area and
  hole count.
- `<case>_footprint_gdal_hull.geojson` — **a recording of one consumer's
  answer.** These are the files originally committed here, produced by the GDAL
  footprint utility, which returns a simplified/hull-like polygon rather than
  the mask. Kept, not deleted, so a future change in GDAL's behaviour is still
  detectable; pointed at by `params.recorded_gdal_footprint`.

`all_valid_rectangular` has no `_gdal_hull` file: every pixel is valid, so the
hull *is* the mask and the second file would be byte-identical.

### How far apart the two are

| Case | GDAL hull | Mask-exact truth | Inflation |
|---|---|---|---|
| `all_valid_rectangular` | Polygon 129600.0 | Polygon 129600.0 | 1.000 |
| `hole_center_nodata` | Polygon 115200.0 | Polygon 115200.0 (1 hole) | 1.000 |
| `rotated_two_islands` | Polygon 15562.5 | **MultiPolygon** 7875.0 | 1.976× |
| `nonsquare_diagonal_sparse` | Polygon 27000.0 | **MultiPolygon** 14400.0 | 1.875× |
| `thin_corridor_shape` | Polygon 38437.5 | Polygon 13750.0 | 2.795× |

For `rotated_two_islands` and `nonsquare_diagonal_sparse` the hull is not merely
larger — it merges regions that are genuinely disjoint. A consumer validating
"does my footprint code keep disjoint regions disjoint?" against the hull would
be told that merging them is correct.

`examples/test_gdal_footprint.py` asserts both halves: GDAL still reproduces its
own recording exactly, *and* GDAL's answer strictly covers and exceeds the truth
for those three, with the parts merged. Before Plan 32 it compared GDAL only to
the hull at `max_diff_ratio=1e-10` — a regression check on GDAL against itself,
which could not fail for the reason these cases exist.

### `min_rect_ratio`

The thresholds in each `case.yaml` describe genuinely non-rectangular shapes and
were re-derived from the truth geometry in Plan 32. The previous values
(0.74 / 0.93 / 0.76 / 0.98) had been fitted to the hulls, which are
near-rectangular by construction, so they asserted almost nothing; the truth
ratios are 0.375 / 0.500 / 0.275 / 0.889.

### Regeneration

Every raster here and every `_footprint_truth.geojson` is emitted by
`scripts/generate_raster_fixtures.py` from a single array, so the two cannot
drift apart. They previously did: the committed `hole_center_nodata` raster
carried NoData on the 1 px outer border with a fully valid interior — the exact
inverse of the description above — and its footprint had been regenerated from
that drifted raster, so the two agreed with each other while contradicting the
case's stated purpose. See `docs/plans/28-validate-geocase.md` Phase 1 and
`docs/plans/32-footprint-truth-and-ambiguous-zero.md` Phase 1.
