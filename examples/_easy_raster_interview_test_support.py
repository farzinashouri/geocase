"""Edge-case tests for the easy *raster* interview utilities.

These mirror ``_easy_geospatial_interview_test_support.py`` but target the
twenty raster-focused exercises in
``examples/interview_questions/easy_raster_interview_questions.py``.

The functions in that module are the deliberately *simple* reference
implementations. Tests here fall into two groups:

* **Baseline tests** assert behaviour the simple helpers get right; they pass
  today and lock in the happy path.
* **Edge-case tests** (suffixed ``_edge``) document where the simple helpers
  break against the newly-added raster coverage (NaN NoData DEMs, rotated
  geotransforms, out-of-bounds sampling, NaN histograms). They assert the
  *robust* behaviour we want and are marked ``xfail`` until a hardened
  ``_perfect`` variant is added, exactly as planned for the raster questions.

Only ``osgeo`` (GDAL) and ``rasterio`` are required, plus the GeoCase catalog
to resolve bundled raster fixtures.
"""

from __future__ import annotations

import importlib.util
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pytest

pytest.importorskip("osgeo")
import rasterio  # noqa: E402
from osgeo import gdal  # noqa: E402

from geocase.catalog import load_case_index, load_case_metadata, select_cases  # noqa: E402
from geocase.cases.factory import create_case  # noqa: E402
from geocase.pytest_plugin.case_diagnostics import build_case_params  # noqa: E402

gdal.UseExceptions()


# ---------------------------------------------------------------------------
# Load the interview module under test
# ---------------------------------------------------------------------------

_MODULE_PATH = (
    Path(__file__).resolve().parent
    / "interview_questions"
    / "easy_raster_interview_questions.py"
)
_MODULE_SPEC = importlib.util.spec_from_file_location(
    "easy_raster_interview_questions",
    _MODULE_PATH,
)
if _MODULE_SPEC is None or _MODULE_SPEC.loader is None:
    raise ImportError(f"Could not load interview module from {_MODULE_PATH}")

_MODULE = importlib.util.module_from_spec(_MODULE_SPEC)
_MODULE_SPEC.loader.exec_module(_MODULE)

raster_info = _MODULE.raster_info
raster_extent = _MODULE.raster_extent
pixel_size = _MODULE.pixel_size
world_to_pixel = _MODULE.world_to_pixel
read_band = _MODULE.read_band
band_statistics = _MODULE.band_statistics
count_valid_pixels = _MODULE.count_valid_pixels
replace_nodata = _MODULE.replace_nodata
ndvi = _MODULE.ndvi
write_geotiff = _MODULE.write_geotiff
resample_raster = _MODULE.resample_raster
reproject_raster = _MODULE.reproject_raster
threshold_mask = _MODULE.threshold_mask
stack_mean = _MODULE.stack_mean
build_overviews = _MODULE.build_overviews
sample_pixel = _MODULE.sample_pixel
pixel_center_to_world = _MODULE.pixel_center_to_world
lonlat_to_raster_crs = _MODULE.lonlat_to_raster_crs
valid_data_area_m2 = _MODULE.valid_data_area_m2
value_histogram = _MODULE.value_histogram


# ---------------------------------------------------------------------------
# GeoCase fixture resolution
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE_ROOT = _REPO_ROOT / "src" / "geocase"
_CASE_INDEX_PATH = _PACKAGE_ROOT / "metadata" / "case-index.yaml"


@lru_cache(maxsize=1)
def _indexed_case_entries() -> tuple[tuple[Any, Path], ...]:
    """Load all indexed case metadata and their case root directories."""
    entries: list[tuple[Any, Path]] = []
    for rel_path in load_case_index(_CASE_INDEX_PATH):
        case_yaml = _PACKAGE_ROOT / rel_path
        metadata = load_case_metadata(case_yaml)
        entries.append((metadata, case_yaml.parent))
    return tuple(entries)


