"""Estimate a ship's position between two GPS fixes.

The naive approach -- linear interpolation of the longitude and latitude
numbers -- is wrong in ways that matter at sea:

* **Antimeridian.** A track from 179.9E to 179.9W is a 22 km hop, but the
  average of ``179.9`` and ``-179.9`` is ``0.0``: the Gulf of Guinea.
* **Convergence of the meridians.** One degree of longitude is 111 km at the
  equator and 29 km at 75N, so a degree-space midpoint is not the halfway
  point of the voyage. The error grows with latitude and with leg length.
* **Ellipsoid vs. sphere.** WGS84 is flattened; a spherical great circle
  departs from the true shortest path by a few hundred metres on an ocean
  crossing.

So we interpolate along the *geodesic* -- the shortest path on the WGS84
ellipsoid -- at constant speed: solve the inverse problem between the two
bracketing fixes for initial azimuth and distance, then solve the forward
problem for the fraction of that distance corresponding to ``t``. pyproj
wraps Karney's GeographicLib, which is accurate to ~15 nm (nanometres)
everywhere, including across the dateline, over the poles, and for
near-antipodal legs.

This is a per-segment estimate; no curve is fitted across neighbouring fixes,
because a smoothing spline can bow the track off a straight leg and would
invent detail the fixes do not contain.
"""

from __future__ import annotations

from bisect import bisect_right
from functools import lru_cache
from math import isfinite
from typing import Sequence, Tuple

__all__ = ["position_at"]

Fix = Tuple[float, float, float]

# Legs shorter than this are treated as a stationary ship: below it the
# azimuth from the inverse solution is numerically meaningless (and can come
# back as NaN for coincident points), while the positional error of just
# returning the earlier fix is under a nanometre.
_STATIONARY_M = 1e-9


@lru_cache(maxsize=1)
def _geod():
    """Return the shared WGS84 geodesic solver.

    Built on first use, not at import time, so that importing this module has
    no side effects (and does not pull in PROJ unless a position is asked for).
    The object is read-only once constructed, so sharing it is safe.
    """
    from pyproj import Geod

    return Geod(ellps="WGS84")


def _wrap_lon(lon: float) -> float:
    """Normalise a longitude to [-180, 180)."""
    return ((float(lon) + 180.0) % 360.0) - 180.0


def _unpack(fix: Fix, index: int) -> Fix:
    """Validate one fix and return it as plain floats."""
    try:
        ts, lon, lat = (float(v) for v in fix[:3])
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError(f"fixes[{index}] is not a (timestamp, lon, lat) triple: {fix!r}") from exc
    if not (isfinite(ts) and isfinite(lon) and isfinite(lat)):
        raise ValueError(f"fixes[{index}] contains a non-finite value: {fix!r}")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"fixes[{index}] has latitude {lat!r} outside [-90, 90]")
    return ts, lon, lat


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Estimate the ship's position at time ``t``.

    Args:
        fixes: GPS fixes as ``(timestamp, lon, lat)``, sorted by timestamp
            ascending. Timestamps are Unix seconds; ``lon``/``lat`` are WGS84
            degrees. Longitudes need not be pre-normalised. Results are
            undefined if the list is not sorted.
        t: Unix timestamp within ``[fixes[0][0], fixes[-1][0]]``.

    Returns:
        ``(lon, lat)`` in WGS84 degrees, with ``lon`` in [-180, 180). A ``t``
        that lands exactly on a fix returns that fix's position unchanged.

    Raises:
        ValueError: if ``fixes`` is empty, a fix is malformed, or ``t`` lies
            outside the window spanned by the fixes (this function
            interpolates; it deliberately does not extrapolate).
    """
    n = len(fixes)
    if n == 0:
        raise ValueError("fixes is empty; need at least one fix to interpolate")

    t = float(t)
    if not isfinite(t):
        raise ValueError(f"t must be a finite timestamp, got {t!r}")

    t_first = _unpack(fixes[0], 0)[0]
    t_last = _unpack(fixes[n - 1], n - 1)[0]
    if not t_first <= t <= t_last:
        raise ValueError(f"t={t!r} is outside the fix window [{t_first!r}, {t_last!r}]")

    # Index of the last fix at or before t. bisect_right skips over runs of
    # duplicate timestamps, so the bracketing segment always has a positive
    # duration for well-formed input.
    i = bisect_right(fixes, t, key=lambda fix: float(fix[0])) - 1
    if i < 0:
        i = 0
    if i >= n - 1:
        _, lon, lat = _unpack(fixes[n - 1], n - 1)
        return _wrap_lon(lon), lat

    t0, lon0, lat0 = _unpack(fixes[i], i)
    t1, lon1, lat1 = _unpack(fixes[i + 1], i + 1)

    span = t1 - t0
    if span <= 0.0:  # duplicate or out-of-order timestamps
        return _wrap_lon(lon1), lat1

    frac = (t - t0) / span
    if frac <= 0.0:
        return _wrap_lon(lon0), lat0
    if frac >= 1.0:
        return _wrap_lon(lon1), lat1

    geod = _geod()
    azimuth, _, distance = geod.inv(lon0, lat0, lon1, lat1)
    if not isfinite(distance) or distance <= _STATIONARY_M or not isfinite(azimuth):
        return _wrap_lon(lon0), lat0

    lon, lat, _ = geod.fwd(lon0, lat0, azimuth, distance * frac)
    return _wrap_lon(lon), float(lat)