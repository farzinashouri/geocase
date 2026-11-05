---
title: "odc-stac: crs= without resolution= gives a 1 x 1 raster"
description: "A 16 x 16 raster at 10 m, loaded with crs=EPSG:4326, comes back as one pixel. The 10 is read as degrees. Nothing raises."
date: 2026-11-05
risk_types: [crs/units, crs/reprojection_error]
cases: [dem_small]
---

# odc-stac: `crs=` without `resolution=` gives a 1 x 1 raster

A 16 x 16 DEM in EPSG:32633 has 10 m pixels. Load it through
`odc.stac.load` and you get a `(1, 16, 16)` array. Add `crs="EPSG:4326"` and
leave `resolution` out, and the same item comes back as `(1, 1, 1)`: one pixel
for the whole scene. No exception, no warning, and the dataset is a perfectly
valid xarray object that happens to hold almost no data.

## The failing call

The raster is [`dem_small`](../_generated/catalog/cases/dem_small.md): 16 x 16
pixels, EPSG:32633, origin (500000, 4500000), 10 m pixels. Wrapped in a STAC
item with the `projection` extension, the two calls differ by one argument
(odc-stac 0.5.3, odc-geo 0.5.3, as reported in the
[public thread](https://github.com/opendatacube/odc-stac/issues/288)):

```python
odc.stac.load([item], bands=["data"]).data.shape                    # (1, 16, 16)
odc.stac.load([item], bands=["data"], crs="EPSG:4326").data.shape   # (1, 1, 1)
```

The cause, as the maintainer confirmed in that thread: when the caller supplies
`crs=` but not `resolution=`, the resolution is taken from the native
metadata, 10, and then used unchanged in the new CRS. In EPSG:4326 the unit is
degrees, so the grid asks for 10-degree pixels.

## The numbers, from the file

The footprint of `dem_small` in EPSG:4326, computed with rasterio and pyproj
from the file's own bounds, is 0.001893 degrees wide and 0.001441 degrees
tall. Divide by a 10-degree pixel and both axes round up to 1 cell. That is
the `(1, 1)` above.

What the caller wanted was 10 metres, and that is not one number in degrees.
At the centre of this scene (latitude 40.65) 10 m east is 0.0001183 degrees
and 10 m north is 0.0000901 degrees. Divide the footprint by those and you get
16.0 columns and 16.0 rows, the original grid. A scalar resolution cannot be
converted exactly: the east-west size of a degree shrinks with the cosine of
latitude, so any conversion has to choose a reference point. The thread
discusses using the output bounding box centre, which is the choice
`odc_geo`'s `compute_output_geobox` already makes.

## Status

The odc-stac maintainer confirmed the diagnosis. It is not fixed: the issue is
open, and the maintainer wrote that a fix may need some refactoring and has
not committed to an approach yet.

## Defences that work

- Pass `resolution=` whenever you pass `crs=`, in the units of the target CRS.
  For EPSG:4326 that means degrees, for example `0.0001`.
- Assert on the output shape. A test that checks `ds.sizes` against the
  expected pixel count catches this at once; the failure is a valid array of
  the wrong size, not an error.
- Compare the output footprint with the input footprint after reprojection. A
  one-pixel result covers the scene extent with a single cell, so area is
  right and everything inside it is gone.
- Watch for the same shape of bug in other loaders: a parameter whose unit is
  inherited from the source CRS and silently reused in the target CRS.

## Try it

The case page: [`dem_small`](../_generated/catalog/cases/dem_small.md). Cases
where a distance or pixel size is read in the wrong CRS unit are listed under
the [`crs/units`](../_generated/catalog/risk/crs-units.md) risk hub.
