"""Split a longitude/latitude polygon that crosses the antimeridian into parts."""

from shapely.geometry import Polygon


def _shift_ring(coords):
    """Return ring coords with longitudes unwrapped to a continuous range."""
    shifted = [coords[0]]
    for lon, lat in coords[1:]:
        prev_lon = shifted[-1][0]
        delta = lon - prev_lon
        if delta > 180:
            lon -= 360
        elif delta < -180:
            lon += 360
        shifted.append((lon, lat))
    return shifted


def _split_ring_at_meridians(coords):
    """Split an unwrapped ring's segments at every 180-degree-multiple crossing.

    Returns a dict mapping integer band index (band k covers lon in
    [180*k - 180, 180*k + 180]) to list of (lon, lat) points contributed
    by that band, in order, forming (possibly open) chains.
    """
    lons = [c[0] for c in coords]
    min_band = int((min(lons) + 180) // 360)
    max_band = int((max(lons) + 180) // 360)

    pieces = {k: [] for k in range(min_band, max_band + 1)}

    def band_of(lon):
        return int((lon + 180) // 360)

    n = len(coords)
    for i in range(n - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        b1 = band_of(lon1)
        pieces[b1].append((lon1, lat1))

        if b1 == band_of(lon2):
            continue

        step = 1 if lon2 > lon1 else -1
        cur_band = b1
        cur_lon, cur_lat = lon1, lat1
        target_band = band_of(lon2)
        while cur_band != target_band:
            if step > 0:
                boundary = (cur_band + 1) * 360 - 180
            else:
                boundary = cur_band * 360 - 180
            if lon2 == lon1:
                break
            t = (boundary - lon1) / (lon2 - lon1)
            t = min(max(t, 0.0), 1.0)
            lat_b = lat1 + t * (lat2 - lat1)
            pieces[cur_band].append((boundary, lat_b))
            cur_band += step
            pieces[cur_band].append((boundary, lat_b))
            cur_lon, cur_lat = boundary, lat_b

    pieces[band_of(coords[-1][0])].append(coords[-1])
    return pieces


def _wrap_to_180(lon):
    wrapped = ((lon + 180) % 360) - 180
    if wrapped == -180 and lon > 0:
        wrapped = 180
    return wrapped


def split_antimeridian(polygon):
    """Split a lon/lat Polygon that may cross the antimeridian.

    Args:
        polygon: shapely Polygon with coordinates in EPSG:4326,
            longitudes in [-180, 180].

    Returns:
        List of shapely Polygons covering the same region, none of which
        crosses the antimeridian.
    """
    ext = list(polygon.exterior.coords)
    shifted_ext = _shift_ring(ext)
    lons = [c[0] for c in shifted_ext]

    if max(lons) - min(lons) <= 180:
        return [polygon]

    band_pieces = _split_ring_at_meridians(shifted_ext)

    result = []
    for band, pts in band_pieces.items():
        if len(pts) < 3:
            continue
        offset = band * 360
        ring = [(lon - offset, lat) for lon, lat in pts]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        ring = [(_wrap_to_180(lon), lat) for lon, lat in ring]
        poly = Polygon(ring)
        if not poly.is_empty and poly.area > 0:
            result.append(poly)

    if not result:
        return [polygon]

    return result