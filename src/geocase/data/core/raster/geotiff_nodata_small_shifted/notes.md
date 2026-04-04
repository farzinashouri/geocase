# GeoTIFF NoData Small Shifted

This fixture is a one-pixel eastward shift of `geotiff_nodata_small`. It keeps
resolution, CRS, band count, and nodata settings unchanged, but moves the
origin by one pixel so alignment logic can distinguish exact-equality checks
from true pixel-lattice compatibility.
