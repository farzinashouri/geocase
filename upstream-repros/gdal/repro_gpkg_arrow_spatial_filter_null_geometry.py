"""GPKG spatial filter + Arrow stream returns the NULL-geometry row (2 vs 3).

Standalone: builds its own file, does not import geocase.

    python repro_gpkg_arrow_spatial_filter_null_geometry.py

Filed: https://github.com/OSGeo/gdal/issues/15465 (Plan 43 queue #10).
The cause is in GDAL, not pyogrio: the extra row is already in the raw Arrow
stream (`OGR_L_GetArrowStream`) after `OGR_L_SetSpatialFilterRect`, while the
ordinary feature iterator honours the filter. It contradicts pyogrio's
`known_issues.md`, which is why it was drafted against pyogrio.

A GPKG layer with two points and one NULL geometry, read under a bbox that
covers both points:

    read_dataframe(path, bbox=bbox)                  -> 2 rows
    read_dataframe(path, bbox=bbox, use_arrow=True)  -> 3 rows

Controls: GeoJSON gives 2 on both paths; GDAL's own feature iterator gives 2.
"""

import tempfile
import warnings
from pathlib import Path

import geopandas as gpd
import pyogrio
from osgeo import gdal, ogr
from pyogrio import open_arrow, read_dataframe, write_dataframe
from shapely.geometry import Point, box

warnings.filterwarnings("ignore")
gdal.UseExceptions()
TMP = Path(tempfile.mkdtemp(prefix="pyogrio-bbox-"))
BBOX = (9.9, 49.9, 11.1, 51.1)


def counts(path):
    numpy_rows = len(read_dataframe(path, bbox=BBOX))
    arrow_rows = len(read_dataframe(path, bbox=BBOX, use_arrow=True))
    mask_arrow = len(read_dataframe(path, mask=box(*BBOX), use_arrow=True))
    with open_arrow(path, bbox=BBOX, use_pyarrow=True) as (_meta, reader):
        raw_stream = reader.read_all().num_rows
    ds = ogr.Open(str(path))
    lyr = ds.GetLayer(0)
    lyr.SetSpatialFilterRect(*BBOX)
    iterator = sum(1 for _ in lyr)
    return numpy_rows, arrow_rows, mask_arrow, raw_stream, iterator


def main():
    print("pyogrio", pyogrio.__version__, "| GDAL", pyogrio.__gdal_version_string__)
    gdf = gpd.GeoDataFrame({"v": [1, 2, 3]}, geometry=[Point(10, 50), Point(11, 51), None], crs="EPSG:4326")
    gpkg, geojson = TMP / "t.gpkg", TMP / "t.geojson"
    write_dataframe(gdf, gpkg)
    write_dataframe(gdf, geojson)

    print("bbox =", BBOX, "covers the two points; the third row has no geometry\n")
    print(f"{'file':8s} {'numpy':>6s} {'arrow':>6s} {'mask+arrow':>11s} {'raw stream':>11s} {'OGR iterator':>13s}")
    g = counts(gpkg)
    j = counts(geojson)
    print(f"{'GPKG':8s} {g[0]:>6d} {g[1]:>6d} {g[2]:>11d} {g[3]:>11d} {g[4]:>13d}")
    print(f"{'GeoJSON':8s} {j[0]:>6d} {j[1]:>6d} {j[2]:>11d} {j[3]:>11d} {j[4]:>13d}   [control]")

    ok = g[0] == 2 and g[1] == 3 and g[3] == 3 and g[4] == 2 and j[0] == j[1] == 2
    print("\nRESULT:", "REPRODUCED" if ok else "did not reproduce")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