@lru_cache(maxsize=1)
def _indexed_case_map() -> dict[str, tuple[Any, Path]]:
    """Map case id to (metadata, case root) for indexed cases."""
    return {metadata.id: (metadata, root) for metadata, root in _indexed_case_entries()}


def _load_case(case_id: str) -> Any:
    """Load an indexed GeoCase fixture by case id."""
    case_entry = _indexed_case_map().get(case_id)
    if case_entry is None:
        raise FileNotFoundError(f"Unknown indexed GeoCase fixture: {case_id}")
    metadata, root = case_entry
    return create_case(metadata, root)


def _raster_metadata() -> list[Any]:
    """All indexed raster-case metadata."""
    return [metadata for metadata, _ in _indexed_case_entries() if metadata.category == "raster"]


def _select_raster_metadata(**selection_kwargs: Any) -> list[Any]:
    """Select indexed raster-case metadata via catalog selectors."""
    return select_cases(_raster_metadata(), category="raster", **selection_kwargs)


def _load_unique_raster(**selection_kwargs: Any) -> Any:
    """Load exactly one bundled raster fixture chosen by metadata selectors."""
    matches = _select_raster_metadata(**selection_kwargs)
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one raster case, found {len(matches)} for {selection_kwargs}."
        )
    return _load_case(matches[0].id)


# --- Named fixtures (the newly-added EO raster coverage) --------------------


def _ndvi_raster_case() -> Any:
    return _load_unique_raster(tags_all=["eo", "ndvi"])


def _optical_rgb_raster_case() -> Any:
    return _load_unique_raster(tags_all=["eo", "rgb"])


def _water_mask_raster_case() -> Any:
    return _load_unique_raster(tags_all=["eo", "water"])


def _dem_raster_case() -> Any:
    """DEM fixture using the NaN NoData convention."""
    return _load_unique_raster(tags_all=["eo", "dem"])


def _multispectral_raster_case() -> Any:
    return _load_unique_raster(tags_all=["eo", "multispectral"])


def _rotated_raster_case() -> Any:
    return _load_unique_raster(tags_all=["rotated"])


def _expected_epsg(meta: Any) -> int | None:
    """Return the EPSG declared in typed assertions, if any."""
    assertions = getattr(meta, "assertions", None)
    return getattr(assertions, "expected_epsg", None) if assertions is not None else None


# Parametrized over every bundled raster fixture.
_RASTER_CASE_PARAMS = build_case_params(_raster_metadata(), load_case=_load_case)


def _is_rotated(path: str) -> bool:
    """True if the raster carries non-zero rotation/skew geotransform terms."""
    with rasterio.open(path) as src:
        return src.transform.b != 0.0 or src.transform.d != 0.0


def _geotransform_envelope(gt: tuple, width: int, height: int) -> tuple[float, float, float, float]:
    """True axis-aligned envelope of a (possibly rotated) geotransform."""
    corners = [(0, 0), (width, 0), (0, height), (width, height)]
    xs = [gt[0] + c * gt[1] + r * gt[2] for c, r in corners]
    ys = [gt[3] + c * gt[4] + r * gt[5] for c, r in corners]
    return min(xs), min(ys), max(xs), max(ys)


_XFAIL_SIMPLE = pytest.mark.xfail(
    reason="Simple raster helper limitation; the perfect variant (added later) will fix this.",
    strict=False,
)


# ===========================================================================
# Question 1 — raster_info
# ===========================================================================
def test_raster_info_reports_optical_rgb_shape_and_bands() -> None:
    """Q1: read width/height/band-count/EPSG for the RGB optical fixture."""
    case = _optical_rgb_raster_case()
    info = raster_info(str(case.primary_path))

    assert info["width"] == 16
    assert info["height"] == 16
    assert info["bands"] == 3
    assert info["epsg"] == 32633


@pytest.mark.parametrize("geocase", _RASTER_CASE_PARAMS)
def test_raster_info_handles_all_raster_cases(geocase: Any) -> None:
    """Q1: basic metadata is sane for every bundled raster fixture."""
    info = raster_info(str(geocase.primary_path))

    assert info["width"] > 0
    assert info["height"] > 0
    assert info["bands"] >= 1

    expected_epsg = _expected_epsg(geocase.metadata)
    if expected_epsg is not None:
        assert info["epsg"] == expected_epsg


