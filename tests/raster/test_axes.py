"""Each axis must actually expose the bug it is named for.

A fixture library whose fixtures do not reproduce the failure is decoration. So
these tests do not merely check the fixture's shape — where it is cheap, they
run the *buggy* code and assert it produces the wrong answer, then run the
correct code and assert it does not.
"""

from __future__ import annotations

import numpy as np
import pytest

from geocase.raster import axes


class TestNodataBorder:
    """3/3 evidence, confirmed live in the adopter's repository."""

    def test_border_is_nodata_and_interior_is_not(self) -> None:
        f = axes.nodata_border(size=256, border=48)
        assert (f.array[:, :48, :] == 0).all()
        assert (f.array[:, 48:-48, 48:-48] != 0).all()

    def test_naive_bilinear_smears_nodata_into_valid_pixels(self) -> None:
        """The actual bug: interpolating without declaring nodata."""
        f = axes.nodata_border(size=64, bands=1, border=8)
        band = f.array[0].astype("float64")

        # A 3x3 box filter stands in for any interpolating kernel: it mixes a
        # pixel with its neighbours, exactly as bilinear resampling does.
        naive = _box_blur(band)

        # The first valid row after the border is contaminated: its value has
        # been pulled toward 0 by the nodata pixels above it.
        first_valid = band[8, 8:-8]
        smeared = naive[8, 8:-8]
        assert (smeared < first_valid).all(), (
            "the fixture failed to expose the smearing bug"
        )

        # Masking nodata before interpolating leaves valid pixels alone.
        masked = _box_blur_masked(band, nodata=0)
        assert np.allclose(masked[8, 8:-8], first_valid, rtol=0.5)

    def test_it_carries_its_own_expectation(self) -> None:
        f = axes.nodata_border()
        assert f.tags["GEOCASE_AXIS"] == "nodata_border"
        assert "src_nodata" in f.tags["GEOCASE_EXPECTS"]


class TestAmbiguousZero:
    """3/3 evidence. 0 is both the sentinel and a valid dark pixel."""

    def test_all_bands_zero_heuristic_misses_the_single_band_zero(self) -> None:
        f = axes.ambiguous_zero(size=64, bands=6, band=2)
        row, col = 32, 32

        all_bands_zero = (f.array == 0).all(axis=0)
        assert not all_bands_zero[row, col], (
            "heuristic should miss it — that is the bug"
        )

        per_band = (f.array == 0).any(axis=0)
        assert per_band[row, col], "per-band checking must catch it"

    def test_the_missed_pixel_becomes_a_plausible_outlier(self) -> None:
        """Why it matters: it normalises to a believable value, not an obvious one."""
        f = axes.ambiguous_zero(size=64, bands=6, band=2)
        band = f.array[2].astype("float64")
        z = (band[32, 32] - band.mean()) / band.std()
        assert -3 < z < 0, f"expected a plausible negative outlier, got z={z}"


class TestAllNodata:
    def test_max_is_zero_so_a_normaliser_divides_by_zero(self) -> None:
        f = axes.all_nodata(size=32)
        band = f.array[0].astype("float64")
        with np.errstate(invalid="ignore", divide="ignore"):
            normalised = band / band.max()
        assert np.isnan(normalised).all(), "the degenerate case must produce NaN"


class TestMetadataAxes:
    def test_missing_authority_has_no_epsg_code(self) -> None:
        f = axes.missing_crs_authority()
        assert f.crs_wkt and 'AUTHORITY["EPSG"' not in f.crs_wkt

    def test_epsg_str_vs_int_is_the_identity_trap(self) -> None:
        axes.epsg_str_vs_int()  # fixture builds
        assert 4326 != "EPSG:4326"  # noqa: PLR0133 - the point of the axis
        from geospatial_spec.common import epsg_equivalent

        assert epsg_equivalent(4326, "EPSG:4326")

    def test_band_count_mismatch_raises_on_hardcoded_reordering(self) -> None:
        f = axes.band_count_mismatch(bands=3)
        with pytest.raises(IndexError):
            _ = f.array[[3, 2, 1]]


class TestGeotransformAxes:
    def test_rotated_transform_breaks_the_naive_inverse(self) -> None:
        f = axes.rotated_transform(size=64, rotation=0.1)
        a, b, c, d, e, _ = f.transform
        col, row = 20, 30
        x = a * col + b * row + c
        naive_col = (x - c) / a  # drops the b term
        assert abs(naive_col - col) > 1, "rotation must break the naive inverse"

    def test_nonsquare_pixel_area_is_wrong_by_the_axis_ratio(self) -> None:
        f = axes.nonsquare_pixels(size=64, resolution=(60.0, 30.0))
        res_x, res_y = abs(f.transform[0]), abs(f.transform[4])
        naive_area = res_x * res_x
        true_area = res_x * res_y
        assert true_area == pytest.approx(naive_area * 2)


def _box_blur(band: np.ndarray) -> np.ndarray:
    """3x3 mean — a stand-in for any interpolating resampler."""
    padded = np.pad(band, 1, mode="edge")
    out = np.zeros_like(band)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            out += padded[
                1 + dy : 1 + dy + band.shape[0], 1 + dx : 1 + dx + band.shape[1]
            ]
    return out / 9.0


def _box_blur_masked(band: np.ndarray, *, nodata: float) -> np.ndarray:
    """The same filter, with nodata excluded from the average."""
    valid = (band != nodata).astype("float64")
    values = np.where(valid.astype(bool), band, 0.0)
    padded_v = np.pad(values, 1, mode="edge")
    padded_m = np.pad(valid, 1, mode="edge")
    total = np.zeros_like(band)
    weight = np.zeros_like(band)
    h, w = band.shape
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            total += padded_v[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
            weight += padded_m[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
    return np.divide(total, weight, out=np.zeros_like(total), where=weight > 0)
