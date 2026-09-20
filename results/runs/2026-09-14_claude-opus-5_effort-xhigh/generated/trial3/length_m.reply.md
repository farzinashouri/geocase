Geodesic (Karney) computation on the WGS84 ellipsoid via `pyproj.Geod` — accurate to sub-millimeter everywhere, with no projection/UTM-zone selection and correct behavior at the poles and across the antimeridian.

```python
"""Geodesic length of EPSG:4326 (WGS84) linestrings, in meters.

Length is computed segment-by-segment as geodesics on the WGS84 ellipsoid
(Karney's algorithms, via ``pyproj.Geod``) rather than by projecting to a
planar CRS. That keeps results accurate anywhere on Earth: there is no
projection zone to choose, no distortion away from a zone's central meridian,
and no special handling needed at the poles or across the antimeridian --- each
segment is the shortest ellipsoidal path between its two endpoints.

Importing this module has no side effects; the ellipsoid model is built on
first use.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from pyproj import Geod

__all__ = ["length_m"]

#: Ellipsoid matching EPSG:4326 / EPSG:7030.
_ELLIPSOID = "WGS84"

#: Geometry types whose coordinate sequence is a single, ordered path.
_LINEAR_TYPES = ("LineString", "LinearRing")


@lru_cache(maxsize=1)
def _geod() -> Geod:
    """Return the shared WGS84 ellipsoid model, constructing it on first call."""
    return Geod(ellps=_ELLIPSOID)


def length_m(line) -> float:
    """Return the geodesic length of ``line`` in meters.

    Parameters
    ----------
    line:
        A shapely ``LineString`` (or ``LinearRing``) whose coordinates are
        ``(longitude, latitude)`` in degrees, EPSG:4326. Any Z values are
        ignored: the result is the length along the ellipsoid surface, not a
        3D slope distance.

    Returns
    -------
    float
        Length in meters. Empty geometries and single-vertex lines give ``0.0``.

    Raises
    ------
    TypeError
        If ``line`` is not a LineString-like geometry. Multi-part geometries are
        rejected rather than silently measured as one path, since that would add
        spurious connector segments between the parts.
    ValueError
        If any coordinate is NaN or infinite.
    """
    geom_type = getattr(line, "geom_type", None)
    if geom_type not in _LINEAR_TYPES:
        name = geom_type or type(line).__name__
        raise TypeError(f"expected a LineString, got {name!r}")

    if line.is_empty:
        return 0.0

    coords = np.asarray(line.coords, dtype=float)
    if coords.shape[0] < 2:
        return 0.0

    # Contiguous 1-D copies: pyproj reads these through the buffer protocol.
    lons = np.ascontiguousarray(coords[:, 0])
    lats = np.ascontiguousarray(coords[:, 1])

    if not (np.isfinite(lons).all() and np.isfinite(lats).all()):
        raise ValueError("line contains non-finite coordinates")

    return float(_geod().line_length(lons, lats))
```