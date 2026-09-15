"""Split polygons that cross the antimeridian into valid, non-crossing pieces."""

from shapely.geometry import Polygon


def _shift_ring(coords):
    """Shift longitudes so the ring is contiguous, working in a +360 extended space."""
    shifted = [coords[0]]
    for lon, lat in coords[1:]:
        prev_lon = shifted[-1][0]
        candidate = lon
        while candidate - prev_lon > 180:
            candidate -= 360
        while candidate - prev_lon < -180:
            candidate += 360
        shifted.append((candidate, lat))
    return shifted


def _crosses_antimeridian(coords):
    for (lon1, _), (lon2, _) in zip(coords, coords[1:]):
        if abs(lon2 - lon1) > 180:
            return True
    return False


def _split_ring_at(shifted_coords, cut_lon):
    """Split a shifted (unwrapped) ring's edges at multiples of 360 offset from cut_lon.

    Returns segments as lists of (lon, lat) still in unwrapped space, each clipped
    to lie within [k*360 + cut_lon - 180, k*360 + cut_lon + 180] for some integer k
    is not attempted here; instead we cut wherever an edge crosses a multiple of 360
    away from the antimeridian (i.e. crosses lon = 180 + 360*k).
    """
    segments = []
    current = [shifted_coords[0]]
    for (lon1, lat1), (lon2, lat2) in zip(shifted_coords, shifted_coords[1:]):
        low = min(lon1, lon2)
        high = max(lon1, lon2)
        k_start = int(low // 360)
        k_end = int(high // 360) + 1
        crossings = []
        for k in range(k_start, k_end + 1):
            boundary = 180 + 360 * k
            if low < boundary < high:
                t = (boundary - lon1) / (lon2 - lon1)
                lat = lat1 + t * (lat2 - lat1)
                crossings.append((boundary, lat, t))
        crossings.sort(key=lambda c: c[2])
        for boundary, lat, _ in crossings:
            current.append((boundary, lat))
            segments.append(current)
            current = [(boundary, lat)]
        current.append((lon2, lat2))
    segments.append(current)

    # Merge first and last segment if the ring is closed (they belong together)
    if len(segments) > 1 and shifted_coords[0] == shifted_coords[-1]:
        first = segments[0]
        last = segments[-1]
        merged = last[:-1] + first
        segments = [merged] + segments[1:-1]

    return segments


def _normalize_lon(lon):
    """Wrap longitude into [-180, 180], mapping the boundary consistently to 180."""
    wrapped = ((lon + 180) % 360) - 180
    if wrapped == -180:
        wrapped = 180
    return wrapped


def _bucket_key(lon):
    """Integer bucket index such that all points in the same 360-wide slice share a key."""
    return round((lon - _normalize_lon(lon)) / 360)


def split_antimeridian(polygon):
    """Split a lon/lat Polygon that may cross the antimeridian into non-crossing pieces.

    Returns a list of Polygons covering the same region, none of which crosses
    or touches the antimeridian except at its edge. If the input does not cross
    the antimeridian, returns [polygon] unchanged.
    """
    exterior = list(polygon.exterior.coords)

    if not _crosses_antimeridian(exterior):
        return [polygon]

    shifted_exterior = _shift_ring(exterior)
    ext_segments = _split_ring_at(shifted_exterior, 180)

    interiors_shifted = []
    for interior in polygon.interiors:
        coords = list(interior.coords)
        interiors_shifted.append(_shift_ring(coords))

    # Group exterior segments by bucket (which 360-wide slice they belong to)
    buckets = {}
    for seg in ext_segments:
        key = _bucket_key(seg[0][0])
        buckets.setdefault(key, []).append(seg)

    interior_buckets = {}
    for shifted_ring in interiors_shifted:
        for seg in _split_ring_at(shifted_ring, 180):
            key = _bucket_key(seg[0][0])
            interior_buckets.setdefault(key, []).append(seg)

    result = []
    for key, segs in buckets.items():
        # Reassemble exterior ring for this bucket by chaining segments end-to-start
        ring_coords = []
        for seg in segs:
            if ring_coords and ring_coords[-1] == seg[0]:
                ring_coords.extend(seg[1:])
            else:
                ring_coords.extend(seg)
        normalized_ext = [(_normalize_lon(lon), lat) for lon, lat in ring_coords]
        if normalized_ext[0] != normalized_ext[-1]:
            normalized_ext.append(normalized_ext[0])

        rings_interiors = []
        for iseg in interior_buckets.get(key, []):
            normalized_int = [(_normalize_lon(lon), lat) for lon, lat in iseg]
            if len(normalized_int) >= 3:
                if normalized_int[0] != normalized_int[-1]:
                    normalized_int.append(normalized_int[0])
                rings_interiors.append(normalized_int)

        if len(normalized_ext) >= 4:
            result.append(Polygon(normalized_ext, rings_interiors))

    return result