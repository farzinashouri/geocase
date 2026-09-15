```python
"""Metric buffering of WGS84 (EPSG:4326) geometries.

`buffer_m(geom, distance_m)` buffers a lon/lat geometry by a distance in
meters and returns the result in lon/lat.

Method
------
Buffering in degrees is wrong everywhere except near the equator, because a
degree of longitude shrinks as cos(latitude).  Instead, each geometry is
projected into a local azimuthal equidistant (AEQD) projection centered on
the geometry itself, buffered there with plain planar `shapely.buffer`, and
projected back.  AEQD is exact in distance and azimuth along rays from its
center, so distortion grows only with the extent of the geometry plus the
buffer distance, not with its position on Earth.  This works at any latitude,
including both poles, and across the antimeridian.

Known limits (inherent to any single-projection approach):

* Accuracy degrades for very large features/distances -- expect sub-percent
  error out to a few hundred km from the center, more beyond ~1000 km.
* A buffer that swallows a pole, or that wraps more than half the globe in
  longitude, cannot be represented as a lon/lat polygon without cutting; the
  returned ring is still geometrically faithful in the projected sense but
  its lon/lat rendering may look odd.  `unwrap_longitudes=False` disables the
  seam-crossing heuristic if you would rather have raw, possibly out-of-range
  longitudes.
"""

from __future__ import annotations

from functools import lru_cache

from pyproj import CRS, Transformer
from shapely import get_coordinates, set_coordinates
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

__all__ = ["buffer_m"]

_WGS84 = "EPSG:4326"


@lru_cache(maxsize=256)
def _transformers(lon0: float, lat0: float):
    """Forward/inverse transformers for an AEQD projection at (lon0, lat0)."""
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} "
        "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )
    fwd = Transformer.from_crs(_WGS84, aeqd, always_xy=True)
    inv = Transformer.from_crs(aeqd, _WGS84, always_xy=True)
    return fwd, inv


def _center(geom: BaseGeometry) -> tuple[float, float]:
    """A representative lon/lat center, safe across the antimeridian.

    Averages longitudes as unit vectors so that e.g. 179 and -179 average to
    180 rather than 0.  Rounded so nearby geometries share a cached
    projection.
    """
    import numpy as np

    coords = get_coordinates(geom)
    if len(coords) == 0:
        raise ValueError("cannot buffer an empty geometry")
    lon = np.radians(coords[:, 0])
    lat = coords[:, 1]
    mean_lon = np.degrees(np.arctan2(np.sin(lon).mean(), np.cos(lon).mean()))
    mean_lat = float(np.clip(lat.mean(), -90.0, 90.0))
    return round(float(mean_lon), 6), round(mean_lat, 6)


def _normalize_longitudes(geom: BaseGeometry, lon0: float) -> BaseGeometry:
    """Wrap longitudes into [-180, 180], keeping each ring contiguous.

    Coordinates are first unwrapped relative to the projection center (so a
    ring straddling the antimeridian stays continuous), then wrapped back
    into range only if the whole geometry fits without crossing the seam.
    """
    import numpy as np

    coords = get_coordinates(geom)
    if len(coords) == 0:
        return geom
    lons = coords[:, 0]
    # Unwrap relative to the center: shift each lon into (lon0-180, lon0+180].
    unwrapped = lon0 + ((lons - lon0 + 180.0) % 360.0) - 180.0
    wrapped = ((unwrapped + 180.0) % 360.0) - 180.0
    # Only wrap into range when doing so does not tear the geometry apart.
    use = wrapped if np.ptp(unwrapped) < 360.0 and (
        np.ptp(wrapped) <= np.ptp(unwrapped) + 1e-9
    ) else unwrapped
    out = coords.copy()
    out[:, 0] = use
    out[:, 1] = np.clip(coords[:, 1], -90.0, 90.0)
    return set_coordinates(geom.__class__(geom), out)


def buffer_m(
    geom: BaseGeometry,
    distance_m: float,
    *,
    quad_segs: int = 16,
    unwrap_longitudes: bool = True,
    **buffer_kwargs,
) -> BaseGeometry:
    """Buffer a lon/lat (EPSG:4326) geometry by ``distance_m`` meters.

    Parameters
    ----------
    geom:
        Any shapely geometry with longitude/latitude coordinates.
    distance_m:
        Buffer distance in meters.  Negative values erode (shapely's usual
        semantics); zero returns a cleaned copy of the input.
    quad_segs:
        Segments per quarter circle used to approximate the buffer's round
        joins.  Passed through to ``shapely.buffer``.
    unwrap_longitudes:
        Post-process output longitudes into [-180, 180] where that can be
        done without splitting a ring.  Set False to get raw values.
    **buffer_kwargs:
        Forwarded to ``shapely.buffer`` (``cap_style``, ``join_style``,
        ``mitre_limit``, ``single_sided``).

    Returns
    -------
    A shapely geometry in EPSG:4326.
    """
    if geom is None:
        raise ValueError("geom must be a shapely geometry")
    if geom.is_empty:
        return geom

    lon0, lat0 = _center(geom)
    fwd, inv = _transformers(lon0, lat0)

    projected = shapely_transform(lambda x, y, z=None: fwd.transform(x, y), geom)
    buffered = projected.buffer(distance_m, quad_segs=quad_segs, **buffer_kwargs)
    if buffered.is_empty:
        return buffered

    result = shapely_transform(lambda x, y, z=None: inv.transform(x, y), buffered)
    if unwrap_longitudes:
        result = _normalize_longitudes(result, lon0)
    return result
```