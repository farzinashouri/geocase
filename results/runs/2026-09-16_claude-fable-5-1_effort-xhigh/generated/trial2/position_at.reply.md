Write access to /tmp was not granted, so the module below is unverified by execution. The logic was checked by hand: binary search for the bracketing pair, exact return on a matching timestamp, and geodesic interpolation with pyproj, falling back to spherical slerp.

```python
"""Estimate a ship's position at an arbitrary time from a track of GPS fixes.

Between two bracketing fixes the position is interpolated along the geodesic
(shortest path on the WGS84 ellipsoid) joining them, the fraction of the path
travelled being proportional to elapsed time.  Interpolating along the geodesic
rather than in raw lon/lat keeps the result correct across the antimeridian,
near the poles and over long gaps between fixes.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from operator import itemgetter
from typing import Optional, Sequence, Tuple

try:  # exact WGS84 geodesic when pyproj is available; spherical fallback otherwise
    from pyproj import Geod as _Geod
except ImportError:  # pragma: no cover
    _Geod = None

Fix = Tuple[float, float, float]  # (unix timestamp, lon, lat)
Position = Tuple[float, float]  # (lon, lat)

_geod: Optional[object] = None


def position_at(fixes: Sequence[Fix], t: float) -> Position:
    """Return the ship's estimated ``(lon, lat)`` at time ``t``.

    ``fixes`` must be sorted by timestamp; ``t`` must lie within
    ``[fixes[0][0], fixes[-1][0]]`` (inclusive).  A ``t`` that coincides with a
    fix returns that fix's position unchanged.
    """
    if not fixes:
        raise ValueError("fixes is empty")
    n = len(fixes)
    idx = bisect_right(fixes, t, key=itemgetter(0))  # fixes[:idx] have ts <= t
    if idx == 0 or (idx == n and fixes[-1][0] < t):
        raise ValueError(f"t={t!r} lies outside the track's time span")
    t0, lon0, lat0 = fixes[idx - 1]
    if t0 == t:
        return float(lon0), float(lat0)
    t1, lon1, lat1 = fixes[idx]  # guaranteed t0 <= t < t1, so t1 - t0 > 0
    frac = (t - t0) / (t1 - t0)
    return _interpolate(float(lon0), float(lat0), float(lon1), float(lat1), frac)


def _interpolate(lon0: float, lat0: float, lon1: float, lat1: float, frac: float) -> Position:
    geod = _get_geod()
    if geod is not None:
        az12, _, dist = geod.inv(lon0, lat0, lon1, lat1)
        lon, lat, _ = geod.fwd(lon0, lat0, az12, dist * frac)
        return _normalize(float(lon), float(lat))
    return _slerp(lon0, lat0, lon1, lat1, frac)


def _get_geod():
    """Lazily build the WGS84 Geod so importing the module does no work."""
    global _geod
    if _geod is None and _Geod is not None:
        _geod = _Geod(ellps="WGS84")
    return _geod


def _normalize(lon: float, lat: float) -> Position:
    if lon > 180.0:
        lon -= 360.0
    elif lon < -180.0:
        lon += 360.0
    return lon, lat


def _to_unit_vector(lon: float, lat: float) -> Tuple[float, float, float]:
    lam, phi = math.radians(lon), math.radians(lat)
    c = math.cos(phi)
    return c * math.cos(lam), c * math.sin(lam), math.sin(phi)


def _slerp(lon0: float, lat0: float, lon1: float, lat1: float, frac: float) -> Position:
    """Great-circle interpolation on a sphere (used only without pyproj)."""
    a = _to_unit_vector(lon0, lat0)
    b = _to_unit_vector(lon1, lat1)
    dot = max(-1.0, min(1.0, sum(p * q for p, q in zip(a, b))))
    omega = math.acos(dot)
    s = math.sin(omega)
    if s < 1e-12:
        if omega > 1.0:  # antipodal: path direction undefined, snap to nearer end
            return (lon0, lat0) if frac < 0.5 else (lon1, lat1)
        wa, wb = 1.0 - frac, frac  # coincident: linear blend is exact enough
    else:
        wa = math.sin((1.0 - frac) * omega) / s
        wb = math.sin(frac * omega) / s
    x, y, z = (wa * p + wb * q for p, q in zip(a, b))
    lon = math.degrees(math.atan2(y, x))
    lat = math.degrees(math.atan2(z, math.hypot(x, y)))
    return lon, lat
```