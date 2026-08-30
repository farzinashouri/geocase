# UTM Zone Boundary Straddle

## What straddling means

UTM zone 32N spans 6E-12E. This polygon spans **5.5E-6.5E**, so a little under
half of it lies west of its own declared zone's edge, with eastings down to
~246 600 m -- outside the 166 000-834 000 m band a point inside zone 32 would
occupy.

This is legal, not corrupt. Every UTM projection is defined across the whole
globe; the zone bounds mark where distortion stays acceptable, not where the
maths stops. Real datasets straddle zone edges constantly, because
administrative and physical boundaries do not respect 6-degree meridians.

## The failure it catches

The tempting-but-wrong behaviour is to re-derive the zone from each vertex's
longitude and reproject piecewise. That produces a polygon whose western half
is transformed with zone 31's central meridian and eastern half with zone 32's,
tearing the geometry along 6E -- typically as a several-hundred-kilometre jump,
or a self-intersection where the rings no longer meet.

A correct consumer uses the **declared** CRS for every vertex and accepts the
mild extra distortion outside the nominal band.

## Why it did not exist before

Every UTM case in the bundled catalog resolved to zone 33N, and both cases
*named* for zone behaviour (`geotiff_utm_boundary`, `utm_zone_33_polygon`) sat
entirely inside one zone. Cross-zone reprojection was therefore untestable
against the bundled data. This case, plus `utm_zone_33n_to_32n_pair`, closes
that.
