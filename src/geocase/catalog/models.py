from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Category = Literal["vector", "raster", "netcdf", "satellite"]
FormatType = Literal[
    "GeoJSON",
    "GPKG",
    "Shapefile",
    "GeoTIFF",
    "NetCDF",
    "Parquet",
    "GML",
    "KML",
    "CSV_WKT",
    "Feather",
    "Arrow",
    "GeoArrow",
    "WKB",
    "WKT",
    "SQLite",
    "FlatGeobuf",
    "Other",
]
TestTier = Literal["unit", "integration", "slow", "remote", "private"]
SizeClass = Literal["tiny", "small", "medium", "large"]
StorageClass = Literal["bundled", "remote", "private"]
LoaderHint = Literal["geopandas", "rasterio", "xarray", "generic"]
Status = Literal["draft", "validated", "published", "deprecated", "archived"]


class FileMap(BaseModel):
    primary: str
    preview: str | None = None
    notes: str | None = None
    sidecars: list[str] = Field(default_factory=list)


class RemoteInfo(BaseModel):
    manifest_key: str | None = None
    uri: str | None = None
    checksum_sha256: str | None = None
    byte_size: int | None = None


ManifestStorageType = Literal["s3", "gcs", "azure", "https", "filesystem"]


class ManifestStorage(BaseModel):
    storage_type: ManifestStorageType
    base_uri: str
    requires_auth: bool = False
    is_public: bool = False


class ManifestCaseEntry(BaseModel):
    case_id: str
    version: str
    relative_path: str
    sha256: str
    byte_size: int | None = None
    archive_format: str | None = None

    # Pairs a remote scene with the small bundled fixture it is the realistic
    # analog of, so contributors can reason about "the big version of this
    # fixture" (see docs/plans/archive/08-raster-action-plan.md, Step 10).
    bundled_analog: str | None = None

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if not value:
            raise ValueError("Manifest case id cannot be empty")
        if value != value.lower():
            raise ValueError("Manifest case id must be lowercase")
        if " " in value:
            raise ValueError("Manifest case id must not contain spaces")
        return value

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Manifest relative_path cannot be empty")
        return value


class ManifestMetadata(BaseModel):
    manifest_key: str
    title: str
    description: str | None = None
    schema_version: str
    storage: ManifestStorage
    cases: list[ManifestCaseEntry] = Field(default_factory=list)

    @field_validator("manifest_key")
    @classmethod
    def validate_manifest_key(cls, value: str) -> str:
        if not value:
            raise ValueError("Manifest key cannot be empty")
        return value


class SpatialExtent(BaseModel):
    """A WGS84 bounding box saying where on Earth a case's data sits.

    Longitudes are degrees east in [-180, 180], latitudes degrees north in
    [-90, 90]. ``north`` must be >= ``south``.

    ``west > east`` is **valid** and means the box crosses the antimeridian:
    the box runs east from ``west``, over 180, and on to ``east``. Without
    that convention an antimeridian case reports a naive envelope spanning the
    whole planet, which is the opposite of the fact its page needs to state.
    It is the same convention the ``geojson_bounds`` benchmark grader uses.

    Extents are *computed from the real bytes* by ``scripts/catalog_extent.py``
    and written into ``case.yaml``, so they cannot drift from the data. The
    prose companion is the hand-written :attr:`CaseMetadata.region`.
    """

    west: float
    south: float
    east: float
    north: float

    @field_validator("west", "east")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180.0 <= value <= 180.0:
            raise ValueError(f"Longitude {value} is outside [-180, 180]")
        return value

    @field_validator("south", "north")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90.0 <= value <= 90.0:
            raise ValueError(f"Latitude {value} is outside [-90, 90]")
        return value

    @model_validator(mode="after")
    def validate_latitude_order(self) -> SpatialExtent:
        if self.north < self.south:
            raise ValueError(
                f"north ({self.north}) must be >= south ({self.south}); "
                "only longitudes may be inverted, to cross the antimeridian"
            )
        return self

    @property
    def crosses_antimeridian(self) -> bool:
        """True when the box wraps past 180 -- see the class docstring."""
        return self.west > self.east


class SourceInfo(BaseModel):
    name: str | None = None
    url: str | None = None
    license: str | None = None
    derived_from: str | None = None


NodataConvention = Literal["sentinel", "nan", "mask", "none"]

#: Whether a transform's coordinates name pixel corners or pixel centres.
#: A *new* Literal rather than an extension of a promised one, so nothing in the
#: v1.0 surface changes. GDAL writes this as the ``AREA_OR_POINT`` tag and omits
#: it entirely for ``area``, which is why the default matters more than the tag.
PixelAnchor = Literal["area", "point"]


