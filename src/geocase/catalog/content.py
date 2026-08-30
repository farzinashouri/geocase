"""Content gate — compare a case's declared assertions against its real bytes.

``scripts/validate_catalog.py`` checks schema, file *existence* and
byte-size-vs-``size_class``. It deliberately opens no data file, which is how
six cases came to declare a nodata value while containing zero nodata pixels,
and how ``hole_center_nodata`` came to describe the exact inverse of its own
raster. A case that returns green for a property it cannot test terminates the
user's search — that is the defect this module closes.

The checks delegate to the same helpers in :mod:`geocase.assertions` that users
call in their own tests, catching :class:`AssertionError` into a message list.
The gate and the user-facing assertions must be the *same code*, or the gate
can pass while a user's identical test fails.

Pure functions, no CLI: ``scripts/validate_case_content.py`` is the runner.
Living here rather than in ``scripts/`` means the pytest job can unit-test it
and users can run it against their own manifest cases.

All three categories are checked. NetCDF was exempt until Plan 34 -- xarray was
absent from the catalog job's install set, so the dispatcher returned ``[]``
for the category and ``latlon_small`` reported green for ``expect_nodata`` and
three risk types that nothing had examined. The extra is installed now and
:func:`check_netcdf_content` is the check; it still returns ``[]`` if xarray is
missing, because an absent optional reader is not a data finding.

See docs/plans/28-validate-geocase.md Phase 1, and
docs/plans/34-close-reviewed-catalog-gaps.md Phase 1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from geocase.catalog.models import CaseMetadata, ExpectedErrorKind

__all__ = [
    "check_case_content",
    "check_extent",
    "check_netcdf_content",
    "check_raster_content",
    "check_vector_content",
    "classify_error",
]


def _err(meta: CaseMetadata, field: str, detail: str) -> str:
    """Format one finding so the case id and the offending field both appear."""
    return f"{meta.id}: {field}: {detail}"


def _collect(errors: list[str], meta: CaseMetadata, field: str, fn: Any) -> None:
    """Run *fn*, turning an AssertionError into a message under *field*."""
    try:
        fn()
    except AssertionError as exc:
        errors.append(_err(meta, field, str(exc)))


def _primary_path(case_dir: Path, meta: CaseMetadata) -> Path:
    return Path(case_dir) / meta.files.primary


# --- raster ---------------------------------------------------------------


def _nodata_pixel_count(data: Any, nodata: float | int) -> int:
    """Count pixels equal to *nodata*, NaN-aware.

    ``nan == nan`` is False, so the plain equality used everywhere else silently
    reports zero matches for the NaN convention.
    """
    import numpy as np

    if isinstance(nodata, float) and np.isnan(nodata):
        return int(np.isnan(data).sum())
    return int((data == nodata).sum())


def _total_nodata_pixels(src: Any, nodata: float | int) -> int:
    total = 0
    for band in range(1, src.count + 1):
        total += _nodata_pixel_count(src.read(band), nodata)
    return total


def check_raster_content(case_dir: Path, metadata: CaseMetadata) -> list[str]:
    """Check a raster case's declared assertions against its pixels."""
    import rasterio

    from geocase.assertions.crs import assert_epsg, assert_has_crs
    from geocase.assertions.raster import (
        assert_band_count,
        assert_band_names,
        assert_colormap_present,
        assert_compression,
        assert_dtype,
        assert_has_overviews,
        assert_is_cog,
        assert_nan_nodata,
        assert_nodata_value,
        assert_pixel_anchor,
        assert_scale_factor,
        assert_shape,
        assert_transform_signs,
    )

    errors: list[str] = []
    hints = metadata.assertions
    path = _primary_path(case_dir, metadata)

    with rasterio.open(path) as src:
        # --- 1.2.3 typed expectations, delegated as-is
        if hints.expect_crs is True:
            _collect(errors, metadata, "expect_crs", lambda: assert_has_crs(src))
        if hints.expected_epsg is not None:
            _collect(
                errors,
                metadata,
                "expected_epsg",
                lambda: assert_epsg(src, hints.expected_epsg),
            )
        if hints.expected_band_count is not None:
            _collect(
                errors,
                metadata,
                "expected_band_count",
                lambda: assert_band_count(src, hints.expected_band_count),
            )
        if hints.expected_dtype is not None:
            _collect(
                errors,
                metadata,
                "expected_dtype",
                lambda: assert_dtype(src, hints.expected_dtype),
            )
        if hints.expected_shape is not None:
            height, width = hints.expected_shape
            _collect(
                errors,
                metadata,
                "expected_shape",
                lambda: assert_shape(src, height, width),
            )
        if hints.expected_compression is not None:
            _collect(
                errors,
                metadata,
                "expected_compression",
                lambda: assert_compression(src, hints.expected_compression),
            )
        if hints.expected_overviews is True:
            _collect(
                errors,
                metadata,
                "expected_overviews",
                lambda: assert_has_overviews(src),
            )
        if hints.expected_band_names:
            _collect(
                errors,
                metadata,
                "expected_band_names",
                lambda: assert_band_names(src, hints.expected_band_names),
            )
        if hints.expected_colormap_present is True:
            _collect(
                errors,
                metadata,
                "expected_colormap_present",
                lambda: assert_colormap_present(src),
            )
        if hints.is_cog is True:
            _collect(errors, metadata, "is_cog", lambda: assert_is_cog(src))
        if hints.expected_scale_factor is not None:
            # Declared by three cases since the raster action plan and read by
            # nothing until plan 34 -- a declared-but-ungated hint of exactly
            # the class plan 27 section 1.2 forbids.
            _collect(
                errors,
                metadata,
                "expected_scale_factor",
                lambda: assert_scale_factor(src, hints.expected_scale_factor),
            )
        if hints.expected_transform_signs is not None:
            _collect(
                errors,
                metadata,
                "expected_transform_signs",
                lambda: assert_transform_signs(src, hints.expected_transform_signs),
            )
        if hints.expected_pixel_anchor is not None:
            _collect(
                errors,
                metadata,
                "expected_pixel_anchor",
                lambda: assert_pixel_anchor(src, hints.expected_pixel_anchor),
            )
        if hints.nodata_convention == "nan":
            _collect(
                errors, metadata, "nodata_convention", lambda: assert_nan_nodata(src)
            )

        # --- 1.2.1 / 1.2.2: the tag AND at least one matching pixel.
        # assert_nodata_value only proves the tag is set; the phantom-nodata
        # cases all passed that and still contained no nodata whatsoever.
        if hints.expect_nodata is True:
            _collect(
                errors, metadata, "expect_nodata", lambda: assert_nodata_value(src)
            )
            if src.nodata is not None and _total_nodata_pixels(src, src.nodata) == 0:
                errors.append(
                    _err(
                        metadata,
                        "expect_nodata",
                        f"declares nodata={src.nodata} but no pixel in any of "
                        f"{src.count} band(s) takes that value",
                    )
                )

        if hints.expected_nodata_value is not None:
            expected = hints.expected_nodata_value
            _collect(
                errors,
                metadata,
                "expected_nodata_value",
                lambda: assert_nodata_value(src, expected),
            )
            if src.nodata == expected and _total_nodata_pixels(src, expected) == 0:
                errors.append(
                    _err(
                        metadata,
                        "expected_nodata_value",
                        f"declares nodata={expected} but no pixel takes that value",
                    )
                )

        # --- 1.3: risk_types as contract, keyed on the vocabulary not on prose
        if "nodata_ignored" in metadata.risk_types:
            if src.nodata is None:
                errors.append(
                    _err(
                        metadata,
                        "nodata_ignored",
                        "risk type declared but the raster has no nodata value set",
                    )
                )
            elif _total_nodata_pixels(src, src.nodata) == 0:
                errors.append(
                    _err(
                        metadata,
                        "nodata_ignored",
                        "risk type declared but the raster contains no nodata pixels, "
                        "so it cannot exercise nodata-ignoring code",
                    )
                )

        errors.extend(_check_footprint(case_dir, metadata, src))

    return errors


