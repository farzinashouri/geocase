"""Tests for the raster side of ``geocase.differential`` — Plan 37 Phase 2.

The entry condition for the raster adapter protocol was raster evidence, and
the 2026-08-31 validation run supplied it: two real rio-tiler defects, both
found by reading one raster case two ways and comparing arrays. The run had to
hand-write that comparison, and got three things wrong on the first pass. Those
three mistakes are what these tests pin, because each one turned a real finding
into noise or hid half of one:

* **NaN-vs-NaN must compare equal.** ``np.array_equal`` reports every
  NaN-nodata raster as diverged; two of the run's three initial "findings" were
  that and nothing else.
* **Masks compare by equality, not truthiness.** The harness's ``mask > 0``
  is correct at every dtype and for exactly that reason stepped straight over
  rio-tiler's ``ImageData.mask`` contract defect.
* **Shape mismatch short-circuits**, the way ``_frames_differ`` checks shape
  before contents, or the reported difference is unreadable.
"""

from __future__ import annotations

import pytest

from geocase.differential import compare_arrays, compare_cases

np = pytest.importorskip("numpy")


class TestNaNIsNotADivergence:
    """The mistake that produced two of the run's three initial findings."""

    def test_nan_in_the_same_position_compares_equal(self):
        """Test two arrays equal but for a shared NaN are not a divergence."""
        left = np.array([[1.0, np.nan], [3.0, 4.0]])
        right = np.array([[1.0, np.nan], [3.0, 4.0]])
        assert compare_arrays(left, right) is None

    def test_nan_against_a_value_is_a_divergence(self):
        """Test NaN tolerance does not extend to NaN-vs-number."""
        left = np.array([[1.0, np.nan], [3.0, 4.0]])
        right = np.array([[1.0, 2.0], [3.0, 4.0]])
        detail = compare_arrays(left, right)
        assert detail is not None
        assert "(0, 1)" in detail

    def test_nan_in_different_positions_is_a_divergence(self):
        """Test a moved NoData pixel is a finding, not tolerated absence."""
        left = np.array([[np.nan, 2.0]])
        right = np.array([[1.0, np.nan]])
        assert compare_arrays(left, right) is not None


class TestTheFirstDifferingCell:
    """A report has to name the cell, not just say the arrays differ."""

    def test_one_differing_cell_is_reported_with_its_index(self):
        """Test the detail carries the index and both values."""
        left = np.array([[1, 2], [3, 4]])
        right = np.array([[1, 2], [3, 9]])
        detail = compare_arrays(left, right)
        assert detail is not None
        assert "(1, 1)" in detail
        assert "4" in detail and "9" in detail

    def test_equal_integer_arrays_agree(self):
        """Test the ordinary agreeing case reports nothing."""
        left = np.array([[1, 2], [3, 4]])
        assert compare_arrays(left, left.copy()) is None

    def test_the_count_of_differing_cells_is_reported(self):
        """Test the detail says how widespread the divergence is.

        ``rotated_two_islands`` diverged on 17 of 64 pixels. "1 cell" and "17
        cells" need different triage, and the first differing index alone does
        not distinguish them.
        """
        left = np.zeros((8, 8))
        right = np.zeros((8, 8))
        right[:2, :] = 1.0
        detail = compare_arrays(left, right)
        assert detail is not None
        assert "16" in detail


class TestShapeShortCircuits:
    """Shape before contents, or the message is unreadable."""

    def test_different_shapes_report_the_shapes(self):
        """Test a shape mismatch names both shapes and nothing else."""
        left = np.zeros((2, 2))
        right = np.zeros((3, 3))
        detail = compare_arrays(left, right)
        assert detail is not None
        assert "(2, 2)" in detail
        assert "(3, 3)" in detail

    def test_a_shape_mismatch_does_not_raise(self):
        """Test comparison of unbroadcastable shapes returns a detail.

        ``np.array_equal`` is safe here but a naive ``left != right`` is not;
        this pins that the short-circuit happens before any elementwise work.
        """
        assert compare_arrays(np.zeros((2, 3)), np.zeros((4, 5))) is not None


class TestMasksCompareByEquality:
    """The mistake that hid half of the rotated-raster defect."""

    def test_masks_differing_only_in_magnitude_are_a_divergence(self):
        """Test 255-vs-1 is reported, where ``mask > 0`` would call it equal.

        This is rio-tiler's ``ImageData.mask`` contract defect exactly: both
        masks are truthy in the same cells, and a truthiness comparator sees
        no difference at all.
        """
        left = np.array([[255, 0], [255, 255]], dtype="uint8")
        right = np.array([[1, 0], [1, 1]], dtype="uint8")
        assert compare_arrays(left, right) is not None

    def test_boolean_masks_that_agree_compare_equal(self):
        """Test the ordinary agreeing mask reports nothing."""
        mask = np.array([[True, False], [True, True]])
        assert compare_arrays(mask, mask.copy()) is None


class TestNonArrayInputs:
    """The comparator has to survive what a real reader hands it."""

    def test_nested_sequences_are_compared_as_arrays(self):
        """Test a reader returning lists is not a crash."""
        assert compare_arrays([[1, 2]], [[1, 2]]) is None
        assert compare_arrays([[1, 2]], [[1, 3]]) is not None

    def test_masked_arrays_compare_on_their_data_and_mask(self):
        """Test a masked array whose fill differs under the mask agrees.

        ``rasterio.read(masked=True)`` returns these, so the raster shape this
        function exists for produces them routinely.
        """
        left = np.ma.masked_array([[1.0, 9.0]], mask=[[False, True]])
        right = np.ma.masked_array([[1.0, -9999.0]], mask=[[False, True]])
        assert compare_arrays(left, right) is None

    def test_masked_arrays_differing_in_their_mask_diverge(self):
        """Test a moved mask is a finding even where the data agrees."""
        left = np.ma.masked_array([[1.0, 2.0]], mask=[[False, True]])
        right = np.ma.masked_array([[1.0, 2.0]], mask=[[True, False]])
        assert compare_arrays(left, right) is not None


class TestTheRasterShapeEndToEnd:
    """Phase 2.3 — a raster reader is already a ``Reader``, with no changes."""

    def test_compare_cases_runs_over_the_raster_corpus(self):
        """Test the two-path raster shape runs end to end and agrees.

        Reading every raster case the same way twice must produce ``agree``
        everywhere: any other outcome means the protocol itself is reporting
        noise, which is the failure mode that makes a differential harness
        useless before it is ever pointed at a real consumer.
        """
        rasterio = pytest.importorskip("rasterio")

        def read_band_one(path):
            with rasterio.open(path) as dataset:
                return dataset.read(1)

        results = compare_cases(
            left=read_band_one,
            right=read_band_one,
            compare=compare_arrays,
            category="raster",
        )

        assert results, "the raster corpus selected no cases"
        divergent = [r for r in results if r.outcome != "agree"]
        assert not divergent, [(r.case_id, r.outcome, r.detail) for r in divergent]
