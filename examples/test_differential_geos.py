"""Differential testing: GEOS through shapely vs. GEOS through ``osgeo.ogr`` (#48).

#27 compared *reading* (pyogrio vs raw OGR). This round compares geometry
*operations*, where GEOS does the work. Both sides get the **same bytes**: each
feature is read once with ``osgeo.ogr`` and exported to ISO WKB, then parsed by
shapely on the left and by ``ogr.CreateGeometryFromWkb`` on the right. Shapely
and GDAL each bundle their own GEOS build, so a disagreement is either a front
end's defaults or a GEOS *version* difference -- the report records both versions
and says which it is likely to be.

Neither side is the oracle; the finding is the disagreement.

Run it (conda ``geocase`` env; needs ``osgeo``)::

    pytest examples/test_differential_geos.py -q -s
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import geocase
from geocase.differential import compare_geometry_ops, render_report, run_round

shapely = pytest.importorskip("shapely")
ogr = pytest.importorskip("osgeo.ogr")
gdal = pytest.importorskip("osgeo.gdal")

gdal.UseExceptions()
ogr.UseExceptions()
# OGR warns on every Area()/Length() of a geometry that has none; the round
# compares the returned 0 and does not need a warning per feature.
gdal.PushErrorHandler("CPLQuietErrorHandler")

#: Fixed so both sides simplify by the same amount.
SIMPLIFY_TOLERANCE = 0.01


def _guard(operation: Callable[[], Any]) -> Any:
    """An operation that raises records ``"error"``: two front ends that both
    refuse the same geometry agree; one that refuses alone is the finding."""
    try:
        return operation()
    except Exception:
        return "error"


def _shapely_ops(geom: Any) -> dict[str, Any]:
    made_valid = _guard(lambda: shapely.make_valid(geom))
    buffered = _guard(lambda: geom.buffer(0))
    simplified = _guard(lambda: geom.simplify(SIMPLIFY_TOLERANCE))
    centroid = _guard(lambda: geom.centroid)
    return {
        "is_valid": geom.is_valid,
        "is_empty": geom.is_empty,
        "area": geom.area,
        "length": geom.length,
        "buffer0_area": buffered if buffered == "error" else buffered.area,
        "centroid": None
        if centroid == "error" or centroid.is_empty
        else [centroid.x, centroid.y],
        "envelope": [] if geom.is_empty else list(geom.bounds),
        "make_valid_is_valid": made_valid
        if made_valid == "error"
        else made_valid.is_valid,
        "make_valid_type": made_valid
        if made_valid == "error"
        else made_valid.geom_type.upper(),
        "make_valid_area": made_valid if made_valid == "error" else made_valid.area,
        "simplify_area": simplified if simplified == "error" else simplified.area,
    }


def _ogr_ops(geom: Any) -> dict[str, Any]:
    made_valid = _guard(lambda: geom.MakeValid())
    buffered = _guard(lambda: geom.Buffer(0))
    simplified = _guard(lambda: geom.SimplifyPreserveTopology(SIMPLIFY_TOLERANCE))
    centroid = _guard(lambda: geom.Centroid())
    empty = geom.IsEmpty()
    if centroid == "error" or centroid.IsEmpty():
        centroid_xy = None
    else:
        centroid_xy = [centroid.GetX(), centroid.GetY()]
    if empty:
        envelope: list[float] = []
    else:
        min_x, max_x, min_y, max_y = geom.GetEnvelope()
        envelope = [min_x, min_y, max_x, max_y]
    return {
        "is_valid": bool(geom.IsValid()),
        "is_empty": bool(empty),
        "area": geom.Area(),
        "length": _ogr_length(geom),
        "buffer0_area": buffered if buffered == "error" else buffered.Area(),
        "centroid": centroid_xy,
        "envelope": envelope,
        "make_valid_is_valid": made_valid
        if made_valid == "error"
        else bool(made_valid.IsValid()),
        "make_valid_type": made_valid
        if made_valid == "error"
        else made_valid.GetGeometryName().upper(),
        "make_valid_area": made_valid if made_valid == "error" else made_valid.Area(),
        "simplify_area": simplified if simplified == "error" else simplified.Area(),
    }


def _ogr_length(geom: Any) -> float:
    """``Length()`` as shapely defines it: a polygon's is its perimeter.

    OGR's ``Length()`` is 0 for areal geometries; ``Boundary().Length()`` is the
    like-for-like. This is a definition difference, not a GEOS one.
    """
    if geom.GetGeometryType() & 0xFF == ogr.wkbGeometryCollection:
        # GEOS has no boundary of a collection; sum the parts instead.
        return sum(
            _ogr_length(geom.GetGeometryRef(i)) for i in range(geom.GetGeometryCount())
        )
    if geom.GetDimension() == 2:
        boundary = geom.Boundary()
        return boundary.Length() if boundary is not None else 0.0
    return geom.Length()


def _wkb_geometries(path: Path) -> list[bytes | None]:
    """First layer's features as ISO WKB; ``None`` where OGR found no geometry."""
    dataset = ogr.Open(str(path))
    if dataset is None:
        raise RuntimeError(f"ogr could not open {path}")
    out: list[bytes | None] = []
    for feature in dataset.GetLayer(0):
        geometry = feature.GetGeometryRef()
        out.append(None if geometry is None else bytes(geometry.ExportToIsoWkb()))
    return out


