"""Unit tests for real geospatial utility functions using GeoCase."""

from __future__ import annotations

from typing import Any, Callable, cast

import pytest

from real_geospatial_function import (
    compute_masked_raster_stats,
    compute_projected_shape_metrics,
)

TypedMarkerDecorator = Callable[
    ..., Callable[[Callable[..., object]], Callable[..., object]]
]

geocase_case = cast(TypedMarkerDecorator, pytest.mark.geocase_case)


@geocase_case("simple_valid_polygon", "polygon_with_hole")
def test_compute_projected_shape_metrics(geocase: Any) -> None:
    gdf = geocase.load()

    metrics = compute_projected_shape_metrics(gdf, target_epsg=3857)

    assert geocase.id in {"simple_valid_polygon", "polygon_with_hole"}
    assert metrics["feature_count"] == float(len(gdf))
    assert metrics["area_sum"] > 0.0
    assert metrics["perimeter_sum"] > 0.0


@geocase_case("geotiff_nodata_small", "geotiff_utm_boundary")
def test_compute_masked_raster_stats(geocase: Any) -> None:
    data, profile, nodata = geocase.read(1)

    stats = compute_masked_raster_stats(data, nodata)

    assert profile["count"] == 1
    assert stats["valid_pixel_count"] > 0.0
    assert 0.0 <= stats["nodata_ratio"] <= 1.0
    assert stats["max"] >= stats["min"]

    if geocase.id == "geotiff_nodata_small":
        assert nodata is not None
        assert stats["nodata_ratio"] > 0.0

    if geocase.id == "geotiff_utm_boundary":
        assert nodata is None
        assert stats["nodata_ratio"] == 0.0
