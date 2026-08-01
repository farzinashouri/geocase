# Manifest Support Plan

> **Archived — superseded. Retained as an implementation log.** Manifest parsing and models shipped; wiring them into the registry is Step 14 of the roadmap.
>
> The single active roadmap is [`docs/contributing/development-plan.md`](../../contributing/development-plan.md).

> Created: April 2026
> Status: Complete (June 2026)

This document captures the proposed implementation plan for adding **manifest support** to GeoCase.

Manifest support is the metadata/catalog layer that allows GeoCase to understand
**external catalogs** beyond the bundled core cases. It is distinct from storage
support: manifests tell GeoCase **what external cases exist** and where they are
supposed to live, while storage support later makes those artifacts
**downloadable, cacheable, and verifiable**.

For the conceptual background and the rationale for separating manifest support
from storage support, see
[`docs/contributing/manifests-and-storage.md`](../../contributing/manifests-and-storage.md).

---

## Goal

Implement the smallest useful version of manifest support so GeoCase can:

- read and validate manifest YAML files,
- understand external case entries such as `coastal_scene_small`,
- resolve remote artifact locations from manifest metadata,
- expose external cases through the catalog layer,
- and prepare the ground for later storage/caching support.

This phase does **not** need to download or unpack remote files yet.

---

## Why this matters

Today, GeoCase runtime behavior is still effectively **bundled-core only**:

- `src/geocase/catalog/registry.py` loads from `case-index.yaml`,
- `src/geocase/catalog/loader.py` parses cases and suites,
- but `src/geocase/catalog/manifests.py` is still a stub,
- and external manifests under `extended-manifests/` are not consumed.

That means GeoCase can document extended catalogs, but it cannot yet ingest
or reason about them at runtime.

Implementing manifest support closes that gap.

---

## Existing repo inputs

The repository already contains the ingredients for a first implementation:

- `src/geocase/metadata/schemas/manifest.schema.yaml`
- `extended-manifests/public-extended.yaml`
- `src/geocase/catalog/models.py` (`RemoteInfo` already exists)
- `docs/remote-datasets.md`
- `docs/contributing/manifests-and-storage.md`

The example manifest already describes entries like:

- `coastal_scene_small`
- `utm_boundary_scene`

with fields such as:

- `manifest_key`
- `storage.storage_type`
- `storage.base_uri`
- `relative_path`
- `sha256`
- `byte_size`
- `archive_format`

---

## Scope of this plan

### In scope

- manifest Pydantic models
- manifest YAML loading
- manifest validation
- URI construction from `base_uri` + `relative_path`
- listing and lookup of manifest-backed case entries
- basic integration with catalog/registry behavior
- unit tests for the above

### Not yet in scope

- downloading files
- caching remote artifacts
- archive extraction
- checksum verification against downloaded bytes
- automatically loading manifest-backed cases as if they were already local

Those belong to later storage work.

---

## Design principles

1. **Keep manifests separate from bundled case metadata at first**
   - a manifest entry is not the same thing as a full `CaseMetadata`
   - do not force remote entries into the bundled-case shape too early

2. **Start with metadata/catalog usefulness**
   - listing, lookup, validation, and URI resolution are enough for the first milestone

3. **Do not break the existing bundled-only registry path**
   - keep current `CaseRegistry.from_index(...)` behavior stable
   - add manifest-aware behavior in a controlled way

4. **Make storage a follow-on layer**
   - manifests define the contract storage must later execute

---

## Proposed implementation phases

### Phase 1 — Manifest models

**Primary file:** `src/geocase/catalog/models.py`

Add typed models for manifest data, likely along these lines:

- `ManifestStorage`
- `ManifestCaseEntry`
- `ManifestMetadata` (or `CatalogManifest`)

### Required fields from schema

For the top-level manifest:

- `manifest_key`
- `title`
- `description` (optional)
- `schema_version`
- `storage`
- `cases`

For storage:

- `storage_type`
- `base_uri`
- `requires_auth` (optional)
- `is_public` (optional)

For case entries:

- `case_id`
- `version`
- `relative_path`
- `sha256`
- `byte_size` (optional)
- `archive_format` (optional)

### Acceptance criteria

- manifest YAML can be parsed into typed Pydantic models
- invalid manifest structure raises clean validation errors

---

### Phase 2 — Manifest loader

**Primary file:** `src/geocase/catalog/manifests.py`

Implement manifest loading/parsing behavior.

Recommended functions:

- `load_manifest(path: Path) -> ManifestMetadata`
- `load_manifest_case_ids(path: Path) -> list[str]` (optional convenience)
- `resolve_manifest_case(manifest: ManifestMetadata, case_id: str) -> ManifestCaseEntry`

This module should mirror the style of `catalog/loader.py`, but remain focused
on manifest-specific logic.

### Acceptance criteria

- `extended-manifests/public-extended.yaml` loads successfully
- empty/missing/invalid manifest files fail clearly
- case entries can be looked up by `case_id`