#: The ``required_drivers`` entry meaning "no OGR driver opens this at all".
#:
#: A WKB or WKT case is a bare geometry blob — a byte string or a text string
#: with no container, no schema and no header — so there is no driver to
#: install and no GDAL build that would help. The empty string is deliberately
#: falsy, so ``all(d in available for d in required_drivers)`` excludes such a
#: case for every possible ``available`` set, without the consumer needing to
#: know the sentinel exists.
NO_OGR_DRIVER = ""


#: How a curated-failure case is expected to fail (plan 28 phase 2.4).
#:
#: A small vocabulary rather than concrete exception classes, because the class
#: is the *consumer's*: the same unclosed ring surfaces as ``GEOSException``
#: from shapely, ``DataSourceError`` from pyogrio and ``ValueError`` from
#: pandas. Naming any of them would pin geocase's metadata to one reader's
#: internals. A harness that could previously assert only *that* a case failed
#: can now assert *how*, which is what separates "failed for the curated
#: reason" from "the driver is missing" and from "the consumer has a new bug".
#:
#: * ``unparseable_geometry`` -- the bytes do not yield a geometry at all
#:   (an unclosed ring, a truncated WKB, malformed JSON). No validity question
#:   arises, because nothing was constructed.
#: * ``unsupported_format`` -- the container is understood but this variant is
#:   not (an unhandled dialect, an unreadable encoding).
#: * ``missing_driver`` -- the reader has no driver installed for the format.
#:   Distinct from the others in that installing something is the fix; see
#:   ``required_drivers``, which lets a consumer predict this before reading.
#: * ``invalid_crs`` -- the CRS definition itself cannot be constructed.
#: * ``invalid_topology`` -- the geometry constructs but the operation rejects
#:   it (a self-intersection an engine refuses rather than repairs).
ExpectedErrorKind = Literal[
    "unparseable_geometry",
    "unsupported_format",
    "missing_driver",
    "invalid_crs",
    "invalid_topology",
]


class KnownDivergence(BaseModel):
    """A catalogued disagreement between two ways of reading the same case.

    Plan 28 phase 2.5. The external pyogrio run found that
    ``empty_geometry_gpkg`` returns a different row count through pyogrio's
    Arrow path than through its numpy path, under a spatial filter — a GDAL
    bug, now filed. It will keep doing that for every user until GDAL fixes it.

    Without somewhere to record that, the next person running a differential
    harness re-investigates from scratch, and — the expensive part — cannot
    tell a *newly introduced* consumer bug on the same case from the one
    already understood. :mod:`geocase.differential` consults this list so a
    matching divergence is reported as ``known`` rather than as a fresh
    failure.

    This is a **record, not an assertion**. Nothing in the content gate can
    verify it: whether the divergence still reproduces depends on the reader
    the user has installed, not on geocase's bytes. What the corpus gates is
    only that the record is well-formed — see
    ``tests/unit/test_known_divergences.py``.

    Attributes:
        consumer: The library that diverges, e.g. ``"pyogrio"``. Required,
            because an unattributed record cannot be matched against anything.
        version_range: Where it was observed, as free text (``">=0.8"``,
            ``"GDAL 3.13.3"``). Free text rather than a parsed specifier: the
            relevant version is often a *transitive* one (GDAL under pyogrio)
            that no Python version specifier addresses.
        description: What actually differs, in a sentence a reader can act on.
        upstream_url: The filed issue or PR, so "is this still open?" is one
            hop away.
    """

    consumer: str
    version_range: str | None = None
    description: str
    upstream_url: str | None = None

    @field_validator("consumer", "description")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "KnownDivergence consumer and description cannot be blank -- "
                "a record nobody can attribute or read is worse than no record"
            )
        return value


