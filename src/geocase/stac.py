"""STAC Items for raster cases — the adapter round 2 had to build by hand.

Plan 38 Phase 2.1. Neither ``stackstac`` nor ``odc-stac`` can consume a bare
GeoTIFF; both take STAC Items. The 2026-08-31 validation run therefore had to
synthesise one per raster case with ``rio_stac.create_stac_item`` before it
could test anything — and that synthesiser was **wrong for**
``bottom_up_dem_small``, writing an inverted ``proj:bbox``. A corpus whose
users must each write that adapter will each hit that bug, and most will
misattribute it to the consumer. So the corpus ships the adapter::

    from geocase.stac import item_for_case, items_for_cases

    item = item_for_case("dem_small")            # projection ext v1.1 AND v2.0
    items = items_for_cases(category="raster")   # identical input, every consumer

Three requirements the hand-built version had to learn:

1. **Emit both ``proj:epsg`` and ``proj:code``.** stackstac reads only the
   former; pystac >= 1.13 rewrites it to the latter on ``from_dict``. An
   adapter emitting one of them silently excludes a consumer. Emitting both is
   spec-legal and is the only way one Item serves both.
2. **Normalise ``proj:bbox``.** Not rio-stac's inverted passthrough — the
   corpus knows its own conventions and should not propagate an invalid Item.
3. **Offer per-band assets *and* a whole-file asset.** stackstac's model is one
   band per asset and it refuses the multi-band rasters; odc-stac reads them.
   Both shapes must be reachable so the difference is a *choice* the harness
   records, not a failure it trips over.

Output is plain ``dict`` — the STAC Item is JSON, and requiring ``pystac`` to
produce one would put a dependency between the corpus and every consumer that
does not use it. ``pystac.Item.from_dict`` accepts what this emits.

Deliberately **not** in :data:`geocase.__all__`: a submodule import, the same
precedent :mod:`geocase.differential` and :mod:`geocase.raster` set.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

__all__ = [
    "PROJECTION_EXTENSION",
    "AssetShape",
    "item_for_case",
    "items_for_cases",
]

#: The projection extension this adapter's property names come from.
PROJECTION_EXTENSION = "https://stac-extensions.github.io/projection/v2.0.0/schema.json"

#: Which asset layout to emit. ``"whole_file"`` is odc-stac's shape (one asset
#: naming the file); ``"per_band"`` is stackstac's (one asset per band, which
#: is the only way it will read a multi-band raster); ``"both"`` carries the
#: two at once so a single Item serves either consumer.
AssetShape = Literal["whole_file", "per_band", "both"]

_ASSET_SHAPES = ("whole_file", "per_band", "both")

#: Placeholder acquisition time. The corpus's rasters are synthetic and carry
#: no acquisition date, but both consumers index by time and neither tolerates
#: a null datetime on an Item with no ``start_datetime``/``end_datetime`` pair.
#: Fixed rather than ``now()`` so two runs produce byte-identical input.
_DATETIME = "2020-01-01T00:00:00Z"


def _case_metadata(case_id: str) -> Any:
    import geocase

    return geocase.get_case(case_id)


def _primary_path(case_id: str) -> Path:
    from geocase.catalog.roots import case_roots_by_id

    roots = case_roots_by_id()
    metadata = _case_metadata(case_id)
    try:
        root = roots[case_id]
    except KeyError as exc:  # a manifest case whose bytes were never fetched
        raise KeyError(
            f"case {case_id!r} has no materialized data on this machine"
        ) from exc
    return Path(root) / str(metadata.files.primary)


def _normalise_bbox(bounds: Any) -> list[float]:
    """Return ``[west, south, east, north]`` with min before max on both axes.

    This is requirement 2, and the entire reason it exists is
    ``bottom_up_dem_small``: its affine has a *positive* ``e`` term, so a
    passthrough that trusts the transform's row order emits ``south > north``.
    rio-stac does exactly that, and the resulting Item is invalid — a consumer
    that trusts it computes an empty or inverted intersection and reports
    nothing, which reads as "the case is fine".
    """
    left, bottom, right, top = (float(value) for value in bounds)
    return [min(left, right), min(bottom, top), max(left, right), max(bottom, top)]


def _geographic_bbox(dataset: Any) -> list[float]:
    """The Item's own ``bbox``: the footprint in lon/lat, ordered."""
    from rasterio.warp import transform_bounds

    if dataset.crs is None:
        return _normalise_bbox(dataset.bounds)
    return _normalise_bbox(
        transform_bounds(dataset.crs, "EPSG:4326", *dataset.bounds, densify_pts=21)
    )


def _geometry_from_bbox(bbox: list[float]) -> dict[str, Any]:
    west, south, east, north = bbox
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
            ]
        ],
    }


def _href(path: Path, style: str) -> str:
    if style == "path":
        return str(path)
    if style == "file_url":
        return path.as_uri()
    raise ValueError(f"unknown href_style {style!r}; expected 'file_url' or 'path'")


def _band_name(dataset: Any, index: int) -> str:
    """A stable per-band asset key.

    The band's own description when the file carries one — that is what a
    consumer resolving an ``eo:bands`` alias will look at — and ``b1``-style
    positional names otherwise, because an asset key must exist regardless.
    """
    description = dataset.descriptions[index - 1]
    if description:
        return str(description)
    return f"b{index}"