def _mask_geometry(src: Any) -> Any:
    """The mask-exact footprint of an open raster, or ``None`` if fully invalid.

    Derived from the actual valid-data mask rather than from the declared
    GeoJSON — the point of the check is that the two can disagree. This is the
    ground truth every footprint declaration is measured against.
    """
    import rasterio.features
    from shapely.geometry import shape
    from shapely.ops import unary_union

    mask = src.dataset_mask()
    parts = [
        shape(geom)
        for geom, value in rasterio.features.shapes(
            mask, mask=mask.astype(bool), transform=src.transform
        )
        if value != 0
    ]
    if not parts:
        return None
    return unary_union(parts)


def _part_count(geom: Any) -> int:
    """Number of disjoint polygons in *geom*."""
    if geom is None:
        return 0
    return len(geom.geoms) if geom.geom_type.startswith("Multi") else 1


def _mask_hole_count(src: Any) -> int:
    """Count interior voids in the valid-data mask of an open raster."""
    from geocase.assertions.footprint import _hole_count

    merged = _mask_geometry(src)
    if merged is None:
        return 0
    return _hole_count(merged)


#: Symmetric-difference-over-truth-area tolerance for a declared footprint.
#: Ground truth is emitted from the same mask the gate re-derives, so the only
#: legitimate divergence is float round-tripping through GeoJSON.
_FOOTPRINT_AREA_TOLERANCE = 1e-6


