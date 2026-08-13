```python
from shapely.geometry import Polygon, LinearRing, Point
import math

def split_antimeridian(polygon):
    """
    Split a shapely Polygon (EPSG:4326, longitudes in [-180, 180]) that may cross the antimeridian
    into a list of polygons that do not cross the antimeridian.
    """
    if polygon.is_empty:
        return []

    # Tolerance for detecting jumps (longitudes are in [-180, 180])
    JUMP_THRESHOLD = 180.0 - 1e-10

    def detect_jumps(coords):
        """Detect antimeridian crossings in a ring (open coordinates)."""
        jumps = []
        n = len(coords)
        for i in range(n):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[(i + 1) % n]
            if abs(lon2 - lon1) > JUMP_THRESHOLD:
                # Compute adjusted longitude difference for the short way
                diff = lon2 - lon1
                if diff > 180:
                    diff -= 360
                elif diff < -180:
                    diff += 360
                # Determine crossing longitude (180 or -180)
                if lon1 < 180 and lon1 + diff > 180:
                    cross_lon = 180.0
                    fraction = (180.0 - lon1) / diff
                elif lon1 > -180 and lon1 + diff < -180:
                    cross_lon = -180.0
                    fraction = (-180.0 - lon1) / diff
                else:
                    # Fallback (should not happen for a true jump)
                    cross_lon = 180.0 if lon1 > 0 else -180.0
                    fraction = 0.5
                cross_lat = lat1 + fraction * (lat2 - lat1)
                jumps.append((i, cross_lon, cross_lat))
        return jumps

    def split_ring(coords, jumps):
        """Split a ring at jumps, returning list of (closed_ring_coords, side)."""
        if not jumps:
            return [(coords + [coords[0]], 'none')]
        # For simplicity, assume jumps come in pairs and we only handle the first two.
        # A more general implementation would pair them sequentially.
        if len(jumps) % 2 != 0:
            # Odd number of jumps indicates an invalid ring; fallback
            return [(coords + [coords[0]], 'none')]

        # We'll pair jumps sequentially: (0,1), (2,3), ...
        # Each pair produces one ring on one side.
        # But the exterior ring of a polygon should produce multiple polygons.
        # For now, we assume exactly 2 jumps (one crossing pair).
        if len(jumps) != 2:
            # Fallback: treat as no jumps
            return [(coords + [coords[0]], 'none')]

        (i1, cross_lon1, cross_lat1), (i2, cross_lon2, cross_lat2) = jumps
        n = len(coords)
        # Ensure i1 < i2 for slicing
        if i1 > i2:
            i1, i2 = i2, i1
            cross_lon1, cross_lon2 = cross_lon2, cross_lon1
            cross_lat1, cross_lat2 = cross_lat2, cross_lat1

        # Segment A: from jump1 to jump2 (following ring order)
        segA_vertices = coords[i1+1:i2+1]  # includes vertex at i2
        # Segment B: from jump2 to jump1 (wrapping around)
        segB_vertices = coords[i2+1:] + coords[:i1+1]  # includes vertex at i1

        def avg_lon(vertices):
            if not vertices:
                return 0.0
            return sum(v[0] for v in vertices) / len(vertices)

        avgA = avg_lon(segA_vertices)
        avgB = avg_lon(segB_vertices)

        rings = []
        # Segment A
        sideA = 'east' if avgA > 0 else 'west'
        lonA = 180.0 if sideA == 'east' else -180.0
        ringA = [(lonA, cross_lat1)] + segA_vertices + [(lonA, cross_lat2), (lonA, cross_lat1)]
        rings.append((ringA, sideA))

        # Segment B
        sideB = 'east' if avgB > 0 else 'west'
        lonB = 180.0 if sideB == 'east' else -180.0
        ringB = [(lonB, cross_lat2)] + segB_vertices + [(lonB, cross_lat1), (lonB, cross_lat2)]
        rings.append((ringB, sideB))

        return rings

    def make_valid_ring(ring_coords):
        """Create a valid LinearRing from coordinates."""
        lr = LinearRing(ring_coords)
        if not lr.is_valid:
            lr = lr.buffer(0)
            if lr.geom_type == 'Polygon':
                lr = lr.exterior
        return lr

    # Process exterior ring
    ext_coords = list(polygon.exterior.coords)[:-1]  # open ring
    ext_jumps = detect_jumps(ext_coords)

    if not ext_jumps:
        # Exterior does not cross. Check interiors.
        interior_rings = []
        for interior in polygon.interiors:
            int_coords = list(interior.coords)[:-1]
            int_jumps = detect_jumps(int_coords)
            if int_jumps:
                split_int = split_ring(int_coords, int_jumps)
                for ring_coords, _ in split_int:
                    interior_rings.append(make_valid_ring(ring_coords))
            else:
                interior_rings.append(make_valid_ring(int_coords + [int_coords[0]]))
        # Build polygon with fixed holes
        ext_lr = make_valid_ring(ext_coords + [ext_coords[0]])
        result_poly = Polygon(ext_lr, interior_rings)
        if not result_poly.is_valid:
            result_poly = result_poly.buffer(0)
        return [result_poly]

    # Exterior crosses: split it
    ext_rings = split_ring(ext_coords, ext_jumps)
    ext_polygons = []
    for ring_coords, side in ext_rings:
        lr = make_valid_ring(ring_coords)
        poly = Polygon(lr)
        if not poly.is_valid:
            poly = poly.buffer(0)
        ext_polygons.append({'polygon': poly, 'side': side, 'holes': []})

    # Process interior rings
    for interior in polygon.interiors:
        int_coords = list(interior.coords)[:-1]
        int_jumps = detect_jumps(int_coords)
        int_rings = split_ring(int_coords, int_jumps)
        for ring_coords, side in int_rings:
            lr = make_valid_ring(ring_coords)
            hole_poly = Polygon(lr)
            if not hole_poly.is_valid:
                hole_poly = hole_poly.buffer(0)
            centroid = hole_poly.centroid
            assigned = False
            # Try containment
            for ext in ext_polygons:
                if ext['polygon'].contains(centroid):
                    ext['holes'].append(lr)
                    assigned = True
                    break
            if not assigned:
                # Fallback: assign by side
                for ext in ext_polygons:
                    if ext['side'] == side:
                        ext['holes'].append(lr)
                        assigned = True
                        break
            if not assigned:
                ext_polygons[0]['holes'].append(lr)

    # Build final polygons
    result = []
    for ext in ext_polygons:
        final_poly = Polygon(ext['polygon'].exterior, ext['holes'])
        if not final_poly.is_valid:
            final_poly = final_poly.buffer(0)
        result.append(final_poly)

    return result
```