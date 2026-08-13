"""The cross-format canonical gate — one geometry, many file formats.

Plan 13. Every ``<geomtype>_<format>_baseline`` case declares
``params.canonical_source_case_id`` and carries the ``cross_format_canonical``
tag, which together promise that the *only* thing varying across the family is
the container. Until this module existed nothing dereferenced that link, so 53
of 60 members held a different geometry from the canonical they named — and a
consumer diffing KML against Shapefile got a "cross-format difference" that was
purely a fixture accident. Two evaluation pilots reported one before catching it.

Cases are auto-discovered from ``case-index.yaml`` rather than listed, so a
baseline added in future is gated without anyone remembering to add it here.

Why this lives in ``tests/`` and not ``scripts/validate_catalog.py``: the CI
``catalog`` job runs inside the GDAL image with ``numpy<2`` and no geopandas,
shapely or pyarrow. The declaration-level checks that need none of those are in
``validate_catalog.py`` (see ``tests/unit/test_validate_catalog_canonical.py``);
everything here needs a real load.

And the load goes through :meth:`VectorCase.load`, deliberately, rather than
``geopandas.read_file``: only that exercises the hand-rolled
CSV_WKT/WKT/WKB/Parquet/Feather/Arrow branches a consumer actually hits.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import shapely
from pyproj import CRS

from geocase.catalog.loader import load_case_index, load_case_metadata
from geocase.catalog.models import CaseMetadata
from geocase.catalog.roots import materialize_case

_SRC = Path(__file__).resolve().parents[2] / "src" / "geocase"
_CASE_INDEX = _SRC / "metadata" / "case-index.yaml"

_CANONICAL_TAG = "cross_format_canonical"

#: Comparison tolerance.
#:
#: Everything but GML and KML is float64 end to end and would pass at exactly
#: zero. Those two serialize coordinates as decimal text, so they need a real
#: tolerance — and 1e-9 degrees is ~0.1 mm, far below any difference that could
#: mean a fixture is wrong.
_TOLERANCE = 1e-9

#: The unified attribute schema every ``_baseline`` fixture is generated with.
_EXPECTED_COLUMNS = frozenset({"id", "name"})

#: Formats where ``_EXPECTED_COLUMNS`` provably cannot survive a round trip, and
#: why. Kept as one constant rather than scattered ``if`` branches so the list of
#: things we have given up on is readable in a single place.
#:
#: Note which format is *absent*: GML. OGR injects ``gml_id`` on read, but an
#: injection only *adds* a column, and the assertion below is a subset relation,
#: so GML keeps both ``id`` and ``name`` and needs no exemption. It is asserted
#: positively in ``TestDocumentedFormatExceptions`` instead.
_COLUMN_EXCEPTIONS: dict[str, str] = {
    # OGR's KML driver maps a field named ``name`` onto the Placemark's ``<name>``
    # element, which reads back capitalised as ``Name``, and synthesizes
    # ``description, timestamp, begin, end, altitudeMode, tessellate, extrude,
    # visibility, drawOrder, icon`` regardless of file content. Writing ``id``
    # additionally collides with the ``<Placemark id>`` attribute and reads back
    # as both ``id`` and ``id2``.
    "KML": "the driver renames `name` to `Name` and synthesizes ~10 columns",
    # Neither format has an attribute slot at all. `VectorCase.load()` synthesizes
    # a single `{"name": <case id>}` row, so `name` is present and `id` cannot be.
    "WKT": "the format carries no attributes; load() synthesizes `name` only",
    "WKB": "the format carries no attributes; load() synthesizes `name` only",
}


# ---------------------------------------------------------------------------
# Auto-discovery
# ---------------------------------------------------------------------------


def _discover() -> list[CaseMetadata]:
    """Return every case declaring a cross-format canonical, sorted by id."""
    src_root = _CASE_INDEX.parent.parent
    found = [load_case_metadata(src_root / rel) for rel in load_case_index(_CASE_INDEX)]
    return sorted(
        (meta for meta in found if _CANONICAL_TAG in meta.tags),
        key=lambda meta: meta.id,
    )


_MEMBERS: list[CaseMetadata] = _discover()


@pytest.fixture(scope="module")
def canonical_geometries() -> dict[str, shapely.geometry.base.BaseGeometry]:
    """Map each canonical case id to its single geometry.

    Loaded once: the six GeoJSON canonicals are the reference every member is
    compared against, and re-reading them per member would be 60 file opens for
    six answers.
    """
    src_root = _CASE_INDEX.parent.parent
    by_id = {
        meta.id: meta
        for meta in (
            load_case_metadata(src_root / rel) for rel in load_case_index(_CASE_INDEX)
        )
    }
    # `.get`, not `[...]`: discovery selects on the *tag*, so a case that keeps
    # the tag and loses the param lands in `_MEMBERS` with nothing to compare
    # against. Subscripting here would raise `KeyError` inside a module-scoped
    # fixture and turn one broken declaration into 180 errored tests with the
    # cause buried. `test_every_member_declares_its_canonical` reports it once,
    # in words; `scripts/validate_catalog.py` is what actually gates it.
    wanted = {
        source_id
        for meta in _MEMBERS
        if (source_id := meta.params.get("canonical_source_case_id")) in by_id
    }
    return {
        case_id: materialize_case(by_id[case_id]).load().geometry.iloc[0]
        for case_id in sorted(wanted)
    }


def _ids(members: list[CaseMetadata]) -> list[str]:
    return [meta.id for meta in members]


# ---------------------------------------------------------------------------
# The gate itself
# ---------------------------------------------------------------------------


class TestDiscovery:
    """The parametrization must not silently collapse to nothing."""

    def test_the_whole_family_is_discovered(self):
        """Test all 60 tagged baselines are gated.

        Without this, deleting the tag from every case would turn the entire
        module green — a gate that quietly checks nothing, which is the exact
        failure mode this plan exists to remove.
        """
        assert len(_MEMBERS) == 60

    def test_every_member_declares_its_canonical(self):
        """Test the tag and the param agree, in one legible failure.

        Discovery keys on the tag, so a case that keeps the tag and drops the
        param is still parametrized — and every geometry assertion below would
        then fail on a missing dictionary key rather than on anything true about
        the fixture. Naming the offenders here costs one assertion and saves
        reading 180 stack traces.
        """
        undeclared = [
            meta.id
            for meta in _MEMBERS
            if "canonical_source_case_id" not in meta.params
        ]

        assert undeclared == [], (
            f"tagged '{_CANONICAL_TAG}' but naming no canonical: {undeclared}"
        )

    def test_every_geometry_family_is_represented(self):
        """Test no family drops out of the comparison."""
        families = {meta.id.split("_")[0] for meta in _MEMBERS}

        assert families == {
            "point",
            "linestring",
            "polygon",
            "multipoint",
            "multilinestring",
            "multipolygon",
        }

    def test_the_canonicals_are_the_six_geojson_references(self):
        """Test every member points at one of six GeoJSON canonicals."""
        sources = {meta.params["canonical_source_case_id"] for meta in _MEMBERS}

        assert sources == {
            "simple_valid_point",
            "simple_valid_linestring",
            "simple_valid_polygon",
            "simple_valid_multipoint",
            "simple_valid_multilinestring",
            "simple_valid_multipolygon",
        }


@pytest.mark.parametrize("meta", _MEMBERS, ids=_ids(_MEMBERS))
class TestCanonicalGeometry:
    """Each member holds its canonical's geometry, and says so honestly."""

    def test_holds_exactly_one_feature(self, meta, canonical_geometries):
        """Test the family compares one geometry, not a collection of them."""
        gdf = materialize_case(meta).load()

        assert len(gdf) == 1

    def test_geometry_type_matches_the_canonical(self, meta, canonical_geometries):
        """Test the driver did not promote the geometry on write.

        `shapely.normalize` canonicalizes component ordering, so it happily
        reports a `Polygon` and a single-part `MultiPolygon` as equal. Only an
        explicit `geom_type` check catches an OGR promotion.
        """
        expected = canonical_geometries[meta.params["canonical_source_case_id"]]
        actual = materialize_case(meta).load().geometry.iloc[0]

        assert actual.geom_type == expected.geom_type
        assert actual.geom_type == meta.geometry_type

    def test_geometry_equals_the_canonical(self, meta, canonical_geometries):
        """Test the coordinates are the canonical's, winding aside.

        Compared through `normalize` because the Shapefile specification mandates
        the opposite ring orientation from RFC 7946 and OGR rewrites winding on
        write regardless of input — so a winding-sensitive assertion would be
        unsatisfiable for the Shapefile members. `normalize` also canonicalizes
        ring start vertex, component order and LineString direction, absorbing
        every legitimate driver rewrite while still failing on any coordinate,
        vertex-count or component-count change.

        The orientation that `normalize` deliberately hides is not lost: it is
        asserted directly by `shapefile_ring_orientation`, in
        `tests/unit/test_format_specific_cases.py`.
        """
        expected = canonical_geometries[meta.params["canonical_source_case_id"]]
        actual = materialize_case(meta).load().geometry.iloc[0]

        assert shapely.equals_exact(
            shapely.normalize(actual),
            shapely.normalize(expected),
            tolerance=_TOLERANCE,
        ), f"{meta.id}: {actual.wkt} != canonical {expected.wkt}"

    def test_crs_is_epsg_4326(self, meta):
        """Test every member declares the same CRS, whatever its encoding.

        Compared through `pyproj.CRS` rather than by string: the
        Parquet/Feather/Arrow/GeoArrow paths return a full PROJJSON object, so
        `str(gdf.crs) == "EPSG:4326"` would fail for four formats that are in
        fact perfectly correct.
        """
        gdf = materialize_case(meta).load()

        assert CRS.from_user_input(gdf.crs) == CRS.from_epsg(4326)

    def test_name_attribute_is_the_case_id(self, meta):
        """Test the `name` value identifies the case that holds it.

        Resolved case-insensitively because OGR's KML driver reads the field back
        as `Name` — see `_COLUMN_EXCEPTIONS`.
        """
        gdf = materialize_case(meta).load()
        column = next(
            (col for col in gdf.columns if col.lower() == "name"),
            None,
        )

        assert column is not None, f"{meta.id} has no name column: {list(gdf.columns)}"
        assert gdf[column].iloc[0] == meta.id

    def test_attribute_schema_is_unified(self, meta):
        """Test `{id, name}` is present, so column diffs mean the format.

        Before unification, diffing `polygon_geopackage_baseline` (`id, name,
        area_sqkm`) against `polygon_shapefile_baseline` (`name`) could not
        distinguish a driver behaviour from a fixture accident — which is the
        family's entire pedagogical payload. Format-idiomatic schemas are covered
        deliberately, and better, by `special/encoding/*`.

        A subset rather than an equality: driver-injected columns are real
        behaviour worth keeping visible.
        """
        if meta.format in _COLUMN_EXCEPTIONS:
            pytest.skip(f"{meta.format}: {_COLUMN_EXCEPTIONS[meta.format]}")

        gdf = materialize_case(meta).load()

        assert _EXPECTED_COLUMNS <= set(gdf.columns)

        identifier = gdf["id"].iloc[0]
        if meta.format == "CSV_WKT":
            # CSV has no type system at all, and `VectorCase.load()` reads it
            # with `csv.DictReader`, which yields `str` for every column. The
            # value is still the same value; only the encoding differs. Coerced
            # here rather than in the loader, which is right to stay lossless.
            identifier = int(identifier)
        assert identifier == 1


