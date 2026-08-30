"""Compute a case's WGS84 extent from its real bytes.

A sibling of :mod:`catalog_geometry` and :mod:`catalog_raster`, and it follows
their conventions: imports of the geospatial stack are lazy, every load failure
is swallowed rather than raised, and coordinates are rounded to a fixed
precision so the committed ``case.yaml`` files do not churn on platform
floating-point noise.

The extent is *derived*, never hand-written -- that is the point. A hand-typed
bbox drifts from the data the first time a fixture is regenerated; a computed
one cannot. The editorial counterpart is ``region:``, which this module never
touches.

Three things are load-bearing:

- **Reprojection is mandatory, not opportunistic.** 23 of the bundled rasters
  are EPSG:32633, whose bounds are metres. Publishing those unprojected would
  place the case at "longitude 500000".
- **Vector cases go through** :meth:`VectorCase.load`, not
  ``geopandas.read_file``. Plan 29 established that the raw reader reaches only
  78 of 104 vector cases; the WKB/WKT/CSV_WKT/Arrow families need the case
  object. Using the raw reader here would silently leave a quarter of the
  catalog with no extent.
- **The antimeridian gets the wrap convention.** ``dateline_crossing_polygon``
  stores unwrapped longitudes (170..190). Taking that envelope literally
  publishes a box spanning most of the planet -- the exact opposite of the
  fact the case exists to demonstrate. See :class:`geocase.SpatialExtent`.

NetCDF is skipped: xarray is not in the ``catalog`` CI job's install set, the
same cut :mod:`geocase.catalog.content` makes. The one netcdf case can carry a
hand-written ``region`` only.

Run ``python scripts/catalog_extent.py --write`` to populate ``extent:``
across the catalog, or ``--check`` to gate it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from geocase.catalog.models import SpatialExtent  # noqa: E402


#: Decimals kept in a written extent. Six is about 10 cm at the equator --
#: far finer than any fixture's placement is meaningful, and coarse enough
#: that the last bits of FP noise never reach a committed file.
PRECISION = 6

#: A geometry whose naive longitude envelope is wider than this is treated as
#: an antimeridian crosser rather than a genuinely near-global dataset. No
#: bundled case is near-global, and the alternative reading -- "this 10-degree
#: polygon really does span the planet" -- is never the true one.
_WRAP_THRESHOLD_DEGREES = 180.0


def _round(value: float) -> float:
    return round(float(value), PRECISION)


def _wrap_longitude(lon: float) -> float:
    """Fold a longitude into [-180, 180]."""
    wrapped = (float(lon) + 180.0) % 360.0 - 180.0
    # ``180`` folds to ``-180``; keep the eastern form, which reads better as
    # the east edge of a box and is what the fixtures were authored with.
    return 180.0 if wrapped == -180.0 and lon > 0 else wrapped


def _extent_from_bounds(
    west: float, south: float, east: float, north: float
) -> SpatialExtent | None:
    """Build an extent from a raw lon/lat envelope, wrapping when it must.

    A wide envelope is the signature of an antimeridian crosser, whether it
    arrived as unwrapped longitudes (170..190, as ``dateline_crossing_polygon``
    stores them) or as a folded pair that already straddles the line. Either
    way the honest box is the *short* way round, which is the wrapped form.
    """
    if any(value != value for value in (west, south, east, north)):  # NaN
        return None
    if any(abs(value) == float("inf") for value in (west, south, east, north)):
        return None

    if east - west > _WRAP_THRESHOLD_DEGREES:
        west, east = _wrap_longitude(east), _wrap_longitude(west)
    else:
        west, east = _wrap_longitude(west), _wrap_longitude(east)

    # Latitudes are *not* clamped into range. ``out_of_bounds_coordinates``
    # carries a point at latitude 100, which is the entire point of the case:
    # clamping it to 90 would publish a plausible-looking box for data that has
    # no valid WGS84 position at all, which is exactly the kind of false green
    # light this catalog exists to eliminate. No extent is the honest answer.
    if not (-90.0 <= float(south) <= 90.0 and -90.0 <= float(north) <= 90.0):
        return None
    south, north = float(south), float(north)
    if north < south:
        return None

    try:
        return SpatialExtent(
            west=_round(west),
            south=_round(south),
            east=_round(east),
            north=_round(north),
        )
    except Exception:
        return None


def _vector_extent(case_id: str) -> SpatialExtent | None:
    import geocase

    gdf = geocase.load_case(case_id).load()
    if gdf is None or len(gdf) == 0:
        return None

    crs = getattr(gdf, "crs", None)
    if crs is not None:
        try:
            if crs.to_epsg() != 4326:
                gdf = gdf.to_crs(4326)
        except Exception:
            # An unconvertible CRS is a case-level fact, not a crash: leave the
            # extent unset rather than publishing metres as degrees.
            return None

    bounds = gdf.geometry.total_bounds
    return _extent_from_bounds(*(float(value) for value in bounds))


def _raster_extent(case_id: str) -> SpatialExtent | None:
    from rasterio.warp import transform_bounds

    import geocase

    # ``case.open()`` rather than a bare ``rasterio.open`` for the same reason
    # the vector path uses ``VectorCase.load``: the case object is what a user
    # would reach for, so the extent is computed from the bytes they would see.
    with geocase.load_case(case_id).open() as src:
        if src.crs is None:
            return None
        bounds = src.bounds
        if src.crs.to_epsg() == 4326:
            west, south, east, north = (float(value) for value in bounds)
        else:
            west, south, east, north = transform_bounds(src.crs, "EPSG:4326", *bounds)
    return _extent_from_bounds(west, south, east, north)


def case_extent(case: Any) -> SpatialExtent | None:
    """Return *case*'s WGS84 extent, or ``None`` when it has none.

    ``None`` is an ordinary outcome, not an error: netcdf is out of scope, a
    CRS-less payload cannot be placed, and several bundled cases are
    deliberately unloadable (``unclosed_ring_polygon`` is malformed on
    purpose). Callers fall back to the ``region`` label alone.
    """
    category = str(getattr(case.category, "value", case.category))
    try:
        if category == "vector":
            return _vector_extent(case.id)
        if category == "raster":
            return _raster_extent(case.id)
    except Exception:
        # Broken fixtures are part of the catalog's point; a load failure here
        # is an expected outcome, the same contract catalog_geometry keeps.
        return None
    return None


# --- writing extents back into the catalog ----------------------------------


def _case_yaml_paths() -> list[tuple[Any, Path]]:
    """Pair each registered case with the YAML file that declares it.

    Resolved through the case index rather than by assuming ``<root>/case.yaml``:
    ``raster/footprint_edge_cases/`` holds five cases in one directory as
    ``case_<id>.yaml``, and the naive form silently skipped all five.
    """
    from geocase.catalog.loader import load_case_index, load_case_metadata
    from geocase.catalog.registry import get_registry

    package_root = SRC_ROOT / "geocase"
    by_id: dict[str, Path] = {}
    for rel_path in load_case_index(package_root / "metadata" / "case-index.yaml"):
        path = package_root / rel_path
        if not path.exists():
            continue
        try:
            by_id[load_case_metadata(path).id] = path
        except Exception:
            continue

    return [
        (case, by_id[case.id])
        for case in get_registry().list_cases()
        if case.id in by_id
    ]


#: Where ``extent:`` is inserted when a file has none. Keeping it next to
#: ``crs:`` groups the spatial facts together, and matches the field order on
#: ``CaseMetadata``.
_EXTENT_ANCHORS = ("crs:", "geometry_type:", "loader_hint:")

#: Marks the generated block so a rewrite can find and replace exactly what it
#: wrote last time. Rewriting must be *idempotent*: the whole value of a
#: generated field is that regenerating changes nothing when nothing moved.
_EXTENT_HEADER = "# Generated by scripts/catalog_extent.py -- do not edit by hand."
_EXTENT_NOTE = "# west > east means the box crosses the antimeridian."


def _render_extent_block(extent: SpatialExtent) -> list[str]:
    return [
        _EXTENT_HEADER,
        _EXTENT_NOTE,
        "extent:",
        f"  west: {extent.west}",
        f"  south: {extent.south}",
        f"  east: {extent.east}",
        f"  north: {extent.north}",
    ]


def _strip_existing_extent(lines: list[str]) -> list[str]:
    """Drop a previously generated ``extent:`` block, comments and all.

    Recognises the block by its generated header, so a hand-written ``extent:``
    in a contributed file is left alone rather than silently rewritten -- and
    so a second ``--write`` run is a no-op.
    """
    out: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index] == _EXTENT_HEADER:
            # Skip the header, the note, ``extent:``, and its indented body.
            index += 1
            if index < len(lines) and lines[index] == _EXTENT_NOTE:
                index += 1
            if index < len(lines) and lines[index].startswith("extent:"):
                index += 1
                while index < len(lines) and lines[index].startswith(("  ", "\t")):
                    index += 1
            # And the blank line the block was separated by.
            while index < len(lines) and not lines[index].strip():
                index += 1
            while out and not out[-1].strip():
                out.pop()
            out.append("")
            continue
        out.append(lines[index])
        index += 1
    return out


def _write_extent(path: Path, extent: SpatialExtent | None) -> bool:
    """Insert, replace, or remove ``extent:`` in *path*. True if it changed.

    ``None`` *removes* a previously generated block rather than leaving it in
    place. A case can stop having a computable extent -- a fixture is
    regenerated outside the WGS84 domain, a payload becomes unreadable -- and a
    stale box surviving that is precisely the drift the field exists to
    prevent.
    """
    original = path.read_text(encoding="utf-8")
    lines = _strip_existing_extent(original.splitlines())

    if extent is None:
        text = "\n".join(lines).rstrip() + "\n"
        if text == original:
            return False
        path.write_text(text, encoding="utf-8")
        return True

    insert_at = len(lines)
    for anchor in _EXTENT_ANCHORS:
        matches = [i for i, line in enumerate(lines) if line.startswith(anchor)]
        if matches:
            insert_at = matches[0] + 1
            break

    block = ["", *_render_extent_block(extent)]
    updated = lines[:insert_at] + block + lines[insert_at:]
    text = "\n".join(updated).rstrip() + "\n"
    if text == original:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--write", action="store_true", help="write computed extents into case.yaml"
    )
    group.add_argument(
        "--check",
        action="store_true",
        help="fail if any declared extent disagrees with the data",
    )
    args = parser.parse_args()

    written = 0
    skipped = 0
    stale: list[str] = []

    for case, path in _case_yaml_paths():
        extent = case_extent(case)
        if extent is None:
            skipped += 1
        if args.write:
            if _write_extent(path, extent):
                written += 1
        else:
            declared = case.extent
            declared_dump = declared.model_dump() if declared else None
            computed_dump = extent.model_dump() if extent else None
            if declared_dump != computed_dump:
                stale.append(f"  {case.id}: declared {declared}, computed {extent}")

    if args.check:
        if stale:
            print("Declared extents are out of date:")
            print("\n".join(stale))
            print("\nRun: python scripts/catalog_extent.py --write")
            return 1
        print(f"Extents up to date ({skipped} case(s) have no computable extent)")
        return 0

    print(f"Wrote {written} extent block(s); {skipped} case(s) skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