def _assets(
    dataset: Any, path: Path, shape: str, href_style: str
) -> dict[str, dict[str, Any]]:
    if shape not in _ASSET_SHAPES:
        raise ValueError(
            f"unknown assets shape {shape!r}; expected one of {_ASSET_SHAPES}"
        )

    href = _href(path, href_style)
    media_type = "image/tiff; application=geotiff"
    assets: dict[str, dict[str, Any]] = {}

    if shape in ("whole_file", "both"):
        assets["data"] = {
            "href": href,
            "type": media_type,
            "roles": ["data"],
            "title": f"{path.name} (all {dataset.count} band(s))",
        }

    if shape in ("per_band", "both"):
        for index in range(1, dataset.count + 1):
            name = _band_name(dataset, index)
            # ``band_index`` is the flat, unambiguous fact a harness needs: a
            # per-band asset that does not say *which* band it is cannot be
            # read back. ``bands`` is the v2.0 spelling and ``eo:bands`` the
            # v1.x one; both ship for the same reason both CRS keys do.
            assets[name] = {
                "href": href,
                "type": media_type,
                "roles": ["data"],
                "band_index": index,
                "bands": [{"name": name, "index": index}],
                "eo:bands": [{"name": name}],
            }

    return assets


def item_for_case(
    case_id: str,
    *,
    assets: AssetShape = "whole_file",
    href_style: Literal["file_url", "path"] = "file_url",
    datetime: str = _DATETIME,
) -> dict[str, Any]:
    """Build a STAC Item for one bundled raster case.

    Args:
        case_id: A raster case id, e.g. ``"dem_small"``.
        assets: Which asset layout to emit. See :data:`AssetShape`.
        href_style: ``"file_url"`` emits a ``file://`` URI (what pystac and
            stackstac expect); ``"path"`` emits a bare filesystem path, for
            the consumers that mishandle ``file://``.
        datetime: The Item's acquisition time. Fixed by default so a repeat
            run produces byte-identical input.

    Returns:
        A plain ``dict`` STAC Item. ``pystac.Item.from_dict`` accepts it.

    Raises:
        KeyError: If the case id is unknown, or its bytes are not on disk.
        ValueError: If the case is not a raster, or ``assets`` is not one of
            :data:`AssetShape`.
        ImportError: If rasterio is not installed — the Item's grid facts come
            from the file, not from ``case.yaml``, so that a declared-vs-real
            drift cannot make it into the Item.
    """
    import rasterio

    metadata = _case_metadata(case_id)
    if metadata.category != "raster":
        raise ValueError(
            f"case {case_id!r} is {metadata.category}, not raster; "
            "STAC Items are only built for raster cases"
        )

    path = _primary_path(case_id)
    with rasterio.open(path) as dataset:
        bbox = _geographic_bbox(dataset)
        properties: dict[str, Any] = {
            "datetime": datetime,
            "proj:shape": [int(dataset.height), int(dataset.width)],
            "proj:transform": [float(value) for value in dataset.transform[:6]],
            "proj:bbox": _normalise_bbox(dataset.bounds),
        }
        if dataset.crs is not None:
            epsg = dataset.crs.to_epsg()
            if epsg is not None:
                # Requirement 1. stackstac reads proj:epsg and nothing else;
                # pystac >= 1.13 rewrites it to proj:code on from_dict. One
                # Item serves both only by carrying both.
                properties["proj:epsg"] = int(epsg)
                properties["proj:code"] = f"EPSG:{epsg}"
            else:
                properties["proj:wkt2"] = dataset.crs.to_wkt()
        item_assets = _assets(dataset, path, assets, href_style)

    return {
        "type": "Feature",
        "stac_version": "1.1.0",
        "stac_extensions": [PROJECTION_EXTENSION],
        "id": case_id,
        "geometry": _geometry_from_bbox(bbox),
        "bbox": bbox,
        "properties": properties,
        "links": [],
        "assets": item_assets,
        "collection": "geocase",
    }


def items_for_cases(
    *,
    assets: AssetShape = "whole_file",
    href_style: Literal["file_url", "path"] = "file_url",
    datetime: str = _DATETIME,
    **selection: Any,
) -> list[dict[str, Any]]:
    """Build Items for every selected raster case, in catalog order.

    Non-raster cases in the selection are **skipped**, not an error: a sweep
    helper that dies on the first vector case cannot be pointed at the corpus,
    which is the only thing anyone wants to point it at. Cases whose bytes are
    not materialized are skipped for the same reason.

    Args:
        assets: See :func:`item_for_case`.
        href_style: See :func:`item_for_case`.
        datetime: See :func:`item_for_case`.
        **selection: Forwarded verbatim to :func:`geocase.list_cases`, so the
            catalog's own selectors are reused rather than reinvented.

    Returns:
        One Item dict per raster case selected.
    """
    import geocase

    items: list[dict[str, Any]] = []
    for metadata in geocase.list_cases(**selection):
        if metadata.category != "raster":
            continue
        try:
            items.append(
                item_for_case(
                    metadata.id,
                    assets=assets,
                    href_style=href_style,
                    datetime=datetime,
                )
            )
        except KeyError:
            # Not materialized on this machine. Blaming the consumer for
            # geocase's missing bytes is what compare_cases already refuses.
            continue
    return items