def _check_footprint(case_dir: Path, metadata: CaseMetadata, src: Any) -> list[str]:
    """1.2.6 — the declared footprint must agree with the real mask.

    This is the check that catches ``hole_center_nodata``: a footprint claiming
    an interior void over a raster whose nodata sits on the outer border.
    """
    declared_name = metadata.params.get("expected_footprint")
    if not declared_name:
        return []

    declared_path = Path(case_dir) / str(declared_name)
    if not declared_path.exists():
        return [
            _err(
                metadata,
                "expected_footprint",
                f"declared footprint file not found: {declared_name}",
            )
        ]

    import geopandas as gpd

    from geocase.assertions.footprint import (
        _hole_count,
        _merged_geometry,
        assert_footprint_similar_to_expected,
    )

    declared = gpd.read_file(declared_path)
    declared_holes = sum(_hole_count(geom) for geom in declared.geometry)
    truth = _mask_geometry(src)
    actual_holes = 0 if truth is None else _hole_count(truth)

    errors: list[str] = []
    if declared_holes != actual_holes:
        errors.append(
            _err(
                metadata,
                "expected_footprint",
                f"declared footprint has {declared_holes} hole(s) but the "
                f"actual nodata mask yields {actual_holes}",
            )
        )

    # Plan 32 1.1 — hole count alone was the right check for
    # ``hole_center_nodata`` and is not sufficient in general: a convex hull
    # over two disjoint islands has zero holes, exactly like the truth, while
    # merging the islands and nearly doubling the area. Part count and area
    # are what separate ground truth from a recorded consumer's answer.
    if truth is not None:
        declared_geom = _merged_geometry(declared)
        declared_parts = _part_count(declared_geom)
        truth_parts = _part_count(truth)
        if declared_parts != truth_parts:
            errors.append(
                _err(
                    metadata,
                    "expected_footprint",
                    f"declared footprint has {declared_parts} part(s) "
                    f"({declared_geom.geom_type}) but the actual nodata mask "
                    f"yields {truth_parts} ({truth.geom_type})",
                )
            )
        _collect(
            errors,
            metadata,
            "expected_footprint",
            lambda: assert_footprint_similar_to_expected(
                declared,
                gpd.GeoDataFrame(geometry=[truth], crs=declared.crs),
                max_diff_ratio=_FOOTPRINT_AREA_TOLERANCE,
                msg=(
                    f"declared footprint area {declared_geom.area:.4f} diverges "
                    f"from the mask-exact area {truth.area:.4f} by more than "
                    f"{_FOOTPRINT_AREA_TOLERANCE:.0e}"
                ),
            ),
        )

    # 1.3 — ``footprint_generation_error`` is the vocabulary entry for "a
    # footprint generator that ignores nodata gets this wrong". A raster whose
    # nodata sits only on the outer border cannot demonstrate that: cropping to
    # the valid extent yields the same polygon either way. Agreement between a
    # footprint and a mask that are *both* hole-free is not evidence the case
    # works -- it is how ``hole_center_nodata`` drifted into claiming an
    # interior void it does not have, and the check that only compares the two
    # declarations to each other cannot see it.
    if "footprint_generation_error" in metadata.risk_types and actual_holes == 0:
        if _nodata_is_border_only(src):
            errors.append(
                _err(
                    metadata,
                    "footprint_generation_error",
                    "risk type declared, but nodata occupies only the outer "
                    "border and the mask has no interior void, so footprint "
                    "extraction that ignores nodata cannot diverge here",
                )
            )
    return errors


