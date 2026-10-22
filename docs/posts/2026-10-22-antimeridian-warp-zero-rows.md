---
title: "The antimeridian warp that came back with zero rows"
description: "GDAL's AutoCreateWarpedVRT returned a 23 x 0 dataset for a 16 x 16 raster crossing 180 degrees, with no error. Reported as gdal#15266, fixed by gdal#15274."
date: 2026-10-22
risk_types: [extent/antimeridian, extent/bounds_normalization]
cases: [optical_dateline_small]
---

# The antimeridian warp that came back with zero rows

A 16 x 16 GeoTIFF in EPSG:4326 goes into `gdal.AutoCreateWarpedVRT` with a
target of EPSG:3857. What comes back is a dataset 23 pixels wide and 0 pixels
tall. No exception, no warning. The failure shows up later, in whatever you do
with the dataset, and it names the wrong thing.

## The failing call

The raster is [`optical_dateline_small`](../_generated/catalog/cases/optical_dateline_small.md).
Its geotransform is `(179.9, 0.02, 0, 1.0, 0, -0.02)`, so the eastern edge
sits at 179.9 + 16 x 0.02 = 180.22 degrees. The reproduction from the report
(GDAL 3.12.2) is:

```python
from osgeo import gdal

gdal.UseExceptions()
src = gdal.Open("optical_dateline_small.tif")
vrt = gdal.AutoCreateWarpedVRT(src, None, "EPSG:3857")
print(vrt.RasterXSize, "x", vrt.RasterYSize)   # 23 x 0
```

Passing that VRT on to `gdal.Warp` ends in "Attempt to create 23x0 dataset is
illegal". That message describes the symptom, and a reader is sent looking at
the output size rather than at the source extent.

## Where the zero comes from

The raster is 0.32 degrees wide and 0.32 degrees tall, about 35 km on a side.
The numbers below come from the file's own bounds, using the spherical Web
Mercator formulas (radius 6,378,137 m):

```python
import math
import rasterio

R = 6378137.0
with rasterio.open("optical_dateline_small.tif") as ds:
    west, south, east, north = ds.bounds

east_wrapped = ((east + 180) % 360) - 180          # 180.22 -> -179.78
x = lambda lon: math.radians(lon) * R
y = lambda lat: R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

print(x(west), x(east_wrapped))                    # 20026376 m, -20013018 m
print(abs(x(east_wrapped) - x(west)))              # 40,039,394 m
print(y(north) - y(south))                         # 35,626 m
```

PROJ wraps the eastern edge from 180.22 to -179.78 degrees, which is
-20,013,018 m in Web Mercator. The western edge stays at +20,026,376 m. The
suggested output extent therefore spans 40,039,394 m in X, about the width of
the planet, against 35,626 m in Y. That is a ratio of roughly 1,124 to 1.

GDAL picks one square pixel size for the output from the diagonal of that
extent, which is dominated by the X span. A pixel that size is larger than the
whole 35,626 m height, and the row count, computed as height divided by pixel
size, rounds down to 0. According to the report, the code already clamped the
opposite case, dimensions that come out too large, a few lines above. The
rounds-to-zero side had no check.

## What it means for your pipeline

Any raster that straddles 180 degrees and is warped to a projected CRS with an
automatic output grid can hit this. Scenes over the North Pacific and
tiles produced by a tiler that does not split at the antimeridian are the
likely sources. A small footprint makes it worse, because the zero comes
from a tall-and-thin ratio: a larger raster might round to one or two rows and
produce a distorted output instead of an error.

Two practical defences hold whatever version you run. Split the footprint at
180 degrees and warp each side separately, or give the warp an explicit target
with its own bounding box, size and CRS rather than asking GDAL to derive one.
A commenter on the tracker preferred the second: warping
to a CRS alone lets the heuristics choose different resolution and offset for
each half, so two pre-split grids may not line up.

## Status

The issue is [gdal#15266](https://github.com/OSGeo/gdal/issues/15266), now
closed. The fix, [gdal#15274](https://github.com/OSGeo/gdal/pull/15274), was
merged on 2026-10-01. It does not change the computed grid: it makes
`GDALSuggestedWarpOutput2` raise an error when the computed dimensions are zero,
so the failure is reported at the call that caused it. The fix is in GDAL's
main branch and will reach users with a future release; GDAL 3.12.2 still
returns the zero-row dataset. A source that crosses 180 degrees is still not
warped to a useful grid by the automatic path, so the defences above stay
relevant after upgrading.

## Try it

The case carries the footprint with `west > east` in its declared extent, the
convention for a box that crosses the antimeridian, so you can feed it to your
own bounds code as well as to GDAL. The case page:
[`optical_dateline_small`](../_generated/catalog/cases/optical_dateline_small.md).
Every case that exercises the same edge is listed under the
[`extent/antimeridian`](../_generated/catalog/risk/extent-antimeridian.md)
risk hub.
