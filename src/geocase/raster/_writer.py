"""GeoTIFF writing, isolated so the primitive never needs rasterio.

Rejector C already imports ``osgeo.gdal`` and will not take a rasterio
dependency for a test helper. So every rasterio import in this package lives
here, is lazy, and is reachable only through :meth:`FixtureSpec.write`. Taking
``.array`` and ``.transform`` and building the file yourself costs nothing.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geocase.raster.primitive import FixtureSpec


def write_geotiff(spec: FixtureSpec, path: Path, *, compress: str = "deflate") -> Path:
    """Write *spec* to *path* as a GeoTIFF."""
    try:
        import rasterio
        from rasterio.transform import Affine
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError(
            "writing a GeoTIFF needs rasterio: pip install 'geocase[write]'. "
            "To avoid the dependency entirely, use the FixtureSpec directly — "
            "its .array, .transform, .crs_wkt and .profile are public."
        ) from exc

    profile = {
        "driver": "GTiff",
        "height": spec.height,
        "width": spec.width,
        "count": spec.count,
        "dtype": spec.dtype,
        "transform": Affine(*spec.transform),
        "compress": compress,
    }
    if spec.crs_wkt is not None:
        profile["crs"] = spec.crs_wkt
    if spec.nodata is not None:
        profile["nodata"] = spec.nodata

    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(spec.array)
        for idx, description in enumerate(spec.band_descriptions, start=1):
            if idx <= spec.count:
                dst.set_band_description(idx, description)
        for idx, band_tags in enumerate(spec.band_tags, start=1):
            if idx <= spec.count and band_tags:
                dst.update_tags(idx, **band_tags)
        if spec.scales is not None:
            dst.scales = spec.scales
        if spec.offsets is not None:
            dst.offsets = spec.offsets
        if spec.tags:
            dst.update_tags(**spec.tags)
    return path
