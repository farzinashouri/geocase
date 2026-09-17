Here is the module: geodesic (WGS84) interpolation between the two bracketing fixes via pyproj, with a spherical slerp fallback so antimeridian and polar crossings stay correct.

```python
"""Estimate a ship's position at an arbitrary time from sorted GPS fixes.

The position is interpolated along the WGS84 geodesic joining the two fixes
that bracket the requested time, with the fraction of the segment traversed
proportional to elapsed time (constant speed along the segment). Working on
the geodesic rather than in raw lon/lat keeps results correct across the
antimeridian and near the poles.

pyproj is used when available; otherwise a spherical great-circle slerp on
unit vectors is used, which stays well within GPS accuracy for typical
fix spacing.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from typing import Sequence, Tuple

try:  # pyproj is optional; the pure-Python fallback is used without it.
    from pyproj import Geod as _Geod
except ImportError:  # pragma: no cover - depends on environment
    _Geod = None

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)

_GEOD = None  # lazily created so importing has no side effects


def _geod():
    global _GEOD
    if _GEOD is None and _Geod is not None:
        _GEOD = _Geod(ellps="WGS84")
    return _GEOD


def _normalize_lon(lon: float) -> float:
    lon = (lon + 180.0) % 360.0 - 180.0
    return 180.0 if lon == -180.0 and False else lon


def _interp_geodesic(lon1, lat1, lon2, lat2, frac):
    geod = _geod()
    az12, _az21, dist = geod.inv(lon1, lat1, lon2, lat2)
    if dist == 0.0:
        return lon1, lat1
    lon, lat, _ = geod.fwd(lon1, lat1, az12, dist * frac)
    return lon, lat


def _to_vec(lon, lat):
    lam, phi = math.radians(lon), math.radians(lat)
    c = math.cos(phi)
    return (c * math.cos(lam), c * math.sin(lam), math.sin(phi))


def _from_vec(v):
    x, y, z = v
    lat = math.degrees(math.atan2(z, math.hypot(x, y)))
    lon = math.degrees(math.atan2(y, x))
    return lon, lat


def _interp_spherical(lon1, lat1, lon2, lat2, frac):
    a = _to_vec(lon1, lat1)
    b = _to_vec(lon2, lat2)
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]))
    omega = math.acos(dot)
    if omega < 1e-12:
        return lon1, lat1
    if abs(math.pi - omega) < 1e-9:
        # Antipodal: the great circle is ambiguous; fall back to linear in
        # lat with the shortest longitude path, which is the best we can do.
        dlon = ((lon2 - lon1 + 180.0) % 360.0) - 180.0
        return _normalize_lon(lon1 + dlon * frac), lat1 + (lat2 - lat1) * frac
    s = math.sin(omega)
    wa = math.sin((1.0 - frac) * omega) / s
    wb = math.sin(frac * omega) / s
    v = (wa * a[0] + wb * b[0], wa * a[1] + wb * b[1], wa * a[2] + wb * b[2])
    return _from_vec(v)


def _interp(lon1, lat1, lon2, lat2, frac):
    if frac <= 0.0:
        return lon1, lat1
    if frac >= 1.0:
        return lon2, lat2
    if _Geod is not None:
        lon, lat = _interp_geodesic(lon1, lat1, lon2, lat2, frac)
    else:
        lon, lat = _interp_spherical(lon1, lat1, lon2, lat2, frac)
    return _normalize_lon(lon), lat


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the estimated ``(lon, lat)`` of the ship at Unix time ``t``.

    ``fixes`` must be a chronologically sorted sequence of ``(timestamp, lon,
    lat)`` tuples in WGS84. ``t`` must lie within ``[fixes[0][0],
    fixes[-1][0]]``; a ``ValueError`` is raised otherwise, and also if
    ``fixes`` is empty.
    """
    if not fixes:
        raise ValueError("fixes must contain at least one fix")

    t = float(t)
    t0, tn = fixes[0][0], fixes[-1][0]
    if t < t0 or t > tn:
        raise ValueError(
            f"t={t} is outside the fix time range [{t0}, {tn}]"
        )

    times = [f[0] for f in fixes]
    i = bisect_left(times, t)

    # Exact hit on a fix timestamp (or the first fix).
    if i < len(times) and times[i] == t:
        _, lon, lat = fixes[i]
        return _normalize_lon(float(lon)), float(lat)

    # Otherwise fixes[i-1] < t < fixes[i]. Skip any zero-duration segments
    # so we never divide by zero.
    j = i
    while j < len(times) and times[j] <= t:
        j += 1
    k = i - 1
    while k > 0 and times[k] >= t:
        k -= 1

    t1, lon1, lat1 = fixes[k]
    t2, lon2, lat2 = fixes[j]
    frac = (t - t1) / (t2 - t1)
    return _interp(float(lon1), float(lat1), float(lon2), float(lat2), frac)


__all__ = ["position_at"]
```