# ===========================================================================
# Question 2 — raster_extent
# ===========================================================================
def test_raster_extent_orders_bounds_for_north_up_raster() -> None:
    """Q2: north-up extent is ordered and matches rasterio bounds."""
    case = _ndvi_raster_case()
    minx, miny, maxx, maxy = raster_extent(str(case.primary_path))

    assert minx < maxx
    assert miny < maxy

    with rasterio.open(case.primary_path) as src:
        assert (minx, miny, maxx, maxy) == pytest.approx(tuple(src.bounds))


@_XFAIL_SIMPLE
def test_raster_extent_rotated_matches_true_envelope_edge() -> None:
    """Q2 edge: rotated geotransforms need the full four-corner envelope.

    The simple helper only uses gt[0], gt[1], gt[3], gt[5], ignoring the
    rotation terms gt[2]/gt[4], so its extent is wrong for a rotated raster.
    """
    case = _rotated_raster_case()
    dataset = gdal.Open(str(case.primary_path))
    gt = dataset.GetGeoTransform()
    expected = _geotransform_envelope(gt, dataset.RasterXSize, dataset.RasterYSize)
    dataset = None

    observed = raster_extent(str(case.primary_path))

    assert observed == pytest.approx(expected)


# ===========================================================================
# Question 3 — pixel_size
# ===========================================================================
@pytest.mark.parametrize("geocase", _RASTER_CASE_PARAMS)
def test_pixel_size_is_positive_for_all_rasters(geocase: Any) -> None:
    """Q3: ground resolution is reported as positive magnitudes."""
    x_res, y_res = pixel_size(str(geocase.primary_path))

    assert x_res > 0
    assert y_res > 0


# ===========================================================================
# Question 4 — world_to_pixel
# ===========================================================================
def test_world_to_pixel_roundtrips_pixel_center() -> None:
    """Q4: a pixel-centre world coordinate maps back to its (row, col)."""
    case = _ndvi_raster_case()
    path = str(case.primary_path)

    x, y = pixel_center_to_world(path, 5, 7)
    row, col = world_to_pixel(path, x, y)

    assert (row, col) == (5, 7)


@_XFAIL_SIMPLE
def test_world_to_pixel_rejects_out_of_bounds_edge() -> None:
    """Q4 edge: a coordinate outside the raster should not yield a valid index.

    The simple helper does no bounds checking and returns negative indices for
    points north/west of the origin.
    """
    case = _ndvi_raster_case()
    path = str(case.primary_path)

    minx, miny, maxx, maxy = raster_extent(path)
    width = maxx - minx

    with pytest.raises((ValueError, IndexError)):
        world_to_pixel(path, minx - width, maxy)


@_XFAIL_SIMPLE
def test_world_to_pixel_rotated_matches_inverse_transform_edge() -> None:
    """Q4 edge: rotated rasters need the inverse of the full geotransform."""
    case = _rotated_raster_case()
    path = str(case.primary_path)

    with rasterio.open(case.primary_path) as src:
        x, y = src.xy(3, 4)  # world coord of pixel centre (row=3, col=4)

    row, col = world_to_pixel(path, x, y)

    assert (row, col) == (3, 4)


# ===========================================================================
# Question 5 — read_band
# ===========================================================================
def test_read_band_returns_expected_shape() -> None:
    """Q5: a single band reads back at the declared shape."""
    case = _ndvi_raster_case()
    arr = read_band(str(case.primary_path))

    assert arr.shape == (16, 16)


def test_read_band_distinguishes_multiband_data() -> None:
    """Q5: distinct bands of the RGB fixture are not collapsed together."""
    case = _optical_rgb_raster_case()
    path = str(case.primary_path)

    red = read_band(path, 1)
    blue = read_band(path, 3)

    assert red.shape == blue.shape
    assert not np.array_equal(red, blue)


