# Actionable Next Steps

> Created: April 2026
> Status: Active planning document (refreshed April 2026)

This document captures the high-level actionable next steps for bringing GeoCase from alpha to a releasable state.

---

## Current State Summary

GeoCase is a geospatial testing toolkit in **alpha (v0.1.0)**.

As of April 2026:

- the documentation consolidation work is complete,
- the focused Phase 2 vector edge-case backlog is complete,
- the universal format/geometry compliance gate is implemented,
- the core test suite under `tests/` is green (`526 passed, 1 skipped`).

The main remaining pre-v1.0 work has shifted away from vector cleanup and toward:

- raster coverage expansion,
- deciding which stubbed modules truly need a v1.0 implementation,
- defining a small stable public API,
- release polish and automation.

Several supporting layers still exist as stubs or partial placeholders: manifests, storage, API, and CLI.

---

## Recently Completed

- **Docs reorganization:** completed via `02-documentation-consolidation.md`
- **Vector Phase 2:** completed via `04-phase-2-vector-edge-cases.md`
- **Format/geometry compliance gate:** implemented via `05-format-geometry-compliance-gate.md`

---

## Priority Actions

### 1. Expand raster test coverage

**Plan anchor:** `docs/plans/03-consolidation-roadmap.md` → Phase 3

This is now the clearest next substantive milestone. The vector backlog is no
longer the bottleneck; raster coverage is the biggest remaining catalog/testing
gap before v1.0.

Focus first on:

- multi-band raster fixtures,
- rotated/skewed transforms,
- dtype coverage,
- overviews / compression / COG behavior,
- parameterized sample-function tests mirroring the vector interview-question pattern.

### 2. Implement manifest support

**File:** `src/geocase/catalog/manifests.py`

Enables external and extended catalog ingestion beyond bundled core cases.
This is the discovery/control layer for remote datasets: it lets GeoCase know
which external cases exist, where they live, which version/checksum they
declare, and how they should appear in the catalog.

Manifest support is useful even before full storage support exists because it
still enables catalog ingestion, validation, listing, filtering, and registry
integration for external cases. For example, GeoCase could understand that
`coastal_scene_small` exists in `extended-manifests/public-extended.yaml`, show
its version and expected archive path, and expose it as an extended case even
if fetching is not implemented yet.

What manifests do **not** provide on their own is transport: without the
storage layer, GeoCase still cannot download, cache, unpack, or checksum-verify
the remote artifact in practice. In other words, manifests make the external
catalog visible and structured; storage makes it executable.

This is still the most directly useful stubbed layer once the raster backlog is
underway, because storage has little value until GeoCase can first ingest and
reason about external catalogs.

See `docs/plans/06-manifest-support.md` for the concrete phased implementation
plan, including proposed models, loader functions, catalog integration, and
tests.

### 3. Implement storage layer

**Files:** `src/geocase/storage/local.py`, `remote.py`, `cache.py`, `hashing.py`

Remote case fetching, caching, and checksum verification. This unlocks larger
datasets that cannot be bundled in the package and pairs naturally with
manifest support.

### 4. Create public API surface

**Files:** `src/geocase/api/__init__.py`, `api/types.py`

Define a small stable import surface so downstream users can rely on GeoCase
without importing internal modules directly.

### 5. Add release automation

Build/publish workflow for PyPI, versioning documentation, and a small release
checklist for maintainers.

---

## Decisions Already Made

### Validators

**File:** `src/geocase/catalog/validators.py`

Validation rules for case metadata and manifests to catch catalog errors early. Currently this logic lives in `scripts/validate_catalog.py` as a standalone maintainer script.

**Decision:** Keep as script for now — not blocking v1.0. Formalize later if programmatic validation is needed.

---

## Secondary Actions

### 6. CLI implementation (optional)

**Files:** `src/geocase/cli/main.py`, `list_cases.py`, `show_case.py`, `fetch_case.py`, `validate_catalog.py`

Basic commands for catalog inspection. Defer to post-v1.0 unless maintainer workflows require it.

### 7. Stub module review

Before implementing every placeholder module, decide which ones are truly part
of the v1.0 surface versus which should remain deferred. Use Phase 4 in
`docs/plans/03-consolidation-roadmap.md` as the decision checklist.

---

## Open Questions

1. **Raster-first sequencing?** Which raster fixture family should land first: multi-band, rotated transforms, or dtype coverage?

2. **Manifest + storage scope?** Is bundled-core + manifest parsing enough for v1.0, or is remote fetching required in the initial release?

3. **CLI timing?** Defer to post-v1.0 or include only a minimal maintainer-facing command set?