class AssertionHints(BaseModel):
    expect_loadable: bool = True
    expect_valid_geometry: bool | None = None
    expect_crs: bool | None = None
    expected_epsg: int | None = None
    expected_geometry_types: list[str] = Field(default_factory=list)
    expect_nodata: bool | None = None

    # Typed raster expectations
    # (see docs/plans/archive/08-raster-action-plan.md, Step 2)
    expected_band_count: int | None = None
    expected_dtype: str | None = None
    expected_shape: list[int] | None = None
    expected_nodata_value: float | int | None = None
    nodata_convention: NodataConvention | None = None
    expected_compression: str | None = None
    expected_overviews: bool | None = None
    expected_band_names: list[str] = Field(default_factory=list)
    expected_scale_factor: float | None = None
    expected_colormap_present: bool | None = None
    is_cog: bool | None = None

    # Georeferencing conventions (plan 34 phase 2). A *list* of signs rather
    # than one value: a rotated affine carries non-zero b/d as well, which no
    # single sign describes. Members are "positive_e" | "negative_e" |
    # "rotated".
    expected_transform_signs: list[str] | None = None
    expected_pixel_anchor: PixelAnchor | None = None

    # OGR driver prerequisites (plan 28 phase 2.1). Additive with an empty
    # default, so every existing case.yaml stays valid.
    #
    # This describes what an **OGR-based consumer** — pyogrio, fiona, ogr2ogr —
    # needs installed before the case will open *for them*. It is not a
    # statement about geocase: ``VectorCase.load()`` reads every bundled vector
    # case without OGR (shapely for WKB/WKT, geopandas' Arrow readers for
    # Parquet/Feather/Arrow), which is why nothing here affects ``load_case``.
    #
    # Three tiers:
    #   ``[]``                 stock GDAL opens it; nothing to check.
    #   ``["Parquet"]``        needs an optional plugin (libgdal-arrow-parquet);
    #                          check against ``pyogrio.list_drivers()`` or
    #                          ``fiona.supported_drivers`` and skip if absent.
    #   ``[NO_OGR_DRIVER]``    no driver exists at any build configuration.
    required_drivers: list[str] = Field(default_factory=list)

    # How this case fails, for the cases that are *meant* to (plan 28 phase
    # 2.4). Additive with a ``None`` default, so every existing case.yaml stays
    # valid. See :data:`ExpectedErrorKind` for the vocabulary and why it is a
    # vocabulary rather than an exception class.
    expected_error_kind: ExpectedErrorKind | None = None

    @model_validator(mode="after")
    def validate_error_kind_needs_a_failure(self) -> AssertionHints:
        """A failure mode on a loadable case describes an event that never occurs.

        Without this, ``expected_error_kind`` could be attached to any case and
        nothing would ever evaluate it -- the "declared but ungated" shape that
        the content gate exists to close.
        """
        if self.expected_error_kind is not None and self.expect_loadable is not False:
            raise ValueError(
                f"expected_error_kind={self.expected_error_kind!r} requires "
                "expect_loadable: false -- a case that loads has no failure mode"
            )
        return self


class CaseMetadata(BaseModel):
    id: str
    title: str
    description: str | None = None
    category: Category
    format: FormatType
    test_tier: TestTier
    size_class: SizeClass
    storage_class: StorageClass
    redistributable: bool
    schema_version: str
    status: Status = "draft"

    tags: list[str] = Field(default_factory=list)
    risk_types: list[str] = Field(default_factory=list)

    behavioral_goal: str | None = None
    expected_capabilities: list[str] = Field(default_factory=list)
    loader_hint: LoaderHint
    geometry_type: str | None = None
    crs: str | None = None

    # Where on Earth this case is. ``extent`` is generated from the data by
    # ``scripts/catalog_extent.py``; ``region`` is a hand-written label. Both
    # optional: netcdf cases get no computed extent, and a case may have no
    # region worth naming. See docs/plans/31-case-geography-and-world-maps.md.
    extent: SpatialExtent | None = None
    region: str | None = None

    files: FileMap
    remote: RemoteInfo | None = None
    source: SourceInfo | None = None
    assertions: AssertionHints = Field(default_factory=AssertionHints)

    # Catalogued consumer disagreements (plan 28 phase 2.5). Additive with an
    # empty default: ``[]`` means "no divergence has been recorded", never "no
    # divergence exists". See :class:`KnownDivergence`.
    known_divergences: list[KnownDivergence] = Field(default_factory=list)

    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value:
            raise ValueError("Case id cannot be empty")
        if value != value.lower():
            raise ValueError("Case id must be lowercase")
        if " " in value:
            raise ValueError("Case id must not contain spaces")
        return value


class SuiteSelection(BaseModel):
    include_case_ids: list[str] = Field(default_factory=list)
    exclude_case_ids: list[str] = Field(default_factory=list)
    category: Category | None = None
    geometry_type: str | None = None
    test_tier: TestTier | None = None
    storage_class: StorageClass | None = None
    format: FormatType | None = None
    loader_hint: LoaderHint | None = None
    tags_any: list[str] = Field(default_factory=list)
    tags_all: list[str] = Field(default_factory=list)
    risk_types_any: list[str] = Field(default_factory=list)
    size_class: SizeClass | None = None


class SuiteMetadata(BaseModel):
    suite_key: str
    title: str
    description: str
    schema_version: str
    selection: SuiteSelection
    case_order: list[str] = Field(default_factory=list)
    notes: str | None = None
