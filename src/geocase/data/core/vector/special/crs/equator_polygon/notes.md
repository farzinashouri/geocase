# equator_polygon

A GeoJSON Polygon that straddles the equator (latitude 0°).

## Purpose

The existing `equator_crossing_line` case provides a LineString that crosses
latitude 0°.  A line is one-dimensional, so it doesn't exercise:

- Area calculations that span hemispheres,
- Polygon clipping at the equator boundary,
- UTM zone-letter selection (N vs S bands),
- Hemisphere-aware containment checks.

This polygon fills that gap with a simple, easy-to-reason-about rectangle.

## Geometry

A closed rectangle spanning −10° to 10° longitude and −5° to 5° latitude.
The geometry is intentionally small and simple so that distortion from
projection choice is minimal but the equator-crossing property is present.

## Edge-case value

| Concern | Detail |
|---|---|
| Hemisphere boundary | Latitude sign changes from negative to positive |
| UTM zone selection | Straddles UTM zones 30/31 and crosses the N/S band line |
| Area calculation | Planar vs geodesic area should agree closely at the equator |
| Containment | Point-in-polygon for (0, 0) — the origin — must return true |
