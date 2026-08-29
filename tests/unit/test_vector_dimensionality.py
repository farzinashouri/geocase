"""Gates for the Z-coordinate vector cases.

Every vector fixture in the catalog was 2D before plan 34, so a consumer that
silently drops the third dimension passed all of them. One ``POLYGON Z``
exercises three separate mechanisms at once: WKB carries Z in its geometry-type
header, GPKG in its per-geometry flag byte, and an OGR driver can drop it
without raising.

The pair is the point. A single WKB fixture would prove shapely round-trips Z;
it takes the GPKG sibling to prove the *driver* preserved it, which is where
the dimension actually goes missing.

The GPKG case also carries the int64 rider: its ``id`` is 9007199254740993,
one past 2^53, so a reader that routes integers through a double returns
...992 and loses the last bit.

See docs/plans/34-close-reviewed-catalog-gaps.md, Phase 4.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from geocase import load_case
from geocase.catalog.content import check_vector_content
from geocase.catalog.registry import get_registry

pytest.importorskip("shapely")

REPO_ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = REPO_ROOT / "src" / "geocase" / "data" / "core" / "vector"

_Z_VALUES = [0.0, 12.5, 25.0, 12.5, 0.0]


def _metadata(case_id: str):  # type: ignore[no-untyped-def]
    return get_registry().get(case_id)


def _case_dir(case_id: str) -> Path:
    from geocase.catalog.roots import case_roots_by_id

    return case_roots_by_id()[case_id]


def _geometry(case_id: str):  # type: ignore[no-untyped-def]
    gdf = load_case(case_id).load()
    return gdf.geometry.iloc[0]


def test_polygon_z_case_carries_z_coordinates() -> None:
    geom = _geometry("polygon_z_wkb")
    assert geom.has_z
    coords = list(geom.exterior.coords)
    assert all(len(c) == 3 for c in coords)
    assert [round(c[2], 6) for c in coords] == _Z_VALUES


def test_polygon_z_survives_the_gpkg_transcoding() -> None:
    """The reason the pair is worth two fixtures.

    WKB carries Z in the geometry-type header; GPKG carries it in a per-geometry
    flag byte. A driver that writes the 2D form raises nothing -- the file is
    valid, the polygon is right, and the elevations are simply gone.
    """
    geom = _geometry("polygon_z_gpkg")
    assert geom.has_z

    wkb_coords = list(_geometry("polygon_z_wkb").exterior.coords)
    gpkg_coords = list(geom.exterior.coords)
    assert len(wkb_coords) == len(gpkg_coords)
    for a, b in zip(wkb_coords, gpkg_coords, strict=True):
        assert round(a[2], 6) == round(b[2], 6)


def test_content_gate_enforces_expect_z() -> None:
    """``params.expect_z`` against a 2D case is exactly one finding."""
    metadata = _metadata("polygon_z_wkb")
    assert check_vector_content(_case_dir("polygon_z_wkb"), metadata) == []

    flat = _metadata("polygon_wkb_baseline").model_copy(deep=True)
    flat.params["expect_z"] = True
    errors = check_vector_content(_case_dir("polygon_wkb_baseline"), flat)
    assert len(errors) == 1
    assert "expect_z" in errors[0]


def test_z_case_extent_ignores_the_third_dimension() -> None:
    """A regression guard on a path that is already closed.

    ``catalog_geometry._ring_path`` slices ``c[:2]`` and ``catalog_extent``
    uses ``total_bounds``, so Z never reaches the projection maths. Pinned
    because the failure would be a crash during page generation, far from the
    fixture that caused it.
    """
    metadata = _metadata("polygon_z_wkb")
    assert metadata.extent is not None
    assert metadata.extent.south < metadata.extent.north
    assert metadata.extent.west < metadata.extent.east


def test_gpkg_sibling_preserves_an_int64_beyond_double_precision() -> None:
    """9007199254740993 is 2^53 + 1: the first integer a float64 cannot hold.

    A reader that routes ids through a double returns ...992. Exact equality is
    the whole assertion -- an off-by-one here is the bug.
    """
    gdf = load_case("polygon_z_gpkg").load()
    assert int(gdf["id"].iloc[0]) == 9007199254740993


def test_content_gate_enforces_the_id_value() -> None:
    metadata = _metadata("polygon_z_gpkg")
    assert check_vector_content(_case_dir("polygon_z_gpkg"), metadata) == []

    wrong = metadata.model_copy(deep=True)
    wrong.params["expected_id_value"] = 1
    errors = check_vector_content(_case_dir("polygon_z_gpkg"), wrong)
    assert len(errors) == 1
    assert "expected_id_value" in errors[0]


def test_z_cases_are_not_family_members() -> None:
    """They vary a property the cross-format family holds constant.

    Same choice plan 33 made for the procedural cases: no
    ``canonical_source_case_id``, no ``cross_format_canonical`` tag, so the
    transcoding gate does not try to diff them against a 2D canonical.
    """
    for case_id in ("polygon_z_wkb", "polygon_z_gpkg"):
        metadata = _metadata(case_id)
        assert "canonical_source_case_id" not in metadata.params
        assert "cross_format_canonical" not in metadata.tags
