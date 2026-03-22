# Database design

GeoCase does not require a database for its first usable version.

For the packaged toolkit, YAML metadata plus local and remote manifests are enough.

## When a database becomes useful

A database is helpful when GeoCase grows into a hosted catalog or service that needs:

- searchable metadata
- version tracking
- public and private registries
- suite management
- governance and provenance
- storage location management

## What the database should store

The database should store catalog metadata, not geospatial blobs.

Recommended entities:

- case
- case_version
- artifact
- tag
- risk_type
- capability
- suite
- storage_location

## Key principle

GeoCase files should live in:

- package data
- object storage
- private user storage

The database should track:

- identifiers
- relationships
- versions
- URIs
- checksums
- selection metadata

## Practical recommendation

Build YAML-first.

Only introduce the database once you need one of these:

- hosted catalog API
- cross-project remote registry
- access-controlled private catalogs
- advanced search and filtering

