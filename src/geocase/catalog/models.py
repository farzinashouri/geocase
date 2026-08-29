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
