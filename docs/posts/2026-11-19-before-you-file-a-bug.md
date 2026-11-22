---
title: "Before you file a bug, check whether anyone will read it"
description: "Two STAC loaders read the same scaled raster 10,000 times apart. Both problems are already public, and the threads show how long a report can sit."
date: 2026-11-19
risk_types: [scaling/ignored]
cases: [ndvi_scaled_int16_small]
---

# Before you file a bug, check whether anyone will read it

Give two STAC loaders the same Item and the same 16 x 16 raster and they return
numbers that differ by a factor of 10,000. Neither raises or warns. We found the
cause, went to report it, and found that every relevant thread was already
public. The more useful finding was how long those threads have been open.

## The case

[`ndvi_scaled_int16_small`](../_generated/catalog/cases/ndvi_scaled_int16_small.md)
is an `int16` NDVI raster with a `0.0001` scale factor and a NoData sentinel of
-32768. The values are stored as integers because that is how scaled products
ship: Sentinel-2 L2A reflectance, for example, is stored as integers with a scale
and, from baseline 04.00, an offset. A reader that skips the scale returns NDVI
"in the thousands", which is not a valid NDVI.

## The numbers, from the file

```python
import geocase

case = geocase.load_case("ndvi_scaled_int16_small")
with case.open() as ds:                 # rasterio dataset
    a = ds.read(1, masked=True)
    scale = ds.scales[0]

a.min(), a.max()                        # -9922, -7647   (raw integers)
a.min() * scale, a.max() * scale        # -0.9922, -0.7647
```

The raw range is -9922 to -7647. With the declared scale applied it is -0.9922
to -0.7647. Both ranges describe the same bytes; only one is an NDVI.

When we wrapped the raster in a STAC Item with `raster:bands` carrying
`scale: 0.0001` and loaded it with both libraries, they disagreed exactly by that
factor:

| loader | range returned |
|---|---|
| odc-stac `.load()` | -9922 .. -7647 (raw integers) |
| stackstac `.stack()` | -0.9922 .. -0.7647 (scaled) |

odc-stac copies only the `nodata`, `data_type` and `unit` fields out of
`raster:bands`, so it has nowhere to keep a scale or an offset. stackstac applies
them. Nothing in either output tells you the other exists.

## The threads are already public

This is not a new finding, and the reports are not ours.

- [odc-stac#55](https://github.com/opendatacube/odc-stac/issues/55) asks for
  `raster:bands` scale and offset support. It was opened on 2022-04-21, has 13
  comments, and is still open. The last activity was in March 2024.
- [stackstac#262](https://github.com/gjoseph92/stackstac/issues/262) reports
  that stackstac requires the deprecated `proj:epsg` and so rejects Items parsed
  by current pystac. It was opened on 2024-11-28 and is still open. A fix,
  [PR #263](https://github.com/gjoseph92/stackstac/pull/263), has not been
  merged.
- [stackstac#270](https://github.com/gjoseph92/stackstac/issues/270) is titled
  "Has the project been abandoned?". It was opened on 2026-03-12, has 8 comments
  and is still open.

We filed nothing on these. A new issue on odc-stac would have been a duplicate of
a four-year-old thread. A new issue on stackstac would have joined a queue that
its own users are asking whether anyone reads. What we added instead was the
comparison above, because a side-by-side of two libraries on one input is sharper
evidence than a description.

## What to do instead

- Search before you write. Open and closed issues, and the open pull requests,
  often hold the answer or the exact duplicate.
- Check the repository's pulse. Look at the date of the last merged pull request
  and whether a pull request that fixes your problem is already sitting
  unreviewed. A report to a repo with no reviewers does not get a fix; a
  patch, or a pin and a note in your own code, does more.
- Do not treat "it loaded" as "it is right". Load the same file through a second,
  independent reader and compare ranges. A factor of 10,000 is easy to see once
  you look and invisible if you do not.
- Apply scale and offset yourself, and assert on the result. A range check such
  as `-1 <= ndvi <= 1` fails on the odc-stac output above and passes on the
  correct one.

## Try it

The case page:
[`ndvi_scaled_int16_small`](../_generated/catalog/cases/ndvi_scaled_int16_small.md).
Cases where a declared scale or offset is not applied are listed under the
[`scaling/ignored`](../_generated/catalog/risk/scaling-ignored.md) risk hub.
