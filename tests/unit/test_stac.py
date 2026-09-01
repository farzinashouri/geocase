"""Tests for ``geocase.stac`` — Plan 38 Phase 2.1.

Neither stackstac nor odc-stac can consume a bare GeoTIFF; both take STAC
Items. The 2026-08-31 round-2 validation run therefore had to synthesise one
per raster case with ``rio_stac.create_stac_item`` before it could test
anything — and that synthesiser wrote an **inverted** ``proj:bbox`` for
``bottom_up_dem_small``, which is the corpus's own bottom-up case. Every user
who writes that adapter hits the same bug, and most misattribute it to the
consumer.

Three requirements the hand-built version had to learn the hard way, each
pinned below:

* **Both ``proj:epsg`` and ``proj:code``.** stackstac reads only the former;
  pystac >= 1.13 rewrites it to the latter on ``from_dict``. Emitting one of
  them silently excludes a consumer.
* **A normalised ``proj:bbox``.** Not rio-stac's inverted passthrough.
* **Per-band assets *and* a whole-file asset.** stackstac's model is one band
  per asset and it refuses multi-band rasters; odc-stac reads them. Both
  shapes have to be reachable so the difference is a choice the harness
  records rather than a failure it trips over.
"""

from __future__ import annotations

import pytest

from geocase.stac import item_for_case, items_for_cases

pytest.importorskip("rasterio")


class TestItemShape:
    """A synthesised Item has to be a valid Item before it is anything else."""

    def test_item_is_a_feature_with_the_required_stac_keys(self):
        """Test the minimum an Item must carry to be read at all."""
        item = item_for_case("dem_small")
        assert item["type"] == "Feature"
        assert item["stac_version"].startswith("1.")
        assert item["id"] == "dem_small"
        assert set(item) >= {
            "type",
            "stac_version",
            "id",
            "geometry",
            "bbox",
            "properties",
            "links",
            "assets",
        }

    def test_datetime_is_present_because_both_consumers_require_one(self):
        """Test properties carry a datetime; stackstac indexes time by it."""
        item = item_for_case("dem_small")
        assert item["properties"]["datetime"] is not None

    def test_bbox_is_geographic_and_ordered(self):
        """Test the Item's own bbox is lon/lat and min-before-max."""
        item = item_for_case("dem_small")
        west, south, east, north = item["bbox"]
        assert west < east
        assert south < north
        assert -180.0 <= west <= 180.0
        assert -90.0 <= south <= 90.0

    def test_unknown_case_raises_keyerror(self):
        """Test a typo'd id fails loudly rather than yielding an empty Item."""
        with pytest.raises(KeyError):
            item_for_case("no_such_case_at_all")

    def test_a_vector_case_is_refused(self):
        """Test the adapter is honest about being raster-only."""
        with pytest.raises(ValueError, match="raster"):
            item_for_case("simple_valid_point")


class TestProjectionExtensionServesBothConsumers:
    """Requirement 1: emit ``proj:epsg`` *and* ``proj:code``."""

    def test_both_spellings_of_the_crs_are_present(self):
        """Test one Item serves stackstac (epsg) and pystac >=1.13 (code)."""
        properties = item_for_case("dem_small")["properties"]
        assert properties["proj:epsg"] == 32633
        assert properties["proj:code"] == "EPSG:32633"

    def test_the_projection_extension_is_declared(self):
        """Test ``stac_extensions`` names projection, so the keys are legal."""
        item = item_for_case("dem_small")
        assert any("projection" in url for url in item["stac_extensions"])

    def test_shape_and_transform_are_declared(self):
        """Test the grid is described, so a consumer need not open the file."""
        properties = item_for_case("dem_small")["properties"]
        assert properties["proj:shape"] == [16, 16]
        assert len(properties["proj:transform"]) in (6, 9)


class TestProjBboxIsNormalised:
    """Requirement 2: the bug rio-stac had, on the corpus's own case."""

    def test_proj_bbox_is_min_before_max_on_a_north_up_raster(self):
        """Test the ordinary case is ordered."""
        properties = item_for_case("dem_small")["properties"]
        west, south, east, north = properties["proj:bbox"]
        assert west < east
        assert south < north

    def test_proj_bbox_is_min_before_max_on_the_bottom_up_raster(self):
        """Test the case that broke rio-stac's synthesiser.

        ``bottom_up_dem_small`` has a positive ``e`` term, so a passthrough
        that trusts the transform's row order emits south > north.
        """
        properties = item_for_case("bottom_up_dem_small")["properties"]
        west, south, east, north = properties["proj:bbox"]
        assert south < north, "inverted proj:bbox — the rio-stac defect"
        assert west < east

    def test_proj_bbox_is_min_before_max_on_a_rotated_raster(self):
        """Test a skewed affine still yields an ordered axis-aligned box."""
        properties = item_for_case("rotated_two_islands")["properties"]
        west, south, east, north = properties["proj:bbox"]
        assert west < east
        assert south < north


