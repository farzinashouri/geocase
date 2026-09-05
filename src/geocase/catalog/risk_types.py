"""The canonical risk-type vocabulary -- plan 40 phase 3.

``risk_types`` is the part of the package external reporters name as the most
useful: it is a search index over *failure modes*, and it takes a consumer from
"what could go wrong with georeferencing" to ``rotated_two_islands`` by name, in
seconds. Round 3 measured the cost of leaving it ungoverned:

* **124 distinct terms over 163 cases, 78 of them singletons** (63%);
* the literal string ``"none"`` used 9 times, which is the absence of a risk
  type spelled wrong;
* ``format_comparison`` on 60 cases (37% of the corpus) -- a
  corpus-construction label, not a failure mode;
* only **four** terms checked against real bytes anywhere in
  :mod:`geocase.catalog.content`, so every other term was indistinguishable
  from a typo. That is the rule plan 27 §1.2 wrote down and never enforced;
* ``docs/adding-a-case.md``'s own worked examples (``topology_breakage``,
  ``attribute_encoding``) existed nowhere in the corpus, so the authoring doc
  actively taught vocabulary drift.

Two levels, ``family/specific``, and a family only exists where it has more
than one member -- otherwise the prefix is decoration. Selection matches the
full term **or** the family prefix (see
:func:`geocase.catalog.selectors.matches_selection`), so
``risk_types_any=["crs"]`` selects the whole CRS family. That is what makes a
large vocabulary browsable without deleting information: the singletons stay,
and they become reachable through their family rather than only by exact
spelling.

Every merged spelling is recorded in :data:`RISK_TYPE_ALIASES` and resolved in
**both** directions -- at load time in :mod:`geocase.catalog.loader`, so the
registry and every generated artifact see canonical terms only, and at
selection time in :mod:`geocase.catalog.selectors`, so a user's existing
``risk_types_any=["coordinate_order"]`` keeps working. ``risk_types`` is a
pinned v1.0 selector surface; renaming a term without the alias layer would be
a silent breaking change of exactly the kind plan 40 §5 exists to prevent.
"""

from __future__ import annotations

from collections.abc import Mapping

