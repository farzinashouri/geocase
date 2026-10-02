```python
import json
from typing import Iterator, Tuple, List, Any

def _yield_coords(geom: dict) -> Iterator[Tuple[float, float]]:
    """Yield (lon, lat) pairs from a GeoJSON geometry object."""
    geom_type = geom.get('type')
    coords = geom.get('coordinates')
    if geom_type == 'Point':
        # coords: [lon, lat, ...]
        yield coords[0], coords[1]
    elif geom_type in ('MultiPoint', 'LineString'):
        for c in coords:
            yield c[0], c[1]
    elif geom_type in ('MultiLineString', 'Polygon'):
        for line in coords:
            for c in line:
                yield c[0], c[1]
    elif geom_type == 'MultiPolygon':
        for polygon in coords:
            for line in polygon:
                for c in line:
                    yield c[0], c[1]
    elif geom_type == 'GeometryCollection':
        for g in geom['geometries']:
            yield from _yield_coords(g)
    # else: ignore unknown types

def _extract_coords(geojson: dict) -> Iterator[Tuple[float, float]]:
    """Yield (lon, lat) pairs from any GeoJSON object (FeatureCollection, Feature, Geometry, etc.)."""
    obj_type = geojson.get('type')
    if obj_type == 'FeatureCollection':
        for feature in geojson['features']:
            yield from _extract_coords(feature)
    elif obj_type == 'Feature':
        yield from _extract_coords(geojson['geometry'])
    elif obj_type == 'GeometryCollection':
        for geom in geojson['geometries']:
            yield from _extract_coords(geom)
    else:
        # Assume it's a geometry object
        yield from _yield_coords(geojson)

def _minimal_longitude_interval(lons: List[float]) -> Tuple[float, float]:
    """
    Return the minimal longitudinal interval covering all given longitudes.
    The interval is returned as (start, end) where start and end are in [-180, 180].
    If the interval crosses the antimeridian, start > end.
    """
    if not lons:
        raise ValueError("No longitudes provided")
    # Normalize to [-180, 180] just in case
    normalized = [((lon + 180) % 360) - 180 for lon in lons]
    sorted_lons = sorted(normalized)
    n = len(sorted_lons)
    if n == 1:
        return sorted_lons[0], sorted_lons[0]
    # Find the maximum gap between consecutive longitudes (including wrap-around)
    max_gap = -1.0
    max_gap_idx = -1  # index of the start of the gap; -1 indicates wrap-around gap
    for i in range(n - 1):
        gap = sorted_lons[i + 1] - sorted_lons[i]
        if gap > max_gap:
            max_gap = gap
            max_gap_idx = i
    wrap_gap = (sorted_lons[0] + 360) - sorted_lons[-1]
    if wrap_gap > max_gap:
        max_gap = wrap_gap
        max_gap_idx = -1
    if max_gap_idx == -1:
        # The minimal interval does not cross the antimeridian
        return sorted_lons[0], sorted_lons[-1]
    else:
        # The minimal interval crosses the antimeridian: from the end of the max gap to its start
        start = sorted_lons[max_gap_idx + 1]
        end = sorted_lons[max_gap_idx]
        return start, end

def geojson_bounds(path: str) -> Tuple[float, float, float, float]:
    """
    Compute the bounding box of all features in a GeoJSON file.

    Args:
        path: Path to the GeoJSON file. Coordinates are assumed to be in EPSG:4326 (longitude/latitude).

    Returns:
        A 4-tuple (min_lon, min_lat, max_lon, max_lat) describing the bounding box.
        Longitudes are in the range [-180, 180]. If the bounding box crosses the antimeridian,
        min_lon will be greater than max_lon.
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    lons = []
    lats = []
    for lon, lat in _extract_coords(data):
        lons.append(lon)
        lats.append(lat)

    if not lons:
        raise ValueError("GeoJSON contains no coordinates")

    min_lat = min(lats)
    max_lat = max(lats)
    min_lon, max_lon = _minimal_longitude_interval(lons)

    return (min_lon, min_lat, max_lon, max_lat)

if __name__ == '__main__':
    # Example usage (not run on import)
    import sys
    if len(sys.argv) > 1:
        try:
            bounds = geojson_bounds(sys.argv[1])
            print(f"Bounds: {bounds}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
```