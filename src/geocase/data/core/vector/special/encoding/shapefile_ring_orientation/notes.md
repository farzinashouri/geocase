# Shapefile Ring Orientation Case

## Purpose

This case pins the one thing a Shapefile round trip changes about a polygon that
is otherwise identical to its source: the **winding order of the rings**.

The geometry is the same square as `simple_valid_polygon` —
`POLYGON ((10 50, 11 50, 11 51, 10 51, 10 50))` in the GeoJSON reference — and
the two are topologically equal. But the exterior ring here runs **clockwise**,
so `geom.exterior.is_ccw` is `False` where the reference's is `True`.

## Mechanism

The Shapefile specification (ESRI, 1998, p. 8) mandates that a polygon's outer
ring be ordered **clockwise** and its holes counter-clockwise. RFC 7946 §3.1.6
and the OGC right-hand rule mandate exactly the opposite. OGR resolves the
conflict by rewriting the orientation on write, regardless of what it was given:

```python
# The written .shp comes back with the winding reversed, silently.
gpd.read_file("rfc7946_ccw.geojson").to_file("out.shp")
```

Nothing warns, nothing fails, and the geometry is not wrong — it is correct
*for the format*.

## Why this breaks real code

The failure mode is code that infers a ring's **role** from its **orientation**:

```python
# Wrong: works on GeoJSON, silently inverts on Shapefile.
outer = next(r for r in rings if r.is_ccw)
holes = [r for r in rings if not r.is_ccw]
```

Ring role is positional — in both formats and in Shapely, `geom.exterior` is the
exterior and `geom.interiors` are the holes, whatever their winding. Orientation
is a serialization detail. Code that conflates the two produces inverted
polygons, negative signed areas, or holes promoted to exteriors, on exactly one
of its input formats.

## Provenance

These bytes are the pre-plan-13 `polygon_shapefile_baseline`, preserved rather
than discarded when that family was converged onto its declared canonical. Its
`name` attribute still reads `baseline_polygon` for that reason.

The preservation is not sentimentality. The `*_baseline` families are compared
with `shapely.normalize` on both sides, which canonicalizes ring orientation by
design — it has to, because the Shapefile members of those families *cannot*
match a CCW canonical. Inside a baseline family this artifact is therefore not
merely undocumented, it is **unassertable**. Only as its own case can anything
assert it at all.

## Expected behavior

- The file loads and the geometry is valid.
- `geom.equals(simple_valid_polygon_geometry)` is `True` — topologically identical.
- `geom.exterior.is_ccw` is `False`, and the reference's is `True`.
- `shapely.normalize` makes the two compare equal; `equals_exact` does not.

## Related cases

- `simple_valid_polygon` — the CCW GeoJSON reference.
- `polygon_shapefile_baseline` — the current Shapefile member of the
  cross-format family, which holds this same geometry and, being a Shapefile, is
  also CW. It is compared winding-insensitively; this case is where the winding
  itself is asserted.
- `shapefile_field_truncation`, `shapefile_encoding_legacy` — the other
  format artifacts promoted to named cases rather than left implicit in a
  baseline.
