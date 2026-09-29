"""Vector differential round -- Plan 42 Phase 3 (#27).

The comparison predicate comes first: a frame's geometry column must be
compared as *geometries* (NULL vs EMPTY vs NaN-coordinate), not as opaque
values, or a finding reads "column 'geometry' differs" with no clue which of
round 2's three defect shapes it is.
"""

from __future__ import annotations

import pytest

from geocase.differential import default_compare

gpd = pytest.importorskip("geopandas")
shapely = pytest.importorskip("shapely")


def _frame(*geoms):
    return gpd.GeoDataFrame({"id": list(range(len(geoms)))}, geometry=list(geoms))


class TestGeometryColumnsAreComparedAsGeometries:
    def test_null_vs_empty_names_the_states(self):
        detail = default_compare(_frame(None), _frame(shapely.from_wkt("POINT EMPTY")))
        assert detail is not None
        assert "geometry state differs: NULL vs EMPTY" in detail
        assert "row 0" in detail

    def test_empty_type_mismatch_is_reported(self):
        detail = default_compare(
            _frame(shapely.from_wkt("POINT EMPTY")),
            _frame(shapely.from_wkt("POLYGON EMPTY")),
        )
        assert detail is not None
        assert "POINT EMPTY vs POLYGON EMPTY" in detail

    def test_identical_geometries_agree(self):
        point = shapely.Point(1, 2)
        assert default_compare(_frame(point, None), _frame(point, None)) is None

    def test_nan_coordinate_vs_present_names_the_states(self):
        detail = default_compare(
            _frame(shapely.Point(float("nan"), 1)), _frame(shapely.Point(0, 1))
        )
        assert detail is not None
        assert "NaN-coordinate vs present" in detail

    def test_non_geometry_columns_keep_their_message(self):
        left, right = _frame(None), _frame(None)
        right["id"] = [7]
        detail = default_compare(left, right)
        assert detail is not None
        assert "column 'id' differs at row 0" in detail
