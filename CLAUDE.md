# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

GeoCase is a pytest plugin + Python library that ships a **curated catalog of geospatial test cases** (vector / raster / NetCDF) so users can run their own geospatial code against realistic edge cases (CRS issues, dateline crossing, topology errors, NoData conventions).

Two surfaces carry a v1.0 compatibility promise and must not break casually:
1. the pytest workflow — fixtures `geocase`, `geocase_case`, `geocase_cases`, `geocase_registry`; markers `geocase_case`, `geocase_suite`, `geocase_select`, `remote`;
2. `import geocase` — everything in `src/geocase/__init__.py`'s `__all__`.

## Environments

Two are maintained deliberately and are **not** interchangeable (see [docs/contributing/workflow.md](docs/contributing/workflow.md)):

- **conda `geocase` (primary, Python 3.14)** — `conda env create -f environment.yml && conda activate geocase`. Only environment with GDAL/`osgeo` bindings. Required for anything touching `examples/` or fixture generation; without `osgeo` the interview-question example modules `importorskip` and silently drop ~1200 tests.
- **`.venv` (CI mirror, Python 3.11)** — `python3.11 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"`. Use to reproduce a CI failure at the supported floor.

## Commands

```bash
pytest tests -q                      # the suite (testpaths = tests, so examples/ needs naming)
pytest tests/unit/test_x.py::test_y  # single test
pytest examples -q                   # demo corpus; needs the conda env
ruff format --check src tests && ruff check src tests   # lint gate (ruff pinned 0.15.7)
mypy src                             # typecheck gate (src only)
mkdocs build --strict                # docs gate; broken internal links fail
```

Catalog gates (the `catalog` CI job; needs `osgeo`, so run under conda). All are `--check` variants of generators — run without `--check` to regenerate, then commit:

```bash
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
python scripts/validate_case_content.py   # declared assertions vs. real bytes
python scripts/generate_raster_fixtures.py --check
python scripts/generate_vector_fixtures.py --check
python scripts/generate_checksums.py --check
python scripts/generate_catalog_pages.py --check
python scripts/generate_raster_previews.py --check
python scripts/generate_vector_coverage_matrix.py --output docs/_generated/vector-coverage-matrix.md
python scripts/generate_raster_coverage_matrix.py --output docs/_generated/raster-coverage-matrix.md
```

Benchmark runner: `python -m geocase.benchmark grade ...` (see `src/geocase/benchmark/cli.py`).

## Architecture

Core data flow — keep this mental model:

`case.yaml → Pydantic model → registry → selectors/suites → case object → .load() → pytest`

- `metadata/case-index.yaml` lists every bundled case's `case.yaml` path; `metadata/suite-index.yaml` + `catalog/suites/*.yaml` define named suites. These indices are **generated** — edit cases, then regenerate.
- `catalog/` — `loader.py` (YAML→model), `models.py` (Pydantic `CaseMetadata`), `registry.py` (in-memory lookup, cached; `reset_registry()` clears), `selectors.py` (filtering), `suites.py`, `manifests.py` (external/remote catalogs layered in via `GEOCASE_MANIFESTS`; ids become *known* without being materialized — missing data raises `RemoteCaseUnavailableError`).
- `catalog/content.py` — the **content gate**: compares each case's declared assertions against its actual pixels/features, delegating to `assertions/` so the gate and the user-facing checks are the same code. `validate_catalog.py` opens no data file (schema/existence/size only, so it runs anywhere); `validate_case_content.py` opens it and therefore runs only in the `catalog` CI job.
- `catalog/roots.py` — maps case id → on-disk directory and builds the runtime case. Deliberately **not** re-exported from `geocase.catalog`: it is the one catalog module importing `geocase.cases`, and `cases.base` imports `catalog.models`, so eager re-export makes the packages circular. Import it directly.
- `cases/` — `BaseCase` subclasses (`vector`, `raster`, `netcdf`) built by `factory.py`; `loaders/` holds the optional-dependency readers (geopandas / rasterio / xarray).
- `api/public.py` + `api/types.py` — the pinned public surface re-exported from `geocase/__init__.py`. `list_cases`/`get_case` return `CaseMetadata`; `load_case` and the fixtures return `BaseCase`.
- `assertions/` — reusable checks (crs, footprint, geometry, topology, raster, format compliance) users call in tests.
- `raster/` — a dependency-free raster primitive (`primitive.py`, public `.array`/`.transform`/`.crs_wkt`) plus `presets/` (sentinel1/2); `_writer.py` needs the `write` extra.
- `benchmark/` — separate LLM-benchmark subsystem (tasks, prompts, runners, grading). Not part of the library's compatibility promise.
- Case data lives in `src/geocase/data/core/{vector,raster,netcdf}/<case_id>/` as `case.yaml` + payload + `checksums.sha256` + `notes.md`.

