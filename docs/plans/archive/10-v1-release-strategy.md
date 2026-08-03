# v1.0 Release Strategy — Ship the pytest Product, Defer Transport

> **Archived — superseded. Retained as an implementation log.** Retained as the detailed rationale and evidence behind Steps 11-16 of the roadmap.
>
> The single active roadmap is [`docs/plans/development-plan.md`](../development-plan.md).

> Created: July 2026
> Status: Folded into the roadmap (July 2026); partially implemented (August 2026)
> Supersedes: `docs/plans/09-storage-api-cli-and-v1-release-plan.md`

---

## Implementation status (as of 1 Aug 2026)

**Done: Stage 0, Stage A, Stage A6.** Remaining: Stages B, C, D, E.

| Stage | Status | Notes |
|---|---|---|
| **0** — Collapse the roadmap | ✅ Done | Plans 01–10 archived; `development-plan.md` is the single roadmap with a Decision log. |
| **A1** — Remove console script | ✅ Done | `[project.scripts]`, `cli/`, and `storage/{local,remote,cache}.py` deleted. |
| **A2** — Fix bare `pytest` | ✅ Done | `testpaths = ["tests"]` + `importorskip("osgeo")`. |
| **A3** — Fix the dev environment | ✅ Done | Resolved differently than proposed — see below. |
| **A4** — Give `hashing.py` a consumer | ✅ Done | `generate_checksums.py` imports `sha256_file`. |
| **A5** — Fix `remote-datasets.md` | ✅ Done | Fence repaired; status note added that transport is v1.1. |
| **A6** — Bundled catalog size | ✅ Done | **36 MB → 4.2 MB**; wheel is 458 KB. |
| **B** — Quality gates | ⬜ Not started | B4 partly done (`requires-python`, tool targets). |
| **C** — Public API | ⬜ Not started | |
| **D** — Manifests reachable | ⬜ Not started | |
| **E** — Docs truth pass & release | ⬜ Not started | |

### Where reality differed from this plan

Findings from implementation. The roadmap carries the corrected versions.

1. **`polygon_sqlite_baseline` does not prove the bloat was unintended** (Stage A6's
   premise). It has 0 of 4 SpatiaLite signature tables and no R-tree — it is plain
   SQLite, and its case tags say `sqlite`, not `spatialite`. It is small because it is a
   *different kind of fixture*. The prescribed fix was still correct; the reasoning was
   not.
2. **SpatiaLite fixtures are not byte-reproducible**, so `generate_vector_fixtures.py`
   could not mirror the raster generator's byte-comparison `--check`.
   `spatialite_history` records wall-clock timestamps and library versions. The gate
   compares observable semantics instead, with identifiers casefolded.
3. **`tiny ≤ 256 KB` was too tight.** The largest honest `tiny` case is 240 KB — 6%
   headroom. Shipped at 512 KB.
4. **The case count was wrong.** Actual: **134 cases (103 vector / 30 raster / 1
   netcdf)**, not "130 / 26". The five `footprint_edge_cases/case_*.yaml` share one
   directory, so counting files named `case.yaml` undercounts.
5. **A3 did not account for `environment.yml`,** which pins conda/3.14 with GDAL and is
   the documented dev environment. Both environments are now kept deliberately:
   conda/3.14 primary (only one with GDAL — without it `pytest examples` collects 37
   tests instead of 1238), `.venv`/3.11 as the CI mirror.
6. **`requires-python` went to `>=3.11`, not the proposed `>=3.10`.** 3.10 is installed
   nowhere and in no CI job, so it would have been the same untested promise as `>=3.9`,
   one version up. 3.11 (CI) and 3.14 (local) are both real.
7. **Two more empty stubs exist** beyond `cli/` and the storage modules:
   `raster/affine_transform_quirk/case.yaml` is empty and silently skipped by
   `build_case_index.py`, yet ships in the wheel; and `requirements-lock.txt` in the repo
   root belongs to an unrelated project (Flask, aiohttp, twine, `issuedb`).

---

## Context

A full audit of the code, tests, CI, and all ten planning documents found that the
engineering to date is strong, but **plan 09 optimizes for the wrong thing and rests on
a stale inventory**. This plan replaces it.