# ===========================================================================
# Question 6 — band_statistics
# ===========================================================================
def test_band_statistics_respects_value_range_for_ndvi() -> None:
    """Q6: NDVI statistics stay within the documented [-1, 1] range."""
    case = _ndvi_raster_case()
    stats = band_statistics(str(case.primary_path))

    assert stats["min"] >= -1.0 - 1e-6
    assert stats["max"] <= 1.0 + 1e-6
    assert math.isfinite(stats["mean"])
    assert math.isfinite(stats["std"])


def test_band_statistics_excludes_sentinel_nodata() -> None:
    """Q6: a sentinel NoData (255) is excluded from the water-mask stats."""
    case = _water_mask_raster_case()
    stats = band_statistics(str(case.primary_path))

    # Only 0/1 are valid; 255 must be masked out.
    assert stats["max"] <= 1.0


@_XFAIL_SIMPLE
def test_band_statistics_handles_nan_nodata_edge() -> None:
    """Q6 edge: NaN NoData must be excluded, but ``arr != nan`` keeps NaNs.

    The DEM fixture uses the NaN NoData convention, so the simple
    ``arr[arr != nodata]`` filter leaves the NaNs in place and the resulting
    statistics are NaN.
    """
    case = _dem_raster_case()
    stats = band_statistics(str(case.primary_path))

    assert math.isfinite(stats["min"])
    assert math.isfinite(stats["max"])
    assert math.isfinite(stats["mean"])


# ===========================================================================
# Question 7 — count_valid_pixels
# ===========================================================================
def test_count_valid_pixels_excludes_sentinel_nodata() -> None:
    """Q7: sentinel NoData pixels are not counted as valid."""
    case = _water_mask_raster_case()
    path = str(case.primary_path)

    arr, _, nodata = case.read(1)
    expected = int(np.count_nonzero(arr != nodata))

    assert count_valid_pixels(path) == expected
    assert count_valid_pixels(path) < arr.size or nodata is None


@_XFAIL_SIMPLE
def test_count_valid_pixels_handles_nan_nodata_edge() -> None:
    """Q7 edge: NaN NoData pixels are wrongly counted as valid by the simple helper."""
    case = _dem_raster_case()
    path = str(case.primary_path)

    arr = read_band(path)
    nan_count = int(np.count_nonzero(np.isnan(arr)))
    assert nan_count > 0  # fixture really has NaN holes

    assert count_valid_pixels(path) == arr.size - nan_count


# ===========================================================================
# Question 8 — replace_nodata
# ===========================================================================
def test_replace_nodata_swaps_only_matching_values() -> None:
    """Q8: only the old NoData value is replaced, leaving a copy."""
    arr = np.array([[0, -9999], [5, -9999]], dtype="float64")

    out = replace_nodata(arr, -9999, 0)

    assert np.array_equal(out, np.array([[0, 0], [5, 0]]))
    assert arr[0, 1] == -9999  # original untouched


# ===========================================================================
# Question 9 — ndvi
# ===========================================================================
def test_ndvi_matches_manual_formula_and_guards_zero_denominator() -> None:
    """Q9: NDVI matches (nir-red)/(nir+red) and returns 0 where both are 0."""
    red = np.array([[100, 0]], dtype="float64")
    nir = np.array([[200, 0]], dtype="float64")

    out = ndvi(red, nir)

    assert out[0, 0] == pytest.approx((200 - 100) / (200 + 100))
    assert out[0, 1] == 0.0


def test_ndvi_from_multispectral_bands_stays_in_range() -> None:
    """Q9: NDVI from the multispectral red/NIR bands is bounded in [-1, 1]."""
    case = _multispectral_raster_case()
    path = str(case.primary_path)

    red = read_band(path, 3).astype("float64")
    nir = read_band(path, 4).astype("float64")

    result = ndvi(red, nir)
    finite = result[np.isfinite(result)]

    assert np.all(finite >= -1.0 - 1e-9)
    assert np.all(finite <= 1.0 + 1e-9)


