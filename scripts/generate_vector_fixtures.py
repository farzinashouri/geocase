"""Reproducible generator for the bundled SQLite/SpatiaLite vector fixtures.

Implements Step 12 of ``docs/contributing/development-plan.md``. Raster fixtures
have had a generator plus a ``--check`` CI gate since plan 08; vector had
neither, so its binary fixtures were unreproducible hand-made artifacts and
nothing would have noticed one growing 280x. That is exactly what happened: the
five SpatiaLite baselines were committed at 6.7 MB each while holding a single
feature, because SpatiaLite's metadata initialization populates
``spatial_ref_sys`` with 6,559 EPSG rows and ``spatial_ref_sys_aux`` with 6,508
more. Trimming the unused SRS rows and running ``VACUUM`` takes each to 240 KB
(-96.5%) while leaving a fully valid SpatiaLite database.

Usage::

    python scripts/generate_vector_fixtures.py            # write all fixtures
    python scripts/generate_vector_fixtures.py --check    # verify up to date

Why ``--check`` compares *semantics* and not bytes
--------------------------------------------------
``scripts/generate_raster_fixtures.py`` can byte-compare a regenerated GeoTIFF
against the committed one. That model does not work here: SpatiaLite records
wall-clock timestamps and the SQLite/SpatiaLite library versions in its
``spatialite_history`` table, so two runs of the same code on the same machine
produce different bytes, and a different machine (or the CI image) adds version
differences on top. Byte-comparison would therefore fail permanently and
meaninglessly.

Instead ``--check`` verifies everything that a consumer of the fixture can
observe -- layer name, geometry column, field names and types, feature count,
per-feature geometry (as WKB) and attributes, SRID, the SpatiaLite table
signature, and a size budget. That catches real drift, including the 280x
regression this script exists to prevent, without false failures.

Only the SQLite/SpatiaLite family is generated. The GeoJSON, GeoPackage, Parquet,
Feather, Arrow, and Shapefile fixtures remain hand-authored; extending this
generator to cover them is follow-on work.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VECTOR_ROOT = REPO_ROOT / "src" / "geocase" / "data" / "core" / "vector"

# Every bundled SQLite fixture holds exactly one feature at EPSG:4326.
_SRID = 4326

# Size budget per generated fixture. The trimmed SpatiaLite files land at
# ~240 KB and the plain-SQLite one at ~24 KB; 512 KB leaves room for ordinary
# variation across SpatiaLite versions while still failing loudly if the
# untrimmed 6.7 MB form ever comes back.
_MAX_BYTES = 512 * 1024

# SpatiaLite drops these rows in on initialization. Everything not referenced by
# ``geometry_columns`` is dead weight; 0 and -1 are SpatiaLite's own sentinels
# and are kept so the database stays structurally valid.
_TRIM_SQL = """
DELETE FROM spatial_ref_sys     WHERE srid NOT IN (SELECT srid FROM geometry_columns)
                                  AND srid NOT IN (0, -1, 4326);
