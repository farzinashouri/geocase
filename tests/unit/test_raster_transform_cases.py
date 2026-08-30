"""Gates for the transform-convention raster cases.

Two georeferencing conventions that every consumer silently assumes, and that
nothing in the catalog exercised before plan 34:

**Transform sign.** All 32 shipped rasters were built with ``from_origin``,
which always emits a negative ``e`` (north-up, row 0 northernmost). A consumer
that hardcodes that assumption passes the entire catalog and then mirrors a
bottom-up DEM vertically the first time it meets one in the wild. The failure
is silent -- the output is a plausible raster of the wrong place.

**Pixel anchor.** ``AREA_OR_POINT`` decides whether a transform's coordinates
name pixel corners or pixel centres, a half-pixel difference invisible to every
existing gate. GDAL omits the tag entirely for the area convention, so a
consumer reading it without a default sees ``None`` and guesses.

The pixel-anchor pair is deliberately a *pair*: two files with identical
transforms and identical arrays differing only in the tag. One file could not
show that the convention changes where a pixel actually sits.

See docs/plans/34-close-reviewed-catalog-gaps.md, Phase 2.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from geocase.catalog.content import check_raster_content
from geocase.catalog.registry import get_registry

rasterio = pytest.importorskip("rasterio")

REPO_ROOT = Path(__file__).resolve().parents[2]
RASTER_ROOT = REPO_ROOT / "src" / "geocase" / "data" / "core" / "raster"
_DIR = RASTER_ROOT / "transform_conventions"


def _metadata(case_id: str):  # type: ignore[no-untyped-def]
    return get_registry().get(case_id)


def _open(case_id: str):  # type: ignore[no-untyped-def]
    return rasterio.open(_DIR / f"{case_id}.tif")


# --- transform sign -------------------------------------------------------


def test_bottom_up_case_has_positive_y_resolution() -> None:
    """The whole point of the fixture: e > 0, which no other case has."""
    with _open("bottom_up_dem_small") as src:
        assert src.transform.e > 0


def test_bottom_up_case_reports_inverted_bounds() -> None:
    """rasterio does **not** normalise: ``bounds.bottom > bounds.top`` here.

    This was written expecting normalisation, and the fixture disproved it.
    ``BoundingBox`` is computed straight from the affine, so a positive ``e``
    puts the larger northing in ``bottom``. That is the trap in its most
    concrete form: any consumer doing ``bounds.top - bounds.bottom`` for a
    height, or feeding these bounds to a windowing helper, gets a negative
    number or an empty read -- and every other fixture in the catalog hides it.

    Pinned as observed behaviour rather than corrected, because it is precisely
    what the case exists to expose.
    """
    with _open("bottom_up_dem_small") as src:
        assert src.bounds.bottom > src.bounds.top
        assert src.bounds.left < src.bounds.right

    # The north-up control orders them the way nearly all code assumes.
    with _open("pixel_is_area_dem_small") as src:
        assert src.bounds.bottom < src.bounds.top


def test_north_up_sibling_still_has_negative_e() -> None:
    """The control. Without it the pair proves nothing about the sign."""
    with _open("pixel_is_area_dem_small") as src:
        assert src.transform.e < 0


def test_declared_transform_signs_match_the_file() -> None:
    """Mutating the declaration produces exactly one finding, named for it."""
    metadata = _metadata("bottom_up_dem_small")
    assert check_raster_content(_DIR, metadata) == []

    wrong = metadata.model_copy(deep=True)
    wrong.assertions.expected_transform_signs = ["negative_e"]
    errors = check_raster_content(_DIR, wrong)
    assert len(errors) == 1
    assert "expected_transform_signs" in errors[0]


# --- pixel anchor ---------------------------------------------------------


def test_pixel_is_point_case_declares_the_tag() -> None:
    with _open("pixel_is_point_dem_small") as src:
        assert src.tags()["AREA_OR_POINT"] == "Point"


def test_pixel_is_area_case_declares_the_tag_explicitly() -> None:
    """Written out rather than left to GDAL's default, so the pair is a true
    differential: both files make a statement, neither is silent."""
    with _open("pixel_is_area_dem_small") as src:
        assert src.tags()["AREA_OR_POINT"] == "Area"


def test_pixel_anchor_half_pixel_offset_is_observable() -> None:
    """The pair shares a transform and an array, and still disagrees on where
    the data sits -- by exactly half a pixel in each direction.

    This is what makes the pair worth two fixtures rather than one tagged file:
    it proves the convention has consequences a consumer can measure.
    """
    with _open("pixel_is_area_dem_small") as area:
        with _open("pixel_is_point_dem_small") as point:
            assert area.transform == point.transform
            assert (area.read(1) == point.read(1)).all()

            pixel_width = area.transform.a
            pixel_height = abs(area.transform.e)

            # Under "Area" the transform's origin is the pixel's upper-left
            # corner; under "Point" it names the pixel's centre. So the same
            # transform places the centre of pixel (0, 0) half a pixel apart.
            area_centre = area.xy(0, 0)
            point_centre = point.transform * (0, 0)

            assert area_centre[0] - point_centre[0] == pytest.approx(pixel_width / 2)
            assert abs(area_centre[1] - point_centre[1]) == pytest.approx(
                pixel_height / 2
            )


def test_declared_pixel_anchor_matches_the_file() -> None:
    metadata = _metadata("pixel_is_point_dem_small")
    assert check_raster_content(_DIR, metadata) == []

    wrong = metadata.model_copy(deep=True)
    wrong.assertions.expected_pixel_anchor = "area"
    errors = check_raster_content(_DIR, wrong)
    assert len(errors) == 1
    assert "expected_pixel_anchor" in errors[0]


# --- the backfilled declarations -----------------------------------------


@pytest.mark.parametrize(
    ("case_id", "expected"),
    [
        ("rotated_two_islands", ["negative_e", "rotated"]),
        ("nonsquare_diagonal_sparse", ["negative_e"]),
    ],
)
def test_backfilled_cases_declare_their_transform_signs(
    case_id: str, expected: list[str]
) -> None:
    """Two cases always had these properties; now they say so."""
    assert _metadata(case_id).assertions.expected_transform_signs == expected


# --- the scale factor hint, gated at last --------------------------------


def test_expected_scale_factor_is_now_enforced() -> None:
    """``expected_scale_factor`` was declared by three cases and read by
    nothing -- a declared-but-ungated hint, which plan 27 section 1.2 forbids.
    """
    metadata = _metadata("ndvi_scaled_int16_small")
    case_dir = RASTER_ROOT / "ndvi_scaled_int16_small"
    assert check_raster_content(case_dir, metadata) == []

    wrong = metadata.model_copy(deep=True)
    wrong.assertions.expected_scale_factor = 0.5
    errors = check_raster_content(case_dir, wrong)
    assert len(errors) == 1
    assert "expected_scale_factor" in errors[0]
