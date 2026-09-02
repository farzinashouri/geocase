"""Gate the raster conventions that external differential runs proved pay.

Plan 37 §1.3 and Plan 38 §1.2. Three runs now agree on the same shape: the
defects come from cases curated around a *named convention* — a rotated affine,
a bottom-up affine, a declared scale/offset, a colormap, an unwrapped
antimeridian — and not from format baselines. Round 2 (2026-08-31) found both
transform conventions again, in libraries round 1 never touched, and
``bottom_up_dem_small`` found two defects on its own.

The risk this file guards against is not a consumer regressing. It is *geocase*
regressing: a fixture regeneration that quietly normalises a rotated affine to
north-up, drops a scale onto 1.0, or wraps a longitude back under 180 would
delete the corpus's only coverage of the axis, and every downstream test would
keep passing while testing nothing. So each property is read from the real bytes
rather than from ``case.yaml`` — the declaration is what a regeneration would
update, and it is the bytes that have to keep the property.
"""

from __future__ import annotations

import pytest

import geocase

rasterio = pytest.importorskip("rasterio")


def open_case(case_id: str):
    """Open a bundled raster case's primary file with rasterio."""
    return rasterio.open(geocase.load_case(case_id).primary_path)


class TestTheTransformConventions:
    """The two affine conventions that produced the most severe findings."""

    def test_rotated_two_islands_really_has_a_rotated_affine(self):
        """Test the skew terms survive regeneration, not just the declaration."""
        with open_case("rotated_two_islands") as dataset:
            transform = dataset.transform

        assert (transform.b, transform.d) != (0.0, 0.0), (
            "rotated_two_islands with a north-up affine is a different case; "
            "it is the skew that caught titiler and rio-tiler"
        )

    def test_bottom_up_dem_small_really_has_a_positive_e(self):
        """Test the bottom-up row order survives regeneration."""
        with open_case("bottom_up_dem_small") as dataset:
            assert dataset.transform.e > 0, (
                "a negative e makes this a north-up DEM and deletes the "
                "convention that caught titiler and rio-stac"
            )


class TestTheScaleOffsetAxis:
    """The axis odc-stac drops and stackstac applies — a 10 000x difference."""

    def test_ndvi_scaled_int16_small_declares_a_non_identity_scale(self):
        """Test the case still carries a scale a consumer can fail to apply."""
        with open_case("ndvi_scaled_int16_small") as dataset:
            assert dataset.scales != (1.0,), (
                "a scale of 1.0 makes applying it and ignoring it indistinguishable"
            )

    def test_multispectral_s2_like_small_declares_a_non_zero_offset(self):
        """Test the offset half of the axis is covered too."""
        with open_case("multispectral_s2_like_small") as dataset:
            offsets = set(dataset.offsets)

        assert offsets != {0.0}, (
            "the BOA offset is the half of the axis that scale alone misses"
        )


class TestTheCategoricalColormaps:
    """titiler returns these cases' colours instead of their class codes."""

    @pytest.mark.parametrize(
        "case_id", ["landcover_small", "landcover_ambiguous_zero_small"]
    )
    def test_the_landcover_cases_carry_a_colormap(self, case_id: str):
        """Test the colormap that makes the class codes losable is present."""
        with open_case(case_id) as dataset:
            colormap = dataset.colormap(1)

        assert colormap, (
            f"{case_id} without a colormap cannot show a consumer returning "
            "colours in place of categorical data"
        )


class TestTheUnwrappedAntimeridian:
    """The convention titiler's ``bounds_to_geometry`` does not handle."""

    def test_optical_dateline_small_stays_unwrapped(self):
        """Test the eastern bound stays beyond 180 rather than wrapping."""
        with open_case("optical_dateline_small") as dataset:
            bounds = dataset.bounds

        assert bounds.right > 180, (
            "wrapping this case to the minx > maxx convention moves it onto "
            "the code path titiler already handles, and the finding is lost"
        )


class TestTheWidenedTransformAxis:
    """Plan 37 Phase 3 — the axis that paid, sampled at more than one point.

    Two cases produced two defects, and both were the *only* case carrying
    their convention. That is a sample size of one per axis, so these three
    cases sample it properly: both conventions at once, a rotation large
    enough that the error is unmistakable, and a rotated source shipped beside
    its correctly-warped reference so a consumer can be checked against the
    right answer rather than only against itself.
    """

    def test_rotated_bottom_up_small_carries_both_conventions(self):
        """Test one case combines rotation with a bottom-up affine.

        rio-tiler's two defects have adjacent root causes and a single
        ``WarpedVRT`` guard fixes both, so a case carrying both is what
        distinguishes a complete fix from a partial one.
        """
        with open_case("rotated_bottom_up_small") as dataset:
            transform = dataset.transform

        assert (transform.b, transform.d) != (0.0, 0.0), "rotation term lost"
        assert transform.e > 0, "bottom-up term lost"

    def test_rotated_steep_small_misplaces_pixels_by_several_cells(self):
        """Test the steep rotation is steep enough to be legible in a report.

        ``rotated_two_islands`` is a shallow rotation: a north-up assumption
        misplaces its corner by roughly one cell, which reads as an edge
        effect. This case has to displace by several cells so the *direction*
        of a consumer's error is visible.
        """
        with open_case("rotated_steep_small") as dataset:
            transform = dataset.transform
            height = dataset.height
            pixel_size = abs(transform.a)

        # Where the grid's bottom-left corner actually is, against where a
        # consumer assuming a north-up affine would place it.
        actual_x, _ = transform * (0, height)
        north_up_x, _ = rasterio.transform.from_origin(
            transform.c, transform.f, pixel_size, pixel_size
        ) * (0, height)

        displacement_cells = abs(actual_x - north_up_x) / pixel_size
        assert displacement_cells > 3, (
            f"displaced only {displacement_cells:.2f} cells; a rotation this "
            "shallow reads as a one-pixel edge effect, not a wrong answer"
        )

    def test_rotated_two_islands_warped_ships_its_reference(self):
        """Test the warped answer travels with the rotated source.

        Following the ``crs_mismatch_overlay_pair`` precedent: a relationship
        between two inputs, expressed as one case with a sidecar. Without it
        every consumer of the rotated case has to build its own ``WarpedVRT``
        reference, which is what all three validation runs had to do.
        """
        case = geocase.load_case("rotated_two_islands_warped")

        with rasterio.open(case.primary_path) as source:
            source_transform = source.transform

        assert (source_transform.b, source_transform.d) != (0.0, 0.0), (
            "the primary file must be the rotated source"
        )

        warped = [p for p in case.sidecar_paths() if p.suffix == ".tif"]
        assert warped, "the warped reference sidecar is missing"

        with rasterio.open(warped[0]) as reference:
            assert (reference.transform.b, reference.transform.d) == (0.0, 0.0), (
                "the reference must be north-up; that is what makes it the "
                "declared correct answer"
            )
