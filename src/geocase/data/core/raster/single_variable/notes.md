# Single-variable controls

Three rasters that each differ from a plain north-up square in **exactly one**
respect. They exist because of an observation from the third external round:

> `rotated_two_islands` was the round's one genuine discovery — a rotated
> geotransform the reporter would not have constructed unprompted. But it
> bundles rotation *with* sparse islands *with* footprint generation. A failure
> with one possible cause is a better bug-finder than a case combining three
> risks.

| case | isolates | bundled counterpart |
|---|---|---|
| `rotated_only_square` | a rotated geotransform (30°) | `rotated_two_islands` |
| `nodata_only_dem_small` | one sentinel nodata value | — |
| `bottom_up_only_square` | a positive-`e` affine | `bottom_up_dem_small` |

## How to use them

They are **controls**, not coverage. Run a consumer against the control and its
bundled counterpart together:

- fails on **both** → the defect is the isolated convention, and it is localised
  with no further argument;
- fails on the **bundled case only** → the interaction between variables is what
  breaks it, which is a different and more interesting bug;
- fails on the **control only** → the bundled case is masking the defect, which
  usually means a second variable is short-circuiting the code path.

## What is deliberately absent

`rotated_only_square` and `bottom_up_only_square` carry **no nodata at all** —
`src.nodata` is `None`, not a declared sentinel that never appears. A sentinel
that is declared and never occurs is the "declared but ungated" shape that Plan
28 Phase 1 found six times in this very corpus, and it would reintroduce the
second variable these cases exist to remove.

`nodata_only_dem_small`'s two sentinels sit in the **interior** (rows 3 and 4),
not on the border. A border sentinel is skipped by any consumer that crops
edges before computing statistics, which would make the case silently inert.

None of the three is a new `from_origin` baseline. Plans 37 §3.3 and 38 §4.5
both record that the corpus is already thick there and that no format baseline
has found a defect in three rounds.

## The answers are shipped, not implied

All three declare `expected_bounds`, and `rotated_only_square` also declares
`expected_pixel_world_pairs` — the pixel↔world round trip. That is the oracle
round 4's reporter had to hand-roll before they could prove a bounds bug, and
it is the difference between a case that is a *stimulus* and one that is an
*oracle*. Every declared value is generated from the real bytes by
`scripts/catalog_truth.py` and gated by `scripts/validate_case_content.py`, so
none of them can drift away from the pixels.
