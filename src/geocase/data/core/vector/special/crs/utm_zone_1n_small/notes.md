# UTM Zone 1N Polygon

## Why zone 1

UTM zone 1N's western edge *is* the antimeridian. That makes it the zone where
longitude-wrapping bugs stop being theoretical: reproject this polygon to
EPSG:4326 with a naive implementation and the result can come back straddling
180 degrees, which a bounding-box computation then reports as a footprint
spanning the entire planet.

Before this case the whole catalog resolved to a single UTM zone (33N), so no
bundled fixture reached any zone edge, let alone this one.

## What to assert

The polygon is stored **projected**, in EPSG:32601 metres -- not in WGS84 with
a zone recorded as a parameter, which is how `utm_zone_33_polygon` works. Both
forms are worth having: that one tests zone *selection* from geographic
coordinates, this one tests handling of coordinates that are already in a
projected CRS whose bounds are awkward.

Reprojected to WGS84 the extent is roughly 179.8W-177.2W, 0.5N-2.5N: entirely
east of the antimeridian, contiguous, and nowhere near 360 degrees wide.

Pairs naturally with `dateline_crossing_polygon` and `classic_antimeridian_polygon`,
which come at the same line from the geographic side.
