"""Vector differential round: pyogrio vs. raw OGR + GEOS -- Plan 42 Phase 3 (#27).

Neither path is the oracle. Left reads each case with ``pyogrio``
(GDAL -> Arrow/numpy -> shapely); right walks the layer with the raw ``osgeo.ogr``
bindings, exports each feature to WKB and parses that with shapely/GEOS. The two
paths share GDAL's drivers but nothing after them, so a disagreement is in the
conversion layer, not in the file.

Run it (conda ``geocase`` env; needs ``osgeo``)::

    pytest examples/test_differential_vector.py -q -s
"""

from __future__ import annotations

import pytest

import geocase
from geocase.differential import compare_cases, summarize

pyogrio = pytest.importorskip("pyogrio")
shapely = pytest.importorskip("shapely")
ogr = pytest.importorskip("osgeo.ogr")


def _openable_vector_cases() -> list[geocase.CaseMetadata]:
    """Vector cases both readers can open (``required_drivers`` decides)."""
    available = set(pyogrio.list_drivers())
    return [
        case
        for case in geocase.list_cases(category="vector")
        if all(driver in available for driver in case.assertions.required_drivers)
    ]


def _read_with_pyogrio(path):
    """Geometries via pyogrio; ``None`` per row when OGR found no geometry.

    The six ``*_csv_wkt_baseline`` cases hold WKT in a *text column* called
    ``geometry``. OGR's CSV driver does not promote it without
    ``GEOM_POSSIBLE_NAMES``, so pyogrio returns a plain ``DataFrame`` whose
    ``geometry`` attribute is that string. Comparing it to a feature geometry
    is comparing an attribute to a geometry -- a harness artifact, not a
    finding -- so only a real geometry column is read as one.
    """
    frame = pyogrio.read_dataframe(path)
    if getattr(frame, "geometry", None) is None or not hasattr(frame, "crs"):
        return [None] * len(frame)
    return list(frame.geometry)


def _read_with_ogr_and_geos(path):
    """First layer's geometries via ``osgeo.ogr`` -> WKB -> GEOS."""
    dataset = ogr.Open(str(path))
    if dataset is None:
        raise RuntimeError(f"ogr could not open {path}")
    layer = dataset.GetLayer(0)
    geometries = []
    for feature in layer:
        geometry = feature.GetGeometryRef()
        if geometry is None:
            geometries.append(None)
        else:
            geometries.append(shapely.from_wkb(bytes(geometry.ExportToIsoWkb())))
    return geometries


def test_pyogrio_and_ogr_geos_agree_on_the_vector_corpus() -> None:
    results = compare_cases(
        left=_read_with_pyogrio,
        right=_read_with_ogr_and_geos,
        consumer="pyogrio",
        cases=_openable_vector_cases(),
    )

    print(f"\nvector round: {summarize(results)}")
    for result in results:
        if result.outcome in {"diverged", "errored"}:
            print(f"  {result.outcome:9} {result.case_id}: {result.detail}")

    assert results, "expected the readers to open at least some vector cases"
