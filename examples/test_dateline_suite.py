"""Plugin-driven suite example for dateline-focused case coverage."""

from __future__ import annotations

import pytest


@pytest.mark.geocase_case("dateline_crossing_polygon")
def test_dateline_case_loads_with_plugin(geocase) -> None:
	gdf = geocase.load()

	assert geocase.id == "dateline_crossing_polygon"
	assert len(gdf) == 1
	assert gdf.crs is not None
	assert gdf.crs.to_epsg() == 4326
