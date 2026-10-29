---
title: "Why your raster mean is negative"
description: "Two NoData pixels of -9999 in a 100-pixel raster of positive values turn a mean of 48.08 into -152.86. Nothing raises."
date: 2026-10-29
risk_types: [nodata/ignored, measurement/incorrect_statistics]
cases: [geotiff_nodata_small]
---

# Why your raster mean is negative

A 10 x 10 float32 GeoTIFF holds 98 measurements between 0.74 and 97.56,
and 2 pixels that say "no data here". Ask numpy for its mean and you get
-152.86. Every real value in the file is positive. The mean is negative, no
exception was raised, and the number looks like a plausible result until
someone asks why.

## The failing call

The raster is [`geotiff_nodata_small`](../_generated/catalog/cases/geotiff_nodata_small.md).
It declares `-9999` as its NoData value. The two computations below differ by
one line:

```python
import numpy as np
import rasterio

with rasterio.open("nodata_sample.tif") as ds:
    a = ds.read(1)
    nd = ds.nodata                      # -9999.0

print(a.mean())                         # -152.8628
print(a[a != nd].mean())                # 48.0787
print(a.min(), a[a != nd].min())        # -9999.0  0.7362
```

The first mean divides the sum of all 100 pixels by 100. The second divides the
sum of the 98 valid pixels by 98. The two sentinel pixels contribute
2 x -9999 = -19,998 to the numerator, and that outweighs the valid sum of
about 4,712 (98 x 48.08), so the sign flips. The minimum is wrong in the same way: it
reports the sentinel, -9999, instead of the smallest real value, 0.74.

## Why nothing complains

The file is valid. The sentinel is stored as an ordinary float, and
`ds.read(1)` returns a plain `ndarray` with the same dtype as the band. NoData
is metadata on the dataset, not on the array, so the information needed to do
the right thing is one attribute away from the data and numpy never sees it.

The error also scales badly with how little of the raster is missing. Here 2%
of the pixels moved the mean by about 201 units, more than four times the true
mean. A raster with a few NoData pixels at the edge of a scene is the common
case, and the result is wrong by an amount that depends on the sentinel, not
on the data.

## Defences that work

- Read with a mask: `ds.read(1, masked=True)` returns a masked array and
  `.mean()` on it gives 48.0787 for this file.
- Mask explicitly with the dataset's declared value, as above, rather than a
  hard-coded `-9999`. Another file may use `-32768`, `0` or `NaN`.
- For a `NaN` NoData value, `a != nd` is always true because `NaN != NaN`.
  Use `np.isnan`, or `np.nanmean`, there. The catalog keeps that case apart
  under
  [`nodata/nan_mishandled`](../_generated/catalog/risk/nodata-nan-mishandled.md).
- Add a test that your statistics function returns the masked value on a file
  with a known sentinel. The expected figures for this case are declared in
  its `case.yaml` and checked against the bytes in CI: masked mean 48.0787,
  naive mean -152.8628, 2 NoData pixels.

## Try it

The case page: [`geotiff_nodata_small`](../_generated/catalog/cases/geotiff_nodata_small.md).
Every case where a NoData convention is ignored is listed under the
[`nodata/ignored`](../_generated/catalog/risk/nodata-ignored.md) risk hub.
