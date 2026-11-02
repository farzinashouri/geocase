"""GPKG spatial filter + Arrow stream returns the NULL-geometry row (2 vs 3).

Standalone: builds its own file, does not import geocase.

    python repro_gpkg_arrow_spatial_filter_null_geometry.py

Filed: https://github.com/OSGeo/gdal/issues/15465 (Plan 43 queue #10).
The cause is in GDAL, not pyogrio: the extra row is already in the raw Arrow
stream (`OGR_L_GetArrowStream`) after `OGR_L_SetSpatialFilterRect`, while the
ordinary feature iterator honours the filter. It contradicts pyogrio's
`known_issues.md`, which is why it was drafted against pyogrio.

A GPKG layer with two points, one NULL geometry (v=3) and one EMPTY geometry
(v=4, `POINT EMPTY`), read under a bbox that covers both points:

    read_dataframe(path, bbox=bbox)                  -> v = 1, 2
    read_dataframe(path, bbox=bbox, use_arrow=True)  -> v = 1, 2, 3

The OGRLayer docs say "features with null or empty geometries will never be
considered as matching a spatial filter". The EMPTY row is already excluded on
every path; only the NULL row leaks. The script checks both, so a fix that
drops NULL must not start returning EMPTY.

Controls: GeoJSON gives 1, 2 on every path; GDAL's own feature iterator gives 1, 2.
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
EXPECTED = [1, 2]
NULL_ROW, EMPTY_ROW = 3, 4


def rows(path):
    """The `v` values each read path returns under BBOX, sorted."""
    out = {
        "numpy": read_dataframe(path, bbox=BBOX)["v"],
        "arrow": read_dataframe(path, bbox=BBOX, use_arrow=True)["v"],
        "mask+arrow": read_dataframe(path, mask=box(*BBOX), use_arrow=True)["v"],
    }
    with open_arrow(path, bbox=BBOX, use_pyarrow=True) as (_meta, reader):
        out["raw stream"] = reader.read_all().column("v").to_pylist()
    ds = ogr.Open(str(path))
    lyr = ds.GetLayer(0)
    lyr.SetSpatialFilterRect(*BBOX)
    out["OGR iterator"] = [f["v"] for f in lyr]
    return {k: sorted(int(x) for x in v) for k, v in out.items()}


def main():
    print("pyogrio", pyogrio.__version__, "| GDAL", pyogrio.__gdal_version_string__)
    gdf = gpd.GeoDataFrame(
        {"v": [1, 2, NULL_ROW, EMPTY_ROW]},
        geometry=[Point(10, 50), Point(11, 51), None, Point()],
        crs="EPSG:4326",
    )
    gpkg, geojson = TMP / "t.gpkg", TMP / "t.geojson"
    write_dataframe(gdf, gpkg)
    write_dataframe(gdf, geojson)

    print("bbox =", BBOX, "covers the two points (v=1, 2);")
    print(f"v={NULL_ROW} has a NULL geometry, v={EMPTY_ROW} has POINT EMPTY\n")
    g, j = rows(gpkg), rows(geojson)
    print(f"{'path':13s} {'GPKG':14s} {'GeoJSON [control]'}")
    for name in g:
        print(f"{name:13s} {g[name]!s:14s} {j[name]}")

    leaked = [n for n, v in g.items() if NULL_ROW in v]
    empty_leaked = [n for n, v in g.items() if EMPTY_ROW in v]
    print("\nNULL row returned by: ", ", ".join(leaked) or "none")
    print("EMPTY row returned by:", ", ".join(empty_leaked) or "none")

    ok = (
        g["numpy"] == g["OGR iterator"] == EXPECTED
        and g["arrow"] == g["raw stream"] == EXPECTED + [NULL_ROW]
        and all(v == EXPECTED for v in j.values())
    )
    print("\nRESULT:", "REPRODUCED" if ok else "did not reproduce")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
