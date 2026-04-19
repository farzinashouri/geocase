# north_pole_polygon

A GeoJSON Polygon that encircles the north pole at latitude 85°N.

## Purpose

The existing `north_pole_point` case puts a single coordinate at 90°N, 0°E.
A point is dimensionless, so it avoids the harder questions:

- How large is the polygon's area?
- What happens when the ring crosses the antimeridian implicitly?
- Do reprojection routines (e.g. WGS 84 → NSIDC Polar Stereographic) keep the
  geometry valid?

This polygon answers those questions by providing a simple four-vertex ring
whose interior includes the pole itself.

## Geometry

A closed ring at 85°N with vertices at longitudes −45°, 45°, 135°, and −135°.
The ring is wound counter-clockwise (right-hand rule) and encloses the pole.

## Edge-case value

| Concern | Detail |
|---|---|
| Area distortion | Equirectangular area is wildly wrong near the pole |
| Reprojection | Some CRS transformations clip or distort polar polygons |
| Antimeridian crossing | The ring implicitly crosses 180° longitude |
| Rendering | Map tiles in Web Mercator cannot show latitudes beyond ~85.06° |