#: Canonical term -> one-line description.
#:
#: The descriptions live here rather than in markdown because they feed the
#: generated vocabulary index in ``scripts/generate_catalog_pages.py``: a term
#: and its meaning drifting apart is the same failure as a case and its
#: metadata drifting apart.
RISK_TYPE_DESCRIPTIONS: dict[str, str] = {
    # -- crs ---------------------------------------------------------------
    "crs/axis_order": (
        "An authority's declared axis order is ignored -- the bytes really are "
        "latitude-first, and a reader assuming lon-first swaps them."
    ),
    "crs/lat_lon_swap": (
        "Coordinates are swapped, detectable because the values fall outside "
        "the valid range rather than because any CRS declares an axis order."
    ),
    "crs/mismatch": (
        "Two inputs disagree about CRS -- a relationship between a pair, which "
        "no single file can express."
    ),
    "crs/mishandled": (
        "A single input's CRS is assumed, dropped or misapplied on its own."
    ),
    "crs/units": (
        "A length is carried across CRSs without unit conversion -- metres used "
        "as degrees, or the reverse."
    ),
    "crs/zone_selection": (
        "The wrong UTM zone is chosen, or data straddling a zone boundary is "
        "forced into one zone."
    ),
    "crs/reprojection_error": (
        "Reprojection loses, distorts or fails outright on the coordinates it is given."
    ),
    "crs/projection_failure": (
        "The projection cannot be constructed or applied at all for this input."
    ),
    "crs/local_distortion": (
        "A projection valid globally distorts unacceptably over the local "
        "extent it is applied to."
    ),
    "crs/projected_coordinate_assumption": (
        "Code assumes projected (metre) coordinates and silently misbehaves on "
        "geographic ones."
    ),
    # -- extent ------------------------------------------------------------
    "extent/antimeridian": (
        "Geometry crossing 180 degrees is split, wrapped, or spans the globe "
        "as a naive envelope."
    ),
    "extent/polar": (
        "Behaviour at or near a pole, where longitude is undefined and "
        "projections become singular."
    ),
    "extent/equatorial": (
        "Behaviour at the equator or a hemisphere boundary, where a sign or a "
        "zone letter flips."
    ),
    "extent/bounds_normalization": (
        "A bounding box is normalised, or left unnormalised, when the opposite "
        "was required."
    ),
    "extent/bbox_misinterpretation": (
        "A bounding box's axis order, CRS or corner convention is read wrongly."
    ),
    "extent/coordinate_wrapping": (
        "Longitudes are wrapped into or out of [-180, 180] when they should "
        "not have been."
    ),
    "extent/coordinate_range_error": (
        "Coordinates fall outside the valid range for their CRS."
    ),
    "extent/coordinate_sign_assumption": (
        "A hemisphere is inferred from a coordinate sign that does not carry it."
    ),
    # -- transform ---------------------------------------------------------
    "transform/rotated": (
        "The geotransform carries rotation or shear terms, which a north-up "
        "assumption silently discards."
    ),
    "transform/bottom_up": (
        "The geotransform has a positive y-step, so rows run south to north "
        "and naive bounds come out inverted."
    ),
    "transform/pixel_anchor": (
        "Transform coordinates name pixel corners or pixel centres, and the "
        "reader assumes the other."
    ),
    "transform/shifted_origin": (
        "The origin is offset from a round number, so an assumed alignment is "
        "half a pixel out."
    ),
    "transform/nonsquare_pixels": (
        "Pixel width and height differ, which a single scalar resolution "
        "cannot express."
    ),
    "transform/pixel_shift": (
        "Pixels land one cell away from where the georeferencing says they should."
    ),
    "transform/rasterization_alignment": (
        "Rasterizing vector input lands on a different lattice than the reference grid."
    ),
    "transform/resampling_assumptions": (
        "A resampling method is assumed, and the wrong one silently changes values."
    ),
    "transform/resolution_mismatch": (
        "Inputs at different resolutions are combined without an explicit target grid."
    ),
    "transform/alignment_too_strict": (
        "An exact-alignment check rejects grids that are equivalent within "
        "floating-point tolerance."
    ),
    # -- nodata ------------------------------------------------------------
    "nodata/ignored": (
        "The nodata value is not masked, so sentinels are treated as real "
        "measurements -- the statistic is wrong and nothing errors."
    ),
    "nodata/ambiguous_zero": (
        "The nodata value is also a legitimate data value, so masking it "
        "destroys real observations."
    ),
    "nodata/nan_mishandled": (
        "NaN as a nodata convention is compared, propagated or filled wrongly."
    ),
    "nodata/mask_misread": (
        "The mask band or alpha channel is read with the wrong polarity or "
        "dtype contract."
    ),
    "nodata/default_value_sink": (
        "A missing value is silently replaced by a type default rather than "
        "preserved as missing."
    ),
    # -- dtype -------------------------------------------------------------
    "dtype/drift": ("The declared dtype and the dtype a reader returns disagree."),
    "dtype/coercion": (
        "Values are silently cast to another dtype, losing range or precision."
    ),
    "dtype/nullable_coercion": (
        "A nullable extension dtype collapses to a non-nullable one, turning "
        "NULL into a sentinel."
    ),
    "dtype/overflow": ("A value exceeds the range its dtype can hold."),
    "dtype/range_truncation": (
        "Values outside the representable range are clipped rather than rejected."
    ),
    "dtype/range_assumption": ("Code assumes a value range the data does not honour."),
    "dtype/value_range_violation": (
        "Values fall outside the range the data's own metadata declares."
    ),
    # -- precision ---------------------------------------------------------
    "precision/loss": (
        "Coordinate or value precision is lost on write, round-trip or rounding."
    ),
    "precision/coordinate_drift": (
        "Coordinates move slightly under repeated transformation."
    ),
    "precision/roundtrip_degradation": (
        "A write-then-read cycle does not return the input unchanged."
    ),
    # -- geometry ----------------------------------------------------------
    "geometry/silent_invalid": (
        "An OGC-invalid or semantically wrong geometry loads without complaint."
    ),
    "geometry/empty": (
        "An empty geometry, which is distinct from a NULL one and from a missing row."
    ),
    "geometry/null_empty_conflation": (
        "NULL, EMPTY and NaN-coordinate geometries are treated as the same thing."
    ),
    "geometry/zero_length": (
        "A line or ring with no extent, which many predicates cannot answer for."
    ),
    "geometry/degenerate_but_parseable": (
        "The geometry parses but is degenerate -- zero area, repeated points, "
        "a collapsed ring."
    ),
    "geometry/ring_orientation": (
        "Ring winding order is reversed, or an exterior ring is read as a hole."
    ),
    "geometry/ring_closure": ("A ring's first and last vertex do not match."),
    "geometry/mixed_output": (
        "An operation returns a mix of geometry types where one was expected."
    ),
    "geometry/repair_variability": (
        "Two engines repair the same invalid geometry differently, or one "
        "returns a GeometryCollection."
    ),
    "geometry/simplification_loss": (
        "Simplification removes detail that the operation depended on."
    ),
    "geometry/overaggressive_dissolve": (
        "A dissolve merges features that should have stayed distinct."
    ),
    "geometry/false_positive_intersection": (
        "Two geometries are reported as intersecting when they do not."
    ),
    "geometry/topology_error": (
        "Self-intersections, overlaps or gaps that violate the layer's "
        "topological contract."
    ),
    "geometry/transitive_cluster_split": (
        "Chained proximity relationships are grouped differently depending on "
        "iteration order."
    ),
    "geometry/parse_exception": (
        "The geometry cannot be parsed at all and the reader raises."
    ),
    # -- measurement -------------------------------------------------------
    "measurement/incorrect_area": (
        "Area is computed in the wrong CRS or with the wrong formula."
    ),
    "measurement/area_distortion": (
        "Area is measured in a projection that does not preserve it."
    ),
    "measurement/distance_error": (
        "Distance is computed in degrees, in the wrong CRS, or against the "
        "wrong threshold."
    ),
    "measurement/incorrect_statistics": (
        "A summary statistic is computed over the wrong pixels -- typically "
        "unmasked ones."
    ),
    "measurement/invalid": ("The measurement is not meaningful for this input at all."),
    # -- format ------------------------------------------------------------
    "format/limitation": (
        "The container cannot represent something the data carries, and drops "
        "or mangles it."
    ),
    "format/driver_behavior": (
        "Behaviour specific to one OGR/GDAL driver rather than to the data."
    ),
    "format/xml_driver_behavior": (
        "GML/KML driver behaviour -- schema inference, namespaces, or "
        "attribute handling."
    ),
    "format/sqlite_driver_behavior": (
        "SQLite/GPKG driver behaviour, including its type affinity rules."
    ),
    "format/columnar_storage_behavior": (
        "Parquet/Feather/Arrow behaviour -- metadata conventions, chunking, "
        "extension types."
    ),
    "format/arrow_ipc_behavior": (
        "Arrow IPC framing, validity bitmaps, or extension-name round-tripping."
    ),
    "format/not_tiled": (
        "The raster is striped rather than tiled, so windowed reads are "
        "expensive or unsupported."
    ),
    "format/overviews_missing": (
        "Overviews are absent, external, or not the ones the reader assumed."
    ),
    "format/sidecar_dropped": (
        "A sidecar file carrying CRS, styling or index information is not read."
    ),
    "format/spec_nonconformance": (
        "The file departs from its own format specification."
    ),
    "format/partial_read_blind_spot": (
        "A windowed, filtered or lazy read returns a different answer than a full read."
    ),
    "format/spatial_index_failure": (
        "A spatial index is missing, stale, or disagrees with the geometry it indexes."
    ),
    "format/text_geometry_parsing": (
        "WKT/CSV text geometry parsing -- whitespace, precision, or dialect."
    ),
    "format/binary_geometry_parsing": (
        "WKB parsing -- endianness, SRID prefixes, or truncation."
    ),
    # -- attribute ---------------------------------------------------------
    "attribute/loss": ("Attribute columns or values are dropped on read or write."),
    "attribute/corruption": ("Attribute values survive but are altered."),
    "attribute/field_name_truncation": (
        "Field names are truncated to a format's length limit, colliding silently."
    ),
    "attribute/encoding_error": (
        "Text is decoded with the wrong codec, or the encoding is not declared."
    ),
    "attribute/mojibake": (
        "Non-ASCII text is double-encoded or replaced, visibly corrupting it."
    ),
    "attribute/schema_mismatch": (
        "The declared schema and the actual columns or types disagree."
    ),
    "attribute/type_coercion": ("An attribute's type changes on round-trip."),
    "attribute/timezone_normalization": (
        "Timestamps are shifted, or a naive timestamp is assumed to be UTC."
    ),
    # -- band --------------------------------------------------------------
    "band/loss": (
        "Bands are dropped, or only the first is read, from a multi-band raster."
    ),
    "band/incorrect_order": ("Bands are returned in a different order than declared."),
    "band/alias_ambiguity": (
        "Two assets or bands claim the same common name, and one is chosen silently."
    ),
    "band/dimension_mismatch": (
        "Band count, shape or dimension order does not match what the metadata "
        "declares."
    ),
    "band/stacking_order_ignored": (
        "Declared stacking or compositing order is not honoured across a group."
    ),
    # -- scaling -----------------------------------------------------------
    "scaling/ignored": (
        "A declared scale factor or offset is not applied, so raw digital "
        "numbers are returned as physical values."
    ),
    "scaling/colormap_dropped": (
        "A palette is applied as colour, or dropped, when the class codes were "
        "the data."
    ),
    "scaling/category_misread": (
        "Categorical codes are interpolated, averaged or rendered as continuous values."
    ),
    "scaling/pixel_lattice_misclassification": (
        "Class boundaries move because the raster was resampled with a "
        "continuous method."
    ),
    "scaling/incorrect_rendering": (
        "The rendered image misrepresents the underlying values."
    ),
    # -- footprint ---------------------------------------------------------
    "footprint/generation_error": (
        "The computed data footprint does not match the valid pixels -- holes "
        "filled, islands merged, or the envelope returned instead."
    ),
    "footprint/geocoding_failure": (
        "The footprint cannot be georeferenced back to ground coordinates."
    ),
    # -- data --------------------------------------------------------------
    "data/quality": ("The data itself is suspect, independent of how it is read."),
    "data/silent_bad_data": (
        "Bad values pass every check and reach the output unflagged."
    ),
    "data/nan_propagation": (
        "NaN spreads through an aggregation that should have excluded it."
    ),
    "data/ambiguous_engine_dependent": (
        "The correct answer depends on which engine is installed, and neither is wrong."
    ),
    "data/coordinate_edge_case": (
        "A coordinate sits exactly on a boundary where the tie-break is unspecified."
    ),
    "data/linear_artifacts_after_repair": (
        "Repair introduces slivers or collinear artifacts that were not in the input."
    ),
    "data/projection_assumptions": (
        "An analysis assumes a projection property the data does not have."
    ),
}

