"""Machine-check ``geocase.synth.spec`` against real product metadata.

Plan 18's mechanism 2: a hand-written "spec-accurate" constant is only worth
depending on if it is verified against the actual authority, not the author's
reading of a PDF. The witnesses under ``tests/synth/data/`` are genuine ESA
product metadata (see PROVENANCE.md); each test asserts that a constant in
``spec.py`` matches what a real granule declares. A disagreement here means
the corpus would ship the defect the project is named after.
"""

from pathlib import Path
from xml.etree import ElementTree

import pytest

from geocase.synth import spec

DATA = Path(__file__).parent / "data"


@pytest.fixture(scope="module")
def mtd():
    return ElementTree.parse(DATA / "MTD_MSIL2A_N0400.xml").getroot()


@pytest.fixture(scope="module")
def s1_annotation():
    return ElementTree.parse(DATA / "s1a-iw-grd-vv-annotation.xml").getroot()


# ------------------------------------------------------------------- S2 L2A


def test_witness_is_the_offset_baseline(mtd):
    baseline = next(mtd.iter("PROCESSING_BASELINE")).text
    assert baseline == spec.S2_OFFSET_BASELINE


def test_boa_quantification_value(mtd):
    value = next(mtd.iter("BOA_QUANTIFICATION_VALUE")).text
    assert int(value) == spec.S2_BOA_QUANTIFICATION_VALUE


def test_boa_add_offset_all_13_bands(mtd):
    offsets = [int(e.text) for e in mtd.iter("BOA_ADD_OFFSET")]
    assert len(offsets) == 13
    assert set(offsets) == {spec.S2_BOA_ADD_OFFSET}


def test_special_values_nodata_and_saturated(mtd):
    declared = {
        e.find("SPECIAL_VALUE_TEXT").text: int(e.find("SPECIAL_VALUE_INDEX").text)
        for e in mtd.iter("Special_Values")
    }
    assert declared == {
        "NODATA": spec.S2_NODATA,
        "SATURATED": spec.S2_SATURATED,
    }


def test_band_resolutions_match_spectral_information(mtd):
    declared = {
        e.attrib["physicalBand"]: int(e.find("RESOLUTION").text)
        for e in mtd.iter("Spectral_Information")
    }
    assert declared == spec.S2_BAND_RESOLUTION_M


def test_10m_band_set_agrees_with_witness(mtd):
    declared_10m = {
        e.attrib["physicalBand"]
        for e in mtd.iter("Spectral_Information")
        if int(e.find("RESOLUTION").text) == 10
    }
    # spec stores the zero-padded filename form; the witness the bare form.
    ours = {f"B{name.lstrip('B').lstrip('0')}" for name in spec.S2_BANDS_10M}
    assert ours == declared_10m


def test_scl_classes_match_scene_classification_list(mtd):
    declared = {
        int(e.find("SCENE_CLASSIFICATION_INDEX").text): e.find(
            "SCENE_CLASSIFICATION_TEXT"
        ).text
        for e in mtd.iter("Scene_Classification_ID")
    }
    assert declared == spec.S2_SCL_CLASSES


# ------------------------------------------------------------------- S1 GRD


def test_grd_product_type(s1_annotation):
    assert s1_annotation.find("adsHeader/productType").text == spec.S1_GRD_PRODUCT_TYPE


def test_grd_pixels_are_detected_amplitude_not_db(s1_annotation):
    assert next(s1_annotation.iter("pixelValue")).text == spec.S1_GRD_PIXEL_VALUE


def test_grd_output_pixels_are_uint16(s1_annotation):
    assert next(s1_annotation.iter("outputPixels")).text == spec.S1_GRD_OUTPUT_PIXELS


def test_iw_grdh_pixel_spacing(s1_annotation):
    rng = float(next(s1_annotation.iter("rangePixelSpacing")).text)
    azi = float(next(s1_annotation.iter("azimuthPixelSpacing")).text)
    assert rng == azi == spec.S1_IW_GRDH_PIXEL_SPACING_M


def test_witness_polarisation_is_in_dual_pol_set(s1_annotation):
    assert s1_annotation.find("adsHeader/polarisation").text in spec.S1_DUAL_POL
