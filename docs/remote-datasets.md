# Remote datasets

GeoCase keeps its bundled core intentionally small. Larger or richer cases can be stored remotely and fetched on demand.

!!! note "Status: manifests in v1.0, transport in v1.1"

    v1.0 ships the *metadata* half of this design. Remote cases are described by
    manifests and are discoverable by id, but GeoCase does not yet download,
    cache, or unpack them — asking for a remote case raises a clear error telling
    you where the artifact lives. The download and cache layer described below is
    planned for v1.1. See
    [the roadmap](contributing/development-plan.md) for the current scope.

## Why remote storage exists

Some cases are useful but not suitable for packaging:

- larger rasters
- multi-file archives
- realistic scene bundles
- optional public downloads
- organization-specific private cases

## Storage classes

GeoCase recognizes three storage classes:

- `bundled`
- `remote`
- `private`

## Remote manifests

Remote datasets are described by manifest files. A manifest maps:

- case id
- version
- relative path
- checksum
- size
- storage backend

GeoCase can use the manifest to:

- locate a remote case
- download it into cache
- verify checksum
- expose the case through the same API as bundled cases

## Recommended flow

1. define the case metadata
2. publish the archive to object storage or static hosting
3. add the case to a manifest
4. fetch on demand during testing

## Private cases

Organizations can later maintain their own private manifests and point GeoCase to them without publishing the underlying datasets.