# ===========================================================================
# Question 10 — write_geotiff
# ===========================================================================
def test_write_geotiff_roundtrips_array_and_georeference(tmp_path: Path) -> None:
    """Q10: a written GeoTIFF reads back with matching data and CRS."""
    array = np.arange(12, dtype="float32").reshape(3, 4)
    geotransform = (500000.0, 10.0, 0.0, 4500000.0, 0.0, -10.0)
    out_path = tmp_path / "written.tif"

    write_geotiff(str(out_path), array, geotransform, 32633)

    with rasterio.open(out_path) as src:
        assert src.width == 4
        assert src.height == 3
        assert src.crs.to_epsg() == 32633
        np.testing.assert_allclose(src.read(1), array)


# ===========================================================================
# Question 11 — resample_raster
# ===========================================================================
def test_resample_raster_to_finer_resolution_grows_dimensions(tmp_path: Path) -> None:
    """Q11: halving the pixel size roughly doubles each dimension."""
    case = _ndvi_raster_case()
    out_path = tmp_path / "resampled.tif"

    x_res, y_res = pixel_size(str(case.primary_path))
    resample_raster(str(case.primary_path), str(out_path), x_res / 2, y_res / 2)

    with rasterio.open(case.primary_path) as src_in, rasterio.open(out_path) as src_out:
        assert src_out.width > src_in.width
        assert src_out.height > src_in.height


# ===========================================================================
# Question 12 — reproject_raster
# ===========================================================================
def test_reproject_raster_changes_crs(tmp_path: Path) -> None:
    """Q12: reprojecting a UTM fixture to WGS84 yields an EPSG:4326 output."""
    case = _ndvi_raster_case()
    out_path = tmp_path / "reprojected.tif"

    reproject_raster(str(case.primary_path), str(out_path), 4326)

    with rasterio.open(out_path) as src:
        assert src.crs.to_epsg() == 4326


# ===========================================================================
# Question 13 — threshold_mask
# ===========================================================================
def test_threshold_mask_marks_values_at_or_above_threshold() -> None:
    """Q13: values >= threshold become 1, others 0, as uint8."""
    arr = np.array([[0.1, 0.5], [0.8, 0.2]])

    mask = threshold_mask(arr, 0.5)

    assert mask.dtype == np.uint8
    assert np.array_equal(mask, np.array([[0, 1], [1, 0]], dtype="uint8"))


# ===========================================================================
# Question 14 — stack_mean
# ===========================================================================
def test_stack_mean_averages_equally_shaped_arrays() -> None:
    """Q14: the per-pixel mean of a stack is computed elementwise."""
    a = np.array([[0.0, 2.0]])
    b = np.array([[4.0, 6.0]])

    out = stack_mean([a, b])

    assert np.array_equal(out, np.array([[2.0, 4.0]]))


def test_stack_mean_rejects_empty_input() -> None:
    """Q14: an empty stack is rejected explicitly."""
    with pytest.raises(ValueError):
        stack_mean([])


# ===========================================================================
# Question 15 — build_overviews
# ===========================================================================
def test_build_overviews_adds_pyramids(tmp_path: Path) -> None:
    """Q15: building overviews registers reduced-resolution levels."""
    case = _optical_rgb_raster_case()
    work_path = tmp_path / "with_overviews.tif"

    # Work on a copy so the bundled fixture stays pristine.
    gdal.Translate(str(work_path), str(case.primary_path))

    build_overviews(str(work_path), [2, 4])

    with rasterio.open(work_path) as src:
        assert len(src.overviews(1)) > 0


# ===========================================================================
# Question 16 — sample_pixel
# ===========================================================================
def test_sample_pixel_matches_array_value() -> None:
    """Q16: sampling a pixel returns the same value as reading the band."""
    case = _ndvi_raster_case()
    path = str(case.primary_path)

    arr = read_band(path)
    row, col = 4, 9

    assert sample_pixel(path, row, col) == pytest.approx(float(arr[row, col]))


