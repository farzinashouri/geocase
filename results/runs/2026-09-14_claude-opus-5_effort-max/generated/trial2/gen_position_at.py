"""Estimate a vessel's position at an arbitrary time between GPS fixes.

``position_at(fixes, t)`` resamples a chronologically sorted track of
``(unix_seconds, lon, lat)`` WGS84 fixes at a time ``t`` that falls inside
the track's time span.

Model
-----
Between two consecutive fixes the vessel is assumed to sail the WGS84
*geodesic* joining them at constant ground speed.  Interpolating along the
geodesic instead of blending the raw ``(lon, lat)`` numbers is what makes
the result usable anywhere on the ocean:

* **Antimeridian.**  The path is built from the initial azimuth and the
  distance between the two fixes, so a leg from 179.9E to 179.9W is the
  ~22 km one, not the ~40 000 km trip the other way around.  No longitude
  unwrapping, no branch cut, no special case.
* **High latitudes.**  A straight line in (lon, lat) is not the path a ship
  sails; near the poles, where meridians converge, the naive blend can sit
  kilometres off the real track at mid-leg.  A geodesic is right there.
* **Ellipsoid, not sphere.**  Distances and azimuths run on WGS84, so the
  answer does not inherit the ~0.3 % error of a spherical Earth model.
* **The poles themselves** are ordinary points for the geodesic solver, so
  crossing near 90 deg needs no projection or coordinate gymnastics.

Known limits: this is dead reckoning, so a manoeuvre that happens entirely
between two fixes cannot be recovered, and a real vessel may steer a
constant heading (rhumb line) rather than a geodesic.  Over the sub-hourly
reporting intervals this is normally used with, those differ by at most a
few hundred metres, and the geodesic is the minimum-assumption choice.
Near-antipodal consecutive fixes are numerically ill-conditioned, but such
a pair is not a real ship track.

``fixes`` must be sorted by timestamp; that precondition is assumed, not
re-verified, so lookup stays O(log n).
"""

from __future__ import annotations

from typing import Sequence, Tuple

from pyproj import Geod

__all__ = ["position_at"]

# Pure, cheap, and stateless: constructing this touches no files or network,
# so importing the module has no side effects.
_GEOD = Geod(ellps="WGS84")


def position_at(fixes: Sequence[Sequence[float]], t: float) -> Tuple[float, float]:
    """Return the estimated ``(lon, lat)`` of the ship at time ``t``.

    Parameters
    ----------
    fixes:
        Chronologically sorted sequence of ``(timestamp, lon, lat)`` fixes.
        Timestamps are Unix seconds; positions are WGS84 degrees.  Extra
        trailing fields per fix (speed, heading, ...) are ignored.
    t:
        Timestamp to evaluate, within ``[fixes[0][0], fixes[-1][0]]``.

    Returns
    -------
    ``(lon, lat)`` in degrees, with longitude wrapped to ``[-180, 180)``.

    Raises
    ------
    ValueError
        If ``fixes`` is empty, if ``t`` lies outside the track's time span,
        or if a bracketing fix has a latitude outside ``[-90, 90]`` (the
        usual symptom of lon/lat being supplied the wrong way round).
    """
    n = len(fixes)
    if n == 0:
        raise ValueError("fixes is empty; cannot interpolate a position")

    i = _first_at_or_after(fixes, t)

    # Land exactly on a reported fix: report it verbatim rather than letting
    # a round trip through the geodesic solver perturb it.
    if i < n and fixes[i][0] == t:
        _, lon, lat = fixes[i][:3]
        return _checked(lon, lat)

    if i == 0 or i == n:
        raise ValueError(
            "t={!r} is outside the track span [{!r}, {!r}]".format(
                t, fixes[0][0], fixes[-1][0]
            )
        )

    t0, lon0, lat0 = fixes[i - 1][:3]
    t1, lon1, lat1 = fixes[i][:3]
    _checked(lon0, lat0)
    _checked(lon1, lat1)

    # t0 < t < t1 strictly, so this division is safe even if the track
    # contains repeated timestamps elsewhere.
    fraction = (t - t0) / (t1 - t0)

    azimuth, _, distance = _GEOD.inv(lon0, lat0, lon1, lat1)
    if distance == 0.0:
        # Vessel stopped (or a duplicated position): azimuth is meaningless.
        return _checked(lon0, lat0)

    lon, lat, _ = _GEOD.fwd(lon0, lat0, azimuth, distance * fraction)
    return _checked(lon, lat)


def _first_at_or_after(fixes: Sequence[Sequence[float]], t: float) -> int:
    """Index of the first fix timestamped at or after ``t``; ``len`` if none.

    Hand-rolled rather than :func:`bisect.bisect_left` so that it works on
    any indexable sequence of sequences — lists of lists, numpy rows — with
    no key function and no cross-type tuple comparison.
    """
    lo, hi = 0, len(fixes)
    while lo < hi:
        mid = (lo + hi) // 2
        if fixes[mid][0] < t:
            lo = mid + 1
        else:
            hi = mid
    return lo


def _checked(lon: float, lat: float) -> Tuple[float, float]:
    """Validate latitude and wrap longitude into ``[-180, 180)``."""
    lat = float(lat)
    if not -90.0 <= lat <= 90.0:
        raise ValueError(
            "latitude {!r} is outside [-90, 90]; are lon and lat swapped?".format(lat)
        )
    return (float(lon) + 180.0) % 360.0 - 180.0, lat