def _nodata_is_border_only(src: Any) -> bool:
    """True if every invalid pixel lies on the outer frame of the raster.

    Distinguishes a genuine interior void from a nodata *collar*, which no
    footprint generator gets wrong.
    """

    mask = src.dataset_mask()
    invalid = mask == 0
    if not invalid.any():
        return False
    interior = invalid[1:-1, 1:-1]
    return not bool(interior.any())


# --- vector ---------------------------------------------------------------


def check_vector_content(case_dir: Path, metadata: CaseMetadata) -> list[str]:
    """Check a vector case's declared assertions against its features."""
    from geocase.assertions.crs import assert_epsg, assert_has_crs
    from geocase.assertions.geometry import (
        assert_feature_count,
        assert_geometry_type,
        assert_valid_geometry,
    )

    errors: list[str] = []
    hints = metadata.assertions

    gdf = _load_for_category(case_dir, metadata)

    if hints.expect_valid_geometry is True:
        _collect(
            errors,
            metadata,
            "expect_valid_geometry",
            lambda: assert_valid_geometry(gdf),
        )
    elif hints.expect_valid_geometry is False:
        # Only the positive direction is enforceable today. ``False`` carries two
        # distinct meanings in the shipped corpus -- "OGC-invalid" (a bowtie) and
        # "OGC-valid but semantically suspect" (null island, a lat/lon swap, an
        # engine-dependent touching ring, EMPTY-vs-NULL) -- and four cases mean
        # the second. Asserting invalidity here would fail them for a schema
        # limitation, not a data defect. Phase 1 deliberately cut the tri-state
        # field (a v1.0 break); Phase 2.4 ships the documented matrix instead.
        pass

    if hints.expect_crs is True:
        _collect(errors, metadata, "expect_crs", lambda: assert_has_crs(gdf))

    if hints.expected_epsg is not None:
        _collect(
            errors,
            metadata,
            "expected_epsg",
            lambda: assert_epsg(gdf, hints.expected_epsg),
        )

    if hints.expected_geometry_types:
        # NULL geometries report a ``geom_type`` of NaN, which is not a type
        # claim the metadata could ever satisfy. ``empty_geometry_gpkg`` exists
        # precisely to carry a NULL row alongside an EMPTY one, so the gate
        # checks the types of the geometries that *have* one.
        present = gdf[~gdf.geometry.isna()]
        _collect(
            errors,
            metadata,
            "expected_geometry_types",
            lambda: assert_geometry_type(present, hints.expected_geometry_types),
        )

    expected_count = metadata.params.get("expected_feature_count")
    if expected_count is not None:
        _collect(
            errors,
            metadata,
            "expected_feature_count",
            lambda: assert_feature_count(gdf, int(expected_count)),
        )

    if metadata.params.get("expect_z") is True:
        _collect(errors, metadata, "expect_z", lambda: _assert_has_z(gdf))

    expected_id = metadata.params.get("expected_id_value")
    if expected_id is not None:
        _collect(
            errors,
            metadata,
            "expected_id_value",
            lambda: _assert_id_value(gdf, int(expected_id)),
        )

    # risk_types as contract. A vocabulary entry nothing gates is
    # indistinguishable from a typo (plan 27 section 1.2), so the term has to
    # be backed by the bytes that justify it.
    if "axis_order" in metadata.risk_types:
        errors.extend(_check_authority_axis_order(case_dir, metadata))

    return errors


