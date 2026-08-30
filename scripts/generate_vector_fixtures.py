"""Reproducible generator for every bundled ``*_baseline`` vector fixture.

Started life (plan 12) covering only the five SpatiaLite databases, because
those were the ones that had silently grown 280x -- 6.7 MB each to hold a single
feature, since SpatiaLite's metadata initialization populates ``spatial_ref_sys``
with 6,559 EPSG rows and ``spatial_ref_sys_aux`` with 6,508 more. Trimming the
unused SRS rows and running ``VACUUM`` takes each to 240 KB (-96.5%) while
leaving a fully valid SpatiaLite database. That is still what happens below.

Plan 13 extended it to all 60 cases tagged ``cross_format_canonical``, and made
the geometry *derived* rather than declared -- see :func:`_specs`.

Usage::

    python scripts/generate_vector_fixtures.py            # write all fixtures
    python scripts/generate_vector_fixtures.py --check    # verify up to date

One geometry, many formats
--------------------------
A ``<geomtype>_<format>_baseline`` case exists so a consumer can hold the
geometry constant and vary only the container. Each declares which geometry it
holds via ``params.canonical_source_case_id``, pointing at the GeoJSON
``simple_valid_<geomtype>`` case. This generator dereferences that link and
writes exactly that geometry, so the promise is kept by construction rather than
by whoever last hand-edited a fixture.

It reads the canonical with ``json`` + ``shapely.geometry.shape`` rather than
``geocase.load_case``: a generator must not depend on the package whose data it
generates, or a bug in the loader can launder itself into the fixtures and then
be confirmed by the loader that produced it. ``verify_dist.py`` was made
independent of the package for the same reason.

Why ``--check`` compares *semantics* and not bytes
--------------------------------------------------
``scripts/generate_raster_fixtures.py`` can byte-compare a regenerated GeoTIFF
against the committed one. That model works here for exactly three formats:

===================  =============  ==================================
Format               Reproducible?  Volatile content
===================  =============  ==================================
WKT, WKB, CSV_WKT    yes            none -- no driver in the loop
GML, KML             yes            none, but written through OGR
FlatGeobuf           per GDAL       none
Shapefile            **no**         ``.dbf`` bytes 1-3 are the last-edit date
GPKG                 **no**         ``gpkg_contents.last_change`` is wall-clock
SQLite/SpatiaLite    **no**         ``spatialite_history`` timestamps + versions
Parquet/Feather/     **no**         ``created_by`` footer, geopandas creator
  Arrow/GeoArrow                      metadata
===================  =============  ==================================

So the three pure-Python formats are byte-compared and everything else is
compared on what a consumer can actually observe -- field names and types,
feature count, per-feature geometry and attributes, SRID, and a size budget.
That catches real drift, including the 280x regression this script exists to
prevent, without failing daily on a date byte.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
VECTOR_ROOT = REPO_ROOT / "src" / "geocase" / "data" / "core" / "vector"

# Every fixture in the cross-format *baseline families* holds exactly one
# feature at EPSG:4326 -- that one-to-one correspondence is what makes the
# families comparable. The procedural cases below are not family members and
# are not bound by it (they are still single-feature today, but for their own
# reasons).
_SRID = 4326

#: Tag and param that together declare "this case mirrors that case's geometry".
#: Kept consistent with ``scripts/validate_catalog.py``, which checks the pair is
#: biconditional; this script only consumes the param.
_CANONICAL_PARAM = "canonical_source_case_id"

# Size budget per generated fixture, counting the primary file plus every
# sidecar sharing its stem (a Shapefile is five files, a GML two).
#
# The trimmed SpatiaLite files land at ~240 KB; 512 KB leaves room for ordinary
# variation across SpatiaLite versions while still failing loudly if the
# untrimmed 6.7 MB form ever comes back. Nothing else is anywhere near that --
# the largest is a ~98 KB GeoPackage -- so they get a tighter bound.
_MAX_BYTES = 512 * 1024
_MAX_BYTES_NON_SPATIALITE = 256 * 1024

# SpatiaLite drops these rows in on initialization. Everything not referenced by
# ``geometry_columns`` is dead weight; 0 and -1 are SpatiaLite's own sentinels
# and are kept so the database stays structurally valid.
_TRIM_SQL = """
DELETE FROM spatial_ref_sys     WHERE srid NOT IN (SELECT srid FROM geometry_columns)
                                  AND srid NOT IN (0, -1, 4326);
