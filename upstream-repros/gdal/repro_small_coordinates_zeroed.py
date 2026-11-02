"""GDAL writes coordinates with |v| in [1e-15, 1e-13) as 0 (WKT and GeoJSON).

Standalone: builds its own file, does not import geocase.

    python repro_small_coordinates_zeroed.py

Filed: https://github.com/OSGeo/gdal/issues/15317
Fixed: https://github.com/OSGeo/gdal/pull/15369 (merged 2026-10-15; both trims)

Both writers default to 15 decimal places. 1e-14 is 0.00000000000001, which is
14 decimal places, so it fits. GDAL's `intelliround` trims the formatted string
anyway and the value is written as 0, with no warning:

  * [1e-14, 1e-13): the "0000000000000" + one digit trim.
  * [1e-15, 1e-14): the other trim (five 0s followed by one digit).

Controls: 1e-16 needs 16 decimal places, one more than the default, so losing
it is documented behaviour. 1e-13 and 1e-12 must survive.
"""

import json
import os
import tempfile

from osgeo import gdal, ogr

gdal.UseExceptions()

IN_CLASS = [1e-15, 5e-15, 1e-14, 2e-14, 5e-14, 9.9e-14]
MUST_SURVIVE = [1e-13, 1e-12]
EXPECTED_LOSS = [1e-16]


def via_wkt(v):
    g = ogr.CreateGeometryFromWkt(f"POINT ({v!r} 1)")
    return float(g.ExportToWkt().split("(")[1].split()[0])


def via_geojson(v):
    d = tempfile.mkdtemp()
    src, dst = os.path.join(d, "in.geojson"), os.path.join(d, "out.geojson")
    with open(src, "w") as f:
        json.dump(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {"id": 1}, "geometry": {"type": "Point", "coordinates": [v, 1.0]}}
                ],
            },
            f,
        )
    gdal.VectorTranslate(dst, src, format="GeoJSON")
    with open(dst) as f:
        return json.load(f)["features"][0]["geometry"]["coordinates"][0]


def main():
    print("GDAL", gdal.__version__)
    print(f"{'input':>10}  {'WKT':>10}  {'GeoJSON':>10}  note")
    zeroed_in_class = False
    controls_ok = True
    for v in EXPECTED_LOSS + IN_CLASS + MUST_SURVIVE:
        w, j = via_wkt(v), via_geojson(v)
        if v in IN_CLASS:
            note = "in the affected class"
            if w == 0.0 or j == 0.0:
                zeroed_in_class = True
                note += "  <-- written as 0"
        elif v in MUST_SURVIVE:
            note = "control: must survive"
            controls_ok &= w != 0.0 and j != 0.0
        else:
            note = "control: 16 decimals, loss is documented"
        print(f"{v:>10g}  {w:>10g}  {j:>10g}  {note}")

    ok = zeroed_in_class and controls_ok
    print("\nRESULT:", "REPRODUCED" if ok else "did not reproduce")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
