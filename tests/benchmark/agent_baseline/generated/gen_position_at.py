"""Estimate a ship's position at an arbitrary time from GPS fixes.

Interpolation is done along the geodesic (great-ellipse path on the WGS84
ellipsoid) between the two fixes that bracket the requested time, so results
are accurate anywhere on the ocean, including across the antimeridian and
near the poles.
"""

from bisect import bisect_right

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def position_at(fixes, t):
    """Return the ship's estimated (lon, lat) at Unix time ``t``.

    Parameters
    ----------
    fixes : sequence of (timestamp, lon, lat)
        Chronologically sorted GPS fixes. Timestamps are Unix seconds,
        positions are WGS84 degrees.
    t : float
        A timestamp between the first and last fix (inclusive).

    Returns
    -------
    (lon, lat) : tuple of float
        Interpolated position in WGS84 degrees, lon in [-180, 180].
    """
    if not fixes:
        raise ValueError("fixes must be a non-empty sequence")
    if t < fixes[0][0] or t > fixes[-1][0]:
        raise ValueError(
            "t=%r is outside the fix time range [%r, %r]"
            % (t, fixes[0][0], fixes[-1][0])
        )

    times = [f[0] for f in fixes]
    # Index of the last fix with timestamp <= t.
    i = bisect_right(times, t) - 1

    t0, lon0, lat0 = fixes[i]
    if t0 == t or i == len(fixes) - 1:
        return (_norm_lon(lon0), lat0)

    t1, lon1, lat1 = fixes[i + 1]
    if t1 == t0:
        # Duplicate timestamps; nothing to interpolate over.
        return (_norm_lon(lon1), lat1)

    frac = (t - t0) / (t1 - t0)

    fwd_az, _back_az, dist = _GEOD.inv(lon0, lat0, lon1, lat1)
    if dist == 0.0:
        return (_norm_lon(lon0), lat0)

    lon, lat, _ = _GEOD.fwd(lon0, lat0, fwd_az, dist * frac)
    return (_norm_lon(lon), lat)


def _norm_lon(lon):
    """Normalize a longitude to the range [-180, 180)."""
    return (lon + 180.0) % 360.0 - 180.0
