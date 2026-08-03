# Release GeoCase 1.0.0 to PyPI, then conda-forge

## Context

`docs/contributing/execution-order.md` reports Batches 1–5 complete — but only **"to the
upload boundary."** That phrasing is accurate: everything the library *does* is
implemented and gated (780 tests, ruff/mypy/docs/catalog gates green, 134 cases, 4.2 MB
bundled data, 27-name public API pinned). What does **not** exist is the packaging and
distribution layer:

- No sdist target — `pyproject.toml:66` configures only `[tool.hatch.build.targets.wheel]`.
  conda-forge builds from the sdist, so without this there is nothing to package.
- No build/publish CI. `.gitlab-ci.yml` has stages `test` and `secret-detection` only;
  no job ever runs `python -m build`, `twine check`, or an upload.
- No verification that the built wheel actually contains `src/geocase/data/**` — the
  release strategy calls this "the single highest-severity release risk," because
  `packages = ["src/geocase"]` shipping without data would produce an installable but
  useless package, and **PyPI artifacts are immutable**.
- No git tags at all, so no tag-triggered release trigger exists.
- No conda recipe anywhere.
- `CHANGELOG.md` already claims 1.0.0 was "published to PyPI" as of 2026-08-02.

Intended outcome: `pip install geocase` and `conda install -c conda-forge geocase` both
work, published from a tag via GitLab CI OIDC trusted publishing (no long-lived token).

**Scope note:** the ~226 staged Batch-5 changes are yours to commit; this plan assumes
they are committed on `main` before the release stage runs. Nothing below touches them.

## Plan

### 1. sdist target + package-data guarantee — `pyproject.toml`

Add next to the existing wheel target (line 66):

```toml
[tool.hatch.build.targets.sdist]
include = ["src/geocase", "tests", "conftest.py", "README.md", "LICENSE", "CHANGELOG.md", "pyproject.toml"]
```