DELETE FROM spatial_ref_sys_aux WHERE srid NOT IN (SELECT srid FROM geometry_columns);
"""

#: Fixed wall-clock stamp written into GeoPackage metadata, so regenerating
#: twice does not leave the file dirty in ``git status``. See
#: :func:`_freeze_gpkg_last_change`.
_FROZEN_TIMESTAMP = "2024-01-01T00:00:00.000Z"

#: ``case.yaml`` ``format`` -> OGR driver name.
_OGR_DRIVERS: dict[str, str] = {
    "Shapefile": "ESRI Shapefile",
    "GPKG": "GPKG",
    "SQLite": "SQLite",
    "GML": "GML",
    "KML": "KML",
    "FlatGeobuf": "FlatGeobuf",
}

#: Formats written by hand in pure Python, with no driver in the loop. These are
#: the only ones ``--check`` can byte-compare.
_TEXT_FORMATS = frozenset({"WKT", "WKB", "CSV_WKT"})

#: Every format written in pure Python, and therefore every format ``--check``
#: can compare as raw bytes. GeoJSON has its own writer (``_write_geojson``)
#: rather than sharing ``_write_text``'s body, but it is byte-comparable for
#: the same reason: no driver, so nothing stamps a version or a timestamp in.
_BYTE_COMPARABLE_FORMATS = _TEXT_FORMATS | {"GeoJSON"}

#: Formats written through geopandas' own writers.
_GEOPANDAS_FORMATS = frozenset({"Parquet", "Feather"})

#: Formats written as a raw Arrow IPC *file*. Not a stream: ``VectorCase.load()``
#: reads these with ``pyarrow.ipc.open_file``, which rejects the stream framing.
_ARROW_FORMATS = frozenset({"Arrow", "GeoArrow"})

#: ``case.yaml`` ``geometry_type`` -> the ``osgeo.ogr`` constant name.
_OGR_GEOMETRY_TYPES: dict[str, str] = {
    "Point": "wkbPoint",
    "LineString": "wkbLineString",
    "Polygon": "wkbPolygon",
    "MultiPoint": "wkbMultiPoint",
    "MultiLineString": "wkbMultiLineString",
    "MultiPolygon": "wkbMultiPolygon",
}

#: The unified attribute schema. Every baseline gets these two columns and
#: nothing else.
#:
#: Before unification, ``polygon_geopackage_baseline`` carried ``id, name,
#: area_sqkm`` and ``polygon_shapefile_baseline`` carried ``name``, so a consumer
#: diffing the two could not tell which differences were *the format* and which
#: were fixture accident -- which is the family's entire pedagogical payload.
#: Format-idiomatic schemas are covered deliberately, and better, by
#: ``special/encoding/*``; duplicating that concern here is what let
#: ``multilinestring_shapefile_baseline`` ship a column named ``segment_co``, a
#: silent DBF 10-character truncation of ``segment_count``.
#:
#: Both names are <=10 characters, so no format needs per-driver field-name
#: special-casing.
_ID_FIELD = "id"
_NAME_FIELD = "name"


@dataclass
class VectorSpec:
    """One bundled baseline fixture, fully derived from its ``case.yaml``."""

    case_id: str
    #: Path of the primary file relative to ``VECTOR_ROOT``.
    rel_path: str
    #: ``case.yaml`` ``format`` value, e.g. ``"GPKG"``.
    format: str
    #: Table/layer name inside the container. Always the primary file's stem,
    #: which is the convention the committed fixtures already follow.
    layer: str
    #: Declared ``geometry_type``, e.g. ``"Polygon"``.
    geometry_type: str
    #: The canonical geometry, oriented CCW if polygonal. A shapely geometry.
    geometry: Any
    #: SpatiaLite metadata + R-tree index, versus a plain OGR SQLite database.
    spatialite: bool = False
    #: Write the 2.5D ("Z") form of ``geometry_type``. Keyed on a flag rather
    #: than a ``"PolygonZ"`` string so ``geometry_type`` stays inside the
    #: values ``SuiteSelection.geometry_type`` filters on.
    has_z: bool = False
    #: Value written to the ``id`` column. Overridden only by the int64 case:
    #: 9007199254740993 is 2^53 + 1, the first integer a float64 cannot hold.
    id_value: int = 1

    @property
    def path(self) -> Path:
        return VECTOR_ROOT / self.rel_path

    @property
    def ogr_geometry_type(self) -> str:
        name = _OGR_GEOMETRY_TYPES[self.geometry_type]
        return f"{name}25D" if self.has_z else name


# ---------------------------------------------------------------------------
# Deriving the specs from the catalog
# ---------------------------------------------------------------------------


def _read_case_files(vector_root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    """Return ``{case_id: (case_dir, parsed case.yaml)}`` for every vector case.

    Parsed with plain ``yaml.safe_load`` rather than ``CaseMetadata``: this
    script deliberately does not import ``geocase`` (see the module docstring),
    and every field it needs is a top-level scalar.
    """
    cases: dict[str, tuple[Path, dict[str, Any]]] = {}
    for case_yaml in sorted(vector_root.rglob("case.yaml")):
        data = yaml.safe_load(case_yaml.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        case_id = data.get("id")
        if not isinstance(case_id, str):
            continue
        if case_id in cases:
            raise RuntimeError(f"Duplicate case id '{case_id}' at {case_yaml}")
        cases[case_id] = (case_yaml.parent, data)
    return cases


def _canonical_geometry(
    source_id: str,
    cases: dict[str, tuple[Path, dict[str, Any]]],
) -> Any:
    """Return the single geometry held by canonical case *source_id*.

    The single-feature requirement below scopes the *canonical sources of the
    transcoding families*, whose purpose is one-to-one comparability across
    formats. It is not a claim about the catalog at large: the procedural cases
    are built by :func:`_procedural_specs` and never reach this function.

    Read straight off disk with ``json`` + ``shapely.geometry.shape``. Polygonal
    geometries are oriented to the RFC 7946 / OGC right-hand rule (exterior CCW,
    interior CW) before being handed to any writer. The committed canonicals are
    already CCW, so this is defensive rather than corrective -- but it makes the
    orientation a property of this script rather than of six JSON files.

    Note that OGR will promptly *reverse* that orientation when writing a
    Shapefile, because the Shapefile specification mandates the opposite. That
    is real, documented behaviour and is preserved deliberately: see the
    ``shapefile_ring_orientation`` case, and the winding-insensitive comparison
    in ``tests/unit/test_cross_format_canonical.py``.
    """
    from shapely.geometry import shape
    from shapely.geometry.polygon import orient

    try:
        case_dir, data = cases[source_id]
    except KeyError:
        raise RuntimeError(
            f"Canonical source case '{source_id}' is not a known vector case"
        ) from None

    if data.get("format") != "GeoJSON":
        raise RuntimeError(
            f"Canonical source '{source_id}' has format {data.get('format')!r}; "
            f"the canonical must be the GeoJSON reference"
        )

    primary = case_dir / data["files"]["primary"]
    payload = json.loads(primary.read_text(encoding="utf-8"))
    features = payload["features"]
    if len(features) != 1:
        raise RuntimeError(
            f"Canonical source '{source_id}' holds {len(features)} features; "
            f"the baseline families compare exactly one"
        )

    geometry = shape(features[0]["geometry"])
    if geometry.geom_type in {"Polygon", "MultiPolygon"}:
        geometry = orient(geometry, sign=1.0)
    return geometry


# ---------------------------------------------------------------------------
# Procedural geometry -- the non-trivial cases
# ---------------------------------------------------------------------------
#
# The hand-authored canonicals top out at 10 vertices and 12 of them are plain
# 5-vertex rectangles, so the bundled catalog cannot fail a vertex-dense
# consumer. These two generators fix that without touching the transcoding
# families: their output becomes its own cases, with no canonical source.
#
# Everything here is pure ``math``. **No ``random``, seeded or otherwise** --
# a PRNG is reproducible only for as long as CPython's stream is, and the
# fixture tree is gated on byte-identical regeneration.

#: Coordinates are rounded to this many decimals, matching
#: ``catalog_extent.py``'s PRECISION, so nothing churns on floating-point noise
#: across platforms or libm versions.
_PROCEDURAL_PRECISION = 6


def _round_point(x: float, y: float) -> tuple[float, float]:
    return round(x, _PROCEDURAL_PRECISION), round(y, _PROCEDURAL_PRECISION)


def _koch_segment(
    a: tuple[float, float], b: tuple[float, float], depth: int
) -> list[tuple[float, float]]:
    """Return the points of the Koch curve from *a* to *b*, excluding *b*.

    One pass replaces ``a -> b`` with ``a, a+(b-a)/3, apex, a+2(b-a)/3``, the
    apex being the middle third's third point rotated 60 degrees outward.
    """
    if depth <= 0:
        return [a]

    (ax, ay), (bx, by) = a, b
    dx, dy = (bx - ax) / 3.0, (by - ay) / 3.0
    p1 = (ax + dx, ay + dy)
    p2 = (ax + 2.0 * dx, ay + 2.0 * dy)

    # Rotate (p2 - p1) by +60 degrees about p1 to raise the apex outward.
    cos60, sin60 = 0.5, math.sqrt(3.0) / 2.0
    ex, ey = p2[0] - p1[0], p2[1] - p1[1]
    apex = (p1[0] + ex * cos60 - ey * sin60, p1[1] + ex * sin60 + ey * cos60)

    return (
        _koch_segment(a, p1, depth - 1)
        + _koch_segment(p1, apex, depth - 1)
        + _koch_segment(apex, p2, depth - 1)
        + _koch_segment(p2, b, depth - 1)
    )


def _koch_ring(
    sides: int, depth: int, radius: float, centre: tuple[float, float]
) -> Any:
    """A Koch snowflake polygon: a regular *sides*-gon with *depth* Koch passes.

    The result has exactly ``sides * 4**depth + 1`` coordinates, the closing
    point included -- a closed form, so a case's vertex count is chosen rather
    than discovered.
    """
    from shapely.geometry import Polygon

    cx, cy = centre
    corners = [
        (
            cx + radius * math.cos(2.0 * math.pi * i / sides),
            cy + radius * math.sin(2.0 * math.pi * i / sides),
        )
        for i in range(sides)
    ]

    points: list[tuple[float, float]] = []
    for i in range(sides):
        points.extend(_koch_segment(corners[i], corners[(i + 1) % sides], depth))

    ring = [_round_point(x, y) for x, y in points]
    return Polygon(ring + [ring[0]])


def _dense_parametric_ring(
    vertices: int,
    radius: float,
    lobes: int,
    amplitude: float,
    centre: tuple[float, float],
) -> Any:
    """A lobed closed ring: ``r(theta) = radius * (1 + amplitude*cos(lobes*theta))``.

    *vertices* is an exact dial on the coordinate count, which is the point:
    fixture size is chosen up front rather than discovered after writing.
    """
    from shapely.geometry import Polygon

    cx, cy = centre
    ring = []
    for i in range(vertices):
        theta = 2.0 * math.pi * i / vertices
        r = radius * (1.0 + amplitude * math.cos(lobes * theta))
        ring.append(_round_point(cx + r * math.cos(theta), cy + r * math.sin(theta)))

    return Polygon(ring + [ring[0]])


#: The procedural cases, keyed by case id. The geometry is built here rather
#: than read off disk, so these deliberately carry no ``canonical_source_case_id``
#: and no ``cross_format_canonical`` tag: they are not members of the 60-case
#: transcoding family and must not be compared against one.
def _procedural_geometries() -> dict[str, Any]:
    # The dense ring is built once and shared: the GeoPackage case is the same
    # geometry through a driver, so building it twice would let the two forms
    # drift apart under an edit to the parameters.
    dense_ring = _dense_parametric_ring(
        vertices=4096, radius=1.2, lobes=17, amplitude=0.18, centre=(24.9, -30.6)
    )
    return {
        "fractal_coastline_polygon": _koch_ring(
            sides=6, depth=4, radius=1.5, centre=(-8.5, 41.2)
        ),
        "dense_ring_polygon_4k": dense_ring,
        "dense_ring_polygon_4k_gpkg": dense_ring,
    }


def _procedural_specs(vector_root: Path = VECTOR_ROOT) -> list[VectorSpec]:
    """Build one spec per procedural case present on disk, sorted by id.

    Same ``VectorSpec`` and therefore the same write backends, fingerprints and
    ``--check`` semantics as the transcoding family -- only the *source* of the
    geometry differs.
    """
    cases = _read_case_files(vector_root)
    geometries = _procedural_geometries()

    specs: list[VectorSpec] = []
    for case_id, geometry in sorted(geometries.items()):
        entry = cases.get(case_id)
        if entry is None:
            raise RuntimeError(
                f"Procedural case '{case_id}' has no case.yaml under {vector_root}"
            )
        case_dir, data = entry
        primary = data["files"]["primary"]
        specs.append(
            VectorSpec(
                case_id=case_id,
                rel_path=(case_dir / primary).relative_to(vector_root).as_posix(),
                format=data["format"],
                layer=Path(primary).stem,
                geometry_type=data["geometry_type"],
                geometry=geometry,
                spatialite="spatialite" in (data.get("tags") or []),
            )
        )
    return specs


#: The Z ring, shared by both dimensional cases so they cannot drift apart.
#: A closed 5-vertex ring with a Z ramp: the elevations are distinct and
#: non-monotonic, so a dropped or truncated dimension is visible rather than
#: coincidentally right.
_Z_RING = (
    (12.50, 55.70, 0.0),
    (12.52, 55.70, 12.5),
    (12.52, 55.72, 25.0),
    (12.50, 55.72, 12.5),
    (12.50, 55.70, 0.0),
)

#: 2^53 + 1 -- the first integer a float64 cannot represent. A reader that
#: routes ids through a double returns ...992.
_BIG_ID = 9007199254740993


def _dimensional_specs(vector_root: Path = VECTOR_ROOT) -> list[VectorSpec]:
    """The Z-coordinate cases.

    Deliberately **not** family members: no ``canonical_source_case_id`` and no
    ``cross_format_canonical`` tag, the same choice plan 33 made for the
    procedural cases and for the same reason -- they vary a property the family
    holds constant, so diffing them against a 2D canonical would report a
    difference that is the entire point of the fixture.

    The pair is what earns two files. Shapely round-tripping Z through WKB
    proves little; a GPKG that still has Z after OGR wrote it proves the
    *driver* preserved a dimension it is free to drop silently.
    """
    from shapely.geometry import Polygon

    geometry = Polygon(_Z_RING)
    cases = _read_case_files(vector_root)

    specs: list[VectorSpec] = []
    for case_id, fmt in (("polygon_z_wkb", "WKB"), ("polygon_z_gpkg", "GPKG")):
        entry = cases.get(case_id)
        if entry is None:
            raise RuntimeError(
                f"Dimensional case '{case_id}' has no case.yaml under {vector_root}"
            )
        case_dir, data = entry
        primary = data["files"]["primary"]
        specs.append(
            VectorSpec(
                case_id=case_id,
                rel_path=(case_dir / primary).relative_to(vector_root).as_posix(),
                format=fmt,
                layer=Path(primary).stem,
                geometry_type=data["geometry_type"],
                geometry=geometry,
                has_z=True,
                # The int64 rider rides on the GPKG sibling, which is the half
                # with a real attribute table to carry it.
                id_value=_BIG_ID if fmt == "GPKG" else 1,
            )
        )
    return specs


# ---------------------------------------------------------------------------
# The large cases -- plan 28 phase 3
# ---------------------------------------------------------------------------
#
# Every other fixture in this file holds one feature. These hold 10,000, and
# the count is the point: with one feature every batch boundary is the same
# boundary and every partial read is the full read, so a probe for
# ``skip_features``, ``max_features``, Arrow chunking or a paged read executes
# without being able to fail. Each case puts its one defect *past* the
# boundary, where only a full read finds it.
#
# They go through their own spec type and their own writer rather than
# widening ``VectorSpec``: that dataclass carries a single ``geometry`` and its
# writers emit exactly one feature, and the ``--check`` fingerprints compare
# every feature's WKB and attributes -- which is right for one feature and
# 10,000 WKB blobs of noise for these.
#
# Same discipline as everything else here: pure ``math``/``itertools``, **no
# ``random``**, so regeneration is byte-identical.

#: The large cases, by id. Listed rather than discovered by tag: each one has a
#: bespoke attribute recipe in :func:`_large_frame`, so a case that reached
#: this set without a recipe is an error worth raising loudly.
_LARGE_CASE_IDS = frozenset(
    {
        "invalid_geometry_at_scale_gpkg",
        "null_after_batch_boundary_gpkg",
        "mixed_timezone_after_batch_gpkg",
    }
)

#: Grid origin and step for the large cases' geometry. A regular lattice, not a
#: cluster: the geometry is deliberately the *uninteresting* part of these
#: cases, so nothing about the defect can be confused with a geometric quirk.
#: 100 columns x 0.005 degrees spans 0.5 degrees of longitude.
_LARGE_ORIGIN = (10.0, 50.0)
_LARGE_STEP = 0.005
_LARGE_COLUMNS = 100

#: Side of the triangles in ``invalid_geometry_at_scale_gpkg``. Comfortably
#: inside ``_LARGE_STEP`` so no two features touch -- an accidental overlap
#: would make the *corpus* topologically interesting in a way the case does not
#: declare.
_LARGE_TRIANGLE = 0.003

#: The two UTC offsets in ``mixed_timezone_after_batch_gpkg``. 4.5 hours apart,
#: so the divergent row lands on a different UTC instant and a reader that
#: silently drops the offset is visible rather than coincidentally right.
_LARGE_TZ_MAJORITY = "+01:00"
_LARGE_TZ_OUTLIER = "+05:30"
_LARGE_TZ_WALL_CLOCK = "2024-01-01T12:00:00.000"


@dataclass
class LargeVectorSpec:
    """One of the plan 28 phase 3 cases: 10,000 features, one defect past the boundary."""

    case_id: str
    #: Path of the primary file relative to ``VECTOR_ROOT``.
    rel_path: str
    #: Table/layer name inside the GeoPackage. Always the primary file's stem.
    layer: str
    #: Declared ``geometry_type``.
    geometry_type: str
    #: Total feature count, defect row included.
    feature_count: int


def _large_grid_point(index: int) -> tuple[float, float]:
    """Return the lattice position of feature *index*, rounded like every other fixture."""
    x = _LARGE_ORIGIN[0] + (index % _LARGE_COLUMNS) * _LARGE_STEP
    y = _LARGE_ORIGIN[1] + (index // _LARGE_COLUMNS) * _LARGE_STEP
    return _round_point(x, y)


def _large_triangle(index: int) -> Any:
    """A valid 3-vertex triangle at feature *index*'s lattice position."""
    from shapely.geometry import Polygon

    x, y = _large_grid_point(index)
    return Polygon(
        [
            (x, y),
            _round_point(x + _LARGE_TRIANGLE, y),
            _round_point(x + _LARGE_TRIANGLE / 2.0, y + _LARGE_TRIANGLE),
        ]
    )