**1. Plan 09's two largest workstreams build transport for cargo that does not exist.**
Both manifests reference 100% placeholder artifacts — every `sha256` is literally
`"replace_me"`, every `base_uri` is `example.org`, and nothing was ever published.
`extended-manifests/satellite-scenes.yaml`'s own header admits fetching "will fail
checksum verification by design." Plan 09 concedes the same in WS2. Confirming how
isolated this is: `grep -rn "geocase.storage" src tests examples scripts` returns **zero
hits** — even the one implemented file, `src/geocase/storage/hashing.py`, has no
consumer. Building `remote.py`/`cache.py`/`local.py` means shipping a layer whose only
user is its own tests.

**2. The real v1.0 blockers are regressions in things already marked "done".**

- `pyproject.toml` declares `geocase = "geocase.cli.main:app"`, but
  `src/geocase/cli/main.py` is a one-line docstring — every install gets a console script
  that dies with `ImportError`.
- `pyproject.toml` sets `testpaths = ["tests", "examples"]`, so the bare `pytest` in the
  README quickstart **hard-fails at collection**: `examples/gdal_footprint.py` imports
  `osgeo` unguarded at module top level.
- `import geocase` exposes nothing — `src/geocase/__init__.py` is a docstring. There is
  no surface to make a 1.0 promise *about*.
- Manifest support (plan 06) is implemented and tested but **unreachable**:
  `CaseRegistry.get_registry()` never calls `from_sources`.

