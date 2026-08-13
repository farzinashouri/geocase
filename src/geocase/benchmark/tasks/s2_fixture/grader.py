"""Oracle for s2_fixture (Plan 18 Phase 0): Sentinel-2 L2A product-spec facts.

The oracle is the published specification, not a corpus fixture, so this task
is free of the trap-2 problem (grading agreement with a tool's own output).

Graded facts, all lookup facts implied by the product name in the prompt:

* Four 10 m bands (B2/B3/B4/B8), ``uint16``, a UTM CRS, 10 m pixels — control.
  Every model should manage this; it isolates the trap from rasterio fluency.
* ``nodata == 0``, the L2A NODATA/saturation sentinel.
* ``BOA_ADD_OFFSET == -1000`` for processing baseline 04.00 (introduced for
  products taken from 2022-01-25). Sentinel-2 Products Specification Document,
  PSD 14.9, §Radiometric offset; ESA baseline 04.00 change notice. This is the
  headline number: obscure, checkable, and unrecoverable by reasoning.
* The quantification value 10000, carried with it.

**Encoding is not graded; the two numbers are.** The fact under test is that
BOA reflectance is ``(DN - 1000) / 10000``. A writer can record that faithfully
in more than one place, and the oracle must accept all of them or it measures
house style rather than knowledge:

* GDAL band metadata, whose convention is ``value = raw * scale + offset``. The
  self-consistent form is therefore ``scales == 1e-4`` with
  ``offsets == -0.1``: the offset is expressed in the *scaled* unit, so
  ``offset / scale == -1000``. Storing ``-1000`` next to a ``1e-4`` scale would
  be arithmetically wrong.
* Product tags ``BOA_ADD_OFFSET`` / ``QUANTIFICATION_VALUE``, which is where a
  real granule actually keeps them (``MTD_MSIL2A.xml``) — genuine L2A rasters
  carry no GDAL scale/offset at all.

Both are accepted. Grading one encoding as the only right answer is the
oracle-is-itself-wrong failure Plan 18 trap 1 names, and it was live here: the
first two clean-room trials wrote the physically correct band form and would
have been scored SILENT while knowing every fact.
"""

import tempfile
from pathlib import Path

# Baseline 04.00 radiometry, from the constants documented above.
BOA_ADD_OFFSET = -1000.0
QUANTIFICATION_VALUE = 10000.0
NODATA = 0.0

# UTM EPSG codes: northern 326xx, southern 327xx, zones 1-60.
_UTM_NORTH = range(32601, 32661)
_UTM_SOUTH = range(32701, 32761)


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * max(1.0, abs(b))


def _radiometry_in_bands(src) -> bool:
    """True if scale/offset together encode (DN - 1000) / 10000."""
    scales, offsets = src.scales, src.offsets
    if len(scales) != src.count or len(offsets) != src.count:
        return False
    if len({round(s, 12) for s in scales}) != 1:
        return False
    if len({round(o, 12) for o in offsets}) != 1:
        return False
    scale, offset = float(scales[0]), float(offsets[0])
    if scale == 0.0:
        return False
    if _close(scale, 1.0 / QUANTIFICATION_VALUE):
        # GDAL-consistent form: offset lives in the scaled (reflectance) unit.
        return _close(offset / scale, BOA_ADD_OFFSET)
    if _close(scale, QUANTIFICATION_VALUE):
        # The specification's own numbers, stored verbatim as a divisor.
        return _close(offset, BOA_ADD_OFFSET)
    return False


def _radiometry_in_tags(src) -> bool:
    tags = {k.upper(): v for k, v in src.tags().items()}

    def num(*keys):
        for k in keys:
            if k in tags:
                try:
                    return float(tags[k])
                except ValueError:
                    return None
        return None

    offset = num("BOA_ADD_OFFSET", "ADD_OFFSET", "RADIO_ADD_OFFSET")
    quant = num("QUANTIFICATION_VALUE", "BOA_QUANTIFICATION_VALUE")
    return (
        offset is not None
        and quant is not None
        and _close(offset, BOA_ADD_OFFSET)
        and _close(quant, QUANTIFICATION_VALUE)
    )


def build_checks(f):
    tmpdir = Path(tempfile.mkdtemp())
    produced = {}

    def _product():
        # Written once and read by both checks, so the control and the edge
        # grade the same bytes.
        if "path" not in produced:
            path = tmpdir / "s2_l2a.tif"
            f(str(path))
            produced["path"] = path
        return produced["path"]

    def opens_as_4band_utm_10m():
        import rasterio

        path = _product()
        with rasterio.open(path) as src:
            epsg = src.crs.to_epsg() if src.crs else None
            res = src.res
            ok = (
                src.count == 4
                and src.dtypes[0] == "uint16"
                and epsg is not None
                and (epsg in _UTM_NORTH or epsg in _UTM_SOUTH)
                and abs(res[0] - 10.0) < 1e-6
                and abs(res[1] - 10.0) < 1e-6
            )
            detail = f"count={src.count}, dtype={src.dtypes[0]}, epsg={epsg}, res={res}"
        return ok, detail

    def baseline_0400_radiometry():
        import rasterio

        path = _product()
        with rasterio.open(path) as src:
            nodata = src.nodata
            ok = (
                nodata is not None
                and abs(nodata - NODATA) < 1e-9
                and (_radiometry_in_bands(src) or _radiometry_in_tags(src))
            )
            radio_tags = {
                k: v
                for k, v in src.tags().items()
                if "OFFSET" in k.upper() or "QUANTIF" in k.upper()
            }
            detail = (
                f"nodata={nodata}, scales={src.scales}, offsets={src.offsets}, "
                f"tags={radio_tags}; "
                f"expected nodata=0 and BOA reflectance = (DN - 1000) / 10000 "
                f"recorded in band metadata or product tags (baseline 04.00)"
            )
        return ok, detail

    return [
        ("opens_as_4band_utm_10m", "control", opens_as_4band_utm_10m),
        ("baseline_0400_radiometry", "edge", baseline_0400_radiometry),
    ]