class TestDocumentedFormatExceptions:
    """The exceptions are asserted, not just described.

    An allowlist nobody checks rots into a list of things that used to be true.
    Each entry here pins the behaviour that earned the exemption, so if a GDAL
    upgrade fixes one of them the test goes red and the exemption can be dropped.
    """

    def test_kml_renames_name_and_synthesizes_columns(self):
        """Test the KML injection set is what `_COLUMN_EXCEPTIONS` claims."""
        meta = next(m for m in _MEMBERS if m.id == "point_kml_baseline")

        columns = set(materialize_case(meta).load().columns)

        assert "name" not in columns
        assert "Name" in columns
        assert {"description", "altitudeMode", "tessellate", "visibility"} <= columns

    def test_gml_injects_gml_id_but_keeps_the_schema(self):
        """Test GML earns no exemption: the injection is purely additive."""
        meta = next(m for m in _MEMBERS if m.id == "point_gml_baseline")

        columns = set(materialize_case(meta).load().columns)

        assert "gml_id" in columns
        assert _EXPECTED_COLUMNS <= columns

    @pytest.mark.parametrize("case_id", ["point_wkt_baseline", "point_wkb_baseline"])
    def test_wkt_and_wkb_carry_only_a_synthesized_name(self, case_id):
        """Test the bare-geometry formats behave as `VectorCase.load()` promises."""
        meta = next(m for m in _MEMBERS if m.id == case_id)

        gdf = materialize_case(meta).load()

        assert list(gdf.columns) == ["name", "geometry"]
        assert gdf["name"].iloc[0] == case_id
