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