def _assert_has_z(gdf: Any) -> None:
    """Every geometry carries a third ordinate."""
    flat = [
        i for i, geom in enumerate(gdf.geometry) if geom is not None and not geom.has_z
    ]
    if flat:
        raise AssertionError(
            f"expect_z is true, but {len(flat)} geometry/geometries are 2D "
            f"(rows {flat[:5]})"
        )


def _assert_id_value(gdf: Any, expected: int) -> None:
    """Exact read-back of an id, for values a float64 cannot hold.

    9007199254740993 is 2^53 + 1. A reader that routes integers through a
    double returns ...992, so approximate comparison would pass the bug.
    """
    if "id" not in gdf.columns:
        raise AssertionError("expected_id_value declared, but there is no 'id' column")
    actual = int(gdf["id"].iloc[0])
    if actual != expected:
        raise AssertionError(f"expected id {expected}, read back {actual}")


def _check_authority_axis_order(case_dir: Path, metadata: CaseMetadata) -> list[str]:
    """Back the ``axis_order`` risk type with the file's actual bytes.

    Only GML is checked: it is the format in this catalog that genuinely
    serialises in authority order, via the ``urn:ogc:def:crs`` form. For any
    other format the term would need its own justification, so silence here is
    deliberate rather than an omission.
    """
    if metadata.format != "GML":
        return []

    import re as _re

    errors: list[str] = []
    path = _primary_path(case_dir, metadata)
    text = path.read_text(encoding="utf-8")

    if "urn:ogc:def:crs:EPSG::4326" not in text:
        errors.append(
            _err(
                metadata,
                "axis_order",
                "declares axis_order, but the file does not use the "
                "urn:ogc:def:crs form that forces authority ordering",
            )
        )
        return errors

    match = _re.search(r"<gml:(?:pos|posList)>([^<]+)</gml:", text)
    if match is None:
        errors.append(
            _err(metadata, "axis_order", "no gml:pos or gml:posList to inspect")
        )
        return errors

    first = float(match.group(1).split()[0])
    extent = metadata.extent
    if extent is not None and not (extent.south - 1.0 <= first <= extent.north + 1.0):
        errors.append(
            _err(
                metadata,
                "axis_order",
                f"declares axis_order, but the first ordinate {first} is not a "
                f"latitude in [{extent.south}, {extent.north}]",
            )
        )
    return errors


# --- netcdf ---------------------------------------------------------------