---

### Phase 3 — URI and metadata resolution

**Primary file:** `src/geocase/catalog/manifests.py`

Implement helpers that turn manifest metadata into runtime-usable references.

Recommended helpers:

- `build_manifest_uri(manifest, entry) -> str`
- `iter_manifest_entries(manifest) -> Iterator[ManifestCaseEntry]`

Example:

- `base_uri = https://example.org/geocase/public`
- `relative_path = coastal_scene_small.zip`

should produce:

- `https://example.org/geocase/public/coastal_scene_small.zip`

### Acceptance criteria

- URI joining is deterministic and tested
- manifest entries can be inspected without downloading anything

---

### Phase 4 — Catalog integration

**Primary files:**

- `src/geocase/catalog/manifests.py`
- `src/geocase/catalog/registry.py`

This phase decides how manifests appear in the catalog layer.

### Recommended first approach

Do **not** change the default bundled registry path immediately.

Instead, add a separate integration path, for example:

- `load_manifest_catalog(...)`
- `CaseRegistry.from_sources(..., manifest_paths=...)`
- or another explicit manifest-aware entry point

The first milestone should allow GeoCase to:

- list manifest-backed case IDs,
- inspect which manifest they came from,
- distinguish bundled versus external entries,
- and surface enough metadata for later storage resolution.

### Acceptance criteria

- bundled catalog behavior still works unchanged
- manifest-backed entries can be listed and inspected
- duplicate case-ID collisions are detected or rejected clearly

---

### Phase 5 — Validation rules

**Primary file:** `src/geocase/catalog/manifests.py`

Add validation beyond pure schema shape.

Examples:

- duplicate `case_id` inside one manifest
- duplicate `case_id` across multiple manifests
- collision with bundled `CaseMetadata.id`
- invalid or empty `relative_path`
- unsupported `archive_format`
- malformed `base_uri`

This may later move into `catalog/validators.py`, but can live with manifest
logic initially.

### Acceptance criteria

- invalid catalog combinations fail early and readably
- manifest collisions do not silently override existing cases

---

### Phase 6 — Tests

**New test file:** `tests/unit/test_manifests.py`

Add tests for:

- valid manifest loading
- missing manifest file
- empty manifest file
- invalid schema
- case lookup by `case_id`
- URI construction
- duplicate ID handling
- collision with bundled case IDs
- manifest-only listing/inspection behavior

Use these as inputs:

- `extended-manifests/public-extended.yaml`
- temporary invalid manifests created in tests

### Acceptance criteria

- manifest behavior is covered by focused unit tests
- regression tests lock in design decisions

---

## Minimum useful milestone

Before any storage work, manifest support should at least make this possible:

- GeoCase can read `extended-manifests/public-extended.yaml`
- GeoCase can say that `coastal_scene_small` exists
- GeoCase can show its manifest key, version, archive path, size, and checksum
- GeoCase can construct the full expected URI
- GeoCase can distinguish that this case is external and not yet materialized locally

If those behaviors work, manifest support is already useful, even without
remote downloading.

---

## What comes later in storage support

Once manifest support exists, the next layer can implement:

- remote download logic
- local cache directory management
- checksum verification against actual bytes
- archive unpacking
- resolving a remote case into a local file tree
- handing that local file tree to normal `VectorCase` / `RasterCase` / `NetCDFCase` loading

Those later phases should live primarily in:

- `src/geocase/storage/remote.py`
- `src/geocase/storage/cache.py`
- `src/geocase/storage/hashing.py`
- `src/geocase/storage/local.py`

---

## Concrete example

Using `extended-manifests/public-extended.yaml`, Phase 1–4 should let GeoCase answer:

- Does `coastal_scene_small` exist? → yes
- Which manifest defines it? → `public-extended`
- What is its expected artifact path? → `coastal_scene_small.zip`
- What is its full URI? → `https://example.org/geocase/public/coastal_scene_small.zip`
- What checksum/version/archive does it declare? → from the manifest metadata

What it should **not** do yet:

- download the zip
- unpack it
- verify bytes against `sha256`
- transparently load it as a local vector/raster case

---

## Recommended implementation order

1. add manifest Pydantic models
2. implement manifest loading
3. implement URI resolution helpers
4. implement manifest listing and lookup
5. add catalog integration without breaking bundled behavior
6. add focused unit tests
7. defer storage execution to the next phase

This order gives GeoCase a meaningful external-catalog feature without taking on
networking, caching, and file-materialization complexity too early.

---

## Final summary

Manifest support is the smallest useful step that turns GeoCase from a
**bundled-core-only runtime** into a system that can also **understand external
catalogs**.

It should be implemented first as a metadata/catalog feature:

- models
- loader
- URI resolution
- lookup/listing
- validation
- tests

That creates a stable foundation for later storage support, where downloads,
caching, checksum verification, and remote case materialization can be added
without changing the fundamental manifest contract.
