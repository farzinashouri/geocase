"""Product-specification constants for synthetic EO fixtures (Plan 18 Phase 1).

Every constant cites its authority twice, per the plan's two mechanisms:

1. The specification document, inline at the constant.
2. A real product's metadata vendored under ``tests/synth/data/``, against
   which ``tests/synth/test_spec_fidelity.py`` machine-checks each value. A
   constant in this file that the witness does not corroborate is a test
   failure, not an opinion.

Witnesses (Copernicus Sentinel data — free and open license, redistributable):

* ``MTD_MSIL2A_N0400.xml`` — genuine ESA L2A user-product metadata from
  ``S2B_MSIL2A_20220413T150759_N0400_R025_T33XWJ_20220414T082126.SAFE``,
  processing baseline 04.00.
* ``s1a-iw-grd-vv-annotation.xml`` — genuine S1A IW GRDH product annotation
  from ``S1A_IW_GRDH_1SDV_20210809T173953_..._6FF8.SAFE``.
"""

from __future__ import annotations

# --------------------------------------------------------------------- S2 L2A
# Sentinel-2 Products Specification Document (S2-PDGS-TAS-DI-PSD, PSD 14.x),
# L2A product; radiometric offset introduced with processing baseline 04.00
# (products acquired from 2022-01-25).

#: First processing baseline that carries the BOA_ADD_OFFSET. Earlier
#: baselines encode reflectance as DN / 10000 with no offset (plan trap 3).
#: Witness: <PROCESSING_BASELINE>04.00</PROCESSING_BASELINE>.
S2_OFFSET_BASELINE = "04.00"

#: Witness: <BOA_QUANTIFICATION_VALUE unit="none">10000</...>.
S2_BOA_QUANTIFICATION_VALUE = 10000

#: Witness: <BOA_ADD_OFFSET band_id="i">-1000</...> for all 13 bands.
#: BOA reflectance = (DN + BOA_ADD_OFFSET) / QUANTIFICATION_VALUE.
S2_BOA_ADD_OFFSET = -1000

#: Witness: Special_Values NODATA=0, SATURATED=65535.
S2_NODATA = 0
S2_SATURATED = 65535

#: Image sample format: 15-bit unsigned integers in a 16-bit container (PSD);
#: written as uint16.
S2_DTYPE = "uint16"

#: Native resolution per physical band, metres. Witness:
#: Spectral_Information physicalBand -> RESOLUTION (13 entries; the witness
#: spells bands without zero padding: B1, B2, ..., B8A, ..., B12).
S2_BAND_RESOLUTION_M: dict[str, int] = {
    "B1": 60,
    "B2": 10,
    "B3": 10,
    "B4": 10,
    "B5": 20,
    "B6": 20,
    "B7": 20,
    "B8": 10,
    "B8A": 20,
    "B9": 60,
    "B10": 60,  # cirrus; present in metadata, no L2A surface-reflectance image
    "B11": 20,
    "B12": 20,
}

#: The four native-10 m bands, in filename (zero-padded) form.
S2_BANDS_10M = ("B02", "B03", "B04", "B08")

#: Scene Classification (SCL) classes, 20 m. Witness:
#: Scene_Classification_List, indices 0-11.
S2_SCL_CLASSES: dict[int, str] = {
    0: "SC_NODATA",
    1: "SC_SATURATED_DEFECTIVE",
    2: "SC_DARK_FEATURE_SHADOW",
    3: "SC_CLOUD_SHADOW",
    4: "SC_VEGETATION",
    5: "SC_NOT_VEGETATED",
    6: "SC_WATER",
    7: "SC_UNCLASSIFIED",
    8: "SC_CLOUD_MEDIUM_PROBA",
    9: "SC_CLOUD_HIGH_PROBA",
    10: "SC_THIN_CIRRUS",
    11: "SC_SNOW_ICE",
}
S2_SCL_RESOLUTION_M = 20

# -------------------------------------------------------------------- S1 GRD
# Sentinel-1 Product Specification (S1-RS-MDA-52-7441); IW GRDH.

#: Witness: adsHeader <productType>GRD</productType>.
S1_GRD_PRODUCT_TYPE = "GRD"

#: GRD pixels are detected amplitude — NOT dB, NOT calibrated backscatter.
#: Witness: imageInformation <pixelValue>Detected</pixelValue>. Calibrated
#: sigma0 (linear or dB) is a derived product obtained via the calibration
#: LUT, never the stored DN.
S1_GRD_PIXEL_VALUE = "Detected"

#: Witness: <outputPixels>16 bit Unsigned Integer</outputPixels>.
S1_GRD_OUTPUT_PIXELS = "16 bit Unsigned Integer"
S1_GRD_DTYPE = "uint16"

#: IW GRDH (high resolution) pixel spacing, metres. Witness:
#: <rangePixelSpacing>1.0e+01</...>, <azimuthPixelSpacing>1.0e+01</...>.
S1_IW_GRDH_PIXEL_SPACING_M = 10.0

#: Polarisations of an IW dual-pol (1SDV) product.
S1_DUAL_POL = ("VV", "VH")


def parse_baseline(baseline: str) -> tuple[int, int]:
    """Parse an ``NN.NN`` processing-baseline string into a comparable tuple."""
    major, minor = baseline.split(".")
    return int(major), int(minor)


def baseline_has_offset(baseline: str) -> bool:
    """True if *baseline* products carry the BOA_ADD_OFFSET (>= 04.00)."""
    return parse_baseline(baseline) >= parse_baseline(S2_OFFSET_BASELINE)
