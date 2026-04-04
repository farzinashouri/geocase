"""Plugin-driven CRS edge-case examples using marker-based selection."""

from __future__ import annotations

from typing import Any, Callable, cast

import pytest


TypedMarkerDecorator = Callable[
	..., Callable[[Callable[..., object]], Callable[..., object]]
]

geocase_select = cast(TypedMarkerDecorator, pytest.mark.geocase_select)
geocase_case = cast(TypedMarkerDecorator, pytest.mark.geocase_case)


@geocase_select(tags_any=["crs"], category="vector")
def test_selected_vector_cases_have_crs(geocase: Any) -> None:
	gdf = geocase.load()

	assert gdf.crs is not None
	assert gdf.crs.to_epsg() is not None


@geocase_case("geotiff_nodata_small")
def test_single_raster_case_with_plugin_fixture(geocase_case: Any) -> None:
	data, profile, nodata = geocase_case.read(1)

	assert geocase_case.category == "raster"
	assert profile["count"] == 1
	assert data.size > 0
	assert nodata is not None
