# Unclosed Ring Polygon

## Purpose
Tests handling of polygons with unclosed exterior rings (first ≠ last coordinate).

## GeoJSON Specification
Per RFC 7946 §3.1.6:
> A linear ring MUST follow the right-hand rule... The first and last positions are equivalent.

## Expected Behavior
- **Strict parsers**: Should reject with ParseException
- **Tolerant parsers** (Shapely, GeoPandas): Auto-close the ring
- **Validation functions**: Should detect and report the issue

## Real-World Occurrence
- Manual GeoJSON editing errors
- Truncated file writes
- Buggy export tools