Including `tests/` matters: conda-forge's recipe test section can then run the suite
against the installed package. Hatchling includes non-`.py` files under `packages` by
default, so the wheel needs no change — but that default must be *proven*, not assumed
(next step). Also confirm `__pycache__` is excluded (it is not currently named anywhere;
hatchling's VCS-aware default excludes it, verify in the artifact check).

### 2. Artifact verification script — `scripts/verify_dist.py`

New script, in the style of the existing `--check` validators in `scripts/`
(`validate_catalog.py`, `generate_checksums.py`). Given `dist/`, it must fail loudly on:

- Wheel does not contain every case data directory. Cross-check the wheel's
  `geocase/data/**` entries against the case ids in `case-index.yaml` — reuse the same
  index loader `scripts/validate_catalog.py` uses rather than re-globbing.
- sdist missing `src/geocase/data` or `tests`.
- Wheel or sdist contains `__pycache__`, `.pyc`, or `.DS_Store`.
- Wheel size regression: hard-fail above a ceiling (~8 MB; measured wheel is 458 KB
  plus data — record the real number when first built and set the ceiling from it, per
  the "re-measure, do not inherit" rule the batches established).
- Version in the artifact filenames equals `geocase.__version__` equals the tag.

This is the gate that answers the highest-severity risk, and it is the reason to build
locally before ever touching PyPI.

### 3. Release CI — `ci/release.yml`, included from `.gitlab-ci.yml`

Add a `release` stage after `test`. Two jobs, both `rules: - if: $CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/`:

- **`build_dist`** — `python -m build` (sdist + wheel), then `python scripts/verify_dist.py dist/`,
  then `twine check dist/*`. Publishes `dist/` as an artifact. Mirror the structure of
  `ci/lint.yml`: pinned tool versions, explicit `before_script` pip install.
- **`publish_pypi`** — `needs: [build_dist]`, `when: manual` for the 1.0.0 upload.
  Uses GitLab OIDC: request an `id_tokens` JWT with `aud: pypi`, exchange it at
  `https://pypi.org/_/oidc/mint-token` for a short-lived API token, then
  `twine upload dist/*`. No `TWINE_PASSWORD` variable is ever stored.

Also add a **TestPyPI variant** (`publish_testpypi`, manual, `aud: testpypi`,
`--repository-url https://test.pypi.org/legacy/`) so the dry run goes through the same
code path as the real upload rather than a separate hand-run command.

### 4. One-time PyPI configuration (you, in the browser)

Documented in the new `docs/contributing/releasing.md`:

- On **test.pypi.org** and **pypi.org** → *Publishing* → add a **pending GitLab publisher**
  for project `geocase`: namespace `fashouri`, project `geocase`, top-level pipeline file
  `.gitlab-ci.yml`, environment left blank (or set, and matched in the job).
- Pending publishers work before the project exists, which is exactly the 1.0.0 case.

### 5. Release sequence

1. Commit the staged Batch-5 work; merge `raster_coverage` → `main`; CI green.
2. `git tag -a v1.0.0 -m "GeoCase 1.0.0"` — but **first** run the tag against TestPyPI
   using a throwaway tag (`v1.0.0rc1`, with `version = "1.0.0rc1"`) so the immutable
   `1.0.0` name on real PyPI is never spent on a dry run.
3. Install from TestPyPI into a clean venv; assert `import geocase`, the 27-name
   `__all__`, `materialize_case` on a bundled case, and that the pytest plugin registers.
4. Bump back to `1.0.0`, tag, run `publish_pypi` manually.
5. Verify `pip install geocase` in a clean venv; confirm the sdist is present on the
   project page (conda-forge needs it).

### 6. conda-forge — `recipe/meta.yaml` + submission checklist

Prepared now, **submitted after** step 5 (conda-forge builds from the PyPI sdist and needs
its sha256). Recipe outline:

- `source: url: .../geocase-1.0.0.tar.gz`, `sha256: <from the published sdist>`.
- `build: noarch: python`, `script: {{ PYTHON }} -m pip install . -vv`, `number: 0`.
- `requirements`: host `python >=3.11`, `hatchling`, `pip`; run `python >=3.11`,
  `pydantic >=2.0`, `pyyaml >=6.0`. Keep the extras **out** of `run` — geopandas/rasterio
  are optional in `pyproject.toml` and pulling GDAL into the base package would make it
  far heavier than the PyPI equivalent.
- `test`: `imports: geocase`, plus `pytest tests -q -m "not remote"` if the sdist's
  `tests/` prove runnable without the optional deps; otherwise imports only.
- `about`: MIT, GitLab URLs (matching the corrected `project.urls`), `doc_url` the
  GitHub Pages docs.
- `extra: recipe-maintainers: [fashouri]`.

Submission: fork `conda-forge/staged-recipes`, add `recipes/geocase/meta.yaml`, open a PR,
respond to the linter bot. Document this in `releasing.md` — including that once merged,
the feedstock's autotick bot handles later versions, so subsequent releases only need the
PyPI upload.

### 7. Documentation truth pass

- `CHANGELOG.md` — leave the 1.0.0 entry, but only after the upload actually happens does
  its "published to PyPI" line become true. If the upload slips past 2026-08-02, correct
  the date rather than leaving a false one.
- `docs/contributing/execution-order.md` — Batch 5 row moves from "Done to the upload
  boundary" to done, and the Status block gains the release facts once measured.
- `docs/contributing/development-plan.md:421-425` — strike through the PyPI checklist
  items as each lands.
- `README.md` — add the conda install line alongside pip.

## Files

| File | Change |
|---|---|
| `pyproject.toml` | add `[tool.hatch.build.targets.sdist]` |
| `scripts/verify_dist.py` | **new** — artifact gate |
| `ci/release.yml` | **new** — `build_dist`, `publish_testpypi`, `publish_pypi` |
| `.gitlab-ci.yml` | add `release` stage + include |
| `docs/contributing/releasing.md` | **new** — the runbook, incl. conda-forge |
| `recipe/meta.yaml` | **new** — conda-forge recipe (sha256 filled post-upload) |
| `README.md`, `CHANGELOG.md`, `docs/contributing/{execution-order,development-plan}.md` | truth pass |

## Verification

1. `python -m build && python scripts/verify_dist.py dist/ && twine check dist/*` locally —
   must pass before any CI work is trusted.
2. `unzip -l dist/*.whl | grep -c 'geocase/data/'` — compare against the 134-case index.
3. Clean venv: `pip install dist/*.whl`, then `python -c "import geocase; print(len(geocase.__all__))"` → 27,
   and `pytest --collect-only` in a scratch dir shows the plugin registered.
4. Full pipeline green on the rc tag, TestPyPI install verified, before the real tag.
5. Post-upload: clean venv `pip install geocase==1.0.0`; PyPI page lists both wheel and sdist.
6. conda: `conda build recipe/` locally (or rely on the staged-recipes CI) before opening the PR.

## Risks

- **Immutability.** Steps 2 and 5 exist entirely to make sure the first upload is right.
  The rc-tag dry run is not optional.
- **OIDC misconfiguration** fails at upload time with a 403, after the tag is cut. The
  TestPyPI run through the same job shape catches this first.
- **conda-forge is gated on PyPI** — the recipe cannot be finished (no sha256) until the
  sdist is live. That ordering is inherent, not a choice.