def check_netcdf_content(case_dir: Path, metadata: CaseMetadata) -> list[str]:
    """Check a NetCDF case's declared assertions against its variables.

    Until Plan 34 this category was not content-checked at all: xarray was not
    in the catalog job's install set, so the dispatcher returned ``[]`` for
    every netcdf case. That made ``latlon_small`` a case returning green for
    ``expect_nodata`` and three risk types without any of them being examined.

    Returns ``[]`` when xarray is absent. A missing optional reader is not a
    finding -- this function is public, and users run it on machines that never
    installed the extra.
    """
    try:
        import xarray as xr
    except ImportError:
        return []

    errors: list[str] = []
    hints = metadata.assertions
    path = _primary_path(case_dir, metadata)

    # decode_cf=False keeps packing attributes observable as attributes. With
    # decoding on, a drifted scale_factor is silently applied and the check
    # compares already-corrected values against themselves.
    with xr.open_dataset(path, decode_cf=False) as ds:
        dims = [str(name) for name in ds.sizes]
        variables = [str(name) for name in ds.data_vars]

        # Order matters, and is the point: an ordering claim is only checkable
        # if the declared order is compared as a sequence, not as a set.
        expected_dims = metadata.params.get("expected_dimensions")
        if expected_dims is not None:
            declared = [str(name) for name in expected_dims]
            _collect(
                errors,
                metadata,
                "expected_dimensions",
                lambda: _assert_sequence(declared, dims, "dimensions"),
            )

        expected_vars = metadata.params.get("expected_variables")
        if expected_vars is not None:
            missing = [str(n) for n in expected_vars if str(n) not in variables]
            _collect(
                errors,
                metadata,
                "expected_variables",
                lambda: _assert_empty(
                    missing,
                    f"declared variables not in the file: {missing}; "
                    f"file has {variables}",
                ),
            )

        if hints.expect_nodata is True:
            _collect(
                errors,
                metadata,
                "expect_nodata",
                lambda: _assert_any_fill_value(ds, variables),
            )

        if hints.expect_crs is True:
            # Strict, deliberately. The lenient reading -- treat an absent CRS
            # variable as not-a-finding -- would ship a check that cannot fail
            # on the only case it runs against, which is the defect this module
            # exists to close. latlon_small's undemonstrable declaration was
            # removed rather than accommodated. See Plan 34 section 1.3.
            _collect(
                errors,
                metadata,
                "expect_crs",
                lambda: _assert_has_grid_mapping(ds),
            )

        if hints.expected_scale_factor is not None:
            _collect(
                errors,
                metadata,
                "expected_scale_factor",
                lambda: _assert_scale_factor(ds, hints.expected_scale_factor),
            )

        expected_units = metadata.params.get("expected_time_units")
        if expected_units is not None:
            _collect(
                errors,
                metadata,
                "expected_time_units",
                lambda: _assert_time_units(ds, str(expected_units)),
            )

    return errors


def _assert_sequence(declared: list[str], actual: list[str], label: str) -> None:
    if declared != actual:
        raise AssertionError(f"declared {label} {declared}, file has {actual}")


def _assert_empty(missing: list[str], detail: str) -> None:
    if missing:
        raise AssertionError(detail)


def _assert_any_fill_value(ds: Any, variables: list[str]) -> None:
    """At least one data variable must declare a _FillValue."""
    for name in variables:
        if "_FillValue" in ds[name].attrs or "missing_value" in ds[name].attrs:
            return
    raise AssertionError(
        f"expect_nodata is true, but no data variable declares a _FillValue "
        f"(checked {variables})"
    )


def _assert_has_grid_mapping(ds: Any) -> None:
    """A CRS claim needs a grid_mapping or a CF crs variable to back it."""
    names = {str(name) for name in ds.variables}
    if names & {"crs", "spatial_ref", "grid_mapping"}:
        return
    for name in ds.data_vars:
        if "grid_mapping" in ds[name].attrs:
            return
    raise AssertionError(
        "expect_crs is true, but the file declares no grid_mapping attribute "
        "and carries no crs/spatial_ref variable"
    )


def _assert_scale_factor(ds: Any, expected: float) -> None:
    for name in ds.data_vars:
        actual = ds[name].attrs.get("scale_factor")
        if actual is not None and float(actual) == float(expected):
            return
    observed = {str(name): ds[name].attrs.get("scale_factor") for name in ds.data_vars}
    raise AssertionError(
        f"no variable declares scale_factor {expected}; observed {observed}"
    )


def _assert_time_units(ds: Any, expected: str) -> None:
    actual = ds["time"].attrs.get("units") if "time" in ds.variables else None
    if actual != expected:
        raise AssertionError(f"declared time units {expected!r}, file has {actual!r}")


# --- extent ---------------------------------------------------------------


def _observed_bounds(
    case_dir: Path, metadata: CaseMetadata
) -> tuple[float, ...] | None:
    """Read the case's real WGS84 envelope, or ``None`` if it has none.

    Reprojection is not optional: 23 bundled rasters are EPSG:32633, whose
    bounds are metres. Comparing those against a degree extent would fail every
    one of them for a defect in the gate.
    """
    if metadata.category == "raster":
        import rasterio
        from rasterio.warp import transform_bounds

        with rasterio.open(_primary_path(case_dir, metadata)) as src:
            if src.crs is None:
                return None
            if src.crs.to_epsg() == 4326:
                return tuple(float(value) for value in src.bounds)
            return tuple(transform_bounds(src.crs, "EPSG:4326", *src.bounds))

    gdf = _load_for_category(case_dir, metadata)
    if gdf is None or len(gdf) == 0:
        return None
    crs = getattr(gdf, "crs", None)
    if crs is not None and crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
    return tuple(float(value) for value in gdf.geometry.total_bounds)