#: The canonical vocabulary. Everything a ``case.yaml`` may declare.
RISK_TYPES: frozenset[str] = frozenset(RISK_TYPE_DESCRIPTIONS)

#: Deprecated spelling -> canonical term.
#:
#: Every entry is a term that appeared in a shipped ``case.yaml`` before this
#: phase. ``risk_types`` is a pinned v1.0 selector surface, so these resolve at
#: selection time forever rather than being deleted: a user's existing
#: ``risk_types_any=["coordinate_order"]`` must keep selecting the same cases.
#:
#: Two terms are deliberately **absent** from this mapping, because they map to
#: nothing:
#:
#: * ``"none"`` (9 cases) -- the absence of a risk type, spelled wrong. Removed
#:   from those cases outright rather than aliased.
#: * ``"format_comparison"`` (60 cases) -- a corpus-construction label, not a
#:   failure mode, covering 37% of the corpus. Moved to ``tags``, where it
#:   remains selectable via ``tags_any=["format_comparison"]``.
RISK_TYPE_ALIASES: Mapping[str, str] = {
    # crs
    "coordinate_order": "crs/axis_order",
    # Deliberately *not* merged into crs/axis_order. The GML baselines declare
    # an authority axis order the bytes genuinely honour; this case is a swap
    # caught only because latitude 100 is out of range. That is a validity
    # signal, not an axis-order declaration, and
    # tests/unit/test_catalog_axis_order.py gates the distinction explicitly.
    "lat_lon_swap": "crs/lat_lon_swap",
    "axis_order": "crs/axis_order",
    # Also deliberately unmerged: crs_mismatch is a property of a *pair* --
    # "one file alone cannot express it", which is the whole reason
    # crs_mismatch_overlay_pair exists -- while crs_mishandled sits on two
    # ordinary single-layer rasters. tests/unit/test_catalog_crs_mismatch.py
    # gates that the pair is the only case claiming the relationship.
    "crs_mishandled": "crs/mishandled",
    "crs_mismatch": "crs/mismatch",
    "crs_unit_confusion": "crs/units",
    "utm_zone_mismatch": "crs/zone_selection",
    "utm_zone_ambiguity": "crs/zone_selection",
    "zone_boundary_artifact": "crs/zone_selection",
    "zone_selection": "crs/zone_selection",
    "reprojection_error": "crs/reprojection_error",
    "projection_failure": "crs/projection_failure",
    "local_projection_distortion": "crs/local_distortion",
    "projected_coordinate_assumption": "crs/projected_coordinate_assumption",
    # extent
    "antimeridian_split": "extent/antimeridian",
    "antimeridian_wrapping": "extent/antimeridian",
    "longitude_not_normalized": "extent/antimeridian",
    "wrapped_coordinate_retention": "extent/antimeridian",
    "polar_projection_singularity": "extent/polar",
    "polar_projection_edge_case": "extent/polar",
    "equatorial_boundary_case": "extent/equatorial",
    "hemisphere_boundary": "extent/equatorial",
    "bounds_normalization": "extent/bounds_normalization",
    "bbox_misinterpretation": "extent/bbox_misinterpretation",
    "coordinate_wrapping": "extent/coordinate_wrapping",
    "coordinate_range_error": "extent/coordinate_range_error",
    "coordinate_sign_assumption": "extent/coordinate_sign_assumption",
    # transform
    "affine_transform_bug": "transform/rotated",
    "nonsquare_pixel_assumption": "transform/nonsquare_pixels",
    "pixel_shape_assumption": "transform/nonsquare_pixels",
    "shifted_origin": "transform/shifted_origin",
    "pixel_shift": "transform/pixel_shift",
    "rasterization_alignment": "transform/rasterization_alignment",
    "resampling_assumptions": "transform/resampling_assumptions",
    "resolution_mismatch": "transform/resolution_mismatch",
    "alignment_too_strict": "transform/alignment_too_strict",
    # nodata
    "nodata_ignored": "nodata/ignored",
    "ambiguous_zero": "nodata/ambiguous_zero",
    "nan_mishandled": "nodata/nan_mishandled",
    "mask_misread": "nodata/mask_misread",
    "default_value_sink": "nodata/default_value_sink",
    # dtype
    "dtype_drift": "dtype/drift",
    "dtype_coercion": "dtype/coercion",
    "nullable_type_coercion": "dtype/nullable_coercion",
    "overflow_assumption": "dtype/overflow",
    "range_truncation": "dtype/range_truncation",
    "range_assumption": "dtype/range_assumption",
    "value_range_violation": "dtype/value_range_violation",
    # precision
    "precision_loss": "precision/loss",
    "precision_rounding": "precision/loss",
    "driver_specific_precision_loss": "precision/loss",
    "integer_precision": "precision/loss",
    "coordinate_drift": "precision/coordinate_drift",
    "roundtrip_degradation": "precision/roundtrip_degradation",
    # geometry
    "silent_invalid_geometry": "geometry/silent_invalid",
    "empty_geometry": "geometry/empty",
    "empty_geometry_handling": "geometry/empty",
    "null_empty_conflation": "geometry/null_empty_conflation",
    "zero_length_geometry": "geometry/zero_length",
    "degenerate_but_parseable": "geometry/degenerate_but_parseable",
    "ring_orientation": "geometry/ring_orientation",
    "ring_ordering": "geometry/ring_orientation",
    "ring_closure_error": "geometry/ring_closure",
    "mixed_geometry_output": "geometry/mixed_output",
    "repair_variability": "geometry/repair_variability",
    "repair_returns_geometrycollection": "geometry/repair_variability",
    "geometry_simplification_loss": "geometry/simplification_loss",
    "overaggressive_dissolve": "geometry/overaggressive_dissolve",
    "false_positive_intersection": "geometry/false_positive_intersection",
    "topology_error": "geometry/topology_error",
    "transitive_cluster_split": "geometry/transitive_cluster_split",
    "parse_exception": "geometry/parse_exception",
    # measurement
    "incorrect_area": "measurement/incorrect_area",
    "area_distortion": "measurement/area_distortion",
    "distance_calculation_error": "measurement/distance_error",
    "distance_threshold_error": "measurement/distance_error",
    "incorrect_statistics": "measurement/incorrect_statistics",
    "invalid_measurement": "measurement/invalid",
    # format
    "format_specific": "format/limitation",
    "format_limitation": "format/limitation",
    "format_limited": "format/limitation",
    "driver_behavior": "format/driver_behavior",
    "xml_driver_behavior": "format/xml_driver_behavior",
    "sqlite_driver_behavior": "format/sqlite_driver_behavior",
    "columnar_storage_behavior": "format/columnar_storage_behavior",
    "arrow_ipc_behavior": "format/arrow_ipc_behavior",
    "not_tiled": "format/not_tiled",
    "overviews_missing": "format/overviews_missing",
    "sidecar_dropped": "format/sidecar_dropped",
    "spec_nonconformance": "format/spec_nonconformance",
    "partial_read_blind_spot": "format/partial_read_blind_spot",
    "spatial_index_failure": "format/spatial_index_failure",
    "text_geometry_parsing": "format/text_geometry_parsing",
    "binary_geometry_parsing": "format/binary_geometry_parsing",
    # attribute
    "attribute_loss": "attribute/loss",
    "attribute_corruption": "attribute/corruption",
    "field_name_truncation": "attribute/field_name_truncation",
    "encoding_error": "attribute/encoding_error",
    "mojibake": "attribute/mojibake",
    "schema_mismatch": "attribute/schema_mismatch",
    "type_coercion": "attribute/type_coercion",
    "timezone_normalization": "attribute/timezone_normalization",
    # band
    "band_loss": "band/loss",
    "incorrect_band_order": "band/incorrect_order",
    "band_alias_ambiguity": "band/alias_ambiguity",
    "dimension_mismatch": "band/dimension_mismatch",
    "stacking_order_ignored": "band/stacking_order_ignored",
    # scaling
    "scale_factor_ignored": "scaling/ignored",
    "scale_offset_ignored": "scaling/ignored",
    "colormap_dropped": "scaling/colormap_dropped",
    "category_misread": "scaling/category_misread",
    "pixel_lattice_misclassification": "scaling/pixel_lattice_misclassification",
    "incorrect_rendering": "scaling/incorrect_rendering",
    # footprint
    "footprint_generation_error": "footprint/generation_error",
    "geocoding_failure": "footprint/geocoding_failure",
    # data
    "data_quality": "data/quality",
    "silent_bad_data": "data/silent_bad_data",
    "nan_propagation": "data/nan_propagation",
    "ambiguous_engine_dependent": "data/ambiguous_engine_dependent",
    "coordinate_edge_case": "data/coordinate_edge_case",
    "linear_artifacts_after_repair": "data/linear_artifacts_after_repair",
    "projection_assumptions": "data/projection_assumptions",
}

