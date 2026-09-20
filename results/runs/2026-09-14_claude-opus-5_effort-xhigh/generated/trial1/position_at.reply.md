Interpolation runs along the WGS84 geodesic between the bracketing fixes, which is what keeps it correct across the antimeridian and at high latitude.

```python
"""Estimate a ship's position at an arbitrary time between GPS fixes.

``position_at`` finds the two fixes that bracket the requested time and
interpolates along the WGS84 geodesic joining them, assuming constant speed
over that leg.

Interpolating longitude and latitude independently would be wrong in two ways
that matter at sea:

* it breaks across the antimeridian -- a leg from +179.9 to -179.9 would be
  walked the long way round the planet; and
* it leaves the true track at high latitude, where a degree of longitude is
  much shorter than a degree of latitude, so the midpoint of a long east-west
  leg can land kilometres off.

Both are avoided by doing the work on the ellipsoid with ``pyproj.Geod``.

Modelling assumption: the leg between two fixes is a geodesic (shortest path).
A vessel holding a constant compass course actually follows a rhumb line; the
two paths coincide at the endpoints and diverge in between, negligibly for the
seconds-to-minutes gaps of AIS/GPS logs but increasingly for very long gaps at
high latitude. Nothing here can recover the real track inside a gap -- it is an
interpolation, not a reconstruction.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from typing import Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

# Constructing a Geod is pure: no I/O, no global state, no network.
_GEOD = Geod(ellps="WGS84")

Fix = Tuple[float, float, float]


def position_at(fixes: Sequence[Fix], t: float) -> Tuple[float, float]:
    """Return the estimated ``(lon, lat)`` of the ship at time ``t``.

    Parameters
    ----------
    fixes:
        Sequence of ``(timestamp, lon, lat)`` GPS fixes sorted by timestamp,
        with Unix-second timestamps and WGS84 degrees. Assumed sorted (it is
        indexed by binary search rather than scanned, so the whole sequence is
        never validated); an out-of-order pair that is actually used raises
        ``ValueError`` instead of returning nonsense.
    t:
        Timestamp to evaluate, between the first and last fix inclusive.

    Returns
    -------
    ``(lon, lat)`` in degrees, longitude normalised to ``[-180, 180]``.

    Raises
    ------
    ValueError
        If ``fixes`` is empty, if ``t`` falls outside the covered interval, or
        if a fix that would be used is malformed.

    Notes
    -----
    If several fixes share a timestamp equal to ``t``, the last of them wins.
    Two fixes that are exactly antipodal have no unique geodesic between them;
    the path chosen in that case is arbitrary but still ends at both fixes.

    Example
    -------
    ``position_at([(0, -179.9, 60.0), (3600, 179.9, 60.0)], 1800)`` returns a
    point hard by longitude 180 -- not one near longitude 0, as component-wise
    interpolation would give.
    """
    n = len(fixes)
    if n == 0:
        raise ValueError("fixes must contain at least one fix")

    t = float(t)
    if not math.isfinite(t):
        raise ValueError(f"t must be a finite timestamp, got {t!r}")

    t_first = float(fixes[0][0])
    t_last = float(fixes[-1][0])
    if not t_first <= t <= t_last:
        raise ValueError(
            f"t={t!r} is outside the interval covered by the fixes "
            f"[{t_first!r}, {t_last!r}]"
        )

    # Rightmost fix at or before t. Guaranteed in range by the check above.
    i = bisect_right(fixes, t, key=_timestamp_of) - 1

    t0, lon0, lat0 = _unpack(fixes[i], i)
    if t0 == t:
        return (_wrap_lon(lon0), lat0)

    t1, lon1, lat1 = _unpack(fixes[i + 1], i + 1)
    if t1 <= t0:
        raise ValueError(
            f"fixes must be sorted by timestamp: fix {i} is at {t0!r} "
            f"but fix {i + 1} is at {t1!r}"
        )

    frac = (t - t0) / (t1 - t0)

    # inv/fwd are a matched pair: the forward azimuth and geodesic distance
    # from fix i to fix i+1, then a partial step along that same geodesic.
    azimuth, _, distance = _GEOD.inv(lon0, lat0, lon1, lat1)
    if distance == 0.0 or not math.isfinite(azimuth):
        # Ship stationary between the two fixes (or a degenerate azimuth at a
        # pole, where every direction is the same point anyway).
        return (_wrap_lon(lon0), lat0)

    lon, lat, _ = _GEOD.fwd(lon0, lat0, azimuth, distance * frac)
    return (_wrap_lon(lon), lat)


def _timestamp_of(fix: Fix) -> float:
    """Sort key for the bracketing search."""
    return fix[0]


def _unpack(fix: Fix, index: int) -> Fix:
    """Return a fix as validated floats, or raise ``ValueError``."""
    try:
        timestamp, lon, lat = fix
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"fix {index} must be a (timestamp, lon, lat) triple, got {fix!r}"
        ) from exc

    try:
        timestamp, lon, lat = float(timestamp), float(lon), float(lat)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"fix {index} has non-numeric values: {fix!r}") from exc

    if not (math.isfinite(timestamp) and math.isfinite(lon) and math.isfinite(lat)):
        raise ValueError(f"fix {index} contains a non-finite value: {fix!r}")
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"fix {index} has latitude {lat!r} outside [-90, 90]")

    return timestamp, lon, lat


def _wrap_lon(lon: float) -> float:
    """Normalise a longitude in degrees to ``[-180, 180]``."""
    if -180.0 <= lon <= 180.0:
        return lon
    return (lon + 180.0) % 360.0 - 180.0
```