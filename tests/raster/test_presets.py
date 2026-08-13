"""Presets: spec fidelity, the size floor, and the escape hatch."""

from __future__ import annotations

import numpy as np
import pytest
from geospatial_spec.sentinel2 import boa_offset, quantification, to_reflectance

from geocase.raster.presets import DEFAULT_SIZE, sentinel1_grd, sentinel2_l2a

rasterio = pytest.importorskip("rasterio")


class TestSentinel2Radiometry:
    def test_default_size_clears_the_vit_floor(self) -> None:
        """Trap 9: the one confirmed adopter cannot use a 32 px fixture."""
        assert DEFAULT_SIZE >= 224
        assert sentinel2_l2a().array.shape[1] >= 224

    def test_dn_round_trips_to_reflectance_for_baseline_0400(self) -> None:
        spec = sentinel2_l2a(size=64, baseline="04.00")
        refl = to_reflectance(spec.array.astype("float64"), baseline="04.00")
        valid = refl[refl > 0]
        assert valid.min() >= 0.0 and valid.max() <= 1.0

    def test_earlier_baseline_encodes_different_pixels(self) -> None:
        """The whole point of the guard: the encoding differs by baseline."""
        post = sentinel2_l2a(size=64, baseline="04.00").array
        pre = sentinel2_l2a(size=64, baseline="03.01").array
        assert not np.array_equal(post, pre)
        # And the difference is exactly the offset.
        assert int(
            (post.astype("int32") - pre.astype("int32")).ravel()[0]
        ) == -boa_offset(baseline="04.00")

    def test_the_same_reflectance_is_recovered_from_both_baselines(self) -> None:
        post = to_reflectance(
            sentinel2_l2a(size=64, baseline="04.00").array.astype("float64"),
            baseline="04.00",
        )
        pre = to_reflectance(
            sentinel2_l2a(size=64, baseline="03.01").array.astype("float64"),
            baseline="03.01",
        )
        assert np.allclose(post, pre)

    def test_tags_declare_the_baseline_and_offset(self) -> None:
        spec = sentinel2_l2a(size=64, baseline="04.00")
        assert spec.tags["PROCESSING_BASELINE"] == "04.00"
        assert spec.tags["BOA_ADD_OFFSET"] == str(boa_offset(baseline="04.00"))
        assert spec.tags["QUANTIFICATION_VALUE"] == str(
            quantification(baseline="04.00")
        )

    def test_pre_offset_baseline_declares_no_offset_tag(self) -> None:
        assert "BOA_ADD_OFFSET" not in sentinel2_l2a(size=64, baseline="03.01").tags

    def test_scales_and_offsets_are_self_consistent(self) -> None:
        spec = sentinel2_l2a(size=64, baseline="04.00")
        quant = float(quantification(baseline="04.00"))
        assert spec.scales == pytest.approx((1.0 / quant,) * 4)
        assert spec.offsets == pytest.approx(
            (boa_offset(baseline="04.00") / quant,) * 4
        )

    def test_20m_bands_carry_upsampled_structure(self) -> None:
        """A 20 m band on the 10 m grid must look block-replicated."""
        spec = sentinel2_l2a(size=64, bands=("B05",))
        band = spec.array[0]
        assert np.array_equal(band[0::2, 0::2], band[1::2, 1::2])


class TestEscapeHatch:
    def test_no_path_returns_the_spec_without_writing(self) -> None:
        spec = sentinel2_l2a(size=64)
        assert hasattr(spec, "array") and hasattr(spec, "transform")

    def test_path_writes_a_readable_geotiff(self, tmp_path) -> None:
        out = sentinel2_l2a(tmp_path / "s2.tif", size=64, baseline="04.00")
        with rasterio.open(out) as src:
            assert src.count == 4
            assert src.nodata == 0
            assert src.tags()["PROCESSING_BASELINE"] == "04.00"
            assert src.descriptions == ("B02", "B03", "B04", "B08")

    def test_scl_sidecar_is_written_next_to_the_stack(self, tmp_path) -> None:
        out = sentinel2_l2a(tmp_path / "s2.tif", size=64, scl=True)
        sidecar = out.with_name(f"{out.stem}_SCL.tif")
        assert sidecar.exists()
        with rasterio.open(sidecar) as src:
            assert src.dtypes[0] == "uint8"
            assert src.res == (20.0, 20.0)

    def test_scl_without_a_path_is_refused(self) -> None:
        with pytest.raises(ValueError, match="requires path="):
            sentinel2_l2a(size=64, scl=True)


class TestSentinel1:
    def test_amplitude_is_uint16_not_db(self) -> None:
        spec = sentinel1_grd(size=64)
        assert spec.array.dtype == np.uint16
        assert (spec.array >= 0).all()
        assert spec.tags["PIXEL_VALUE"] == "Detected"

    def test_calibrated_derivatives_are_float_and_labelled(self) -> None:
        for units in ("linear", "dB"):
            spec = sentinel1_grd(size=64, units=units)
            assert spec.array.dtype == np.float32
            assert spec.tags["UNITS"] == units
            assert spec.nodata is None

    def test_db_values_are_negative_as_real_backscatter_is(self) -> None:
        assert sentinel1_grd(size=64, units="dB").array.max() < 5.0

    def test_border_noise_zeroes_the_leading_columns_only(self) -> None:
        """Range-edge artifact, not a frame: it is not present on all sides."""
        spec = sentinel1_grd(size=64, border_noise=4)
        assert (spec.array[:, :, :4] == 0).all()
        assert (spec.array[:, :, 4:] != 0).all()

    def test_unsupported_arguments_are_refused(self) -> None:
        with pytest.raises(ValueError):
            sentinel1_grd(size=32, pol="HH")
        with pytest.raises(ValueError):
            sentinel1_grd(size=32, units="sigma0")
