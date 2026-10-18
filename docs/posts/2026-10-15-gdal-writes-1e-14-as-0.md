---
title: "GDAL writes 1e-14 as 0, and says nothing"
description: "A coordinate between 1e-15 and 1e-13 is written as 0 by GDAL's WKT and GeoJSON writers, with no error or warning. Reproduced on GDAL 3.12.2; reported as gdal#15317, fixed by gdal#15369."
date: 2026-10-15
risk_types: [precision/formatter_boundary, precision/denormal_magnitude, precision/loss]
cases: [numeric_boundary_1e14, numeric_boundary_1e13]
---

# GDAL writes 1e-14 as 0, and says nothing

A point at `(1e-14, 1e-14)` goes into GDAL and comes out as `(0.0, 0.0)`. No
exception, no warning, no changed return code. The same point at `1e-13` comes
out intact. The loss is silent, and it sits in a range that most test suites
never visit.

## The failing call

The smallest reproduction needs only the OGR Python bindings (GDAL 3.12.2):

```python
from osgeo import gdal, ogr

gdal.UseExceptions()
for v in ("1e-13", "1e-14"):
    print(v, "->", ogr.CreateGeometryFromWkt(f"POINT ({v} 1)").ExportToWkt())
```

```text
1e-13 -> POINT (0.0000000000001 1.0)
1e-14 -> POINT (0.0 1.0)
```

The GeoJSON writer behaves the same way. Feeding the
[`numeric_boundary_1e14`](../_generated/catalog/cases/numeric_boundary_1e14.md)
file holds one point, both coordinates `1e-14`. Reading those two numbers from
the file with `json` and passing them through the same
`CreateGeometryFromWkt(...).ExportToWkt()` call gives `POINT (0.0 0.0)`. The relative error is exactly 1.0:
the whole value is gone, not rounded.

## Why this is not just a precision limit

The tempting reading is "floating point has limits, a number that small is
noise". That does not hold here. The writers default to 15 digits after the
decimal point, and `1e-14` is `0.00000000000001`, which needs only fourteen. The
value fits inside the writer's own default with a digit to spare, and the
neighbouring magnitude `1e-13` is written correctly. The companion case,
[`numeric_boundary_1e13`](../_generated/catalog/cases/numeric_boundary_1e13.md),
exists so that a consumer can check both sides of the edge in one run.

According to the report on the GDAL tracker, the cause is a trailing-digit
cleanup in `intelliround()` in `ogr/ogrutils.cpp`. At that point the string for
`1e-14` is `0.000000000000010`. The branch inspects a run of trailing
characters for zeros, then removes eight characters. It checks seven of them.
The one it does not check is the `1`, the only significant digit, and it is
removed with the rest. A second trim, for five zeros followed by one digit, drops
the digit in the same way, so `1e-15` is lost too. The affected range is from
1e-15 up to but not including 1e-13. The first sweep put the lower edge at
1e-14, because it counted smaller values as expected precision loss; writing
the fix showed the error. Values below 1e-15 need more than 15 decimal places,
so losing them is documented behaviour, not this defect.

## What it means for your pipeline

Most geographic coordinates are nowhere near this scale, so a typical map
workflow will never notice. The exposure is in places where small numbers are
legitimate values: projected coordinates in a local engineering frame centred on
the origin, normalised or unit-square geometry, offsets and residuals stored as
geometry, and test fixtures built to probe numeric limits. A round trip through a
text format will flatten any of those to zero, and a geometry that collapses to
the origin can pass every validity check you have, because a point at `(0, 0)`
is a perfectly valid point.

If you cannot upgrade or avoid the range, the writer options for coordinate
precision (significant figures rather than fixed decimals) avoid the trim. The
reporter's concern, though, is that the loss is silent, and a workaround you
have to know about in advance is not a safeguard.

## Status

The issue is [gdal#15317](https://github.com/OSGeo/gdal/issues/15317). The fix,
[gdal#15369](https://github.com/OSGeo/gdal/pull/15369), changes the two trims in
`intelliround()` so they no longer remove the only significant digit. Dan Baston
approved and merged it on 2026-10-15, and the issue is closed. Even Rouault
commented on the PR that the change is "technically" correct and doubted that a
real use case would hit it. The fix is in GDAL's main branch and will reach users
with the next GDAL release; versions up to 3.12.2 still write these values as 0.

## Try it

The expected answer ships with the case as `expected_roundtrip_coordinates`, so
you can grade your own read/write path rather than decide what "survived" means.
The case page:
[`numeric_boundary_1e14`](../_generated/catalog/cases/numeric_boundary_1e14.md).
Every case in the family is listed under the
[`precision/formatter_boundary`](../_generated/catalog/risk/precision-formatter-boundary.md)
risk hub.
