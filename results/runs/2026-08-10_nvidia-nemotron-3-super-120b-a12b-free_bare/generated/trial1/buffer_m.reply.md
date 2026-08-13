```python
from shapely.geometry import BaseGeometry
from shapely.ops import transform
import pyproj

def buffer_m(geom: BaseGeometry, distance_m: float) -> BaseGeometry:
    """
    Buffer a geometry in EPSG:4326 by a given distance in metres.

    Parameters
    ----------
    geom : shapely geometry
        Input geometry with coordinates in longitude/latitude (EPSG:4326).
    distance_m : float
        Buffer distance in metres (positive for expansion, negative for shrinkage).

    Returns
    -------
    shapely geometry
        Buffered geometry, coordinates still in EPSG:4326.
    """
    if geom.is_empty:
        return geom

    # Centroid of the input geometry (in lon/lat) to centre the local projection
    centroid = geom.centroid
    lon0, lat0 = centroid.x, centroid.y

    # Source CRS: WGS84 (lon/lat)
    wgs84 = pyproj.CRS("EPSG:4326")
    # Target CRS: Azimuthal Equidistant centred at the centroid, units in metres
    aeqd_proj = (
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 "
        f"+datum=WGS84 +units=m +no_defs"
    )
    aeqd = pyproj.CRS(aeqd_proj)

    # Transformers: forward (lon/lat -> metres) and inverse (metres -> lon/lat)
    project = pyproj.Transformer.from_crs(wgs84, aeqd, always_xy=True).transform
    unproject = pyproj.Transformer.from_crs(aeqd, wgs84, always_xy=True).transform

    # Project to metres, buffer, then transform back
    geom_m = transform(project, geom)
    geom_buf_m = geom_m.buffer(distance_m)
    geom_buf = transform(unproject, geom_buf_m)

    return geom_buf
```