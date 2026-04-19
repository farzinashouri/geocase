from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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


class SourceInfo(BaseModel):
    name: str | None = None
    url: str | None = None
    license: str | None = None
    derived_from: str | None = None


class AssertionHints(BaseModel):
    expect_loadable: bool = True
    expect_valid_geometry: bool | None = None
    expect_crs: bool | None = None
    expected_epsg: int | None = None
    expected_geometry_types: list[str] = Field(default_factory=list)
    expect_nodata: bool | None = None


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