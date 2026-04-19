# south_pole_polygon

A GeoJSON Polygon that encircles the south pole at latitude 85°S.

## Purpose

Mirrors `north_pole_polygon` for the southern hemisphere.  Antarctic
projections (EPSG:3031 — Antarctic Polar Stereographic) and sea-ice
workflows need polygons that enclose the south pole.

## Geometry

A closed ring at 85°S with vertices at longitudes −45°, −135°, 135°, and 45°.
The winding order is reversed relative to the north-pole case so the interior
still contains the pole (counter-clockwise on the sphere, clockwise in
projected 2-D for a south-polar view).

## Edge-case value

| Concern | Detail |
|---|---|
| Area distortion | Same as north pole — equirectangular area is meaningless |
| Reprojection | Must work with EPSG:3031 and similar Antarctic CRS |
| Winding order | Opposite to the north-pole case if viewed in 2-D |
| Rendering | Web Mercator clips below ~−85.06° |
