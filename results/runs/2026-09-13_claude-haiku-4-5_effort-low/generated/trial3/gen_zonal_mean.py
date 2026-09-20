import rasterio
import numpy as np
from shapely.geometry import Point


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        transform = src.transform
        nodata = src.nodata
        
        height, width = data.shape
        rows, cols = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
        
        xs = transform.c + (cols + 0.5) * transform.a + (rows + 0.5) * transform.b
        ys = transform.f + (cols + 0.5) * transform.d + (rows + 0.5) * transform.e
        
        mask = np.array([polygon.contains(Point(x, y)) for x, y in zip(xs.flat, ys.flat)])
        mask = mask.reshape(data.shape)
        
        if nodata is not None:
            mask = mask & (data != nodata)
        
        valid_values = data[mask]
        if valid_values.size == 0:
            return None
        return float(np.mean(valid_values))