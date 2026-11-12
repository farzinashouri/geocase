---
title: "A polygon that crosses the dateline is not a bug: your bbox is"
description: "A 20 x 10 degree polygon across the antimeridian becomes a 340 x 10 degree box after a Web Mercator round trip. The polygon was fine."
date: 2026-11-12
risk_types: [extent/bbox_misinterpretation, extent/coordinate_wrapping]
cases: [dateline_crossing_polygon]
---

# A polygon that crosses the dateline is not a bug: your bbox is

Take a rectangle in the North Pacific, 20 degrees wide and 10 degrees tall,
straddling the antimeridian. Send it to Web Mercator and back, ask for its
bounds, and you get a box 340 degrees wide. The polygon did not change. The
number you asked it for was always going to be wrong, because a bounding box
written as `[west, south, east, north]` has no way to say "go east from 170 and
stop at 170 on the other side".

## The case

[`dateline_crossing_polygon`](../_generated/catalog/cases/dateline_crossing_polygon.md)
is one valid `Polygon` in EPSG:4326. Its ring, read straight from
`geometry.geojson`, is:

```text
(170, 40) (190, 40) (190, 50) (170, 50) (170, 40)
```

The longitudes run 170 to 190. That is a legal way to write a shape that crosses
the antimeridian, because it keeps the ring continuous. It is also outside the
`[-180, 180]` range that a lot of code assumes, so what happens next depends on
which tool touches it.

## The numbers, from the file

```python
import geocase

gdf = geocase.load_case("dateline_crossing_polygon").load()

gdf.total_bounds                        # [170, 40, 190, 50]
w, s, e, n = gdf.total_bounds
(e - w) * (n - s)                       # 200 square degrees

back = gdf.to_crs(3857).to_crs(4326)
back.total_bounds                       # [-170, 40, 170, 50]
w, s, e, n = back.total_bounds
(e - w) * (n - s)                       # 3400 square degrees
```

Before the round trip, the bounds are `[170, 40, 190, 50]` and the box covers
200 square degrees. After it, the bounds are `[-170, 40, 170, 50]` and the box
covers 3,400. That is 17 times more area, and it is the wrong 3,400: the new
box is the whole band of longitude from -170 to 170, which is the part of the
Pacific the polygon is not in. In Web Mercator the projected x range of the
polygon is about -18,924 km to 18,924 km, the full width of the map, because
the shape was wrapped to the other edge and its extent now spans it.

Nothing raised. Every step returned a valid geometry in a valid CRS.

## Why the obvious test passes

The check people reach for is "if `east - west` is more than 180, the box
crosses the dateline". On the original file it does not fire: `190 - 170` is 20.
The shape crosses the antimeridian but the check reads it as a small box
that merely extends past 180. The same check on the round-tripped bounds gives
340, and then it does fire, on a geometry that now describes the wrong region.
A rule keyed on width cannot tell the two cases apart, because the information
that matters is not in the width. It is in which way the ring was wrapped.

## What to do instead

- Treat a bbox as a pair of longitudes with a direction, not a box. A filter that
  accepts `west > east` and means "wrap" is correct; one that silently swaps
  them is the bug.
- Normalise on purpose. Pick a convention for the pipeline (-180 to 180, or
  0 to 360) and convert at the edges, not in the middle where a reprojection
  does it for you.
- Test the round trip. Project, un-project, and compare bounds and area with
  the originals. An area that grows 17 times is not a rounding error.
- Split at the antimeridian when a tool needs a single box, and union the
  results, rather than asking one rectangle to cover two edges of the map.

## Try it

The case page:
[`dateline_crossing_polygon`](../_generated/catalog/cases/dateline_crossing_polygon.md).
Cases where a bbox or longitude is read without allowing for wrapping are listed
under the
[`extent/bbox_misinterpretation`](../_generated/catalog/risk/extent-bbox-misinterpretation.md)
risk hub; the wrapping side is under
[`extent/coordinate_wrapping`](../_generated/catalog/risk/extent-coordinate-wrapping.md).