def _large_bowtie() -> Any:
    """A self-intersecting quadrilateral -- the one invalid feature in 10,000.

    The classic bowtie: the ring's second and fourth vertices are swapped, so
    the two edges cross at the centre. ``shapely`` reports
    ``Self-intersection``; GEOS, GDAL and PostGIS all agree it is invalid,
    which matters because a case whose invalidity is engine-dependent tests the
    engine rather than the consumer (that is what
    ``ambiguous_engine_dependent_polygon`` is for).
    """
    from shapely.geometry import Polygon

    x, y = _LARGE_ORIGIN
    side = _LARGE_TRIANGLE
    return Polygon(
        [
            (x, y),
            _round_point(x + side, y + side),
            _round_point(x + side, y),
            _round_point(x, y + side),
        ]
    )


def _large_frame(spec: LargeVectorSpec) -> Any:
    """Return the full GeoDataFrame for *spec* -- geometry, attributes and defect.

    Split out from the writer so a test can build the frame twice and compare,
    which is what proves determinism without writing a megabyte to disk.
    """
    import geopandas
    import pandas as pd
    from shapely.geometry import Point

    n = spec.feature_count
    ids = list(range(n))

    if spec.case_id == "invalid_geometry_at_scale_gpkg":
        geometries = [_large_triangle(i) for i in range(n)]
        # The defect is the *last* feature, not a middle one: a consumer that
        # reads any prefix of the file -- one batch, half the file, all but the
        # final row -- sees clean data. A middle position would be found by
        # roughly half of all partial reads and would blunt the claim.
        geometries[-1] = _large_bowtie()
        attributes: dict[str, Any] = {"id": ids}
    else:
        geometries = [Point(*_large_grid_point(i)) for i in range(n)]
        if spec.case_id == "null_after_batch_boundary_gpkg":
            # ``Int64`` (the pandas nullable dtype), not ``int64``: writing a
            # NULL through a numpy int column is impossible, and writing it
            # through a float column would make the file itself float -- which
            # is the *consumer's* coercion, and therefore the thing under test
            # rather than a property of the fixture.
            attributes = {
                "id": ids,
                "measure": pd.array([i for i in range(n - 1)] + [None], dtype="Int64"),
            }
        elif spec.case_id == "mixed_timezone_after_batch_gpkg":
            # The column is written as text by ``_write_large`` -- see there for
            # why the offsets cannot go through a pandas dtype.
            attributes = {"id": ids}
        else:  # pragma: no cover - _large_specs() rejects these first
            raise RuntimeError(f"no frame recipe for large case '{spec.case_id}'")

    return geopandas.GeoDataFrame(attributes, geometry=geometries, crs=f"EPSG:{_SRID}")


