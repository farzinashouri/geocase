"""Parametrized vector integration examples using GeoCase runtime."""

from pathlib import Path

import pytest

from geocase.catalog.loader import load_case_metadata
from geocase.cases.factory import create_case


_VECTOR_CASE_DIRS = {
	"simple_valid_polygon": Path("src/geocase/data/core/vector/polygon/geojson/simple_valid_polygon"),
	"polygon_with_hole": Path("src/geocase/data/core/vector/special/holes/polygon_with_hole"),
	"self_intersecting_polygon": Path("src/geocase/data/core/vector/special/invalid/self_intersecting_polygon"),
	"dateline_crossing_polygon": Path("src/geocase/data/core/vector/special/dateline/dateline_crossing_polygon"),
}


@pytest.mark.parametrize("case_id", sorted(_VECTOR_CASE_DIRS.keys()))
def test_vector_cases_load_and_reproject(case_id: str) -> None:
	root = _VECTOR_CASE_DIRS[case_id]
	meta = load_case_metadata(root / "case.yaml")
	case = create_case(meta, root)
	gdf = case.load()

	assert len(gdf) >= 1
	assert gdf.crs is not None
	assert gdf.crs.to_epsg() == 4326

	projected = gdf.to_crs(3857)
	area_m2 = float(projected.area.sum())
	perimeter_m = float(projected.length.sum())

	if case_id == "self_intersecting_polygon":
		assert area_m2 >= 0
	else:
		assert area_m2 > 0
	assert perimeter_m > 0


@pytest.mark.parametrize(
	"case_id, expected_validity",
	[
		("simple_valid_polygon", True),
		("polygon_with_hole", True),
		("self_intersecting_polygon", False),
		("dateline_crossing_polygon", True),
	],
)
def test_vector_case_validity_matches_metadata_hint(
	case_id: str,
	expected_validity: bool,
) -> None:
	root = _VECTOR_CASE_DIRS[case_id]
	meta = load_case_metadata(root / "case.yaml")
	case = create_case(meta, root)
	gdf = case.load()

	observed_validity = bool(gdf.geometry.is_valid.all())
	assert observed_validity is expected_validity