def check_extent(case_dir: Path, metadata: CaseMetadata) -> list[str]:
    """Check a declared ``extent`` against where the data actually is.

    ``extent`` is generated by ``scripts/catalog_extent.py``, so a mismatch
    means a fixture moved without a regeneration -- and every page and world
    map built from that extent is now pointing at the wrong place.

    No declared extent is not a finding: the field is optional, and netcdf and
    the deliberately-unloadable cases legitimately carry none.
    """
    if metadata.extent is None:
        return []

    from geocase.assertions.extent import assert_bounds

    try:
        observed = _observed_bounds(case_dir, metadata)
    except Exception as exc:
        return [_err(metadata, "extent", f"could not read bounds: {exc}")]
    if observed is None:
        return []

    errors: list[str] = []
    _collect(
        errors,
        metadata,
        "extent",
        lambda: assert_bounds(observed, metadata.extent),  # type: ignore[arg-type]
    )
    return errors


# --- 2.4: expected-error taxonomy -----------------------------------------


#: Exception *type* names that identify a failure mode on their own.
#:
#: Matched on the unqualified class name and on the names of its bases, so a
#: consumer's subclass (``pyogrio.errors.DataSourceError`` derives from
#: ``DataLayerError``) resolves the same way as the base it derives from.
_ERROR_KIND_BY_TYPE: dict[str, ExpectedErrorKind] = {
    # shapely: raised while *constructing* a geometry, so nothing exists to
    # ask a validity question about.
    "GEOSException": "unparseable_geometry",
    "ShapelyError": "unparseable_geometry",
    "WKBReadingError": "unparseable_geometry",
    "WKTReadingError": "unparseable_geometry",
    # json / pandas: the payload is not even parseable text.
    "JSONDecodeError": "unparseable_geometry",
    "ParserError": "unparseable_geometry",
    # pyproj / rasterio: the CRS definition itself will not construct.
    "CRSError": "invalid_crs",
    "ProjError": "invalid_crs",
    "TopologicalError": "invalid_topology",
}

#: Substrings of an exception *message* that identify a failure mode.
#:
#: Needed because the informative exceptions in this space are frequently a
#: bare ``RuntimeError`` or ``DataSourceError`` carrying GDAL's own wording —
#: the type says nothing and only the message discriminates. Checked in order,
#: lowercased, and only after the type table misses.
_ERROR_KIND_BY_MESSAGE: tuple[tuple[str, ExpectedErrorKind], ...] = (
    ("not recognized as a supported file format", "missing_driver"),
    ("unable to find driver", "missing_driver"),
    ("driver is not available", "missing_driver"),
    ("no such file or directory", "missing_driver"),
    ("unsupported", "unsupported_format"),
    ("unrecognized", "unsupported_format"),
    ("not supported", "unsupported_format"),
    ("linearring", "unparseable_geometry"),
    ("closed linestring", "unparseable_geometry"),
    ("parse", "unparseable_geometry"),
    ("expecting value", "unparseable_geometry"),
    ("crs", "invalid_crs"),
    ("self-intersection", "invalid_topology"),
    ("topolog", "invalid_topology"),
)


def classify_error(exc: BaseException) -> ExpectedErrorKind | None:
    """Map a consumer's exception onto the :data:`ExpectedErrorKind` vocabulary.

    Returns ``None`` for anything the vocabulary does not cover. That is
    deliberate: forcing an unrecognised failure into the nearest term would
    make the gate green for a case failing in a way nobody has looked at, which
    is the exact defect this module exists to close. An unmapped exception on a
    case that declares a kind is therefore reported, not excused.

    Type is consulted before message, because a type is a much stronger signal
    than a substring — but most of GDAL's failures arrive as a bare
    ``RuntimeError``, so the message table carries the real weight.
    """
    for klass in type(exc).__mro__:
        kind = _ERROR_KIND_BY_TYPE.get(klass.__name__)
        if kind is not None:
            return kind

    message = str(exc).lower()
    for needle, kind in _ERROR_KIND_BY_MESSAGE:
        if needle in message:
            return kind
    return None


