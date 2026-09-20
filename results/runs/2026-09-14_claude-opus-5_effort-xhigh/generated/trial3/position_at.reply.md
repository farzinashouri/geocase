```python
"""Interpolate a ship's position between consecutive GPS fixes.

Positions are WGS84 (lon, lat) in degrees; timestamps are Unix seconds.

Method
------
Between the two fixes that bracket the requested time, the ship is assumed to
travel at constant speed along the *geodesic* joining them. The point is found
with pyproj's geodesic solvers on the WGS84 ellipsoid:

    inv(p0, p1) -> (initial azimuth, distance)
    fwd(p0, azimuth, fraction * distance) -> position

This is correct everywhere on the globe, including across the antimeridian and
over the poles, because no arithmetic is ever done on raw longitude values
(naive per-component linear interpolation fails badly near +/-180 degrees and at
high latitudes). Ellipsoidal geodesics also avoid the ~0.3% error of a spherical
approximation, which is ~1.5 km over a 500 km leg.

Importing this module performs no I/O and creates no global state; the Geod
object is built lazily on first use.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

Fix = Tuple[float, float, float]  # (timestamp, lon, lat)

_GEOD: Optional[Geod] = None


def _geod() -> Geod:
    """Return the shared WGS84 geodesic solver, creating it on first use."""
    global _GEOD
    if _GEOD is None:
        _GEOD = Geod(ellps="WGS84")
    return _GEOD


def _normalize(lon: float, lat: float) -> Tuple[float, float]:
    """Wrap longitude into [-180, 180) and clamp latitude against float noise."""
    lon = ((float(lon) + 180.0) % 360.0) - 180.0
    lat = min(90.0, max(-90.0, float(lat)))
    return lon, lat


def _bracket_index(fixes: Sequence[Fix], t: float) -> int:
    """Index of the rightmost fix whose timestamp is <= ``t``.

    Equivalent to ``bisect_right(timestamps, t) - 1``, written out so no
    auxiliary list of timestamps has to be materialized per call.
    """
    lo, hi = 0, len(fixes)
    while lo < hi:
        mid = (lo + hi) // 2
        if fixes[mid][0] <= t:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Estimate the ship's position at time ``t``.

    Parameters
    ----------
    fixes:
        Chronologically sorted ``(timestamp, lon, lat)`` triples. Timestamps are
        Unix seconds; ``lon``/``lat`` are WGS84 degrees. At least one fix is
        required, and timestamps must be non-decreasing.
    t:
        Unix timestamp within ``[fixes[0][0], fixes[-1][0]]``.

    Returns
    -------
    (lon, lat)
        Interpolated WGS84 position, longitude wrapped into [-180, 180).

    Raises
    ------
    ValueError
        If ``fixes`` is empty, ``t`` lies outside the covered interval, or the
        bracketing timestamps are not increasing (i.e. the input is unsorted).
    """
    n = len(fixes)
    if n == 0:
        raise ValueError("fixes must contain at least one fix")

    t = float(t)
    t_first = fixes[0][0]
    t_last = fixes[-1][0]
    if not (t_first <= t <= t_last):
        raise ValueError(
            f"t={t!r} is outside the fix interval [{t_first!r}, {t_last!r}]"
        )

    i = _bracket_index(fixes, t)

    # Exactly on a fix (including the final one): report it verbatim rather than
    # round-tripping through the geodesic solver.
    if fixes[i][0] == t:
        return _normalize(fixes[i][1], fixes[i][2])

    t0, lon0, lat0 = fixes[i]
    t1, lon1, lat1 = fixes[i + 1]
    if t1 <= t0:
        raise ValueError(
            f"fixes are not chronologically sorted at index {i}: {t0!r} >= {t1!r}"
        )

    geod = _geod()
    az12, _az21, dist = geod.inv(lon0, lat0, lon1, lat1)
    if not dist:  # stationary leg (or identical endpoints)
        return _normalize(lon0, lat0)

    fraction = (t - t0) / (t1 - t0)
    lon, lat, _ = geod.fwd(lon0, lat0, az12, dist * fraction)
    return _normalize(lon, lat)
```