"""The escape hatch must survive having no rasterio at all.

Rejector C already imports ``osgeo.gdal`` and will not add rasterio for a test
helper. If building a fixture requires rasterio anyway, the escape hatch is a
claim in a docstring rather than a property of the code — so it is tested in a
subprocess with rasterio genuinely unimportable.

A subprocess is necessary: rasterio is imported by other tests in this suite,
and once it is in ``sys.modules`` a blocked import still succeeds.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

PROGRAM = textwrap.dedent(
    """
    import sys, importlib.abc

    class BlockRasterio(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "rasterio" or fullname.startswith("rasterio."):
                raise ImportError("no rasterio in this environment")
            return None

    sys.meta_path.insert(0, BlockRasterio())

    from geocase.raster import raster_fixture
    from geocase.raster.axes import ambiguous_zero, nodata_border

    f = nodata_border(size=256, border=48)
    assert f.array.shape == (4, 256, 256)
    assert f.nodata == 0
    assert f.profile["driver"] == "GTiff"
    assert len(f.transform) == 6

    g = ambiguous_zero(size=64)
    assert g.array.shape[0] == 6

    h = raster_fixture(bands=2, size=(240, 300), crs=None)
    assert h.crs_wkt is None

    try:
        f.write("/tmp/geocase-should-not-exist.tif")
    except ImportError as exc:
        assert "geocase[write]" in str(exc), exc
    else:
        raise AssertionError("write() must fail loudly without rasterio")

    print("OK")
    """
)


def test_fixtures_build_without_rasterio() -> None:
    result = subprocess.run(
        [sys.executable, "-c", PROGRAM], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