#: Terms deleted rather than aliased, and why. Kept as data so
#: ``scripts/validate_catalog.py`` can say *what happened to* a term rather
#: than only that it is unknown -- the rc1 -> rc3 lesson from plan 40 §2, where
#: a correct fix went out with no signal as to what had changed.
RISK_TYPE_RETIRED: Mapping[str, str] = {
    "none": (
        "the absence of a risk type, spelled wrong; removed from the 9 cases "
        "that carried it rather than replaced"
    ),
    "format_comparison": (
        "a corpus-construction label rather than a failure mode, covering 37% "
        "of the corpus; moved to tags -- select it with "
        'tags_any=["format_comparison"]'
    ),
}


def canonical_risk_type(term: str) -> str:
    """Return the canonical spelling of *term*.

    An unknown term is returned unchanged: resolution is not validation.
    ``scripts/validate_catalog.py`` is what rejects a typo, and it opens no
    data file, so that gate runs anywhere -- including without ``osgeo``.
    """
    return RISK_TYPE_ALIASES.get(term, term)


def canonical_risk_types(terms: list[str]) -> list[str]:
    """Resolve a whole ``risk_types`` list, de-duplicating and sorting.

    Merging makes duplicates possible where none existed: a case declaring both
    ``ring_orientation`` and ``ring_ordering`` resolves to one term twice.
    """
    return sorted({canonical_risk_type(t) for t in terms})


def risk_type_family(term: str) -> str | None:
    """Return the family prefix of *term*, or ``None`` if it is flat."""
    return term.split("/")[0] if "/" in term else None


def families() -> dict[str, list[str]]:
    """Return ``{family: sorted members}`` for every multi-member family."""
    out: dict[str, list[str]] = {}
    for term in sorted(RISK_TYPES):
        family = risk_type_family(term)
        if family is not None:
            out.setdefault(family, []).append(term)
    return out
