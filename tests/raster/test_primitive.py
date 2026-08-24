"""The primitive's contract: escape hatch, size floor, and the nodata axes."""

from __future__ import annotations

import numpy as np
import pytest

from geocase.raster import DEFAULT_SIZE, MIN_USEFUL_SIZE, raster_fixture


def test_escape_hatch_needs_no_writer() -> None:
    """Array, transform and CRS are public; nothing is written, nothing imported."""
    f = raster_fixture(bands=4, dtype="uint16", size=(256, 256), crs=None, nodata=None)
    assert f.array.shape == (4, 256, 256)
    assert f.array.dtype == np.uint16
    assert f.crs_wkt is None
    assert len(f.transform) == 6
    assert f.profile["driver"] == "GTiff"


def test_default_size_clears_the_vit_floor() -> None:
    """Trap 9: below 224 px a fixture cannot exercise a ViT pipeline at all."""
    assert DEFAULT_SIZE >= MIN_USEFUL_SIZE
    assert raster_fixture().array.shape[1] >= MIN_USEFUL_SIZE


def test_size_accepts_rectangles() -> None:
    f = raster_fixture(size=(240, 300))
    assert f.height == 240 and f.width == 300


# ------------------------------------------------------------------- nodata


def test_nodata_border_frames_the_scene() -> None:
    f = raster_fixture(bands=2, size=64, nodata=0, nodata_border=8)
    assert (f.array[:, :8, :] == 0).all()
    assert (f.array[:, -8:, :] == 0).all()
    assert (f.array[:, :, :8] == 0).all()
    assert (f.array[:, :, -8:] == 0).all()
    # And the interior is untouched.
    assert (f.array[:, 8:-8, 8:-8] != 0).all()


def test_single_band_zero_hides_from_an_all_bands_heuristic() -> None:
    """The confirmed live bug: one band reading 0 in an otherwise valid pixel."""
    f = raster_fixture(bands=6, size=64, nodata=0, nodata_single_band=2)
    row, col = 32, 32
    assert f.array[2, row, col] == 0
    others = [b for b in range(6) if b != 2]
    assert (f.array[others, row, col] != 0).all()
    # An all-bands-zero mask does not flag it, which is exactly the failure.
    all_zero = (f.array == 0).all(axis=0)
    assert not all_zero[row, col]


def test_all_nodata_produces_degenerate_statistics() -> None:
    f = raster_fixture(bands=3, size=32, nodata=0, all_nodata=True)
    assert (f.array == 0).all()
    assert f.array.max() == 0  # a x/max(x) normaliser divides by zero here


def test_nodata_pixels_without_a_declared_sentinel_is_refused() -> None:
    """Silently writing nodata pixels with nodata=None would be its own trap."""
    with pytest.raises(ValueError, match="nodata=None"):
        raster_fixture(size=64, nodata_border=4)


def test_border_wider_than_the_scene_is_refused() -> None:
    with pytest.raises(ValueError, match="no valid pixels"):
        raster_fixture(size=16, nodata=0, nodata_border=8)


# ---------------------------------------------------------------------- CRS


def test_no_authority_crs_is_valid_wkt_without_an_epsg_code() -> None:
    f = raster_fixture(size=32, crs="no-authority")
    assert f.crs_wkt is not None
    assert "PROJCS" in f.crs_wkt
    assert 'AUTHORITY["EPSG"' not in f.crs_wkt


def test_bogus_crs_is_not_parseable() -> None:
    assert raster_fixture(size=32, crs="bogus").crs_wkt == "NOT_A_REAL_CRS"


def test_int_and_str_epsg_agree() -> None:
    assert (
        raster_fixture(size=32, crs=4326).crs_wkt
        == raster_fixture(size=32, crs="EPSG:4326").crs_wkt
    )


def test_unparseable_crs_is_refused() -> None:
    with pytest.raises(ValueError, match="neither WKT"):
        raster_fixture(size=32, crs="totally-not-a-crs")


# ---------------------------------------------------------------- transform


def test_rotated_transform_keeps_its_rotation_terms() -> None:
    f = raster_fixture(
        size=32, transform=(10.0, 2.0, 500_000.0, 2.0, -10.0, 4_500_000.0)
    )
    assert f.transform[1] != 0 and f.transform[3] != 0


def test_nonsquare_pixels_differ_by_axis() -> None:
    f = raster_fixture(size=32, resolution=(60.0, 30.0))
    assert abs(f.transform[0]) == 30.0
    assert abs(f.transform[4]) == 60.0


# ------------------------------------------------------------------- values


def test_values_are_deterministic() -> None:
    a = raster_fixture(bands=2, size=64)
    b = raster_fixture(bands=2, size=64)
    assert np.array_equal(a.array, b.array)


def test_bands_differ_from_each_other() -> None:
    """Band-ordering bugs must be visible in the pixel values."""
    f = raster_fixture(bands=4, size=64)
    assert not np.array_equal(f.array[0], f.array[1])


def test_supplied_values_are_used_and_shape_checked() -> None:
    data = np.full((2, 32, 32), 7, dtype="uint16")
    assert (raster_fixture(bands=2, size=32, values=data).array == 7).all()
    with pytest.raises(ValueError, match="expected"):
        raster_fixture(bands=3, size=32, values=data)
