import shapely.geometry as geom
from shapely.geometry.base import BaseGeometry
from typing import List, Set


def _canonical_point(p: geom.Point) -> str:
    return f"POINT({p.x} {p.y})"


def _canonical_linestring(ls: geom.LineString) -> str:
    coords = list(ls.coords)
    rev = coords[::-1]
    # choose lexicographically smaller representation
    if tuple(rev) < tuple(coords):
        coords = rev
    coord_str = ",".join(f"{x} {y}" for x, y in coords)
    return f"LINESTRING({coord_str})"


def _canonical_polygon(poly: geom.Polygon) -> str:
    def _canonical_ring(ring: geom.LinearRing) -> List[tuple]:
        # drop closing point for rotation, then add it back
        coords = list(ring.coords)[:-1]
        # ensure correct orientation: exterior CCW, interior CW
        if ring.is_ccw != (ring is poly.exterior):
            coords = coords[::-1]
        # rotate to minimal coordinate
        idx = min(range(len(coords)), key=lambda i: coords[i])
        coords = coords[idx:] + coords[:idx]
        coords.append(coords[0])  # close ring
        return coords

    ext_coords = _canonical_ring(poly.exterior)
    ext_str = ",".join(f"{x} {y}" for x, y in ext_coords)

    interior_strs = []
    for interior in poly.interiors:
        int_coords = _canonical_ring(interior)
        int_str = ",".join(f"{x} {y}" for x, y in int_coords)
        interior_strs.append(int_str)
    interior_strs.sort()

    if interior_strs:
        return f"POLYGON(({ext_str}),({'),('.join(interior_strs)}))"
    else:
        return f"POLYGON(({ext_str}))"


def _canonical_multipoint(mp: geom.MultiPoint) -> str:
    coords = sorted((p.x, p.y) for p in mp.geoms)
    coord_str = ",".join(f"{x} {y}" for x, y in coords)
    return f"MULTIPOINT({coord_str})"


def _canonical_multilinestring(mls: geom.MultiLineString) -> str:
    strs = sorted(_canonical_linestring(ls) for ls in mls.geoms)
    return f"MULTILINESTRING({','.join(strs)})"


def _canonical_multipolygon(mp: geom.MultiPolygon) -> str:
    strs = sorted(_canonical_polygon(p) for p in mp.geoms)
    return f"MULTIPOLYGON({','.join(strs)})"


def _canonical_geometrycollection(gc: geom.GeometryCollection) -> str:
    strs = sorted(_canonical_geometry(g) for g in gc.geoms)
    return f"GEOMETRYCOLLECTION({','.join(strs)})"


def _canonical_geometry(g: BaseGeometry) -> str:
    if g.is_empty:
        return "EMPTY"
    t = g.type
    if t == "Point":
        return _canonical_point(g)
    if t == "LineString":
        return _canonical_linestring(g)
    if t == "Polygon":
        return _canonical_polygon(g)
    if t == "MultiPoint":
        return _canonical_multipoint(g)
    if t == "MultiLineString":
        return _canonical_multilinestring(g)
    if t == "MultiPolygon":
        return _canonical_multipolygon(g)
    if t == "GeometryCollection":
        return _canonical_geometrycollection(g)
    raise NotImplementedError(f"Unsupported geometry type: {t}")


def dedupe_geoms(geoms: List[BaseGeometry]) -> List[BaseGeometry]:
    """
    Return a new list with duplicate geometries removed, preserving the first
    occurrence of each geometry and the original order.

    Two geometries are considered duplicates if they describe exactly the same
    set of points in the plane, regardless of coordinate ordering or ring
    orientation.
    """
    seen: Set[str] = set()
    result: List[BaseGeometry] = []

    for g in geoms:
        key = _canonical_geometry(g)
        if key not in seen:
            seen.add(key)
            result.append(g)

    return result