def _write_large(spec: LargeVectorSpec, dest: Path) -> None:
    """Write a large case: geopandas for the bulk, SQL for what pandas cannot express.

    ``geopandas.to_file`` rather than the ``osgeo.ogr`` loop ``_write_ogr``
    uses. Ten thousand ``ogr.Feature`` round trips is slow enough to make
    ``--check`` unpleasant, and none of the reasons ``_write_ogr`` exists
    (SpatiaLite options, per-driver layer creation flags) apply to a plain
    GeoPackage.

    ``SPATIAL_INDEX=NO``: the R-tree costs ~750 KB on 10,000 features -- more
    than half the payload -- to accelerate a query no case here performs. The
    R-tree is covered deliberately by the SpatiaLite five, at one feature each.
    """
    import sqlite3 as _sqlite3

    _remove_existing(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    from osgeo import gdal

    frame = _large_frame(spec)
    with gdal.config_option("OGR_CURRENT_DATE", _FROZEN_TIMESTAMP):
        frame.to_file(
            dest, driver="GPKG", layer=spec.layer, SPATIAL_INDEX="NO", index=False
        )

    if spec.case_id == "mixed_timezone_after_batch_gpkg":
        # Written as SQL text rather than as a pandas column, because there is
        # no pandas dtype that survives this. A ``datetime64[ns, tz]`` column
        # holds exactly *one* timezone by construction, and an object column of
        # per-value ``tzinfo`` is normalised to UTC by the writer -- either way
        # the mixed offset is gone before it reaches the file. GeoPackage
        # stores DATETIME as ISO 8601 text, so the offsets can simply be
        # written, which is also how a real dataset acquires them: from a
        # producer that recorded local time.
        con = _sqlite3.connect(dest)
        try:
            con.execute(f'ALTER TABLE "{spec.layer}" ADD COLUMN observed DATETIME')
            con.executemany(
                f'UPDATE "{spec.layer}" SET observed = ? WHERE id = ?',
                [
                    (f"{_LARGE_TZ_WALL_CLOCK}{_LARGE_TZ_MAJORITY}", i)
                    for i in range(spec.feature_count - 1)
                ],
            )
            con.execute(
                f'UPDATE "{spec.layer}" SET observed = ? WHERE id = ?',
                (
                    f"{_LARGE_TZ_WALL_CLOCK}{_LARGE_TZ_OUTLIER}",
                    spec.feature_count - 1,
                ),
            )
            con.commit()
            # ``ALTER TABLE`` plus 10,000 updates leaves free pages behind;
            # without this the file is ~40% larger than its content.
            con.execute("VACUUM")
        finally:
            con.close()

    _freeze_gpkg_last_change(dest)


def _large_specs(vector_root: Path = VECTOR_ROOT) -> list[LargeVectorSpec]:
    """Build one spec per large case present on disk, sorted by id.

    Feature counts come from ``params.expected_feature_count`` in the
    ``case.yaml`` rather than being repeated here, so the number the generator
    writes and the number phase 1's content gate checks cannot disagree.
    """
    cases = _read_case_files(vector_root)

    specs: list[LargeVectorSpec] = []
    for case_id in sorted(_LARGE_CASE_IDS):
        entry = cases.get(case_id)
        if entry is None:
            raise RuntimeError(
                f"Large case '{case_id}' has no case.yaml under {vector_root}"
            )
        case_dir, data = entry
        primary = data["files"]["primary"]
        count = (data.get("params") or {}).get("expected_feature_count")
        if not isinstance(count, int):
            raise RuntimeError(
                f"Large case '{case_id}' must declare params.expected_feature_count; "
                f"the generator takes its size from the metadata, not the reverse"
            )
        specs.append(
            LargeVectorSpec(
                case_id=case_id,
                rel_path=(case_dir / primary).relative_to(vector_root).as_posix(),
                layer=Path(primary).stem,
                geometry_type=data["geometry_type"],
                feature_count=count,
            )
        )
    return specs


#: Size budget for a large case's payload, well under ``validate_catalog.py``'s
#: 5 MB ``small`` limit but tight enough to catch a regression: the three land
#: at 1.4 MB, 0.5 MB and 0.7 MB, and the R-tree alone would add ~0.75 MB.
_MAX_BYTES_LARGE = 2 * 1024 * 1024


def _fingerprint_large(path: Path, spec: LargeVectorSpec) -> dict[str, object]:
    """Return what ``--check`` compares for a large case.

    Not the per-feature fingerprint ``_fingerprint_ogr`` uses: 10,000 WKB blobs
    in a diff message are unreadable, and a mismatch anywhere in them says
    nothing about *what* changed. Compared instead on the case's schema, its
    size, and the **defect** each case exists to carry -- which is the property
    that would actually be lost in a regeneration, and the one whose loss the
    small-case fingerprint would report as an anonymous byte difference.
    """
    import geopandas
    import pandas as pd

    gdf = geopandas.read_file(path, layer=spec.layer)

    fingerprint: dict[str, object] = {
        "feature_count": len(gdf),
        "columns": sorted(c for c in gdf.columns if c != gdf.geometry.name),
        "epsg": gdf.crs.to_epsg() if gdf.crs is not None else None,
        "geometry_types": sorted(set(gdf.geometry.geom_type)),
        # The corners of the lattice: enough to catch a moved or rescaled grid
        # without carrying 10,000 coordinates.
        "bounds": [round(float(v), _PROCEDURAL_PRECISION) for v in gdf.total_bounds],
    }

    if spec.case_id == "invalid_geometry_at_scale_gpkg":
        fingerprint["invalid_rows"] = [
            i for i, valid in enumerate(gdf.geometry.is_valid) if not valid
        ]
    elif spec.case_id == "null_after_batch_boundary_gpkg":
        fingerprint["null_rows"] = [
            i for i, missing in enumerate(gdf["measure"].isna()) if missing
        ]
    elif spec.case_id == "mixed_timezone_after_batch_gpkg":
        observed = pd.to_datetime(gdf["observed"], utc=True)
        # Distinct UTC instants, not the raw strings: the offsets are the
        # point, and a reader that normalises them away collapses this to one.
        fingerprint["distinct_instants"] = sorted(
            str(value) for value in observed.unique()
        )

    return fingerprint


def _specs(vector_root: Path = VECTOR_ROOT) -> list[VectorSpec]:
    """Build one spec per case declaring a canonical source, sorted by id.

    Discovered by walking ``case.yaml`` rather than listed here, so a baseline
    added later is generated -- and therefore gated -- without anyone
    remembering to edit this file.

    Geometry is *derived* from ``params.canonical_source_case_id``. Until plan 13
    it was declared literally, and this docstring said deriving would "silently
    rewrite the fixtures and break the tests that assert against them". That was
    true when written and is false now: no test in the suite asserts a baseline
    coordinate (``grep -rn "POINT (\\|POLYGON ((\\|LINESTRING (" tests/ examples/``
    returns nothing), and the literals had drifted so far that 53 of the 60
    fixtures held a *different* geometry from the canonical they named. The
    warning label was pointing at the wrong hazard: the risk was never rewriting
    the fixtures, it was leaving them wrong.
    """
    cases = _read_case_files(vector_root)

    specs: list[VectorSpec] = []
    for case_id, (case_dir, data) in sorted(cases.items()):
        params = data.get("params") or {}
        source_id = params.get(_CANONICAL_PARAM)
        if not source_id:
            continue

        primary = data["files"]["primary"]
        rel_path = (case_dir / primary).relative_to(vector_root).as_posix()
        fmt = data["format"]
        if (
            fmt not in _OGR_DRIVERS
            and fmt not in _TEXT_FORMATS
            and fmt not in _GEOPANDAS_FORMATS
            and fmt not in _ARROW_FORMATS
        ):
            raise RuntimeError(f"Case '{case_id}' has unsupported format {fmt!r}")

        specs.append(
            VectorSpec(
                case_id=case_id,
                rel_path=rel_path,
                format=fmt,
                layer=Path(primary).stem,
                geometry_type=data["geometry_type"],
                geometry=_canonical_geometry(source_id, cases),
                spatialite="spatialite" in (data.get("tags") or []),
            )
        )
    return specs


# ---------------------------------------------------------------------------
# Write backends -- one per branch of VectorCase.load()'s dispatch
# ---------------------------------------------------------------------------


def _sibling_files(primary: Path) -> list[Path]:
    """Return *primary* plus every sidecar sharing its stem.

    A Shapefile is ``.shp/.shx/.dbf/.prj/.cpg`` and a GML is ``.gml/.xsd``; both
    need removing before a rewrite and counting against the size budget.
    """
    if not primary.parent.is_dir():
        return []
    return sorted(p for p in primary.parent.glob(primary.stem + ".*") if p.is_file())


def _remove_existing(primary: Path) -> None:
    """Delete *primary* and its sidecars so a rewrite cannot leave stale files.

    Matched on stem rather than delegating to ``Driver.DeleteDataSource``: that
    leaves the GML ``.xsd`` behind, and a stale ``.xsd`` describing a schema the
    ``.gml`` no longer has is exactly the kind of half-updated fixture this
    generator exists to make impossible.
    """
    for path in _sibling_files(primary):
        path.unlink()


def _spatial_reference() -> Any:
    """Return the EPSG:4326 SRS every fixture is written with.

    ``OAMS_TRADITIONAL_GIS_ORDER`` is not optional. EPSG:4326 declares its axes
    as (latitude, longitude), and GDAL 3 honours that by default -- so the
    lon/lat coordinates handed to :meth:`SetGeometry` get written out reversed
    by any driver that serializes in the SRS's declared axis order. The KML
    driver is one: without this call ``point_kml_baseline`` ships
    ``<coordinates>55.7,12.5</coordinates>`` and loads back as
    ``POINT (55.7 12.5)``, a fixture that is wrong in a way no size or checksum
    check would ever notice.

    GML is deliberately *not* affected: it writes ``urn:ogc:def:crs:EPSG::4326``,
    which forces (lat, lon) in ``gml:pos`` regardless of this setting, so the
    committed files read ``55.7 12.5``. That looks swapped to a naive text diff
    but round-trips correctly through OGR, and it is the real behaviour of the
    URN form -- worth keeping rather than papering over.
    """
    from osgeo import osr

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(_SRID)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return srs


def _write_ogr(spec: VectorSpec, dest: Path) -> None:
    """Write *spec* through an OGR driver: Shapefile, GPKG, SQLite, GML, KML, FGB.

    Still ``osgeo.ogr`` rather than pyogrio, deliberately: the SpatiaLite path
    below needs ``SPATIALITE=YES`` plus the trim-and-``VACUUM`` step, and pyogrio
    exposes no equivalent.
    """
    from osgeo import gdal, ogr

    ogr.UseExceptions()

    _remove_existing(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    driver = ogr.GetDriverByName(_OGR_DRIVERS[spec.format])

    ds_options: list[str] = []
    layer_options: list[str] = []
    if spec.format == "SQLite":
        ds_options = ["SPATIALITE=YES"] if spec.spatialite else []
        layer_options = ["GEOMETRY_NAME=GEOMETRY"]
        # The R-tree is the point of the SpatiaLite five; the plain-SQLite case
        # exists to contrast the non-SpatiaLite driver path against them.
        layer_options.append("SPATIAL_INDEX=YES" if spec.spatialite else "FORMAT=WKB")
    elif spec.format == "FlatGeobuf":
        # A spatial index over a single feature is pure overhead, and FlatGeobuf
        # writes it as a separate packed section that varies with GDAL's
        # node-size default.
        layer_options = ["SPATIAL_INDEX=NO"]
    elif spec.format == "Shapefile":
        # Makes GDAL emit the ``.cpg`` codepage sidecar the committed fixtures
        # already carry. Without it a reader has to guess the DBF encoding.
        layer_options = ["ENCODING=UTF-8"]

    # GeoPackage stamps `gpkg_contents.last_change` from the wall clock. Pinning
    # it here keeps regeneration idempotent; `_freeze_gpkg_last_change` below
    # repairs it afterwards for GDAL builds where this option does not take.
    with gdal.config_option("OGR_CURRENT_DATE", _FROZEN_TIMESTAMP):
        ds = driver.CreateDataSource(str(dest), options=ds_options)
        layer = ds.CreateLayer(
            spec.layer,
            _spatial_reference(),
            getattr(ogr, spec.ogr_geometry_type),
            options=layer_options,
        )

        layer.CreateField(ogr.FieldDefn(_ID_FIELD, ogr.OFTInteger64))
        layer.CreateField(ogr.FieldDefn(_NAME_FIELD, ogr.OFTString))

        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField(_ID_FIELD, spec.id_value)
        feature.SetField(_NAME_FIELD, spec.case_id)
        # Handed over as WKB rather than WKT: float64 in, float64 out, with no
        # decimal round trip to lose a digit in.
        feature.SetGeometry(ogr.CreateGeometryFromWkb(spec.geometry.wkb))
        layer.CreateFeature(feature)

        feature = None
        layer = None
        ds = None

    if spec.format == "SQLite":
        _trim_and_vacuum(dest)
    elif spec.format == "GPKG":
        _freeze_gpkg_last_change(dest)


def _write_text(spec: VectorSpec, dest: Path) -> None:
    """Write *spec* as WKT, WKB or CSV_WKT -- pure Python, no driver.

    These three are the only formats ``--check`` byte-compares, because these
    three are the only ones nothing stamps a timestamp or a library version into.
    """
    import shapely

    _remove_existing(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if spec.format == "WKT":
        # No trailing newline, matching the committed fixtures.
        # ``VectorCase.load()`` strips anyway.
        dest.write_text(spec.geometry.wkt, encoding="utf-8")
        return

    if spec.format == "WKB":
        # Little-endian, no embedded SRID -- the form the committed fixtures
        # already use, and the one `shapely.wkb.loads` reads without hints.
        dest.write_bytes(
            shapely.to_wkb(spec.geometry, byte_order=1, include_srid=False)
        )
        return

    if spec.format == "CSV_WKT":
        # `lineterminator="\n"` because csv.writer defaults to CRLF, which would
        # make the committed bytes platform-dependent. "geometry" is one of the
        # three column names `VectorCase.load()` recognises.
        with dest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow([_ID_FIELD, _NAME_FIELD, "geometry"])
            writer.writerow([1, spec.case_id, spec.geometry.wkt])
        return

    raise RuntimeError(f"{spec.case_id}: {spec.format} is not a text format")


def _frame(spec: VectorSpec) -> Any:
    """Return the single-row GeoDataFrame the columnar backends write."""
    import geopandas

    return geopandas.GeoDataFrame(
        {_ID_FIELD: [1], _NAME_FIELD: [spec.case_id]},
        geometry=[spec.geometry],
        crs=f"EPSG:{_SRID}",
    )


def _write_geopandas(spec: VectorSpec, dest: Path) -> None:
    """Write *spec* as GeoParquet or GeoFeather.

    ``schema_version`` is pinned rather than left to the geopandas default so a
    geopandas upgrade cannot silently move the committed metadata to a new
    GeoParquet revision. 1.0.0 is what the committed fixtures carry, and it
    satisfies ``geocase.assertions.format_compliance.assert_geoparquet_metadata``
    (it requires ``primary_column`` and ``columns``, both present since 0.4).
    That assertion runs over these files in ``tests/unit/test_format_compliance.py``.
    """
    _remove_existing(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    frame = _frame(spec)
    if spec.format == "Parquet":
        frame.to_parquet(dest, schema_version="1.0.0")
    else:
        frame.to_feather(dest, schema_version="1.0.0")


def _write_arrow_ipc(spec: VectorSpec, dest: Path) -> None:
    """Write *spec* as an Arrow IPC **file**.

    ``pyarrow.ipc.new_file``, not ``new_stream``: ``VectorCase.load()`` reads
    these with ``pyarrow.ipc.open_file``, which needs the file format's footer
    and magic. A stream-framed fixture is silently unloadable.

    Both ``Arrow`` and ``GeoArrow`` cases go through the same path and land on
    the ``geoarrow.wkb`` extension type, which is what the committed fixtures
    already carry -- the two case families differ in what they document, not in
    their encoding.
    """
    import pyarrow as pa

    _remove_existing(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    table = pa.table(_frame(spec).to_arrow())
    with pa.ipc.new_file(str(dest), table.schema) as writer:
        writer.write_table(table)


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


def _freeze_gpkg_last_change(path: Path) -> None:
    """Pin ``gpkg_contents.last_change`` so regeneration is idempotent.

    ``OGR_CURRENT_DATE`` is set around the write above and handles this on GDAL
    builds that honour it. This is the fallback: whether the config option is
    respected varies by GDAL version, and without it every regeneration leaves
    every GeoPackage dirty in ``git status`` -- which trains people to
    ``git checkout`` fixture changes wholesale, including real ones.
    """
    con = sqlite3.connect(path)
    try:
        con.execute("UPDATE gpkg_contents SET last_change = ?", (_FROZEN_TIMESTAMP,))
        con.commit()
    finally:
        con.close()


def _write_geojson(spec: VectorSpec, dest: Path) -> None:
    """Write *spec* as a GeoJSON FeatureCollection -- pure Python, no driver.

    Only the *procedural* cases take this path. The transcoding family's
    GeoJSON canonicals are hand-authored source files: they are what everything
    else is derived *from*, so a generator that rewrote them would be arguing
    with its own input.

    Written by hand rather than through OGR for the same reason as the WKT/WKB
    formats: no driver means no library version or timestamp stamped into the
    output, so ``--check`` can compare bytes rather than semantics.
    """
    from shapely.geometry import mapping

    _remove_existing(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {_ID_FIELD: 1, _NAME_FIELD: spec.case_id},
                "geometry": mapping(spec.geometry),
            }
        ],
    }
    # No indentation: at 4096 vertices, ``indent=2`` costs ~200 KB of leading
    # whitespace and pushes the file past the size budget. One coordinate pair
    # per line would be the readable compromise, but these files are generated
    # and diffed by the checksum gate, not read by hand.
    dest.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")


def _write_fixture(spec: VectorSpec, dest: Path) -> None:
    """Create *dest* from *spec*, dispatching on format.

    The dispatch deliberately mirrors ``VectorCase.load()``'s, branch for
    branch. If the two ever diverge, a fixture is being written by one code path
    and read by another, which is how a format ends up unloadable with every
    test still green.
    """
    if spec.format == "GeoJSON":
        _write_geojson(spec, dest)
    elif spec.format in _OGR_DRIVERS:
        _write_ogr(spec, dest)
    elif spec.format in _TEXT_FORMATS:
        _write_text(spec, dest)
    elif spec.format in _GEOPANDAS_FORMATS:
        _write_geopandas(spec, dest)
    elif spec.format in _ARROW_FORMATS:
        _write_arrow_ipc(spec, dest)
    else:  # pragma: no cover - _specs() rejects these first
        raise RuntimeError(f"{spec.case_id}: no writer for format {spec.format!r}")


# ---------------------------------------------------------------------------
# Fingerprints -- what `--check` compares
# ---------------------------------------------------------------------------


def _fingerprint_ogr(path: Path, spec: VectorSpec) -> dict[str, object]:
    """Return everything observable about a driver-backed fixture.

    Deliberately excludes raw bytes, and for SQLite also ``spatialite_history``
    (wall-clock timestamps and library versions) -- see the module docstring.
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

    layer = None
    ds = None

    fingerprint: dict[str, object] = {
        "layer": layer_name,
        "geom_column": geom_column,
        "fields": fields,
        "features": features,
        "epsg": str(epsg) if epsg is not None else None,
    }

    if spec.format == "SQLite":
        # The 280x regression this script exists to prevent was 13,067 rows of
        # unused EPSG metadata, which is invisible in every field above.
        con = sqlite3.connect(path)
        try:
            fingerprint["tables"] = sorted(
                r[0].lower()
                for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            )
            fingerprint["spatial_ref_sys_rows"] = con.execute(
                "SELECT count(*) FROM spatial_ref_sys"
            ).fetchone()[0]
        finally:
            con.close()

    return fingerprint


def _fingerprint_text(path: Path, spec: VectorSpec) -> dict[str, object]:
    """Return the raw bytes of a pure-Python fixture.

    A genuine byte comparison, which these three formats can afford because
    nothing writes a timestamp or a library version into them.
    """
    return {"bytes": path.read_bytes()}


def _fingerprint_arrow(path: Path, spec: VectorSpec) -> dict[str, object]:
    """Return the observable content of a Parquet/Feather/Arrow fixture.

    Bytes are out: all four embed a ``created_by``/``creator`` string naming the
    writing library and its version, so two correct files from two machines
    differ. Compared instead on the frame a consumer actually gets back --
    read through the same calls ``VectorCase.load()`` makes.
    """
    import geopandas
    import shapely

    if spec.format == "Parquet":
        gdf = geopandas.read_parquet(path)
    elif spec.format == "Feather":
        gdf = geopandas.read_feather(path)
    else:
        import pyarrow.ipc as ipc

        with ipc.open_file(str(path)) as reader:
            gdf = geopandas.GeoDataFrame.from_arrow(reader.read_all())

    geometry_column = gdf.geometry.name
    attributes = [column for column in gdf.columns if column != geometry_column]

    return {
        "columns": list(gdf.columns),
        "dtypes": [str(gdf[column].dtype) for column in attributes],
        "values": [tuple(row) for row in gdf[attributes].itertuples(index=False)],
        # WKB of the normalized geometry: byte-identical for byte-identical
        # coordinates, and immune to a driver reordering rings.
        "geometries": [
            shapely.to_wkb(shapely.normalize(geom)) for geom in gdf.geometry
        ],
        # `to_epsg()` rather than `str(crs)`: these four formats store a full
        # PROJJSON object, whose key order and PROJ-version-dependent datum
        # ensemble members are not stable enough to compare textually.
        "epsg": gdf.crs.to_epsg() if gdf.crs is not None else None,
    }


def _fingerprint(path: Path, spec: VectorSpec) -> dict[str, object]:
    """Fingerprint *path* using the strategy its format allows."""
    if spec.format in _OGR_DRIVERS:
        return _fingerprint_ogr(path, spec)
    if spec.format in _BYTE_COMPARABLE_FORMATS:
        return _fingerprint_text(path, spec)
    return _fingerprint_arrow(path, spec)


def _short(value: object, limit: int = 160) -> str:
    """Return ``repr(value)`` truncated, so a WKB blob cannot flood the report."""
    text = repr(value)
    return text if len(text) <= limit else f"{text[:limit]}... ({len(text)} chars)"


def _diff(expected: dict[str, object], actual: dict[str, object]) -> list[str]:
    """Return human-readable differences between two fingerprints."""
    return [
        f"{key}: expected {_short(expected[key])}, got {_short(actual[key])}"
        for key in sorted(expected)
        if expected[key] != actual[key]
    ]


def _payload_bytes(primary: Path) -> int:
    """Return the on-disk size of a fixture, sidecars included."""
    return sum(path.stat().st_size for path in _sibling_files(primary))


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


def _missing_dependency() -> str | None:
    """Return an actionable message naming the first missing dependency, if any.

    Every one of these is a "cannot verify" condition, never a pass. The catalog
    CI job installed ``.[raster]`` only until plan 13, so geopandas and pyarrow
    were genuinely absent there -- and a gate that quietly checks nothing is
    worse than no gate, because it advertises coverage that does not exist.
    """
    try:
        from osgeo import ogr  # noqa: F401
    except ImportError:
        return (
            "this generator needs the GDAL Python bindings (osgeo), which are "
            "source-only on PyPI. Use the conda environment "
            "(see docs/contributing/workflow.md)."
        )

    for module, extra in (
        ("shapely", "vector"),
        ("geopandas", "vector"),
        ("pyarrow", "vector"),
        ("yaml", "base"),
    ):
        try:
            __import__(module)
        except ImportError:
            return (
                f"this generator needs '{module}', which is missing. Install the "
                f"'{extra}' extra: pip install -e .[{extra}]"
                if extra != "base"
                else f"this generator needs '{module}', which is missing."
            )

    if not _has_spatialite():
        return (
            "GDAL is present but has no SpatiaLite support, so the SpatiaLite "
            "fixtures cannot be generated or verified.\n"
            "  Locally: use the conda environment (it bundles libspatialite).\n"
            "  In CI: the gdal 'ubuntu-small' image omits SpatiaLite; switch the "
            "job to 'ubuntu-full' or install libsqlite3-mod-spatialite."
        )
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or verify the bundled baseline vector fixtures."
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

    problem = _missing_dependency()
    if problem is not None:
        # Exit 2, not 1: this is "cannot verify", which is a different failure
        # from "fixtures have drifted" and needs a different fix.
        print(f"ERROR: {problem}", file=sys.stderr)
        return 2

    specs = _specs(args.vector_root)
    if not specs:
        print(
            f"ERROR: no cases under {args.vector_root} declare "
            f"'params.{_CANONICAL_PARAM}'. Either the tree moved or the catalog "
            f"lost its cross-format family; either way this is not a pass.",
            file=sys.stderr,
        )
        return 2

    # The procedural cases go through the same write backends, fingerprints and
    # budget checks; only where their geometry comes from differs.
    specs = specs + _procedural_specs(args.vector_root)
    specs = specs + _dimensional_specs(args.vector_root)

    # The large cases (plan 28 phase 3) do not: they hold 10,000 features, so
    # they have their own writer, their own fingerprint and their own budget.
    # They still share this loop, because being outside the regeneration gate
    # is exactly how ``hole_center_nodata`` drifted into the inverse of its own
    # description.
    large = _large_specs(args.vector_root)

    if args.check:
        problems: list[str] = []
        for spec in specs:
            dest = args.vector_root / spec.rel_path
            if not dest.exists():
                problems.append(f"{spec.case_id}: missing ({dest})")
                continue

            budget = _MAX_BYTES if spec.spatialite else _MAX_BYTES_NON_SPATIALITE
            size = _payload_bytes(dest)
            if size > budget:
                problems.append(
                    f"{spec.case_id}: {size / 1024:.0f} KB exceeds the "
                    f"{budget / 1024:.0f} KB budget -- was it regenerated "
                    f"without trimming spatial_ref_sys?"
                )

            with tempfile.TemporaryDirectory() as tmp:
                candidate = Path(tmp) / dest.name
                _write_fixture(spec, candidate)
                for line in _diff(
                    _fingerprint(candidate, spec), _fingerprint(dest, spec)
                ):
                    problems.append(f"{spec.case_id}: {line}")

        for large_spec in large:
            dest = args.vector_root / large_spec.rel_path
            if not dest.exists():
                problems.append(f"{large_spec.case_id}: missing ({dest})")
                continue

            size = _payload_bytes(dest)
            if size > _MAX_BYTES_LARGE:
                problems.append(
                    f"{large_spec.case_id}: {size / 1024:.0f} KB exceeds the "
                    f"{_MAX_BYTES_LARGE / 1024:.0f} KB budget -- was it "
                    f"regenerated with a spatial index?"
                )

            with tempfile.TemporaryDirectory() as tmp:
                candidate = Path(tmp) / dest.name
                _write_large(large_spec, candidate)
                for line in _diff(
                    _fingerprint_large(candidate, large_spec),
                    _fingerprint_large(dest, large_spec),
                ):
                    problems.append(f"{large_spec.case_id}: {line}")

        if problems:
            print("Vector fixtures out of date:")
            for line in problems:
                print(f"  {line}")
            return 1
        print(
            f"All vector fixtures up to date "
            f"({len(specs) + len(large)} fixtures, {len(large)} large)"
        )
        return 0

    for spec in specs:
        dest = args.vector_root / spec.rel_path
        _write_fixture(spec, dest)
        print(
            f"Wrote {dest.relative_to(REPO_ROOT)} "
            f"({_payload_bytes(dest) / 1024:.1f} KB)"
        )

    for large_spec in large:
        dest = args.vector_root / large_spec.rel_path
        _write_large(large_spec, dest)
        print(
            f"Wrote {dest.relative_to(REPO_ROOT)} "
            f"({_payload_bytes(dest) / 1024:.1f} KB, "
            f"{large_spec.feature_count} features)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