**3. The quality gates are far weaker than 715 tests suggests.** CI runs a hand-kept
*allowlist* that has drifted: ~300 tests never run, including all 211 of
`tests/unit/test_format_compliance.py` (plan 05's deliverable) and all of
`tests/unit/test_manifests.py` (plan 06's). Two files CI names are empty stubs. Measured,
not assumed: `ruff check` → **1043 errors** (722 tab-indentation — the repo is mixed tabs
and spaces); `mypy src` → **18 errors, "errors prevented further checking"**, meaning
`strict = true` has never type-checked a single function body.

**4. `requires-python = ">=3.9"` is a promise the project cannot currently keep.** Every
CI job runs `python:3.11` only; neither floor nor ceiling is tested.
`src/geocase/catalog/models.py` combines `from __future__ import annotations` with PEP 604
unions (`str | None`) inside pydantic model bodies, which pydantic must `eval` at
class-construction time — on 3.9 that raises `TypeError` without `eval-type-backport`. So
`import geocase` may simply fail on the advertised floor. In a release whose entire point
is a compatibility promise, this is the biggest hole.

Underneath it all is a process problem: **four competing "what's next" documents**
(`docs/plans/01`, `03`, `09`, and `docs/plans/development-plan.md` — the only one
README links) using **five sequencing vocabularies** (Phases/Steps/Workstreams/Waves/
"stages"). That already produced commit `6391e04 "stage 3 of plan 9 is done"`, which
actually contained plan 08 Step 9 work, and left plan 09 calling the implemented
`hashing.py` a stub. Plan 03 lists CLI as explicitly **not in scope for v1.0**; plan 09
reverses it without recording why.

**Intended outcome:** v1.0 as an honest compatibility promise about the pytest workflow
and a small public API — the genuinely mature parts — with storage deferred to v1.1.

### Decisions confirmed

| Question | Decision |
|---|---|
| Storage layer | **Defer to v1.1.** Discoverable remote cases, clear errors, no transport. |
| CLI | **Remove the entry point** and `cli/` stubs. Honors plan 03 and README. |
| `examples/` corpus | **Leave as-is** (repo-only, not in the wheel). Revisit post-1.0. |
| Version | **v1.0 on the narrowed scope.** |

Because `examples/` stays, lint and type gates are **scoped to `src` and `tests`** —
otherwise the 5,350-line demo corpus dominates every number and the gates mean nothing.

---

## Stage 0 — Collapse the roadmap (do this first) ✅ DONE

Every later stage edits plan statuses; doing this last means writing updates into four
documents that are about to be retired.

- **Keep one roadmap.** Recommend `docs/plans/development-plan.md` as the
  survivor — it is the only one README links and already uses one vocabulary ("Step N").
  Fold this plan's content in as later steps.
- **Archive, don't delete,** `docs/plans/01..09` → `docs/plans/archive/`, each with a
  "superseded; retained as implementation log" header. Plans 04 and 08 contain real
  history worth keeping.
- **Record the 03-vs-09 reversal in a Decision log:** v1.0 = pytest + public-API
  compatibility promise; `api/` in; `cli/` out (plan 09's reversal withdrawn); `storage/`
  deferred to v1.1, with the v1.1 gate stated as *"at least one real published archive
  with a real sha256."*
- Mark plans 04, 05, 06, 08 **Complete** (06 is still "Active" despite being fully
  shipped).

## Stage A — Make the advertised product actually work ✅ DONE

- **A1 — Remove the console script.** Delete `[project.scripts]` from `pyproject.toml`
  and delete `src/geocase/cli/` (six one-line stubs). Empty stub packages are what
  generated this confusion in the first place: plan 09's entire Workstream 4 exists
  because a stub directory implied a commitment. Same reasoning for
  `src/geocase/storage/{local,remote,cache}.py`. **Keep `storage/hashing.py`.**
- **A2 — Fix bare `pytest`.** Two independent fixes, both needed: narrow `testpaths` to
  `["tests"]`; and add `pytest.importorskip("osgeo")` in
  `examples/test_gdal_footprint.py` just above its `from gdal_footprint import ...`.
  A guard inside `examples/gdal_footprint.py` will not work — it is not a test module —
  and the `sys.path` insert must stay above the skip. This is a bug fix to make
  collection work, not the deferred `examples/` cleanup.
- **A3 — Fix the dev environment.** All 16 current failures are solely `pyarrow` missing
  from `.venv` (which is Python 3.14). `pyproject.toml` already declares it correctly
  under the `vector` extra, and `dev` pulls `all` — the venv is just stale. Recreate on a
  CI-tested Python and confirm `pytest tests -q` → 714 passed, 1 skipped.
- **A4 — Give `hashing.py` a consumer.** `scripts/generate_checksums.py` duplicates
  `sha256_file` byte-for-byte, and `hashing.py`'s docstring says it "mirrors" it. Import
  it instead. One line; makes the only real storage code reachable and covered by the
  existing `generate_checksums.py --check` CI gate.
- **A5 — Fix `docs/remote-datasets.md`.** It is structurally broken and live on the
  published site: an unterminated ` ```md ` fence near the top means **the whole page
  renders as a code block**, and it ends with a stray `.s`.
- **A6 — Fix the bundled catalog's size.** See the dedicated section below; it is large
  enough to warrant its own treatment and must land before the first PyPI upload.

## Stage A6 — The bundled catalog's size (the wheel *is* the product) ✅ DONE

The bundled data is **36 MB, and ~93% of it is accidental bloat.** Five SQLite fixtures
are 6.7 MB each — the `point`, `multipoint`, `linestring`, `multilinestring`, and
`multipolygon` `_sqlite_baseline/data.sqlite` files — and each contains **exactly one
feature**. They were written with full SpatiaLite metadata initialization: 27 tables,
including a `spatial_ref_sys` populated with 6,559 EPSG rows.

The sixth SQLite fixture proves this is avoidable and unintended:
`polygon_sqlite_baseline/geometry.sqlite` holds the same 1-feature payload in **24 KB**
with 4 tables and a 1-row `spatial_ref_sys`. The five outliers are inconsistent with
their own sibling, and with the project's stated principle that bundled fixtures stay
tiny/small while realism lives in remote scenes.

**The fix (verified empirically on a copy).** Do *not* rewrite them as plain SQLite —
that would make the `spatialite` tag and the "SQLite/SpatiaLite" descriptions false and
would drop the only real SpatiaLite driver coverage in the catalog. Instead delete the
unused SRS rows and `VACUUM`:

```sql
DELETE FROM spatial_ref_sys     WHERE srid NOT IN (SELECT srid FROM geometry_columns)
                                  AND srid NOT IN (0, -1, 4326);
DELETE FROM spatial_ref_sys_aux WHERE srid NOT IN (SELECT srid FROM geometry_columns);
VACUUM;
```

Measured on `point_sqlite_baseline/data.sqlite`: **6,844 KB → 240 KB (−96.5%)**, still a
real SpatiaLite database with its full table structure, and `geopandas.read_file()` still
returns 1 Point feature at EPSG:4326 — satisfying the case's declared `expect_crs` /
`expected_epsg: 4326` / `expected_geometry_types` assertions and the existing
`test_load_sqlite_*` tests, which assert only feature count and geometry type.

Note the bulk is split across **two** tables: `spatial_ref_sys` (6,559 EPSG rows) and
`spatial_ref_sys_aux` (760 KB). Trimming only the first leaves ~1 MB.

- Apply to all five; expected total **36 MB → ~3.7 MB**.
- Regenerate each `checksums.sha256` and re-run `generate_checksums.py --check`.
- Do this **before** the first PyPI upload — a published artifact is immutable, and
  36 MB sets a baseline that cannot be quietly walked back.
- This shrinks the *wheel*, not the *clone*. The 6.7 MB blobs stay in git history, so
  `git clone` remains large unless history is rewritten — not recommended for this.

**Root cause — the systemic fix.** There is no `scripts/generate_vector_fixtures.py`.
Raster has both a generator *and* a `generate_raster_fixtures.py --check` CI gate; vector
has neither, so its fixtures are unreproducible hand-made artifacts and nothing would
notice one growing 280×. Add the vector generator mirroring the raster one, so these five
files are regenerable rather than hand-patched.

**Guardrail — make `size_class` mean something.** All five declare `size_class: tiny`
while being 6.7 MB. `SizeClass` is a bare `Literal["tiny","small","medium","large"]` with
no byte thresholds, and `scripts/validate_catalog.py` never checks file size at all. Add
threshold enforcement (e.g. tiny ≤ 256 KB, small ≤ 5 MB) to `validate_catalog.py`, which
is already CI-gated. That turns "the metadata is lying" into a build failure and catches
the next occurrence for free.

## Stage B — Quality gates you can trust ⬜ NEXT

- **B1 — Replace the allowlist with directory runs.** `pytest tests/ -q` in CI; the whole
  suite is ~23s. Delete the three empty stub test files
  (`tests/unit/test_vector_loaders.py`, `tests/integration/test_core_vector_suite.py`,
  `tests/integration/test_remote_fetch.py`) — CI currently *names*
  `test_vector_loaders.py` and runs nothing, advertising coverage that does not exist.
  Reintroduce `test_remote_fetch.py` with v1.1. Update README's "Local equivalents",
  which reproduces the allowlist verbatim.
- **B2 — Ruff needs a normalization commit first.** 1043 errors, 722 of them W191
  tab-indentation (`src/geocase/pytest_plugin/fixtures.py`, `catalog/manifests.py`,
  `pytest_plugin/__init__.py`, `markers.py`, `scripts/validate_catalog.py`, much of
  `tests/`). Sequence as three separate commits: (1) `ruff format` — whitespace only,
  verifying identical test output before and after so it never pollutes `git blame`;
  (2) `ruff check --fix` plus hand-fixes for the residual N806/N811/E402/E501; (3) *then*
  add the CI job. Adding the gate first turns CI red on 1043 errors, and the temptation
  becomes `ignore = ["W191","E501"]`, permanently entrenching the mixed indentation.
- **B3 — Mypy: fix the config, start non-strict.** The 18 errors are all missing
  stubs/imports, so the true error count is unknown. Add `types-PyYAML` and
  `types-shapely` to the `dev` extra; add `ignore_missing_imports` overrides for
  rasterio/pyarrow/osgeo/netCDF4/geopandas; fix `python_version = "3.9"`, which currently
  makes mypy parse *pytest's own source* under 3.9 grammar and emit a bogus
  pattern-matching syntax error. Then gate **`catalog/` + `api/` only** under strict — the
  layers that define the v1.0 promise — and ratchet outward in v1.1. Do not block the
  release on repo-wide strict.
- **B4 — Python support matrix.** Bump `requires-python` to `>=3.10` (3.9 is EOL and
  likely already broken per Context #4), drop the 3.9 classifier, add 3.13, and add a CI
  matrix over floor and ceiling. If 3.9 must stay, it requires
  `eval-type-backport; python_version < "3.10"` *and* a 3.9 CI job to prove it.
- **B5 — Markers.** `slow` and `remote` are declared and used **zero** times. Drop
  `slow`. Keep `remote` and wire it: in `pytest_generate_tests`, attach
  `pytest.mark.remote` to cases whose `storage_class == "remote"` (~5 lines). That gives
  users `pytest -m "not remote"` — exactly the escape hatch Stage D creates a need for.
- **B6 — Measure coverage, don't gate it.** ~300 tests are entering CI for the first
  time; any floor picked now is arbitrary. Report non-blocking for one release, record
  the number in the CHANGELOG, and set the floor in v1.1.

## Stage C — The v1.0 surface: public API ⬜ TODO

Mostly a facade — `src/geocase/catalog/__init__.py` already exports a clean `__all__`.

- **`api/types.py`** — re-export stable types from `catalog/models.py` and `cases/`.
  **Deliberately exclude the manifest models** (plan 09 wanted them): exporting a schema
  that will be revised in v1.1 pins the wrong thing. They stay importable from
  `geocase.catalog`.
- **`api/public.py`** — `list_cases()` (reusing `selectors.select_cases`, which already
  takes the `SuiteSelection` kwargs), `get_case()`, `load_case()` (via
  `cases/factory.create_case`), `show_case()`, `list_suites()`/`get_suite()`.
  **Move `_case_roots_by_id`/`_materialize_case` out of
  `src/geocase/pytest_plugin/fixtures.py` into the API (or a shared `catalog/roots.py`)
  and have the plugin import them** — the plugin currently owns path-resolution the API
  needs, and duplicating it would create two `lru_cache`s to invalidate.
- **`src/geocase/__init__.py`** — the public surface plus `__version__` derived from
  `importlib.metadata.version("geocase")`, *not* a hardcoded literal, so it cannot drift
  from `pyproject.toml`. Document the fixture names in the module docstring; they are
  part of the promise even though they are not importable.
- **`tests/unit/test_public_api.py`** — pin `sorted(__all__)` against a literal. This is
  the compatibility promise made executable.
- Document that `list_cases()` returns `CaseMetadata` while the `geocase` *fixture*
  yields a `BaseCase`; that asymmetry will otherwise generate issues.

## Stage D — Manifests reachable and honest (no transport) ⬜ TODO

- **D1** — Wire `get_registry()` to `from_sources` with a `GEOCASE_MANIFESTS` env var.
  Read the env var **inside** `get_registry`, not at module import, or tests that
  monkeypatch it will silently no-op.
- **D2** — Close the `CaseRegistry` asymmetry (manifest ids appear in
  `list_ids`/`__contains__`/`__len__` but not `list_cases`/`__iter__`/`get`). Do **not**
  force manifest entries into `list_cases()` — `ManifestCaseEntry` is not `CaseMetadata`
  and that would be a type lie. Instead add `is_remote()`, `list_remote_ids()`,
  `get_manifest()`, `get_manifest_entry()`, and have `get()` raise a
  `RemoteCaseUnavailableError` **subclassed from `KeyError`** so existing callers keep
  working. Include `build_manifest_uri(...)` in the message so users can fetch manually.
  Read `tests/unit/test_manifests.py` first — it pins current `__len__`/`__contains__`.
- **D3** — The hidden second failure path: `fixtures.py::_case_roots_by_id` is
  `@lru_cache`d and built **only** from `case-index.yaml`, so once manifest ids resolve,
  `_materialize_case` raises `KeyError: No case root found...` — an internal-sounding
  error that defeats D2's clear one. `_materialize_case` must check `is_remote()` first,
  and `reset_registry()` must call `cache_clear()`. **D2 and D3 must land in the same
  commit.** Also decide and document that `geocase_select`/`geocase_suite` stay
  bundled-only in v1.0, emitting a warning naming the excluded remote ids.
- **D4** — Teach `scripts/validate_catalog.py` to validate `extended-manifests/` (reusing
  `load_manifest` + `from_sources`), wired into `ci/catalog-validation.yml`. Explicitly
  **allow** `sha256: "replace_me"` with a warning — gating on the placeholders would
  block the v1.1 work they exist for.
- **Out of scope:** no download, cache, unpack, or `materialize_case`.

## Stage E — Docs truth pass and release ⬜ TODO

- **Stale facts to correct** (all verified): `docs/contributing/workflow.md` says "216
  unit tests" (715) and lists manifests and `loaders/` as stubs (both implemented);
  `structure-and-planning.md` and `codebase-summary.md` say raster has "2 cases + 1 stub"
  (26); `manifests-and-storage.md` says manifest parsing is stubbed — rewrite it rather
  than flip it, since storage is now *deliberately* deferred. Correct counts: 130
  `case.yaml` (103 vector / 26 raster / 1 netcdf), 715 tests.
- **mkdocs nav** omits plans 07/08/09, `docs/_generated/raster-coverage-matrix.md`, and
  `codebase-summary.md`. After Stage 0 the plans collapse to one "Roadmap" entry; add the
  raster matrix beside the vector one (both are already CI-gated, so publishing only one
  is odd).
- **Release:** `CHANGELOG.md` (none exists), noting the CLI entry-point removal as a
  **breaking change**; version `0.1.0` → `1.0.0`; classifier `3 - Alpha` →
  `5 - Production/Stable`; README status line → 1.0.

### E4 — PyPI publishing checklist

Already in good shape: `src/geocase/py.typed` exists (so shipped types are visible to
downstream mypy), `LICENSE` is present, `readme = "README.md"` is wired, and the name
**`geocase` is available** on PyPI (verified: `/pypi/geocase/json` → 404, with
`geopandas` → 200 as a control). Remaining mechanics:

- **Verify the wheel contains the catalog.** `[tool.hatch.build.targets.wheel]` sets only
  `packages = ["src/geocase"]`. Run `python -m build` and inspect: the wheel must contain
  all 130 case directories, their payloads, and `metadata/*.yaml`. A 1.0 wheel missing
  `data/core/` would be catastrophic and is the single highest-severity release risk.
- **Configure an sdist target.** No `[tool.hatch.build.targets.sdist]` exists; confirm
  the default sdist is sane, and decide whether `examples/`, `docs/`, and
  `extended-manifests/` should ship in it.
- **Choose the auth mechanism.** Prefer PyPI **trusted publishing via GitLab CI OIDC**
  over a long-lived API token — no secret to rotate or leak. Requires a one-time
  publisher configured on PyPI against the GitLab project/ref before the first upload.
- **`twine check dist/*`** as a gate before upload; it also flags the PEP 639 duplication
  between `license = "MIT"` and the `License :: OSI Approved :: MIT License` classifier
  (harmless, but drop one).
- **TestPyPI dry run first**, then install from TestPyPI into a clean venv and run the
  Stage-A smoke check against the *installed* package, not the source tree.
- **Fix `project.urls`** — they point at `github.com/farzinashouri/geocase` while the
  project lives on GitLab, and `Documentation` points at a GitHub Pages URL. Confirm the
  docs site exists before advertising it in PyPI metadata; a 404 on the Documentation
  link is visible to every visitor.
- **Tag-triggered job.** PyPI uploads are immutable — a version number can never be
  reused, which is why Stage A6 must land first.

## Open item to decide explicitly

`src/geocase/loaders/` (146 lines) is a second, parallel load path: `cases/vector.py`,
`raster.py`, and `netcdf.py` import geopandas/rasterio/xarray **directly**, and nothing
in `src/` imports `geocase.loaders` except itself — only tests do. Plan 03 recommended
deleting it, but four test modules import `rasterio_loader.open_raster`. Recommend
**keeping it and making it the single path** (have `cases/raster.py` call it): a smaller
diff than rewriting four test modules, and it removes the duplication. This is the last
unresolved item from plan 03's Phase 4 table.

---

## Ordering

Stage 0 → A (incl. A6) → B → C → D → E, with C able to run in parallel with B.

Hard constraints: A1 before E (cannot publish a broken entry point); A6 before the first
upload (immutable artifacts); B2's normalization commit before B2's gate; B4 before E
(classifiers); C before D2 (`show_case` reports remote state); **D2 and D3 atomic**.

If the priority is a fast first upload rather than a polished one, Stages A + C + E alone
are sufficient to publish. B and D make the release *trustworthy* rather than merely
*installable*, and B is what prevents the next round of drift.

### Recommended implementation batches

Execute stage-by-stage with a verification checkpoint per batch, not bullet-by-bullet and
not all at once. Batches 1 and 2 are complete; the reasoning for the rest is unchanged.

| # | Batch | Checkpoint | Status |
|---|---|---|---|
| 1 | Stage 0 + A1–A5 | `pytest tests -q` green with no collection error; no console script | ✅ Done |
| 2 | **A6 alone** | checksums regenerate; SQLite tests pass; wheel size | ✅ Done |
| 3 | B2 (3 commits) → B1, B3, B5, B6 | CI green on directory runs; record the coverage number | ⬜ Next |
| 4 | C, then **D2+D3 atomic**, then D1/D4 | `test_public_api.py` pins `__all__`; remote-id error asserted | ⬜ |
| 5 | E + E4 | `mkdocs build`; wheel holds all 134 cases; TestPyPI dry run | ⬜ |

Why batched this way:

- **A had to come first** because it changes what "green" means. Until `testpaths` and
  the venv were fixed there was no trustworthy signal to verify anything else against.
- **A6 stayed alone** because it rewrites five binary fixtures and their checksums. Mixed
  with semantic changes, a failure would have been ambiguous.
- **B2 needs its own three commits** (`ruff format` → `ruff check --fix` → gate), as this
  plan already argues, so the whitespace pass never pollutes `git blame`.
- **D2+D3 must be one commit** — D3's `lru_cache` path defeats D2's clear error otherwise.
- **C can run in parallel with B**, but C must precede D2.

Two adjustments learned from batches 1–2:

- **Verify the plan's empirical claims before acting on them.** A6's numbers reproduced
  exactly, but its supporting argument did not survive checking, and three other figures
  in this document were wrong. Re-measure rather than trusting a stated number.
- **Do not trust B3's "18 errors" baseline.** `[tool.mypy] python_version` moved from
  `3.9` to `3.11`, which should remove the bogus pattern-matching parse error this plan
  attributes to mypy reading pytest's source under 3.9 grammar. Re-measure at the start
  of batch 3.

Note that **B4 is partly done** already: `requires-python`, classifiers, and the mypy and
ruff target versions were settled while resolving A3. What remains of B4 is the CI matrix
over floor (3.11) and ceiling (3.14).

## Verification

- **Clean install:** fresh venv → `pip install -e ".[dev]"` → `pytest` green with no
  collection error; `python -c "import geocase; print(geocase.__version__); geocase.list_cases()"`
  works; confirm no `geocase` console script is installed.
- **CI:** every test under `tests/` runs; ruff and mypy jobs pass at their scoped targets;
  the catalog-validation gates (index/checksums/fixtures plus both coverage-matrix
  git-diff gates) still pass; the new Python matrix passes on floor and ceiling.
- **API stability:** `tests/unit/test_public_api.py` pins the exported names.
- **Remote cases:** a manifest id is discoverable and raises the documented v1.1 error —
  asserted by a test checking the message text, through both `registry.get()` and the
  pytest fixture path.
- **Packaging:** the built wheel contains the full case catalog; `twine check` passes;
  a TestPyPI install smoke-tests clean.
- **Docs:** `mkdocs build` succeeds; `remote-datasets.md` renders as prose, not a code
  block; no doc still claims manifests are stubbed or that raster has 2 cases.

## Deferred to v1.1

Storage transport (`remote`/`cache`/`local`/resolver), end-to-end remote loading,
`tests/integration/test_remote_fetch.py`, `scripts/package_extended_cases.py`, repo-wide
mypy strict, a coverage floor, a CLI, and the `examples/` corpus cleanup. The v1.1
storage gate is **one real published archive with a real checksum**.
