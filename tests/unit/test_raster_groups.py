"""Gate the four cases round 2 could not express — Plan 38 Phase 4.

Every geocase raster case was one standalone file, so the corpus could not
express stacking order, mosaic compositing, temporal grouping, or two assets in
one Item. ``odc.stac.load`` and ``stackstac.stack`` both take a *sequence* of
Items and their whole reason for existing is what happens across that
sequence — the run could only ever hand them a list of one.

Deliberately **no new** ``from_origin`` EPSG:32633 baselines: Plan 37 §3 says
the corpus is thick there and thin on convention divergence, and round 2
confirms it. The single rotated raster and the single bottom-up raster found
four defects between them; the 31 north-up UTM baselines found their defects
only in aggregate, on an option axis.

As in ``test_transform_conventions.py``, every property is read from the real
bytes rather than from ``case.yaml``: the declaration is what a regeneration
would update, and it is the bytes that have to keep the property.
"""

from __future__ import annotations

import pytest

import geocase

rasterio = pytest.importorskip("rasterio")

#: The overlap group — Phase 4.1. Three small rasters sharing a CRS, with
#: deliberate partial overlap and distinct constant values so that "which pixel
#: won" is readable by inspection rather than by arithmetic.
OVERLAP_GROUP = (
    "overlap_group_north",
    "overlap_group_centre",
    "overlap_group_south",
)


def open_case(case_id: str):
    """Open a bundled raster case's primary file with rasterio."""
    return rasterio.open(geocase.load_case(case_id).primary_path)


class TestTheOverlapGroupExists:
    """Phase 4.1 — the gap with the most attached evidence."""

    @pytest.mark.parametrize("case_id", OVERLAP_GROUP)
    def test_each_member_is_a_registered_raster_case(self, case_id):
        """Test the members are selectable individually, like any case."""
        metadata = geocase.get_case(case_id)
        assert metadata.category == "raster"

    @pytest.mark.parametrize("case_id", OVERLAP_GROUP)
    def test_each_member_names_the_group_it_belongs_to(self, case_id):
        """Test the group is a declared relationship, not a naming accident.

        A divergence that is a relationship between two inputs is not
        expressible by two independently selectable cases, which is why
        ``utm_zone_33n_to_32n_pair`` and ``crs_mismatch_overlay_pair`` declare
        theirs. A stack of three needs the same.
        """
        metadata = geocase.get_case(case_id)
        assert metadata.params.get("group") == "overlap_group"
        assert set(metadata.params.get("group_members", [])) == set(OVERLAP_GROUP)

    @pytest.mark.parametrize("case_id", OVERLAP_GROUP)
    def test_each_member_declares_its_stacking_order(self, case_id):
        """Test the group has an order, or "which pixel won" is unanswerable."""
        order = geocase.get_case(case_id).params.get("stack_order")
        assert isinstance(order, int)
        assert 1 <= order <= len(OVERLAP_GROUP)

    def test_the_stacking_orders_are_distinct(self):
        """Test no two members claim the same position in the stack."""
        orders = [geocase.get_case(c).params["stack_order"] for c in OVERLAP_GROUP]
        assert sorted(orders) == [1, 2, 3]


class TestTheOverlapGroupOverlaps:
    """A group whose members do not overlap tests nothing about compositing."""

    def test_every_member_shares_one_crs(self):
        """Test the group is stackable without a reprojection confound."""
        crss = set()
        for case_id in OVERLAP_GROUP:
            with open_case(case_id) as dataset:
                crss.add(dataset.crs.to_string())
        assert len(crss) == 1, crss

    def test_consecutive_members_partially_overlap(self):
        """Test the overlap is *partial*: neither disjoint nor identical."""
        bounds = []
        for case_id in OVERLAP_GROUP:
            with open_case(case_id) as dataset:
                bounds.append(dataset.bounds)

        for left, right in zip(bounds, bounds[1:], strict=False):
            overlap_width = min(left.right, right.right) - max(left.left, right.left)
            overlap_height = min(left.top, right.top) - max(left.bottom, right.bottom)
            assert overlap_width > 0 and overlap_height > 0, "members are disjoint"
            assert (left.left, left.bottom, left.right, left.top) != (
                right.left,
                right.bottom,
                right.right,
                right.top,
            ), "members are identical, so compositing is unobservable"

    def test_each_member_carries_a_distinct_constant_value(self):
        """Test which member a composited pixel came from is readable."""
        import numpy as np

        values = []
        for case_id in OVERLAP_GROUP:
            with open_case(case_id) as dataset:
                band = dataset.read(1, masked=True)
            unique = np.unique(band.compressed())
            assert unique.size == 1, f"{case_id} is not constant: {unique}"
            values.append(float(unique[0]))
        assert len(set(values)) == len(values), values

    def test_the_members_are_on_a_shared_pixel_grid(self):
        """Test a stack does not need resampling to composite.

        Off-grid members would make every compositing difference a resampling
        difference, which is a different finding on a different axis.
        """
        transforms = []
        for case_id in OVERLAP_GROUP:
            with open_case(case_id) as dataset:
                transforms.append(dataset.transform)

        first = transforms[0]
        for transform in transforms[1:]:
            assert (transform.a, transform.e) == (first.a, first.e)
            assert (transform.c - first.c) % first.a == pytest.approx(0.0, abs=1e-6)


