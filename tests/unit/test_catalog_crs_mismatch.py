"""Gates for ``crs_mismatch_overlay_pair`` -- the catalog's first two-layer case.

``crs_mismatch`` sits in the README's opening prose and in plan 24's
pre-committed search vocabulary, and until plan 36 **no case declared it**.
The nearest candidates (``rasterize_match_wgs84_polygon``,
``web_mercator_baseline``) are single-layer, and a CRS mismatch is a
*relationship between two inputs*: one file alone cannot express it.

The trap this case encodes: both layers are individually well-formed and both
parse without warning. The defect only exists in the pair -- the sidecar's
coordinates are UTM 33N metres while its ``crs`` member declares EPSG:4326.
Code that trusts the declaration overlays them and sees agreement; code that
reprojects properly puts them ~5000 km apart.

See docs/plans/36-rc3-release-runbook-and-crs-mismatch.md, Phase 2, which
executes plan 27 section 1.1's ``crs_mismatch_overlay_pair``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geocase.catalog.registry import get_registry

CASE_ID = "crs_mismatch_overlay_pair"


def _metadata():  # type: ignore[no-untyped-def]
    return get_registry().get(CASE_ID)


def _case_dir() -> Path:
    from geocase.catalog.roots import case_roots_by_id

    return case_roots_by_id()[CASE_ID]


def _layer(name: str) -> dict:
    return json.loads((_case_dir() / name).read_text(encoding="utf-8"))


def test_case_declares_crs_mismatch() -> None:
    """The vocabulary gap this case exists to close."""
    assert "crs_mismatch" in _metadata().risk_types
    assert "reprojection_error" in _metadata().risk_types


def test_case_is_the_only_crs_mismatch_case() -> None:
    """Guards the claim in the roadmap and the README.

    If a second case ever declares the term this should be relaxed, not
    deleted -- but the count is worth knowing about deliberately.
    """
    from geocase import list_cases

    declaring = [c.id for c in list_cases() if "crs_mismatch" in c.risk_types]
    assert declaring == [CASE_ID]


def test_pair_ships_as_one_case_with_a_sidecar() -> None:
    """One case, two files.

    A relationship split across two independently-selectable cases can be
    *selected apart*, and a selector returning half a relationship is a
    footgun. Plan 27 section 1.1 left the structure open; plan 36 settles it
    here.
    """
    files = _metadata().files
    assert files.primary == "reference_wgs84.geojson"
    assert files.sidecars == ["mismatched_utm33.geojson"]
    for name in (files.primary, *files.sidecars):
        assert (_case_dir() / name).is_file()


def test_reference_layer_is_honest_wgs84() -> None:
    """The control half: declared EPSG:4326 and actually in degrees."""
    layer = _layer("reference_wgs84.geojson")
    coords = layer["features"][0]["geometry"]["coordinates"][0]
    for lon, lat in coords:
        assert -180.0 <= lon <= 180.0
        assert -90.0 <= lat <= 90.0


def test_sidecar_declares_4326_but_holds_projected_metres() -> None:
    """The defect, asserted against the bytes.

    This is the whole case. The GeoJSON ``crs`` member says EPSG:4326 while
    every ordinate is a UTM 33N easting/northing, far outside degree range.
    """
    layer = _layer("mismatched_utm33.geojson")

    declared = layer["crs"]["properties"]["name"]
    assert "4326" in declared, "the sidecar must *claim* WGS84 -- that is the trap"

    coords = layer["features"][0]["geometry"]["coordinates"][0]
    for easting, northing in coords:
        assert abs(easting) > 180.0 or abs(northing) > 90.0, (
            "sidecar ordinates must be projected metres, not degrees"
        )


def test_both_layers_describe_the_same_ground_footprint() -> None:
    """Reprojecting the sidecar lands it on the reference, within tolerance.

    Without this the case would just be two unrelated files. The mismatch is
    only meaningful because the *correct* interpretation makes them agree.
    """
    pyproj = pytest.importorskip("pyproj")

    meta = _metadata()
    true_epsg = meta.params["sidecar_true_epsg"]
    tolerance = meta.params["agreement_tolerance_m"]

    transformer = pyproj.Transformer.from_crs(
        f"EPSG:{true_epsg}", "EPSG:4326", always_xy=True
    )

    reference = _layer("reference_wgs84.geojson")["features"][0]["geometry"][
        "coordinates"
    ][0]
    projected = _layer("mismatched_utm33.geojson")["features"][0]["geometry"][
        "coordinates"
    ][0]
    assert len(reference) == len(projected)

    geod = pyproj.Geod(ellps="WGS84")
    for (ref_lon, ref_lat), (easting, northing) in zip(reference, projected):
        lon, lat = transformer.transform(easting, northing)
        _, _, distance = geod.inv(ref_lon, ref_lat, lon, lat)
        assert distance <= tolerance, (
            f"reprojected corner is {distance:.1f} m from its reference corner"
        )


def test_naive_overlay_is_catastrophically_wrong() -> None:
    """The consequence, measured rather than asserted in prose.

    Trusting the sidecar's declared CRS puts the footprint thousands of
    kilometres away. The number is what makes the case worth shipping.
    """
    meta = _metadata()
    minimum = meta.params["naive_overlay_error_min_km"]

    pyproj = pytest.importorskip("pyproj")
    geod = pyproj.Geod(ellps="WGS84")

    ref_lon, ref_lat = _layer("reference_wgs84.geojson")["features"][0]["geometry"][
        "coordinates"
    ][0][0]
    # Read the sidecar the way naive code does: ordinates taken as degrees.
    bad_lon, bad_lat = _layer("mismatched_utm33.geojson")["features"][0]["geometry"][
        "coordinates"
    ][0][0]
    bad_lon = ((bad_lon + 180.0) % 360.0) - 180.0
    bad_lat = max(-90.0, min(90.0, bad_lat))

    _, _, distance = geod.inv(ref_lon, ref_lat, bad_lon, bad_lat)
    assert distance / 1000.0 >= minimum
