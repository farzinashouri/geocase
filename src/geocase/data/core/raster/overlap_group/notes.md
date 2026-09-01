# Overlap Group

Three small rasters that exist only as a **group**. They share a directory for
the same reason the footprint edge cases and the transform conventions do:
their value is entirely in the relationship between them, and no one of them
means anything alone.

## Why these exist

Every other raster case in this catalog is one standalone file. That made four
things unexpressible:

- stacking order,
- mosaic compositing,
- temporal grouping,
- and two assets in one STAC Item.

`odc.stac.load` and `stackstac.stack` both take a **sequence** of Items, and
what happens across that sequence is their whole reason for existing. The
2026-08-31 round-2 validation run could only ever hand them a list of one, so
the entire surface went untested — and it is the surface those two libraries
are.

## The geometry

| Case | Stack order | Constant value | Band alias | Nodata corner |
|---|---|---|---|---|
| `overlap_group_north` | 1 | 10.0 | `red` | top-left |
| `overlap_group_centre` | 2 | 20.0 | `red` | top-right |
| `overlap_group_south` | 3 | 30.0 | `nir` | bottom-left |

Each is 12×12 at 30 m in EPSG:32633, offset from its predecessor by **6 cells
diagonally** — half its width. Four properties are load-bearing and each is
gated in `tests/unit/test_raster_groups.py`:

- **Partial overlap.** Disjoint members never composite; identical members make
  compositing unobservable. Consecutive members overlap in a quarter of their
  area.
- **A shared pixel grid.** Off-grid members would turn every compositing
  difference into a resampling difference, which is a different finding on a
  different axis.
- **Distinct constant values.** "Which pixel won" is then readable by
  inspection rather than by arithmetic.
- **One nodata corner each, at a different corner.** A composite's fill
  behaviour is visible as well as its ordering.

## The shared band alias

Two of the three declare `common_name: red`. That is the ordinary Sentinel-2
shape — several assets legitimately carrying the same alias — and it is what
makes a consumer resolving the alias **silently to the first candidate**
visible rather than invisible. `odc-stac` does exactly that today, and its
source carries its own `# maybe warn about ambiguity?` note.

The two red members carry different constant values (10.0 and 20.0), so
resolving to the wrong one is a wrong *value*, not merely a wrong provenance.

## Reading them as STAC Items

```python
from geocase.stac import items_for_cases

items = items_for_cases(
    include_ids=[
        "overlap_group_north",
        "overlap_group_centre",
        "overlap_group_south",
    ],
    assets="per_band",
)
```

`geocase.stac` normalises `proj:bbox` and emits both `proj:epsg` and
`proj:code`, so the same list is byte-identical input for stackstac and
odc-stac. See `docs/plans/38-six-consumer-round-2-and-the-stac-adapter.md`.
