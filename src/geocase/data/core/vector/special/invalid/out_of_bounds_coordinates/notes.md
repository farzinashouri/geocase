# Out-of-Bounds Coordinates

## Purpose
Tests detection of coordinates that exceed valid geographic ranges.

## Valid Coordinate Ranges
| Dimension | Range | Notes |
|-----------|-------|-------|
| Latitude | [-90, 90] | North/South of Equator |
| Longitude | [-180, 180] | East/West of Prime Meridian |

## This Case
- **Longitude**: -0.1° (valid)
- **Latitude**: 100° (INVALID - exceeds 90° maximum)

## Common Causes
1. **Lat/Lon Swap**: GeoJSON uses [Lon, Lat] but data came from [Lat, Lon] system
2. **Unit Confusion**: Degrees vs radians vs other units
3. **Projection Errors**: Projected coordinates mistakenly stored as geographic

## Expected Behavior
- **Spatial indexes**: Should reject (can't index invalid coordinates)
- **Coordinate validation**: Should detect and report
- **Reprojection**: Will fail or produce garbage results

## Real-World Occurrence
- Excel/CSV imports where column order is assumed
- API responses from systems using [Lat, Lon] order
- Copy-paste errors in manual data entry

## Why this case does not carry the `axis_order` risk type

It is the obvious candidate — cause 1 above is literally a lat/lon swap — but
the term belongs to the six `*_gml_baseline` cases instead, and the distinction
is worth stating so it is not rediscovered.

This case detects a swap **only because latitude 100 happens to be out of
range**. That is a *validity* signal: the same check catches a unit error, a
projected coordinate stored as geographic, or a corrupted digit. Swap a point at
latitude 45 and longitude 10 and this case's mechanism sees nothing wrong.

`axis_order` names a different property: a file whose **declared** coordinate
order differs from the reader's assumed one, with every value perfectly valid on
both readings. The GML baselines carry that — `urn:ogc:def:crs:EPSG::4326` forces
latitude-first on disk — and they carry it for in-range coordinates, which is
what makes the swap silent rather than detectable.
