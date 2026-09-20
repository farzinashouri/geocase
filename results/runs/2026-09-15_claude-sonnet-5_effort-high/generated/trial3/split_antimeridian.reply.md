```python
"""Split polygons crossing the antimeridian into non-crossing pieces."""

from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon, box


def _unwrap_ring(coords):
    coords = np.asarray(coords, dtype=float)
    unwrapped = coords.copy()
    unwrapped[:, 0] = np.unwrap(coords[:, 0], period=360.0)
    return unwrapped


def _align_ring(unwrapped, reference_lon):
    shift = 360.0 * round((reference_lon - unwrapped[:, 0].mean()) / 360.0)
    if shift:
        unwrapped = unwrapped.copy()
        unwrapped[:, 0] = unwrapped[:, 0] + shift
    return unwrapped


def _ring_crosses(coords):
    lons = [c[0] for c in coords]
    return any(abs(lons[i] - lons[i - 1]) > 180.0 for i in range(1, len(lons)))


def _shift_polygon(polygon: Polygon, dx: float) -> Polygon:
    exterior = [(x + dx, y) for x, y in polygon.exterior.coords]
    interiors = [[(x + dx, y) for x, y in ring.coords] for ring in polygon.interiors]
    return Polygon(exterior, interiors)


def split_antimeridian(polygon: Polygon) -> list[Polygon]:
    """Split a lon/lat (EPSG:4326) polygon crossing the antimeridian into pieces.

    Returns a list of valid polygons, each with longitudes in [-180, 180]
    and none crossing the antimeridian internally, that together cover the
    same region as the input. A polygon that does not cross the
    antimeridian is returned unchanged as a single-element list.
    """
    exterior_coords = list(polygon.exterior.coords)
    interior_coords = [list(ring.coords) for ring in polygon.interiors]

    crosses = _ring_crosses(exterior_coords) or any(
        _ring_crosses(ring) for ring in interior_coords
    )
    if not crosses:
        return [polygon]

    unwrapped_exterior = _unwrap_ring(exterior_coords)
    ref_lon = unwrapped_exterior[:, 0].mean()

    unwrapped_interiors = [
        _align_ring(_unwrap_ring(ring), ref_lon) for ring in interior_coords
    ]

    unwrapped_polygon = Polygon(unwrapped_exterior, unwrapped_interiors)

    lon_arrays = [unwrapped_exterior[:, 0]] + [r[:, 0] for r in unwrapped_interiors]
    all_lons = np.concatenate(lon_arrays)
    min_lon, max_lon = all_lons.min(), all_lons.max()

    k_min = int(np.floor((min_lon + 180.0) / 360.0))
    k_max = int(np.floor((max_lon + 180.0) / 360.0))

    pieces = []
    for k in range(k_min, k_max + 1):
        window = box(-180.0 + 360.0 * k, -90.0, 180.0 + 360.0 * k, 90.0)
        clipped = unwrapped_polygon.intersection(window)
        if clipped.is_empty:
            continue
        geoms = clipped.geoms if hasattr(clipped, "geoms") else [clipped]
        for geom in geoms:
            if geom.is_empty or geom.geom_type != "Polygon" or geom.area == 0:
                continue
            pieces.append(_shift_polygon(geom, -360.0 * k))

    return pieces
```