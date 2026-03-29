"""End-to-end real geospatial function test using GeoCase runtime."""

from pathlib import Path

import numpy as np

from geocase.catalog.loader import load_case_metadata
from geocase.cases.factory import create_case


def test_vector_reproject_area_perimeter() -> None:
    root = Path("src/geocase/data/core/vector/simple_valid_polygon")
    meta = load_case_metadata(root / "case.yaml")
    case = create_case(meta, root)
    gdf = case.load()

    projected = gdf.to_crs(3857)
    area_m2 = float(projected.area.sum())
    perimeter_m = float(projected.length.sum())

    assert case.id == "simple_valid_polygon"
    assert len(gdf) == 1
    assert gdf.crs is not None
    assert gdf.crs.to_epsg() == 4326
    assert area_m2 > 0
    assert perimeter_m > 0


def test_raster_nodata_masked_summary_stats() -> None:
    root = Path("src/geocase/data/core/raster/geotiff_nodata_small")
    meta = load_case_metadata(root / "case.yaml")
    case = create_case(meta, root)

    data, profile, nodata = case.read(1)

    assert case.id == "geotiff_nodata_small"
    assert profile["count"] == 1
    assert profile["dtype"] == "float32"
    assert nodata is not None

    nodata_mask = data == nodata
    valid = data[~nodata_mask]

    nodata_pixels = int(np.sum(nodata_mask))
    valid_mean = float(valid.mean())
    valid_std = float(valid.std())

    assert nodata_pixels > 0
    assert valid.size > 0
    assert np.isfinite(valid_mean)
    assert np.isfinite(valid_std)
