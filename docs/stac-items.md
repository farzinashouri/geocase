---
title: STAC Items for raster cases
description: "geocase.stac turns any bundled raster case into a STAC Item, so stackstac and odc-stac get byte-identical input without each user rewriting the adapter."
---

# STAC Items for raster cases

Some consumers cannot read a file. `stackstac.stack` and `odc.stac.load` both
take **STAC Items**, so pointing either of them at a bundled GeoTIFF requires an
adapter first. `geocase.stac` is that adapter.

```python
from geocase.stac import item_for_case, items_for_cases

item = item_for_case("dem_small")            # one Item, as a plain dict
items = items_for_cases(category="raster")   # every raster case, in catalog order
```

Output is a plain `dict`, not a `pystac.Item`. A STAC Item is JSON, and
requiring `pystac` to produce one would put a dependency between this catalog
and every consumer that does not use it. `pystac.Item.from_dict` accepts what
this emits.

## Why this ships instead of being an example

A validation run on 2026-08-31 read the corpus with six consumers. Two of them
needed Items, so the run synthesised one per raster case with
`rio_stac.create_stac_item` — and that synthesiser was **wrong for
`bottom_up_dem_small`**, writing an inverted `proj:bbox` (south greater than
north) because it trusted the transform's row order on a bottom-up affine.

The resulting Item is invalid. A consumer that trusts it computes an empty or
inverted intersection and reports nothing, which reads as *the case is fine*.
Every user who writes that adapter hits the same bug, and most misattribute it
to the consumer. So the catalog owns it.

## Three things the hand-built version got wrong

### Both `proj:epsg` and `proj:code`

The projection extension renamed the key in v2.0. `stackstac` reads only
`proj:epsg`; `pystac` ≥ 1.13 rewrites it to `proj:code` on `from_dict`. An
adapter emitting one of them silently excludes a consumer — no error, just a
grid derived from nothing.

Emitting both is spec-legal, and it is the only way one Item serves both:

```python
properties = item_for_case("dem_small")["properties"]
properties["proj:epsg"]  # 32633
properties["proj:code"]  # "EPSG:32633"
```

### A normalised `proj:bbox`

Every bbox this module emits is `[west, south, east, north]` with min before
max on both axes, regardless of what the file's affine implies. That is the
`bottom_up_dem_small` fix, and it is gated for the north-up, bottom-up and
rotated cases in `tests/unit/test_stac.py`.

### Per-band *and* whole-file assets

The two consumers disagree about what an asset is. `stackstac`'s model is one
band per asset, and it refuses a multi-band raster; `odc-stac` reads the whole
file from one asset. Both shapes are reachable, so the difference is a **choice
your harness records** rather than a failure it trips over:

| `assets=` | Shape | Suits |
|---|---|---|
| `"whole_file"` (default) | one `data` asset naming the file | odc-stac |
| `"per_band"` | one asset per band, each with `band_index` | stackstac |
| `"both"` | the file asset *and* the band assets | either, from one Item |

```python
item = item_for_case("geotiff_multiband_small", assets="per_band")
sorted(asset["band_index"] for asset in item["assets"].values())  # [1, 2, 3]
```

## Hrefs

`href_style="file_url"` (the default) emits a `file://` URI, which is what
pystac and stackstac expect. `href_style="path"` emits a bare filesystem path,
for the consumers that mishandle `file://`.

## Groups of Items

`items_for_cases` is the reason the [overlap
group](_generated/catalog/cases/overlap_group_north.md) exists. Both libraries
take a *sequence* of Items and what happens across that sequence is their whole
reason for existing — stacking order, mosaic compositing, band-alias
resolution. Until the group landed, the corpus could only ever hand them a list
of one.

```python
items = items_for_cases(
    include_ids=[
        "overlap_group_north",
        "overlap_group_centre",
        "overlap_group_south",
    ],
    assets="per_band",
)
```

Two of those three declare `common_name: red` — the ordinary Sentinel-2 shape —
so a consumer resolving the alias silently to the first candidate is visible
rather than invisible.

Non-raster cases in a selection are **skipped**, not an error. A sweep helper
that dies on the first vector case cannot be pointed at the corpus, which is
the only thing anyone wants to point it at.

## Related docs

- [Differential testing](differential-testing.md) — the harness these Items feed
- [Case discovery](case-discovery.md) — the selectors `items_for_cases` forwards to
- [Dataset catalog](dataset-catalog.md) — what is in the raster set
