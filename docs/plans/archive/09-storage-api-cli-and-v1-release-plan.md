# Storage Layer, Public API/CLI, and v1.0 Release Plan

> **Archived — superseded. Retained as an implementation log.** Superseded by plan 10; its storage and CLI workstreams were deferred/withdrawn. See the Decision log.
>
> The single active roadmap is [`docs/plans/development-plan.md`](../development-plan.md).

> Created: June 2026
> Status: Withdrawn (July 2026)

## Context

Raster coverage (`docs/plans/08-raster-action-plan.md`, Phase 3) is treated as
fully done, including Steps 9–10 (Priority 2–4 raster families + the
manifest-backed follow-on boundary). A thorough review of the repo shows that
**manifest support (`docs/plans/06-manifest-support.md`, the discovery/catalog
layer) is also already implemented**:

- `src/geocase/catalog/models.py` — `ManifestStorage`, `ManifestCaseEntry`,
  `ManifestMetadata`, `RemoteInfo`
- `src/geocase/catalog/manifests.py` — `load_manifest`, `resolve_manifest_case`,
  `build_manifest_uri`, `iter_manifest_entries`, duplicate-id validation
- `src/geocase/catalog/registry.py` — `CaseRegistry.from_sources(...)` with
  bundled/manifest collision detection
- `tests/unit/test_manifests.py` — models, loader, URI, registry integration

So the remaining pre-v1.0 work is **Phase 4 (stub resolution)** and **Phase 5
(release polish)** from `docs/plans/03-consolidation-roadmap.md`. The genuinely
unbuilt layers are:

- `src/geocase/storage/*` — `remote.py`, `cache.py`, `hashing.py`, `local.py`
  are all one-line docstring stubs. This is the **transport/materialization**
  layer that turns manifest entries into real local files (the natural pairing
  with now-complete manifest support).
- `src/geocase/api/*` — `public.py`, `types.py` empty; top-level
  `src/geocase/__init__.py` exports nothing.
- `src/geocase/cli/*` — empty, yet `pyproject.toml` declares
  `geocase = "geocase.cli.main:app"`, so the installed console script is
  currently **broken**.
- `scripts/validate_catalog.py` does not validate manifests; no `CHANGELOG`;
  version still `0.1.0`.

**Decisions (confirmed with user):** target a **full v1.0** — implement the
storage layer *and* the API/CLI/release polish, treating end-to-end remote case
loading as a v1.0 feature; ship a **minimal stable public API and a working
CLI** (defer only `fetch`-heavy CLI niceties as needed).

Intended outcome: `geocase` installs cleanly, exposes a small stable public API,
has a functioning CLI, can fetch/verify/unpack/load manifest-backed remote
cases end-to-end, and is release-ready as v1.0.0.

---

## Workstream 1 — Storage layer (`src/geocase/storage/`)

Goal: turn a manifest entry into a verified local file tree that the existing
case loaders can open. Follow the responsibilities in
`docs/contributing/manifests-and-storage.md` (§"What storage support means").
Keep zero new hard dependencies — use `urllib`, `hashlib`, `zipfile`/`tarfile`
from stdlib; `https` and `filesystem` storage types only for v1.0 (s3/gcs/azure
explicitly deferred and should raise a clear `NotImplementedError`).

- **`hashing.py`** — reuse the existing streaming digest pattern from
  `scripts/generate_checksums.py:sha256_file`. Provide
  `sha256_file(path) -> str` and `verify_checksum(path, expected_sha256) -> None`
  (raises a `ChecksumMismatchError` with expected/actual on drift). Optionally
  `verify_size(path, expected_bytes)`.
- **`cache.py`** — resolve a cache root: `GEOCASE_CACHE_DIR` env var, else
  `platform`-appropriate default (`~/.cache/geocase`). Provide
  `cache_root() -> Path`, and `entry_path(case_id, version) -> Path` for the
  per-case/per-version directory. Reuse-if-present logic (skip re-download when a
  verified extracted tree already exists).
- **`remote.py`** — `download(uri, dest) -> Path` for `https` (stdlib
  `urllib.request`) and `filesystem` (`base_uri` is a local path / `file://`).
  Dispatch on `ManifestStorage.storage_type`; unsupported backends raise a clear
  error. No retries/auth beyond what `requires_auth` flags imply (auth deferred).
- **`local.py`** — `unpack(archive_path, dest_dir) -> Path` honoring
  `archive_format` (`zip`, `tar`/`tar.gz`; none → copy file as-is). Safe
  extraction (guard against path traversal).
- **High-level resolver** — add `storage/resolver.py` (or `storage/__init__.py`)
  with `materialize_case(manifest, entry, *, cache=None) -> Path` orchestrating:
  `build_manifest_uri` → `download` to cache → `verify_checksum` (+ size) →
  `unpack` → return the local case directory. Idempotent via the cache.

Tests (`tests/unit/test_storage.py`, `tests/integration/test_remote_case_loading.py`):
drive everything through a **`filesystem` storage backend** pointed at a
`tmp_path` so no network is required — create a small zipped fixture, register it
via a temp manifest, and assert it downloads/verifies/unpacks. Add a
checksum-mismatch failure test. Mark any real-network test (if added) `remote`
tier and skip by default.

---

## Workstream 2 — Wire remote cases into runtime loading

Goal: a selected manifest-backed case can be loaded with the same ergonomics as
a bundled case.

