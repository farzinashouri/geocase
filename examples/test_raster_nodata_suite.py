"""Parametrized raster integration examples using GeoCase runtime."""

from pathlib import Path

import numpy as np
import pytest

from geocase.catalog.loader import load_case_metadata
from geocase.cases.factory import create_case


_RASTER_CASE_DIRS = {
	"geotiff_nodata_small": Path("src/geocase/data/core/raster/geotiff_nodata_small"),
	"geotiff_utm_boundary": Path("src/geocase/data/core/raster/geotiff_utm_boundary"),
}


@pytest.mark.parametrize("case_id", sorted(_RASTER_CASE_DIRS.keys()))
def test_raster_cases_open_and_have_expected_profile(case_id: str) -> None:
	root = _RASTER_CASE_DIRS[case_id]
	meta = load_case_metadata(root / "case.yaml")
	case = create_case(meta, root)

	with case.open() as src:
		assert src.count == 1
		assert src.crs is not None
		assert src.crs.to_epsg() == 32633


def test_nodata_case_masked_statistics() -> None:
	root = _RASTER_CASE_DIRS["geotiff_nodata_small"]
	meta = load_case_metadata(root / "case.yaml")
	case = create_case(meta, root)

	data, profile, nodata = case.read(1)

	assert profile["dtype"] == "float32"
	assert nodata is not None

	nodata_mask = data == nodata
	valid = data[~nodata_mask]

	assert int(np.sum(nodata_mask)) > 0
	assert valid.size > 0
	assert np.isfinite(float(valid.min()))
	assert np.isfinite(float(valid.max()))
	assert np.isfinite(float(valid.mean()))


def test_utm_boundary_case_has_no_explicit_nodata() -> None:
	root = _RASTER_CASE_DIRS["geotiff_utm_boundary"]
	meta = load_case_metadata(root / "case.yaml")
	case = create_case(meta, root)

	with case.open() as src:
		assert src.nodata is None