def _read(
    path: Path,
    *,
    parse: Callable[[bytes], Any],
    ops: Callable[[Any], dict[str, Any]],
    union: Callable[[list[Any]], dict[str, Any]],
) -> dict[str, Any]:
    wkbs = _wkb_geometries(path)
    try:
        geoms = [parse(w) for w in wkbs if w is not None]
    except Exception as exc:
        # One exception type for both sides, so identical GEOS refusals agree.
        raise RuntimeError(str(exc)) from exc
    return {
        "features": [ops(g) for g in geoms],
        "union": union(geoms) if geoms else None,
    }


def _shapely_union(geoms: list[Any]) -> dict[str, Any]:
    merged = _guard(lambda: shapely.union_all(geoms))
    if merged == "error":
        return {"union_area": merged, "union_type": merged}
    return {"union_area": merged.area, "union_type": merged.geom_type.upper()}


def _ogr_union(geoms: list[Any]) -> dict[str, Any]:
    def run() -> Any:
        collection = ogr.Geometry(ogr.wkbGeometryCollection)
        for geom in geoms:
            collection.AddGeometry(geom)
        return collection.UnaryUnion()

    merged = _guard(run)
    if merged == "error":
        return {"union_area": merged, "union_type": merged}
    return {"union_area": merged.Area(), "union_type": merged.GetGeometryName().upper()}


def _compare_case(left: Any, right: Any) -> str | None:
    if len(left["features"]) != len(right["features"]):
        return f"{len(left['features'])} features vs {len(right['features'])}"
    problems = []
    for index, (a, b) in enumerate(
        zip(left["features"], right["features"], strict=True)
    ):
        detail = compare_geometry_ops(a, b)
        if detail is not None:
            problems.append(f"feature {index}: {detail}")
    union = compare_geometry_ops(left["union"], right["union"])
    if union is not None:
        problems.append(f"union: {union}")
    return " | ".join(problems) or None


def _cases() -> list[geocase.CaseMetadata]:
    """Vector cases OGR can open and that carry geometry (CSV text columns do
    not: they would compare nothing and pad the `agree` count)."""
    from geocase.catalog.roots import case_roots_by_id

    roots = case_roots_by_id()
    usable = []
    for case in geocase.list_cases(category="vector"):
        try:
            wkbs = _wkb_geometries(roots[case.id] / case.files.primary)
        except RuntimeError:
            continue
        if any(w is not None for w in wkbs):
            usable.append(case)
    return usable


def _ogr_geos_version() -> str:
    return (
        f"{ogr.GetGEOSVersionMajor()}.{ogr.GetGEOSVersionMinor()}"
        f".{ogr.GetGEOSVersionMicro()}"
    )


def test_shapely_and_ogr_geos_agree_on_the_vector_corpus(capsys) -> None:
    cases = _cases()
    shapely_geos = ".".join(str(n) for n in shapely.geos_version)
    ogr_geos = _ogr_geos_version()
    report = run_round(
        title="GEOS operations: shapely vs osgeo.ogr",
        left=lambda p: _read(
            p, parse=shapely.from_wkb, ops=_shapely_ops, union=_shapely_union
        ),
        right=lambda p: _read(
            p,
            parse=ogr.CreateGeometryFromWkb,
            ops=_ogr_ops,
            union=_ogr_union,
        ),
        compare=_compare_case,
        consumer="shapely",
        cases=cases,
        notes=(
            f"{len(cases)} of {len(geocase.list_cases(category='vector'))} vector "
            "cases compared; the rest cannot be opened by OGR here or hold no "
            "geometry (CSV text columns). Both sides parse the same ISO WKB. "
            "OGR exposes no `is_valid` reason, so only the boolean is compared. "
            + (
                "The two GEOS versions differ: a divergence may be a GEOS version "
                "difference (a finding about pinning, not a bug)."
                if shapely_geos != ogr_geos
                else "Same GEOS version on both sides."
            )
        ),
        environment={
            "shapely": shapely.__version__,
            "GEOS (shapely)": shapely.geos_version,
            "GEOS (GDAL)": ogr_geos,
            "GDAL": gdal.__version__,
        },
    )
    with capsys.disabled():
        print("\n" + render_report(report))
    assert report.results, "expected at least some vector cases with geometry"