# ===========================================================================
# Question 17 — pixel_center_to_world
# ===========================================================================
def test_pixel_center_to_world_matches_rasterio_xy() -> None:
    """Q17: pixel-centre coordinates match rasterio's xy() for a north-up grid."""
    case = _ndvi_raster_case()
    path = str(case.primary_path)

    with rasterio.open(case.primary_path) as src:
        expected_x, expected_y = src.xy(6, 3)

    x, y = pixel_center_to_world(path, 6, 3)

    assert x == pytest.approx(expected_x)
    assert y == pytest.approx(expected_y)


def test_pixel_center_to_world_handles_rotated_transform() -> None:
    """Q17: the helper already accounts for rotation terms (gt[2]/gt[4])."""
    case = _rotated_raster_case()
    path = str(case.primary_path)

    with rasterio.open(case.primary_path) as src:
        expected_x, expected_y = src.xy(3, 4)

    x, y = pixel_center_to_world(path, 3, 4)

    assert x == pytest.approx(expected_x)
    assert y == pytest.approx(expected_y)


# ===========================================================================
# Question 18 — lonlat_to_raster_crs
# ===========================================================================
def test_lonlat_to_raster_crs_projects_into_raster_frame() -> None:
    """Q18: a lon/lat near the raster maps into finite projected coordinates."""
    case = _ndvi_raster_case()
    path = str(case.primary_path)

    # Pick a lon/lat from inside the raster by inverse-projecting its centre.
    with rasterio.open(case.primary_path) as src:
        cx, cy = src.xy(src.height // 2, src.width // 2)
        from pyproj import Transformer

        to_wgs84 = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True)
        lon, lat = to_wgs84.transform(cx, cy)

    x, y = lonlat_to_raster_crs(path, lon, lat)

    assert math.isfinite(x)
    assert math.isfinite(y)
    assert x == pytest.approx(cx, abs=1e-3)
    assert y == pytest.approx(cy, abs=1e-3)


# ===========================================================================
# Question 19 — valid_data_area_m2
# ===========================================================================
def test_valid_data_area_m2_matches_valid_pixel_count() -> None:
    """Q19: valid-data area equals valid pixel count times pixel area."""
    case = _water_mask_raster_case()
    path = str(case.primary_path)

    x_res, y_res = pixel_size(path)
    expected = count_valid_pixels(path) * x_res * y_res

    assert valid_data_area_m2(path) == pytest.approx(expected)


@_XFAIL_SIMPLE
def test_valid_data_area_m2_handles_nan_nodata_edge() -> None:
    """Q19 edge: NaN NoData inflates the area because NaNs are counted valid."""
    case = _dem_raster_case()
    path = str(case.primary_path)

    arr = read_band(path)
    nan_count = int(np.count_nonzero(np.isnan(arr)))
    x_res, y_res = pixel_size(path)
    expected = (arr.size - nan_count) * x_res * y_res

    assert valid_data_area_m2(path) == pytest.approx(expected)


# ===========================================================================
# Question 20 — value_histogram
# ===========================================================================
def test_value_histogram_counts_all_valid_pixels() -> None:
    """Q20: histogram counts sum to the number of valid pixels."""
    case = _ndvi_raster_case()
    path = str(case.primary_path)

    counts, edges = value_histogram(path, bins=8)

    assert len(edges) == len(counts) + 1
    assert sum(counts) == count_valid_pixels(path)


@_XFAIL_SIMPLE
def test_value_histogram_handles_nan_nodata_edge() -> None:
    """Q20 edge: a NaN NoData DEM breaks ``np.histogram`` range computation.

    The simple helper does not strip NaNs (NaN NoData survives ``arr != nodata``),
    so ``np.histogram`` raises on the non-finite range. The robust behaviour is
    to histogram only the finite valid pixels.
    """
    case = _dem_raster_case()
    path = str(case.primary_path)

    counts, edges = value_histogram(path, bins=8)

    assert len(edges) == len(counts) + 1
    assert sum(counts) == count_valid_pixels(path)
