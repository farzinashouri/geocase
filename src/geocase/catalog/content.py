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

See docs/plans/28-validate-geocase.md, Phase 1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from geocase.catalog.models import CaseMetadata

__all__ = [
    "check_case_content",
    "check_extent",
    "check_raster_content",
    "check_vector_content",
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
        assert_shape,
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


def _mask_hole_count(src: Any) -> int:
    """Count interior voids in the valid-data mask of an open raster.

    Derived from the actual mask rather than from the declared GeoJSON — the
    point of the check is that the two can disagree.
    """
    import numpy as np
    import rasterio.features
    from shapely.geometry import shape
    from shapely.ops import unary_union

    from geocase.assertions.footprint import _hole_count

    mask = src.dataset_mask()
    shapes = [
        shape(geom)
        for geom, value in rasterio.features.shapes(
            mask, mask=mask.astype(bool), transform=src.transform
        )
        if value != 0
    ]
    if not shapes:
        return 0
    merged = unary_union(shapes)
    assert np is not None
    return _hole_count(merged)


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

    from geocase.assertions.footprint import _hole_count

    declared = gpd.read_file(declared_path)
    declared_holes = sum(_hole_count(geom) for geom in declared.geometry)
    actual_holes = _mask_hole_count(src)

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

    return errors


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


# --- dispatch -------------------------------------------------------------


def check_case_content(case_dir: Path, metadata: CaseMetadata) -> list[str]:
    """Check one case's declared assertions against its actual data.

    Returns a list of human-readable error strings — empty means the case's
    declarations are backed by real bytes. Never raises for a data problem:
    a case that fails to open is itself a finding.

    NetCDF cases are not content-checked beyond what the schema gate already
    does; xarray is not in the catalog CI job's install set (Phase 1 cut).
    """
    case_dir = Path(case_dir)
    path = _primary_path(case_dir, metadata)

    if not path.exists():
        return [_err(metadata, "files.primary", f"primary file not found: {path.name}")]

    if metadata.category == "netcdf":
        return []

    # 1.2.5 — an expected-failure that silently stopped failing is a corpus
    # defect too, so the negative case is checked before the positive ones.
    if metadata.assertions.expect_loadable is False:
        try:
            _load_for_category(case_dir, metadata)
        except Exception:
            return []
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
    from geocase.cases.raster import RasterCase
    from geocase.cases.vector import VectorCase

    case = create_case(metadata, Path(case_dir))
    if isinstance(case, RasterCase):
        with case.open() as src:
            return src.read(1)
    if isinstance(case, VectorCase):
        return case.load()
    raise TypeError(f"No content reader for case category '{metadata.category}'")