class TestAssetShapes:
    """Requirement 3: per-band assets *and* a whole-file asset."""

    def test_whole_file_asset_is_always_present(self):
        """Test odc-stac's shape — one asset naming the file — is reachable."""
        assets = item_for_case("geotiff_multiband_small")["assets"]
        assert "data" in assets
        assert assets["data"]["href"].endswith(".tif")

    def test_per_band_assets_are_emitted_for_a_multiband_raster(self):
        """Test stackstac's shape — one asset per band — is also reachable."""
        assets = item_for_case("geotiff_multiband_small", assets="per_band")
        assert len(assets["assets"]) == 3
        for name, asset in assets["assets"].items():
            assert asset["href"].endswith(".tif")
            assert asset["bands"][0]["index"] >= 1 or "eo:bands" in asset
            assert name != "data"

    def test_per_band_assets_declare_which_band_they_are(self):
        """Test a band asset says its 1-based index, or it is unreadable."""
        assets = item_for_case("geotiff_multiband_small", assets="per_band")["assets"]
        indices = sorted(asset["band_index"] for asset in assets.values())
        assert indices == [1, 2, 3]

    def test_both_shapes_are_available_at_once(self):
        """Test ``assets="both"`` carries the whole file and the bands."""
        assets = item_for_case("geotiff_multiband_small", assets="both")["assets"]
        assert "data" in assets
        assert len(assets) == 4

    def test_a_singleband_raster_still_gets_one_band_asset(self):
        """Test the per-band shape degenerates cleanly, not to zero assets."""
        assets = item_for_case("dem_small", assets="per_band")["assets"]
        assert len(assets) == 1

    def test_an_unknown_asset_shape_is_refused(self):
        """Test a typo does not silently produce the default shape."""
        with pytest.raises(ValueError, match="assets"):
            item_for_case("dem_small", assets="whole-file")


class TestHrefsResolve:
    """An Item nobody can open is not an adapter."""

    def test_href_points_at_the_real_file_on_disk(self):
        """Test the asset href resolves to the case's materialized bytes."""
        from pathlib import Path
        from urllib.parse import urlparse

        href = item_for_case("dem_small")["assets"]["data"]["href"]
        assert href.startswith("file://")
        assert Path(urlparse(href).path).is_file()

    def test_hrefs_can_be_plain_paths_for_consumers_that_dislike_file_urls(self):
        """Test ``absolute_href=False`` yields a bare path."""
        from pathlib import Path

        href = item_for_case("dem_small", href_style="path")["assets"]["data"]["href"]
        assert not href.startswith("file://")
        assert Path(href).is_file()


class TestItemsForCases:
    """The whole point: byte-identical input for every consumer."""

    def test_items_for_cases_returns_one_item_per_raster_case(self):
        """Test the sweep helper covers the raster category."""
        items = items_for_cases(category="raster")
        assert len(items) > 20
        assert all(item["type"] == "Feature" for item in items)

    def test_selection_is_forwarded_to_list_cases(self):
        """Test the catalog's own selectors are reused, not reinvented."""
        items = items_for_cases(include_ids=["dem_small", "ndvi_small"])
        assert sorted(item["id"] for item in items) == ["dem_small", "ndvi_small"]

    def test_non_raster_cases_are_skipped_rather_than_raising(self):
        """Test a mixed selection yields the rasters, not an exception.

        A sweep helper that dies on the first vector case cannot be pointed at
        the corpus, which is the only thing anyone wants to point it at.
        """
        items = items_for_cases(include_ids=["dem_small", "simple_valid_point"])
        assert [item["id"] for item in items] == ["dem_small"]

    def test_items_are_deterministic(self):
        """Test two calls agree, so a differential run is reproducible."""
        assert items_for_cases(include_ids=["dem_small"]) == items_for_cases(
            include_ids=["dem_small"]
        )