`geofacts` (formerly `geospatial-spec`) is a hard dependency and the dependency is strictly one-directional: it has zero dependencies, permanently, and must never import from geocase.

## Conventions that bite

- **Generated artifacts are gated.** `docs/_generated/*`, per-case catalog pages, checksums, and both coverage matrices are compared against a fresh regeneration in CI. Changing a case id, CRS, dtype, or nodata value means regenerating and committing.
- **Never reformat benchmark artifacts.** `tests/benchmark/agent_baseline/generated` and `results/runs` are excluded from ruff: they must stay byte-identical because their `module_sha256` is recorded provenance.
- mypy strictness is per-module: `geocase.catalog.*` and `geocase.api.*` are strict; the rest ratchets in v1.1. `tests/` is not typechecked.
- Adding a case: see [docs/adding-a-case.md](docs/adding-a-case.md) — metadata-first, then `build_case_index.py`, then validate.
- Plans and roadmap live in [docs/plans/](docs/plans/); `development-plan.md` is authoritative on scope.

## Working rules (non-negotiable)

- **Never commit or push.** Do not run `git commit`, `git push`, or merge a PR. Leave the work in the working tree, say what changed, and let the user commit. (Enforced by a PreToolUse deny hook in `.claude/settings.json`.)
- **Config goes in `.claude/settings.json`,** not `settings.local.json`. Permissions, hooks, and env belong in the committed project file; `settings.local.json` holds only personal overrides.
- **Deletion always asks.** `rm`, `rmdir`, `git clean`, and `find -delete` require explicit user confirmation, even in auto mode.
- **TDD, always.** In both plans and implementation: write the failing unit test first, watch it fail, then write the code that makes it pass. A plan phase that ships code without a preceding test is malformed.
- **Every written plan becomes a doc in [docs/plans/](docs/plans/).** Never leave a plan in the chat only. Use the existing convention: `NN-kebab-title.md` with the next free number, a `> **Status: proposed YYYY-MM-DD.**` blockquote under the H1, `## Phase N` / `### N.M` structure, and a new row in [docs/plans/index.md](docs/plans/index.md). One scoped deliverable per file — `development-plan.md` stays the only document that says "what's next".
- **Mark progress in the plan doc as you implement it.** Completing a phase or step means updating that plan file in the same change: flip the `Status:` header (`proposed` → `implemented YYYY-MM-DD`, or note the partial — "Phases 1–3 implemented; Phase 4 blocked on ..."), mark the finished `### N.M` sections done, and record anything that turned out differently from the plan. Update the plan's row in `index.md` too. A plan doc that still reads "proposed" after the code landed is a bug.
- **Docs follow code, same change.** Any code change updates the affected docs in the same pass — `docs/`, docstrings, `CLAUDE.md`, and the generated artifacts (regenerate, don't hand-edit `docs/_generated/*`).
- **Be concise.** Answers roughly half your usual length: state the result and what it means, skip the recap and the option survey.
