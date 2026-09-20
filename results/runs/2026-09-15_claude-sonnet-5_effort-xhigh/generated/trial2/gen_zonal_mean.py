"""Zonal mean of raster pixel values whose centres fall within a polygon."""

from typing import Optional

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry.base import BaseGeometry


def zonal_mean(raster_path: str, polygon: BaseGeometry) -> Optional[float]:
    if polygon is None or polygon.is_empty:
        return None

    with rasterio.open(raster_path) as src:
        data = src.read(1)
        nodata = src.nodata

        # all_touched=False (the default) burns in a pixel only when its
        # centre lies inside the geometry, matching the required semantics.
        centre_mask = geometry_mask(
            [polygon],
            out_shape=data.shape,
            transform=src.transform,
            invert=True,
        )

        if nodata is None:
            valid_mask = centre_mask
        elif np.isnan(nodata):
            valid_mask = centre_mask & ~np.isnan(data)
        else:
            valid_mask = centre_mask & (data != nodata)

        if not np.any(valid_mask):
            return None

        return float(data[valid_mask].mean())