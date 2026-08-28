"""Assertions module — reusable geospatial validation checks."""

from geocase.assertions.crs import assert_crs_units, assert_epsg, assert_has_crs
from geocase.assertions.extent import assert_bounds
from geocase.assertions.footprint import (
    assert_footprint_no_holes,
    assert_footprint_rectangularity,
    assert_footprint_similar_to_expected,
)
from geocase.assertions.format_compliance import (
    assert_format_compliance,
    assert_geoparquet_metadata,
    registered_format_validators,
)
from geocase.assertions.geometry import (
    assert_feature_count,
    assert_geometry_type,
    assert_has_holes,
    assert_invalid_geometry,
    assert_no_holes,
    assert_valid_geometry,
)
from geocase.assertions.metadata import (
    assert_case_loadable,
    assert_matches_raster_hints,
    assert_matches_vector_hints,
)
from geocase.assertions.raster import (
    assert_band_count,
    assert_band_names,
    assert_colormap_present,
    assert_compression,
    assert_dtype,
    assert_has_overviews,
    assert_is_cog,
    assert_nan_nodata,
    assert_no_nodata_pixels,
    assert_nodata_masked,
    assert_nodata_value,
    assert_shape,
)
from geocase.assertions.topology import (
    assert_no_duplicates,
    assert_no_null_geometries,
    assert_no_self_intersections,
)

__all__ = [
    # Geometry
    "assert_valid_geometry",
    "assert_invalid_geometry",
    "assert_geometry_type",
    "assert_has_holes",
    "assert_no_holes",
    "assert_feature_count",
    "assert_footprint_no_holes",
    "assert_footprint_rectangularity",
    "assert_footprint_similar_to_expected",
    # CRS
    "assert_has_crs",
    "assert_epsg",
    "assert_crs_units",
    # Extent
    "assert_bounds",
    # Raster
    "assert_band_count",
    "assert_nodata_value",
    "assert_dtype",
    "assert_shape",
    "assert_nodata_masked",
    "assert_no_nodata_pixels",
    "assert_compression",
    "assert_has_overviews",
    "assert_nan_nodata",
    "assert_is_cog",
    "assert_band_names",
    "assert_colormap_present",
    # Topology
    "assert_no_self_intersections",
    "assert_no_duplicates",
    "assert_no_null_geometries",
    # Metadata
    "assert_case_loadable",
    "assert_matches_vector_hints",
    "assert_matches_raster_hints",
    # Format compliance
    "assert_format_compliance",
    "assert_geoparquet_metadata",
    "registered_format_validators",
]
