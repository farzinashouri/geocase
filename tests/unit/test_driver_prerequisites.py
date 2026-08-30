"""Tests for ``AssertionHints.required_drivers`` — Plan 28 phase 2.1.

``required_drivers`` answers one question, and only that one: *what must an
OGR-based consumer (pyogrio, fiona, ogr2ogr) have installed before this case
will open for them?*

It is **not** a statement about geocase. ``VectorCase.load()`` opens all 113
vector cases with no OGR driver at all — WKB/WKT go through shapely, and
Parquet/Feather/Arrow through geopandas' own Arrow readers. The external
pyogrio validation run logged 20 of those as spurious failures purely because
nothing in the metadata said "you need a driver for this".

The three tiers this file pins:

* **no declaration** — an OGR consumer opens the case with a stock GDAL build;
* **a named driver** — the case needs an optional GDAL plugin
  (``libgdal-arrow-parquet``), which is installable;
* **the empty-string sentinel** ``NO_OGR_DRIVER`` — no OGR driver exists at any
  build configuration, because the payload is a bare geometry blob with no
  container. Installing something is not the fix; using shapely is.
"""

from __future__ import annotations

import pytest

import geocase
from geocase.catalog.models import NO_OGR_DRIVER

# Formats whose payload is a bare geometry blob: a WKB byte string or a WKT
# text string, with no feature table, no schema and no header. There is no OGR
# driver for "a geometry with nothing around it".
_BARE_GEOMETRY_FORMATS = {"WKB", "WKT"}

# Formats carried by the optional GDAL Arrow/Parquet plugin.
_ARROW_FAMILY_DRIVERS = {
    "Parquet": "Parquet",
    "Feather": "Arrow",
    "Arrow": "Arrow",
    "GeoArrow": "Arrow",
}


@pytest.fixture(scope="module")
def vector_cases() -> list[geocase.CaseMetadata]:
    return geocase.list_cases(category="vector")


class TestBareGeometryCases:
    """WKB/WKT: no driver exists, so the declaration says exactly that."""

    def test_every_bare_geometry_case_declares_the_sentinel(
        self, vector_cases: list[geocase.CaseMetadata]
    ):
        """Test each WKB/WKT case declares NO_OGR_DRIVER."""
        bare = [c for c in vector_cases if c.format in _BARE_GEOMETRY_FORMATS]
        assert bare, "expected the corpus to carry WKB/WKT cases"

        undeclared = [
            c.id for c in bare if c.assertions.required_drivers != [NO_OGR_DRIVER]
        ]
        assert undeclared == []

    def test_the_sentinel_is_falsy_so_it_cannot_be_installed(self):
        """Test NO_OGR_DRIVER is the empty string, not a driver name."""
        assert NO_OGR_DRIVER == ""
        assert not NO_OGR_DRIVER


class TestArrowFamilyCases:
    """Parquet/Feather/Arrow/GeoArrow: a real, installable driver name."""

    def test_each_arrow_family_case_names_its_driver(
        self, vector_cases: list[geocase.CaseMetadata]
    ):
        """Test the declared driver matches the GDAL driver for that format."""
        wrong = {
            c.id: c.assertions.required_drivers
            for c in vector_cases
            if c.format in _ARROW_FAMILY_DRIVERS
            and c.assertions.required_drivers != [_ARROW_FAMILY_DRIVERS[c.format]]
        }
        assert wrong == {}

    def test_their_declarations_are_installable_driver_names(
        self, vector_cases: list[geocase.CaseMetadata]
    ):
        """Test they name a driver rather than the not-openable sentinel."""
        for case in vector_cases:
            if case.format in _ARROW_FAMILY_DRIVERS:
                assert all(case.assertions.required_drivers)


class TestStockGdalCases:
    """Everything a plain GDAL build opens declares no prerequisite."""

    def test_stock_formats_declare_nothing(
        self, vector_cases: list[geocase.CaseMetadata]
    ):
        """Test GeoJSON/GPKG/Shapefile/… stay empty, so [] means 'just open it'."""
        stock = [
            c
            for c in vector_cases
            if c.format not in _BARE_GEOMETRY_FORMATS
            and c.format not in _ARROW_FAMILY_DRIVERS
        ]
        assert stock

        declared = {
            c.id: c.assertions.required_drivers
            for c in stock
            if c.assertions.required_drivers
        }
        assert declared == {}

    def test_raster_and_netcdf_cases_are_untouched(self):
        """Test the metadata pass stayed on the vector side."""
        others = [c for c in geocase.list_cases() if c.category in {"raster", "netcdf"}]
        assert others
        assert all(not c.assertions.required_drivers for c in others)


class TestTheFilterActuallySeparates:
    """The plan's acceptance bar: the declaration must partition the corpus.

    ``loader_hint`` marks all 113 vector cases ``geopandas`` and therefore
    cannot express this. ``required_drivers`` must, or 2.1 has not landed.
    """

    def test_the_three_tiers_partition_the_vector_corpus(
        self, vector_cases: list[geocase.CaseMetadata]
    ):
        """Test every vector case falls in exactly one tier, and none is empty."""
        no_driver = [
            c for c in vector_cases if c.assertions.required_drivers == [NO_OGR_DRIVER]
        ]
        needs_plugin = [
            c
            for c in vector_cases
            if c.assertions.required_drivers
            and c.assertions.required_drivers != [NO_OGR_DRIVER]
        ]
        stock = [c for c in vector_cases if not c.assertions.required_drivers]

        assert len(no_driver) + len(needs_plugin) + len(stock) == len(vector_cases)
        assert no_driver and needs_plugin and stock

    def test_a_consumer_can_skip_what_it_cannot_open(
        self, vector_cases: list[geocase.CaseMetadata]
    ):
        """Test the pyogrio-run use case: filter to what a stock build opens."""
        available = {"GeoJSON", "GPKG", "ESRI Shapefile", "KML", "GML", "SQLite"}

        openable = [
            c
            for c in vector_cases
            if all(driver in available for driver in c.assertions.required_drivers)
        ]

        assert openable
        assert len(openable) < len(vector_cases)
        assert all(c.format not in _BARE_GEOMETRY_FORMATS for c in openable)
        assert all(c.format not in _ARROW_FAMILY_DRIVERS for c in openable)