class TestTheSharedBandAlias:
    """Phase 4.2 — two assets in one group both claiming ``red``."""

    def test_two_group_members_declare_the_same_common_name(self):
        """Test the ambiguity exists to be resolved.

        The ordinary Sentinel-2 shape. odc-stac resolves the alias silently to
        the first candidate today and the source carries its own
        ``# maybe warn about ambiguity?`` note; a consumer doing that is only
        *visible* if two candidates exist.
        """
        common_names = [
            geocase.get_case(case_id).params.get("common_name")
            for case_id in OVERLAP_GROUP
        ]
        assert common_names.count("red") == 2, common_names

    def test_the_ambiguous_members_are_otherwise_distinguishable(self):
        """Test a consumer picking the wrong one produces a wrong *value*."""
        import numpy as np

        reds = [
            case_id
            for case_id in OVERLAP_GROUP
            if geocase.get_case(case_id).params.get("common_name") == "red"
        ]
        values = []
        for case_id in reds:
            with open_case(case_id) as dataset:
                values.append(
                    float(np.unique(dataset.read(1, masked=True).compressed())[0])
                )
        assert values[0] != values[1]

    def test_the_stac_item_group_carries_both_red_assets(self):
        """Test the ambiguity survives the adapter, which is where it matters."""
        from geocase.stac import items_for_cases

        items = items_for_cases(include_ids=list(OVERLAP_GROUP), assets="per_band")
        red_assets = [
            name
            for item in items
            for name, asset in item["assets"].items()
            if "red" in name.lower()
            or any(
                band.get("common_name") == "red" for band in asset.get("eo:bands", [])
            )
        ]
        assert len(red_assets) == 2, red_assets


class TestTheSecondCrsFamily:
    """Phase 4.3 — 31 of 34 rasters were EPSG:32633."""

    def test_the_geographic_twin_case_exists(self):
        """Test the same footprint is available in a geographic CRS."""
        metadata = geocase.get_case("crs_family_pair_geographic")
        assert metadata.category == "raster"

    def test_the_projected_twin_case_exists(self):
        """Test the projected half of the pair exists too."""
        metadata = geocase.get_case("crs_family_pair_projected")
        assert metadata.category == "raster"

    def test_the_pair_declares_its_relationship(self):
        """Test the pairing is declared, following the Plan 36 §2 precedent."""
        for case_id in ("crs_family_pair_projected", "crs_family_pair_geographic"):
            params = geocase.get_case(case_id).params
            assert params.get("pair") == "crs_family_pair"
            assert params.get("pair_role") in {"projected", "geographic"}

    def test_the_two_halves_really_are_in_different_crs_families(self):
        """Test the unit-change axis is assertable from inside the corpus.

        This is the axis that caught odc-stac's HIGH defect, and until now it
        was reachable only through an external consumer's ``crs=`` option.
        """
        with open_case("crs_family_pair_projected") as projected:
            projected_crs = projected.crs
        with open_case("crs_family_pair_geographic") as geographic:
            geographic_crs = geographic.crs

        assert projected_crs.is_projected
        assert geographic_crs.is_geographic
        assert projected_crs.linear_units != "unknown"

    def test_the_two_halves_describe_the_same_ground(self):
        """Test the pair is a reprojection, not two unrelated scenes."""
        from rasterio.warp import transform_bounds

        with open_case("crs_family_pair_projected") as projected:
            projected_wgs84 = transform_bounds(
                projected.crs, "EPSG:4326", *projected.bounds
            )
        with open_case("crs_family_pair_geographic") as geographic:
            geographic_wgs84 = transform_bounds(
                geographic.crs, "EPSG:4326", *geographic.bounds
            )

        for left, right in zip(projected_wgs84, geographic_wgs84, strict=True):
            assert left == pytest.approx(right, abs=1e-3)


class TestTheSecondRotatedRaster:
    """Phase 4.4 — ``rotated_two_islands`` was 2-for-2 and one of a kind."""

    def test_the_nonsquare_rotated_case_exists(self):
        """Test a second point on the rotation axis ships."""
        assert geocase.get_case("rotated_nonsquare_small").category == "raster"

    def test_it_really_is_rotated(self):
        """Test the skew survives regeneration."""
        with open_case("rotated_nonsquare_small") as dataset:
            transform = dataset.transform
        assert (transform.b, transform.d) != (0.0, 0.0)

    def test_its_pixels_are_not_square(self):
        """Test the API-asymmetry axis the run stumbled into is expressible.

        A scalar ``resolution=`` cannot express non-square pixels, so a harness
        passing one silently squares the grid. That was the harness's bug, and
        the corpus is what made it visible — but only on a north-up case. This
        makes it reachable while rotated.
        """
        with open_case("rotated_nonsquare_small") as dataset:
            transform = dataset.transform
        x_size = (transform.a**2 + transform.d**2) ** 0.5
        y_size = (transform.b**2 + transform.e**2) ** 0.5
        assert x_size != pytest.approx(y_size, rel=1e-6)

    def test_its_skew_sign_differs_from_rotated_two_islands(self):
        """Test the second point is a *different* rotation, not a copy.

        "Handles rotation" and "handles *this* rotation" are different claims,
        and one sample cannot distinguish them.
        """
        with open_case("rotated_two_islands") as first:
            first_b = first.transform.b
        with open_case("rotated_nonsquare_small") as second:
            second_b = second.transform.b
        assert (first_b > 0) != (second_b > 0), (
            f"both skews have the same sign ({first_b}, {second_b}); "
            "the second case does not widen the axis"
        )
