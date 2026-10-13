"""Differential testing: pyproj vs GDAL's ``osr`` on every case's CRS (#47).

Both wrap PROJ. A disagreement is therefore in a **binding or its defaults**
(axis order, authority lookup, pipeline choice), not in PROJ itself. If a
finding does look like PROJ, the repro must show it with the ``projinfo`` /
``cs2cs`` command-line tools before anyone files it against PROJ.

Neither side is the oracle; the finding is the disagreement. Each case is read
four ways -- the CRS it *declares* and the CRS the *file* carries (as WKT), each
with traditional-GIS and with authority axis order -- and the facts compared
with :func:`geocase.differential.compare_crs_facts`. A difference between the
two axis passes is expected; a difference between the two libraries *within* a
pass is the finding.

Run it::

    pytest examples/test_differential_proj.py -q -s
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import geocase
from geocase.differential import compare_crs_facts, render_report, run_round

pyproj = pytest.importorskip("pyproj")
osr = pytest.importorskip("osgeo.osr")
gdal = pytest.importorskip("osgeo.gdal")
ogr = pytest.importorskip("osgeo.ogr")

# Point both bindings at one PROJ database. Left to itself osr searches its own
# default list, and where that list's first entries are missing it can fail to
# open `proj.db` that pyproj opens fine -- an environment fault that would
# otherwise report as 148 `errored` cases.
osr.SetPROJSearchPaths([pyproj.datadir.get_data_dir()])
osr.UseExceptions()
gdal.UseExceptions()
ogr.UseExceptions()

_DIRECTIONS = {1: "north", 2: "south", 3: "east", 4: "west", 5: "up", 6: "down"}


def _corners(case: geocase.CaseMetadata) -> list[tuple[float, float]]:
    extent = case.extent
    assert extent is not None
    return [
        (extent.west, extent.south),
        (extent.east, extent.north),
    ]


def _case_for(path: Path) -> geocase.CaseMetadata:
    return geocase.get_case(path.parent.name)


def _file_wkt(path: Path, category: str) -> str | None:
    """The CRS the file carries, as WKT. GDAL does the extraction on both sides,
    so a difference here is in the parse, not in the file reading."""
    if category == "vector":
        dataset = ogr.Open(str(path))
        if dataset is None or dataset.GetLayerCount() == 0:
            return None
        srs = dataset.GetLayer(0).GetSpatialRef()
        return srs.ExportToWkt() if srs is not None else None
    dataset = gdal.Open(str(path))
    wkt = dataset.GetProjection() if dataset is not None else ""
    return wkt or None


def _pyproj_facts(source: str, points: list[tuple[float, float]], *, xy: bool) -> Any:
    crs = pyproj.CRS.from_user_input(source)
    wgs84 = pyproj.CRS.from_epsg(4326)
    # The round trip also goes through WKT2: export from one side, parse, compare.
    pyproj.CRS.from_wkt(crs.to_wkt())
    forward = pyproj.Transformer.from_crs(wgs84, crs, always_xy=xy)
    back = pyproj.Transformer.from_crs(crs, wgs84, always_xy=xy)
    native = [forward.transform(*p) for p in points]
    authority = crs.to_authority()
    return {
        "authority": f"{authority[0]}:{authority[1]}" if authority else None,
        "axis_order": [a.direction for a in crs.axis_info],
        "units": crs.axis_info[0].unit_name,
        "is_geographic": crs.is_geographic,
        "is_projected": crs.is_projected,
        "roundtrip": [list(p) for p in native],
        "to_4326": [list(back.transform(*p)) for p in native],
    }


def _osr_facts(source: str, points: list[tuple[float, float]], *, xy: bool) -> Any:
    crs = osr.SpatialReference()
    crs.SetFromUserInput(source)
    reparsed = osr.SpatialReference()
    reparsed.ImportFromWkt(crs.ExportToWkt(["FORMAT=WKT2"]))
    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    strategy = osr.OAMS_TRADITIONAL_GIS_ORDER if xy else osr.OAMS_AUTHORITY_COMPLIANT
    crs.SetAxisMappingStrategy(strategy)
    wgs84.SetAxisMappingStrategy(strategy)
    forward = osr.CoordinateTransformation(wgs84, crs)
    back = osr.CoordinateTransformation(crs, wgs84)
    native = [forward.TransformPoint(*p)[:2] for p in points]
    name, code = crs.GetAuthorityName(None), crs.GetAuthorityCode(None)
    geographic = bool(crs.IsGeographic())
    return {
        "authority": f"{name}:{code}" if name else None,
        "axis_order": [
            _DIRECTIONS.get(crs.GetAxisOrientation(None, i), "other")
            for i in range(crs.GetAxesCount())
        ],
        "units": crs.GetAngularUnitsName() if geographic else crs.GetLinearUnitsName(),
        "is_geographic": geographic,
        "is_projected": bool(crs.IsProjected()),
        "roundtrip": [list(p) for p in native],
        "to_4326": [list(back.TransformPoint(*p)[:2]) for p in native],
    }


def _reader(
    facts: Callable[..., Any], *, source: str, xy: bool
) -> Callable[[Path], Any]:
    def read(path: Path) -> Any:
        case = _case_for(path)
        if source == "declared":
            text = case.crs
        else:
            text = _file_wkt(path, case.category)
        if text is None:
            return None
        # osr applies the strategy to the transformation only; the definition
        # facts (axis order, units) are independent of it.
        points = _corners(case)
        if xy:
            return facts(text, points, xy=True)
        return facts(text, [(y, x) for x, y in points], xy=False)

    return read


def _cases() -> list[geocase.CaseMetadata]:
    """Cases with a declared CRS and an extent. Skipped: `crs: None` (no CRS to
    parse) and netcdf (no computed extent)."""
    return [
        c
        for c in geocase.list_cases()
        if c.crs is not None and c.extent is not None and c.category != "netcdf"
    ]


def _file_cases() -> list[geocase.CaseMetadata]:
    """Cases whose file GDAL can open and which carries a CRS of its own.

    A file GDAL cannot open fails identically on both sides, which the harness
    classifies as `agree`; a file with no CRS yields nothing to compare. Both
    would pad the `agree` count with cases that compared nothing, so they are
    left out and counted in the report notes instead.
    """
    from geocase.catalog.roots import case_roots_by_id

    roots = case_roots_by_id()
    usable = []
    for case in _cases():
        try:
            wkt = _file_wkt(roots[case.id] / case.files.primary, case.category)
        except RuntimeError:
            continue
        if wkt is not None:
            usable.append(case)
    return usable


@pytest.mark.parametrize("source", ["declared", "file"])
@pytest.mark.parametrize("xy", [True, False], ids=["traditional", "authority"])
def test_pyproj_and_osr_agree_on_the_corpus(source: str, xy: bool, capsys) -> None:
    cases = _cases() if source == "declared" else _file_cases()
    notes = (
        f"{len(cases)} of {len(geocase.list_cases())} cases compared. Left out: "
        "5 with `crs: None`, 6 with no computed extent (netcdf)"
        + (
            "; for the file round also the cases GDAL cannot open here (WKB/WKT "
            "blobs, and Arrow/Parquet without `libgdal-arrow-parquet`) and the "
            "CSVs, which carry no CRS."
            if source == "file"
            else "."
        )
    )
    report = run_round(
        title=f"pyproj vs osr: {source} CRS, {'traditional' if xy else 'authority'} axis order",
        left=_reader(_pyproj_facts, source=source, xy=xy),
        right=_reader(_osr_facts, source=source, xy=xy),
        compare=compare_crs_facts,
        consumer="pyproj",
        cases=cases,
        notes=notes,
        environment={
            "pyproj": pyproj.__version__,
            "PROJ (pyproj)": pyproj.proj_version_str,
            "GDAL": gdal.__version__,
        },
    )
    with capsys.disabled():
        print("\n" + render_report(report))
    assert report.results, "expected at least some cases with a CRS and extent"
