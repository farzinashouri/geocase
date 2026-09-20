```python
"""Estimate a ship's position at an arbitrary time from GPS fixes.

Positions between two fixes are interpolated along the WGS84 geodesic
(the shortest path on the ellipsoid), so results are correct across the
antimeridian, near the poles, and over long legs where straight-line
interpolation in lon/lat would cut across the map.
"""

from __future__ import annotations

import bisect
import math
from typing import Sequence, Tuple

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)

_geod = None  # lazily constructed pyproj.Geod; keeps import side-effect free


def _normalize_lon(lon: float) -> float:
    """Wrap a longitude into [-180, 180]."""
    lon = (lon + 180.0) % 360.0 - 180.0
    return 180.0 if lon == -180.0 and lon != lon else lon


def _geodesic_point(lon1: float, lat1: float, lon2: float, lat2: float, f: float) -> Tuple[float, float]:
    """Point at fraction f (0..1) along the WGS84 geodesic from p1 to p2."""
    global _geod
    if _geod is None:
        from pyproj import Geod  # imported here so importing this module has no side effects

        _geod = Geod(ellps="WGS84")
    az12, _az21, dist = _geod.inv(lon1, lat1, lon2, lat2)
    if dist == 0.0:
        return _normalize_lon(lon1), lat1
    lon, lat, _ = _geod.fwd(lon1, lat1, az12, dist * f)
    return _normalize_lon(lon), lat


def _spherical_point(lon1: float, lat1: float, lon2: float, lat2: float, f: float) -> Tuple[float, float]:
    """Great-circle slerp fallback used only if pyproj is unavailable."""
    p1, l1 = math.radians(lat1), math.radians(lon1)
    p2, l2 = math.radians(lat2), math.radians(lon2)
    v1 = (math.cos(p1) * math.cos(l1), math.cos(p1) * math.sin(l1), math.sin(p1))
    v2 = (math.cos(p2) * math.cos(l2), math.cos(p2) * math.sin(l2), math.sin(p2))
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(v1, v2))))
    omega = math.acos(dot)
    if omega < 1e-12:
        return _normalize_lon(lon1), lat1
    s = math.sin(omega)
    a, b = math.sin((1.0 - f) * omega) / s, math.sin(f * omega) / s
    x, y, z = (a * u + b * w for u, w in zip(v1, v2))
    lat = math.degrees(math.atan2(z, math.hypot(x, y)))
    lon = math.degrees(math.atan2(y, x))
    return _normalize_lon(lon), lat


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the estimated (lon, lat) of the ship at Unix time ``t``.

    ``fixes`` must be a chronologically sorted sequence of (timestamp, lon, lat)
    tuples in WGS84. ``t`` must lie within [first timestamp, last timestamp].
    Interpolation is along the geodesic between the bracketing fixes, at
    constant speed.
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    times = [float(fx[0]) for fx in fixes]
    if t < times[0] or t > times[-1]:
        raise ValueError(f"t={t} is outside the fix range [{times[0]}, {times[-1]}]")

    # Index of the first fix with timestamp >= t.
    i = bisect.bisect_left(times, t)
    if times[i] == t:
        _, lon, lat = fixes[i]
        return _normalize_lon(float(lon)), float(lat)

    t0, lon0, lat0 = (float(v) for v in fixes[i - 1])
    t1, lon1, lat1 = (float(v) for v in fixes[i])
    span = t1 - t0
    if span <= 0:  # duplicate timestamps; nothing to interpolate
        return _normalize_lon(lon1), lat1
    f = (t - t0) / span

    try:
        return _geodesic_point(lon0, lat0, lon1, lat1, f)
    except ImportError:
        return _spherical_point(lon0, lat0, lon1, lat1, f)
```