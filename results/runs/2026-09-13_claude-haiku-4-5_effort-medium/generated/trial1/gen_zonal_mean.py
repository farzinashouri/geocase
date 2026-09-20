import numpy as np
import rasterio
from shapely.geometry import Point
from shapely.prepared import prep


def zonal_mean(raster_path, polygon):
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        transform = src.transform
        nodata = src.nodata
        
        # Create mask of valid pixels
        if nodata is None:
            valid_mask = np.ones(data.shape, dtype=bool)
        else:
            try:
                if np.isnan(nodata):
                    valid_mask = ~np.isnan(data)
                else:
                    valid_mask = data != nodata
            except TypeError:
                valid_mask = data != nodata
        
        rows, cols = np.where(valid_mask)
        
        # Calculate pixel center coordinates
        xs = transform.c + (cols + 0.5) * transform.a
        ys = transform.f + (rows + 0.5) * transform.e
        
        # Check which pixels are inside polygon
        prepared = prep(polygon)
        inside = np.array([prepared.contains(Point(x, y)) for x, y in zip(xs, ys)])
        
        if not np.any(inside):
            return None
        
        return float(np.mean(data[rows[inside], cols[inside]]))