def _check_expected_error_kind(metadata: CaseMetadata, exc: BaseException) -> list[str]:
    """Check the exception a curated-failure case raised against its declaration."""
    declared = metadata.assertions.expected_error_kind
    if declared is None:
        return []

    observed = classify_error(exc)
    if observed == declared:
        return []

    detail = (
        f"observed {observed!r}" if observed else "the failure matched no known kind"
    )
    return [
        _err(
            metadata,
            "expected_error_kind",
            f"declared {declared!r}, but {detail}: {type(exc).__name__}: {exc}",
        )
    ]


# --- dispatch -------------------------------------------------------------


def check_case_content(case_dir: Path, metadata: CaseMetadata) -> list[str]:
    """Check one case's declared assertions against its actual data.

    Returns a list of human-readable error strings — empty means the case's
    declarations are backed by real bytes. Never raises for a data problem:
    a case that fails to open is itself a finding.
    """
    case_dir = Path(case_dir)
    path = _primary_path(case_dir, metadata)

    if not path.exists():
        return [_err(metadata, "files.primary", f"primary file not found: {path.name}")]

    # 1.2.5 — an expected-failure that silently stopped failing is a corpus
    # defect too, so the negative case is checked before the positive ones.
    if metadata.assertions.expect_loadable is False:
        try:
            _load_for_category(case_dir, metadata)
        except Exception as exc:
            # 2.4 — it failed, which 1.2.5 already required. Now check that it
            # failed the way the case says it does: "failed for the curated
            # reason" and "failed because the reader changed underneath us"
            # were previously indistinguishable, and only the first is green.
            return _check_expected_error_kind(metadata, exc)
        return [
            _err(
                metadata,
                "expect_loadable",
                "declared unloadable, but the primary file opened successfully",
            )
        ]

    try:
        if metadata.category == "raster":
            errors = check_raster_content(case_dir, metadata)
        elif metadata.category == "netcdf":
            errors = check_netcdf_content(case_dir, metadata)
        else:
            errors = check_vector_content(case_dir, metadata)
        return errors + check_extent(case_dir, metadata)
    except Exception as exc:  # a case that cannot be opened is a finding
        return [
            _err(
                metadata,
                "expect_loadable",
                f"declared loadable, but reading it raised {type(exc).__name__}: {exc}",
            )
        ]


def _load_for_category(case_dir: Path, metadata: CaseMetadata) -> Any:
    """Load a case the same way a *user* would, via the case object.

    Deliberately not ``geopandas.read_file``: the WKB/WKT/CSV_WKT/Parquet cases
    are bare blobs or Arrow files that OGR either cannot open at all or needs
    ``libgdal-arrow-parquet`` for, while :meth:`VectorCase.load` reads them
    through shapely and ``read_parquet``. Using the raw reader here would make
    the gate fail 19 perfectly good cases for a defect in the gate.
    """
    from geocase.cases.factory import create_case
    from geocase.cases.netcdf import NetCDFCase
    from geocase.cases.raster import RasterCase
    from geocase.cases.vector import VectorCase

    case = create_case(metadata, Path(case_dir))
    if isinstance(case, RasterCase):
        with case.open() as src:
            return src.read(1)
    if isinstance(case, VectorCase):
        return case.load()
    if isinstance(case, NetCDFCase):
        # Needed by the expect_loadable branches, not only by the netcdf
        # content check. Without it a netcdf case declared unloadable would
        # "pass" on the TypeError this used to raise -- green for the wrong
        # reason, which is the failure mode this module exists to catch.
        return case.load()
    raise TypeError(f"No content reader for case category '{metadata.category}'")
