import rasterio
from pyproj import Transformer


def sample_at(raster_path, lon, lat):
    with rasterio.open(raster_path) as dataset:
        if dataset.crs is not None and not dataset.crs.to_epsg() == 4326:
            transformer = Transformer.from_crs(
                "EPSG:4326", dataset.crs, always_xy=True
            )
            x, y = transformer.transform(lon, lat)
        else:
            x, y = lon, lat

        row, col = dataset.index(x, y)

        if row < 0 or row >= dataset.height or col < 0 or col >= dataset.width:
            return None

        band = dataset.read(1, window=((row, row + 1), (col, col + 1)))
        value = band[0, 0]

        nodata = dataset.nodata
        if nodata is not None and value == nodata:
            return None

        try:
            import math

            if math.isnan(value):
                return None
        except TypeError:
            pass

        return float(value)