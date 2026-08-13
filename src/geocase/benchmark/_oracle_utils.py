"""Shared oracle helpers. Everything here is computed from first principles
(pyproj.Geod, the Web Mercator formulas, the geohash bit interleaving) — never
from the GeoCase fixture corpus (Plan 15, trap 2)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pyproj
from pyproj import Geod

GEOD = Geod(ellps="WGS84")


def rel_ok(got: float, expected: float, tol: float) -> bool:
    return abs(got - expected) <= tol * abs(expected)


def make_utm_nodata_raster(path: Path) -> None:
    """10x10 EPSG:32633 raster, 100 m pixels, value 42, nodata -9999 at (5,5)."""
    import rasterio
    from rasterio.transform import from_origin

    transform = from_origin(500_000, 6_600_000, 100, 100)
    data = np.full((10, 10), 42.0, dtype="float32")
    data[5, 5] = -9999.0
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:32633",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)


def utm_pixel_lonlat(row: int, col: int) -> tuple[float, float]:
    """Lon/lat of a pixel centre of the raster built by make_utm_nodata_raster."""
    x = 500_000 + (col + 0.5) * 100
    y = 6_600_000 - (row + 0.5) * 100
    t = pyproj.Transformer.from_crs("EPSG:32633", "EPSG:4326", always_xy=True)
    return t.transform(x, y)


def xyz_tile_bounds(z: int, x: int, y_xyz: int) -> tuple[float, float, float, float]:
    n = 2**z

    def lon(xx):
        return xx / n * 360.0 - 180.0

    def lat(yy):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy / n))))

    return (lon(x), lat(y_xyz + 1), lon(x + 1), lat(y_xyz))


# ---------------------------------------------------------------- geohash
# Standard geohash bit interleaving, implemented from the definition so the
# oracle owes nothing to any geohash library a model might also use.
_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def geohash_decode_bounds(gh: str) -> tuple[float, float, float, float]:
    """(west, south, east, north) of the cell."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    even = True  # even bit index -> longitude
    for ch in gh:
        idx = _BASE32.index(ch)
        for bit in (16, 8, 4, 2, 1):
            if even:
                mid = (lon_lo + lon_hi) / 2
                if idx & bit:
                    lon_lo = mid
                else:
                    lon_hi = mid
            else:
                mid = (lat_lo + lat_hi) / 2
                if idx & bit:
                    lat_lo = mid
                else:
                    lat_hi = mid
            even = not even
    return (lon_lo, lat_lo, lon_hi, lat_hi)


def geohash_encode(lon: float, lat: float, precision: int) -> str:
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    even = True
    chars: list[str] = []
    idx = 0
    bit = 0
    while len(chars) < precision:
        if even:
            mid = (lon_lo + lon_hi) / 2
            if lon >= mid:
                idx = idx * 2 + 1
                lon_lo = mid
            else:
                idx = idx * 2
                lon_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid:
                idx = idx * 2 + 1
                lat_lo = mid
            else:
                idx = idx * 2
                lat_hi = mid
        even = not even
        bit += 1
        if bit == 5:
            chars.append(_BASE32[idx])
            idx = 0
            bit = 0
    return "".join(chars)


def geohash_neighbors_oracle(gh: str) -> set[str]:
    """The 8 neighbours, by decoding the cell and re-encoding offset centres."""
    w, s, e, n = geohash_decode_bounds(gh)
    dlon, dlat = e - w, n - s
    clon, clat = (w + e) / 2, (s + n) / 2
    out = set()
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            if i == j == 0:
                continue
            lat = clat + j * dlat
            if not -90 < lat < 90:
                continue
            lon = clon + i * dlon
            lon = (lon + 180) % 360 - 180
            out.add(geohash_encode(lon, lat, len(gh)))
    return out