DELETE FROM spatial_ref_sys_aux WHERE srid NOT IN (SELECT srid FROM geometry_columns);
"""


@dataclass
class VectorSpec:
    """Declarative description of one bundled SQLite vector fixture."""

    case_id: str
    #: Path of the fixture relative to ``VECTOR_ROOT``.
    rel_path: str
    #: Table/layer name inside the database.
    layer: str
    #: OGR geometry type name, e.g. ``wkbPoint``.
    geom_type: str
    #: Geometry as WKT; the single feature's shape.
    wkt: str
    #: ``[(field_name, ogr_type_name, value), ...]`` for the single feature.
    fields: list[tuple[str, str, object]] = field(default_factory=list)
    #: SpatiaLite metadata + R-tree index, versus a plain OGR SQLite database.
    spatialite: bool = True

    @property
    def path(self) -> Path:
        return VECTOR_ROOT / self.rel_path


def _specs() -> list[VectorSpec]:
    """Declare every bundled SQLite fixture.

    Geometries and attributes are declared literally rather than derived from
    each case's ``params.canonical_source_case_id``. Those declarations do not
    currently hold for the SpatiaLite five -- ``point_sqlite_baseline`` is
    ``POINT (10 52)`` while its declared source ``simple_valid_point`` is
    ``POINT (12.5 55.7)`` -- so deriving would silently rewrite the fixtures and
    break the tests that assert against them.
    """
    def std(name: str) -> list[tuple[str, str, object]]:
        """The shared ``id``/``name`` attribute pair used by the SpatiaLite five."""
        return [("id", "OFTInteger64", 1), ("name", "OFTString", name)]

    return [
        VectorSpec(
            case_id="point_sqlite_baseline",
            rel_path="point/sqlite/point_sqlite_baseline/data.sqlite",
            layer="data",
            geom_type="wkbPoint",
            wkt="POINT (10 52)",
            fields=std("sample_point"),
        ),
        VectorSpec(
            case_id="linestring_sqlite_baseline",
            rel_path="linestring/sqlite/linestring_sqlite_baseline/data.sqlite",
            layer="data",
            geom_type="wkbLineString",
            wkt="LINESTRING (0 0,1 1,2 0)",
            fields=std("sample_linestring"),
        ),
        VectorSpec(
            case_id="multipoint_sqlite_baseline",
            rel_path="multipoint/sqlite/multipoint_sqlite_baseline/data.sqlite",
            layer="data",
            geom_type="wkbMultiPoint",
            wkt="MULTIPOINT (0 0,1 1,2 2)",
            fields=std("sample_multipoint"),
        ),
        VectorSpec(
            case_id="multilinestring_sqlite_baseline",
            rel_path=(
                "multilinestring/sqlite/multilinestring_sqlite_baseline/data.sqlite"
            ),
            layer="data",
            geom_type="wkbMultiLineString",
            wkt="MULTILINESTRING ((0 0,1 1),(2 2,3 3))",
            fields=std("sample_multilinestring"),
        ),
        VectorSpec(
            case_id="multipolygon_sqlite_baseline",
            rel_path="multipolygon/sqlite/multipolygon_sqlite_baseline/data.sqlite",
            layer="data",
            geom_type="wkbMultiPolygon",
            wkt="MULTIPOLYGON (((0 0,1 0,1 1,0 1,0 0)),((2 2,3 2,3 3,2 3,2 2)))",
            fields=std("sample_multipolygon"),
        ),
        # Deliberately plain SQLite, not SpatiaLite: this case tags only
        # ``sqlite`` and exists to contrast OGR's non-SpatiaLite driver path
        # against the five above, which tag ``spatialite``.
        VectorSpec(
            case_id="polygon_sqlite_baseline",
            rel_path="polygon/sqlite/polygon_sqlite_baseline/geometry.sqlite",
            layer="geometry",
            geom_type="wkbPolygon",
            wkt="POLYGON ((10 50,11 50,11 51,10 51,10 50))",
            fields=[("name", "OFTString", "baseline_polygon")],
            spatialite=False,
        ),
    ]


def _trim_and_vacuum(path: Path) -> None:
    """Drop unused SRS rows and compact the database in place."""
    con = sqlite3.connect(path)
    try:
        tables = {
            r[0]
            for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "spatial_ref_sys_aux" in tables:
            con.executescript(_TRIM_SQL)
            con.commit()
        con.execute("VACUUM")
    finally:
        con.close()


def _write_fixture(spec: VectorSpec, dest: Path) -> None:
    """Create *dest* from *spec* using OGR, then trim and compact it."""
    from osgeo import ogr, osr

    ogr.UseExceptions()

    if dest.exists():
        dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)

    driver = ogr.GetDriverByName("SQLite")
    ds_options = ["SPATIALITE=YES"] if spec.spatialite else []
    ds = driver.CreateDataSource(str(dest), options=ds_options)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(_SRID)

    layer_options = ["GEOMETRY_NAME=GEOMETRY"]
    if spec.spatialite:
        layer_options.append("SPATIAL_INDEX=YES")
    else:
        layer_options.append("FORMAT=WKB")

    layer = ds.CreateLayer(
        spec.layer,
        srs,
        getattr(ogr, spec.geom_type),
        options=layer_options,
    )

    for name, type_name, _value in spec.fields:
        layer.CreateField(ogr.FieldDefn(name, getattr(ogr, type_name)))

    feature = ogr.Feature(layer.GetLayerDefn())
    for name, _type_name, value in spec.fields:
        feature.SetField(name, value)
    feature.SetGeometry(ogr.CreateGeometryFromWkt(spec.wkt))
    layer.CreateFeature(feature)

    feature = None
    layer = None
    ds = None

    _trim_and_vacuum(dest)


def _fingerprint(path: Path) -> dict[str, object]:
    """Return everything observable about a fixture, excluding volatile metadata.

    Deliberately excludes ``spatialite_history`` (wall-clock timestamps and
    library versions) and raw file bytes -- see the module docstring.
    """
    from osgeo import ogr

    ogr.UseExceptions()

    ds = ogr.Open(str(path))
    if ds is None:
        raise RuntimeError(f"OGR could not open {path}")
    layer = ds.GetLayer(0)
    defn = layer.GetLayerDefn()

    # SQLite identifiers are case-insensitive, and the case GDAL emits for the
    # geometry column (and the derived ``idx_<table>_<geom>`` R-tree tables)
    # varies by version. Casefold every identifier so a GDAL upgrade does not
    # register as fixture drift -- the exact false failure this check exists to
    # avoid. Values and types are compared as-is.
    fields = [
        (defn.GetFieldDefn(i).GetName().lower(), defn.GetFieldDefn(i).GetTypeName())
        for i in range(defn.GetFieldCount())
    ]

    features = []
    layer.ResetReading()
    for feat in layer:
        geom = feat.GetGeometryRef()
        features.append(
            (
                geom.ExportToWkb() if geom is not None else None,
                tuple(feat.GetField(n) for n, _ in fields),
            )
        )

    srs = layer.GetSpatialRef()
    epsg = srs.GetAuthorityCode(None) if srs is not None else None

    # Read everything off the layer before releasing the datasource below;
    # the layer is owned by it and becomes invalid once it is closed.
    layer_name = layer.GetName().lower()
    geom_column = layer.GetGeometryColumn().lower()

    con = sqlite3.connect(path)
    try:
        tables = sorted(
            r[0].lower()
            for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        )
        srs_rows = con.execute("SELECT count(*) FROM spatial_ref_sys").fetchone()[0]
    finally:
        con.close()

    layer = None
    ds = None
    return {
        "layer": layer_name,
        "geom_column": geom_column,
        "fields": fields,
        "features": features,
        "epsg": str(epsg) if epsg is not None else None,
        "tables": tables,
        "spatial_ref_sys_rows": srs_rows,
    }


def _diff(expected: dict[str, object], actual: dict[str, object]) -> list[str]:
    """Return human-readable differences between two fingerprints."""
    return [
        f"{key}: expected {expected[key]!r}, got {actual[key]!r}"
        for key in sorted(expected)
        if expected[key] != actual[key]
    ]


def _has_spatialite() -> bool:
    """Return whether this GDAL build can actually create SpatiaLite databases.

    The GDAL ``SQLite`` driver is always present, but ``SPATIALITE=YES`` only
    works when GDAL was linked against libspatialite. Probing by creating a
    throwaway database is the only reliable test.
    """
    from osgeo import ogr

    driver = ogr.GetDriverByName("SQLite")
    if driver is None:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.sqlite"
        try:
            ogr.DontUseExceptions()
            ds = driver.CreateDataSource(str(probe), options=["SPATIALITE=YES"])
            if ds is None:
                return False
            ds = None
            con = sqlite3.connect(probe)
            try:
                tables = {
                    r[0]
                    for r in con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            finally:
                con.close()
            return "spatial_ref_sys_aux" in tables
        except Exception:
            return False
        finally:
            ogr.UseExceptions()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or verify bundled SQLite/SpatiaLite vector fixtures."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any fixture has drifted, instead of writing it.",
    )
    parser.add_argument(
        "--vector-root",
        type=Path,
        default=VECTOR_ROOT,
        help="Root directory for vector case folders.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()

    try:
        from osgeo import ogr  # noqa: F401
    except ImportError:
        print(
            "ERROR: this generator needs the GDAL Python bindings (osgeo), which "
            "are source-only on PyPI. Use the conda environment "
            "(see docs/contributing/workflow.md).",
            file=sys.stderr,
        )
        return 2

    if not _has_spatialite():
        # Exit 2, not 1: this is "cannot verify", which is a different failure
        # from "fixtures have drifted" and needs a different fix. Never degrade
        # to a silent pass -- a gate that quietly checks nothing is worse than
        # no gate, because it advertises coverage that does not exist.
        print(
            "ERROR: GDAL is present but has no SpatiaLite support, so the "
            "SpatiaLite fixtures cannot be generated or verified.\n"
            "  Locally: use the conda environment (it bundles libspatialite).\n"
            "  In CI: the gdal 'ubuntu-small' image omits SpatiaLite; switch the "
            "job to 'ubuntu-full' or install libsqlite3-mod-spatialite.",
            file=sys.stderr,
        )
        return 2

    specs = _specs()

    if args.check:
        problems: list[str] = []
        for spec in specs:
            dest = args.vector_root / spec.rel_path
            if not dest.exists():
                problems.append(f"{spec.case_id}: missing ({dest})")
                continue

            size = dest.stat().st_size
            if size > _MAX_BYTES:
                problems.append(
                    f"{spec.case_id}: {size / 1024:.0f} KB exceeds the "
                    f"{_MAX_BYTES / 1024:.0f} KB budget -- was it regenerated "
                    f"without trimming spatial_ref_sys?"
                )

            with tempfile.TemporaryDirectory() as tmp:
                candidate = Path(tmp) / dest.name
                _write_fixture(spec, candidate)
                for line in _diff(_fingerprint(candidate), _fingerprint(dest)):
                    problems.append(f"{spec.case_id}: {line}")

        if problems:
            print("Vector fixtures out of date:")
            for line in problems:
                print(f"  {line}")
            return 1
        print(f"All vector fixtures up to date ({len(specs)} fixtures)")
        return 0

    for spec in specs:
        dest = args.vector_root / spec.rel_path
        _write_fixture(spec, dest)
        print(f"Wrote {dest.relative_to(REPO_ROOT)} ({dest.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
