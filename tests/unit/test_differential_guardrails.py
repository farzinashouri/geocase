"""Tests for the raster adapter's guardrails — Plan 38 Phase 2.2 and 2.3.

The round-2 validation run's first sweep was **killed by the OS** after 28 CPU
minutes and 3 GB RSS, and a later one had a case that did not return a geobox
in 90 seconds. Both were consumer defects — odc-stac deriving a 3.17e12 pixel
grid, and the same root cause failing to terminate on an antimeridian source —
but a harness that dies reports nothing at all. The finding has to survive the
defect that produced it.

Phase 2.3's cast-before-fill trap is pinned here too: ``.filled(np.nan)`` on an
*integer* masked array raises, so the cast to float64 must precede the fill.
That belongs in the adapter rather than in each consumer's harness.
"""

from __future__ import annotations

import pytest

from geocase.differential import (
    PixelBudgetError,
    ReaderTimeoutError,
    guarded_reader,
    to_common_currency,
)

np = pytest.importorskip("numpy")


class TestPixelBudget:
    """An absurd derived grid is the finding, not an allocation."""

    def test_a_grid_within_budget_is_read_normally(self):
        """Test the guard is transparent when nothing is wrong."""
        reader = guarded_reader(lambda path: np.zeros((10, 10)), max_pixels=1000)
        assert reader("ignored").shape == (10, 10)

    def test_an_oversized_grid_raises_before_the_read(self):
        """Test the probe fires without the reader ever being called.

        Reading first and checking after is what allocated 3 GB.
        """
        calls = []

        def probe(path):
            calls.append(path)
            return (2_000_000, 2_000_000)

        def reader(path):  # pragma: no cover - must never run
            raise AssertionError("reader ran despite an over-budget probe")

        guarded = guarded_reader(reader, size_probe=probe, max_pixels=10_000)
        with pytest.raises(PixelBudgetError) as excinfo:
            guarded("case.tif")
        assert calls == ["case.tif"]
        assert "4000000000000" in str(excinfo.value)

    def test_the_budget_has_a_documented_default(self):
        """Test a caller who sets nothing is still protected."""
        from geocase.differential import DEFAULT_MAX_PIXELS

        assert DEFAULT_MAX_PIXELS > 0
        reader = guarded_reader(lambda path: np.zeros((4, 4)))
        assert reader("ignored").shape == (4, 4)

    def test_the_budget_error_is_a_finding_not_a_crash(self):
        """Test ``compare_case`` records it as ``errored``, not a traceback."""
        from geocase.differential import compare_cases

        def exploding(path):
            raise PixelBudgetError("derived grid of 3170000000000 pixels")

        results = compare_cases(
            left=exploding,
            right=exploding,
            include_ids=["dem_small"],
        )
        assert results[0].outcome == "agree"


class TestReaderTimeoutError:
    """odc-stac's hang is upstream of any shape a size check could see."""

    def test_a_prompt_reader_returns_its_value(self):
        """Test the timeout is transparent when the reader is fast."""
        reader = guarded_reader(lambda path: "done", timeout=5.0)
        assert reader("ignored") == "done"

    def test_a_hanging_reader_raises_readertimeout(self):
        """Test a reader that never returns becomes a reported finding."""
        import time

        def hangs(path):
            time.sleep(10.0)

        guarded = guarded_reader(hangs, timeout=0.2)
        with pytest.raises(ReaderTimeoutError):
            guarded("case.tif")

    def test_the_readers_exception_is_propagated_unchanged(self):
        """Test the guard does not swallow a genuine consumer crash."""

        def boom(path):
            raise ValueError("consumer said no")

        guarded = guarded_reader(boom, timeout=5.0)
        with pytest.raises(ValueError, match="consumer said no"):
            guarded("case.tif")


class TestCommonCurrency:
    """Cross-library comparison needs one representation."""

    def test_an_integer_array_becomes_float64(self):
        """Test the dtype is unified before anything else happens."""
        result = to_common_currency(np.array([[1, 2], [3, 4]], dtype="int16"))
        assert result.dtype == np.float64

    def test_nodata_is_folded_to_nan(self):
        """Test a sentinel becomes NaN, so two fill values agree."""
        result = to_common_currency(
            np.array([[1, -9999], [3, 4]], dtype="int16"), nodata=-9999
        )
        assert np.isnan(result[0, 1])
        assert result[0, 0] == 1.0

    def test_an_integer_masked_array_does_not_raise(self):
        """Test the cast precedes the fill.

        ``.filled(np.nan)`` on an int masked array raises — the trap the run
        hit. Casting first is the whole fix, and it belongs here rather than
        in every consumer's harness.
        """
        masked = np.ma.masked_array(
            np.array([[1, 2], [3, 4]], dtype="int32"),
            mask=[[False, True], [False, False]],
        )
        result = to_common_currency(masked)
        assert result.dtype == np.float64
        assert np.isnan(result[0, 1])
        assert result[1, 1] == 4.0

    def test_a_float_array_with_nan_nodata_is_unchanged(self):
        """Test the NaN convention needs no special-casing by the caller."""
        array = np.array([[1.0, np.nan]], dtype="float32")
        result = to_common_currency(array, nodata=float("nan"))
        assert result.dtype == np.float64
        assert np.isnan(result[0, 1])

    def test_two_readers_with_different_fill_values_agree_afterwards(self):
        """Test the point of the exercise: the currency makes them comparable."""
        from geocase.differential import compare_arrays

        left = to_common_currency(np.array([[1, -9999]], dtype="int16"), nodata=-9999)
        right = to_common_currency(np.array([[1, 0]], dtype="uint8"), nodata=0)
        assert compare_arrays(left, right) is None