- Bridge `CaseRegistry` manifest entries to materialization: given a
  manifest-backed `case_id`, resolve its `ManifestMetadata`/`ManifestCaseEntry`
  (registry already stores the owning manifest in `_manifest_cases`), call
  `materialize_case`, then hand the local tree to the normal
  `VectorCase`/`RasterCase`/`NetCDFCase` machinery in `src/geocase/cases/`
  (a remote archive unpacks to a directory containing its own `case.yaml`;
  load it via `catalog/loader.load_case_metadata` then `cases/factory.create_case`).
- Surface a clear error when a remote case is requested but storage cannot
  resolve it (missing checksum like the current `replace_me`, network off, etc.).
  Note: `extended-manifests/public-extended.yaml` uses placeholder `sha256:
  "replace_me"` and an `example.org` base — real fetching is only exercised in
  tests via the filesystem backend; the public manifest stays a documented
  example until real artifacts are published.

---

## Workstream 3 — Public API surface (`src/geocase/api/`)

Goal: a small, stable import surface so users don't reach into internals.
Confirmed: **minimal API**.

- **`api/types.py`** — re-export the stable types: `CaseMetadata`,
  `SuiteMetadata`, and the manifest models from `catalog/models.py`.
- **`api/public.py`** — thin functions over the registry/cases:
  `list_cases(...)` (optionally filtered, reusing `catalog/selectors.py` /
  suite selection), `get_case(case_id)`, `show_case(case_id)` (human-readable
  summary incl. `remote, not fetched` state per the storage doc §"Unified
  catalog discovery"), and `load_case(case_id)` (materializes if remote, else
  loads bundled).
- **`src/geocase/__init__.py`** — export the public API + `__version__`.
- Tests: `tests/unit/test_public_api.py` asserting the import surface is stable
  and the functions behave (including a manifest-backed `show_case` reporting
  remote state).

---

## Workstream 4 — Minimal working CLI (`src/geocase/cli/`)

Goal: make the declared `geocase = "geocase.cli.main:app"` entry point real.
Confirmed: **fix CLI**. Use stdlib `argparse` (no new dependency) with an
`app()` callable as the entry point.

- **`cli/main.py`** — `app()` dispatching subcommands.
- **`cli/list_cases.py`** — `geocase list` (optionally `--category/--tag`).
- **`cli/show_case.py`** — `geocase show <case_id>` (uses `api.show_case`).
- **`cli/validate_catalog.py`** — `geocase validate` delegating to the existing
  `scripts/validate_catalog.py` logic (or import-and-call).
- **`cli/fetch_case.py`** — `geocase fetch <case_id>` calling
  `storage.materialize_case`; minimal, can print the cached path.
- Tests: `tests/unit/test_cli.py` invoking `app()` with argv lists and asserting
  output/exit codes.

---

## Workstream 5 — Catalog/manifest validation + CI

- Extend `scripts/validate_catalog.py` to validate manifests under
  `extended-manifests/` against `src/geocase/metadata/schemas/manifest.schema.yaml`
  and the cross-source rules already in `registry.from_sources` (duplicate ids
  within/across manifests, collisions with bundled ids, `archive_format`
  whitelist, well-formed `base_uri`). Reuse `catalog/manifests.load_manifest`.
- Add the manifest validation + the new storage/api/cli tests to CI:
  `ci/catalog-validation.yml` (add a manifest-validation step) and
  `ci/extended-tests.yml` (run the new test modules).

---

## Workstream 6 — Release polish → v1.0.0 (Phase 5)

- Stub-resolution decisions are now all "implement" (storage/api/cli) — record
  the outcomes in `docs/plans/03-consolidation-roadmap.md` (Phase 4 table) and
  mark `06-manifest-support.md` as completed.
- Bump `pyproject.toml` version to `1.0.0` and change the classifier from
  `3 - Alpha` to `5 - Production/Stable`. Add `numpy` handling per raster open
  question #2 only if storage/tests require it (otherwise leave transitive).
- Create `CHANGELOG.md` (none exists) covering raster expansion, manifest
  support, storage layer, public API, CLI.
- Add a PyPI build/publish workflow (mirror existing `ci/*.yml` style) and a
  short maintainer release checklist.
- Final docs pass: `docs/remote-datasets.md` and
  `docs/contributing/manifests-and-storage.md` status banners (currently say
  "storage still stubbed") updated to reflect shipped storage support.

---

## Recommended order

1. Storage layer (WS1) — foundational, fully testable offline via filesystem backend.
2. Runtime wiring for remote cases (WS2).
3. Public API (WS3) — depends on WS1/WS2 for `load_case`.
4. CLI (WS4) — sits on top of the API.
5. Validation + CI (WS5).
6. Release polish + v1.0.0 tag (WS6).

---

## Verification

- **Unit/integration tests:** `pip install -e .[dev]` then `pytest` — all green,
  including new `test_storage.py`, `test_remote_case_loading.py`,
  `test_public_api.py`, `test_cli.py`. Existing `tests/unit/test_manifests.py`
  must stay green (no regression to `from_sources`).
- **Offline end-to-end storage:** a test creates a zipped fixture + temp
  manifest with `storage_type: filesystem`, then asserts
  `materialize_case`/`load_case` downloads, verifies sha256, unpacks, and loads
  it like a bundled case; plus a checksum-mismatch test that raises cleanly.
- **CLI smoke:** `python -m build` / `pip install -e .` then run `geocase list`,
  `geocase show <id>`, `geocase validate`, `geocase fetch <id>` (filesystem
  backend) — entry point resolves and commands succeed.
- **Public API:** `python -c "import geocase; print(geocase.__version__); geocase.list_cases()"`.
- **Catalog/CI gates:** `python scripts/validate_catalog.py` (now incl.
  manifests), `python scripts/build_case_index.py --check`,
  `python scripts/generate_checksums.py --check`, and the coverage-matrix diff
  gates all pass.
