"""Oracle for sample_at, ported verbatim from the Step 0 grader."""

import math
import tempfile
from pathlib import Path

from geocase.benchmark._oracle_utils import make_utm_nodata_raster, utm_pixel_lonlat


def build_checks(f):
    tmp = Path(tempfile.mkdtemp()) / "utm_nodata.tif"
    make_utm_nodata_raster(tmp)

    def control():
        lon, lat = utm_pixel_lonlat(2, 2)
        got = f(str(tmp), lon, lat)
        ok = (
            got is not None
            and not (isinstance(got, float) and math.isnan(got))
            and abs(float(got) - 42.0) < 1e-6
        )
        return ok, f"got {got!r}, expected 42.0"

    def nodata():
        lon, lat = utm_pixel_lonlat(5, 5)
        got = f(str(tmp), lon, lat)
        ok = got is None or (isinstance(got, float) and math.isnan(got))
        return ok, f"got {got!r}, expected None (pixel is the -9999 nodata sentinel)"

    return [
        ("valid_pixel_utm_raster", "control", control),
        ("nodata_sentinel", "edge", nodata),
    ]
