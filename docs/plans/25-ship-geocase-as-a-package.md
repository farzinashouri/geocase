# Ship GeoCase as an installable package

## Context

GeoCase is complete as a library — 1701 tests pass, 135 curated cases, a 27-name pinned
public API, and release machinery (`scripts/verify_dist.py`, `.github/workflows/release.yml`,
`docs/contributing/releasing.md`) already written by Plan 11. What has never happened is the
upload: nothing is on any package index, so the value proposition — a lightweight, immutable,
offline-reliable catalog of spatial failures that CI can depend on — is currently unreachable
by `pip install`.

Recent work drifted the repo away from that shippable state. This plan closes the gap and gets
a verified artifact onto TestPyPI, leaving the real PyPI `1.0.0` name unspent until the
rehearsal proves the pipeline end-to-end.

**The blocking discovery:** `geofacts` (a *hard runtime dependency*, `pyproject.toml:38`) is
**not on PyPI** — it resolves only from a sibling checkout at `../geofacts`. Publishing GeoCase
before it means `pip install geocase` fails at install time for every user. This forces a
two-package release in a strict order. `geofacts` itself is ready: clean tree, tagged `v0.1.1`,
zero dependencies, 46 tests passing, and a `publish.yml` that already defaults to TestPyPI.

Decisions taken: **TestPyPI dry run first**; **conda-forge deferred** to a follow-up (it is
gated on the published sdist's sha256 regardless).

**Scope note added after discussion.** Packaging is necessary but is not what determines whether
this gets used. The bottleneck is discovery, not quality: the package is better than its odds,
and nobody searches for a category they don't know exists. So this plan also does the two cheap
things that move adoption more than any release chore — a README opening that shows a real edge
case in ten seconds (§8), and a concrete outreach step to validate against real libraries (§9).
`geofacts` stays a separate package: `pip install geocase` already pulls it transitively, so
users never install two things. That split is a bet on it having a life of its own; if it has no
external users in ~6 months, vendor it into `geocase/_facts/` and retire the package.

## Plan

### 1. Commit the `geofacts` rename in geocase

The working tree holds a finished, mechanical rename (`geospatial_spec` → `geofacts`) across 9
files. The suite passes with it. Commit as-is — no code changes needed.

Remaining stale references are **docs/plans only** and are historical records, so leave them:
`docs/plans/{19,20,21,22}.md`, `docs/plans/index.md`, `docs/evidence/.../TEMPLATE.md`.

### 2. Fix the stale case count: 134 → 135

The catalog grew to 135 (`geocase.list_cases()` confirms; `src/geocase/benchmark/fixtures.py:3`
already says 135) but the number is hardcoded as 134 elsewhere. **`recipe/meta.yaml:40` is a
real build-breaker** — it asserts `== 134` and would fail the conda build.

Update: `recipe/meta.yaml:40`, `README.md:5`, `CHANGELOG.md:208`,
`docs/contributing/releasing.md:59,108`, `docs/dataset-catalog.md:32`,
`.github/workflows/release.yml:50` (comment).

`scripts/verify_dist.py` reads `case-index.yaml` dynamically and needs no change — the right
pattern; prefer it over new hardcoding.

### 3. Resolve the 4.2 MB vs 2.1 MB contradiction

`README.md:5` says 4.2 MB; `docs/dataset-catalog.md:31` and a CHANGELOG "Fixed" entry claim the
real figure is 2.1 MB. Measured `du -sh src/geocase/data` = **4.2 MB**, so README is correct and
the "correction" to 2.1 MB is itself wrong. Fix the two places asserting 2.1 MB.

Note: the 2 MB artifact ceiling in `verify_dist.py:47-50` is **not** in conflict — the data
compresses ~9x (measured wheel 456 KB, sdist 274 KB). Leave it.

### 4. Truth-pass the false claims

- `CHANGELOG.md:116` — "the first release published to PyPI" is false today. Reword to
  present tense / move under Unreleased until the upload lands.
- `CHANGELOG.md:114` — `## [1.0.0] — 2026-08-02` is a past date for an unreleased version.
  Correct at real release time.
- `CHANGELOG.md:170` — "`project.urls` now point at GitLab" is false; they point at GitHub
  (`pyproject.toml:72-77`), matching `origin`. Fix.
- `README.md:31` — the unhedged `conda install -c conda-forge geocase` has no feedstock. Hedge
  it the way the pip line at `README.md:22` already is.
- `docs/contributing/releasing.md:14` — says "GitLab-issued JWT"; the repo is GitHub Actions.
  Also `:66-71` describes a `__version__`/`importlib.metadata` check that `verify_dist.py` no
  longer does (it reads `pyproject.toml`). Fix both.

### 5. Publish `geofacts` 0.1.1 to TestPyPI, then PyPI

In `/Users/farzinashouri/projects/GeoCase/geofacts` (separate repo):

1. Add a `[tool.hatch.build.targets.sdist]` section — there is none, and an sdist is needed for
   conda-forge later and is good practice regardless.
2. Register pending OIDC publishers on test.pypi.org and pypi.org for repo
   `farzinashouri/geofacts`, workflow `publish.yml`, environments `testpypi` / `pypi`
   (this is a **browser step, yours**).
3. `workflow_dispatch` → `testpypi`, verify a clean-venv install.
4. Publish a GitHub Release on `v0.1.1` → uploads to real PyPI.

`geofacts` goes to **real** PyPI in this pass — GeoCase's TestPyPI rehearsal must resolve it,
and TestPyPI is not a reliable dependency source. Its `0.1.x` name is cheap; GeoCase's `1.0.0`
is the one worth protecting.

### 6. Rehearse GeoCase on TestPyPI

1. Bump `pyproject.toml:7` to `1.0.0rc2` (`rc1` is already tagged and burned).
2. Local gate first, per `releasing.md:45-76`:
   `rm -rf dist/ && python -m build && python scripts/verify_dist.py dist/ --expected-version 1.0.0rc2 && twine check dist/*`
   The stale `dist/` from Aug 6 must be cleared — it predates `tests/raster/` and
   `tests/benchmark/`, which is why it appears to ship a truncated 21-file suite.
   Confirm the rebuilt sdist carries all 41 test files.
3. Register the GeoCase pending publishers (browser, yours), same shape as step 5.
4. Tag `v1.0.0rc2`, push; approve the `publish-testpypi` environment.
5. Verify in a clean venv:
   `pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ geocase`
   then assert `len(geocase.__all__) == 27`, `len(geocase.list_cases()) == 135`,
   `load_case(...)` materializes a bundled case, and `pytest --collect-only` in a scratch dir
   shows the plugin auto-registered via `[project.entry-points.pytest11]`.

### 7. Stop the release here

Real-PyPI `1.0.0` and the conda-forge staged-recipes PR are the follow-up, once the rehearsal
is green. Do not cut `v1.0.0` in this pass.

### 8. Rewrite the README opening (highest-leverage change in this plan)

Currently the first thing a reader sees is a compatibility promise and a version status block —
information that matters to *existing* users and means nothing to a newcomer. Nothing shows the
value in ten seconds.

Replace the opening with a concrete edge case that looks trivial and isn't: a short before/after
where plausible-looking geospatial code silently returns a wrong answer, and a GeoCase case
catches it. Best candidates from the existing catalog — pick whichever is most visceral:
a NoData convention that silently skews a mean, or a CRS that compares unequal while being the
same CRS (`tests/raster/test_axes.py:89` already demonstrates the `4326` vs `"EPSG:4326"` trap).

Framing changes, per discussion:

- Lead with the failure, not the philosophy. The honest competitor is the hand-picked
  `test_data/sample.tif` and one-off `numpy` arrays teams already improvise — a far more
  familiar pain than AI generation, and an easier case to win.
- Demote the AI argument to a closing line ("your assistant can lean on this instead of
  inventing it"). It's largely true, but it dates the pitch and picks an unnecessary fight.
- Cut "foolproof" and "standardized". Nothing with 135 cases is foolproof, and a standard is
  conferred by a field, not claimed on day one. Overclaiming undercuts what is solidly true.
- Move the status/compatibility block below the example.

### 9. Tidy the plans, and validate against a real library

**Archive dead plans.** `docs/plans/` holds 24 plans across several abandoned directions.
`docs/plans/archive/` already exists — move the superseded ones there so the active set reflects
reality. This is the entirety of the "repo is messy" problem: `src/geocase/` is coherent and
well-tested, and none of the mess is visible on the package page. Explicitly **not** starting a
fresh repo — that would forfeit git history and the benchmark artifacts' recorded provenance to
solve a problem a file move solves.

**Then the step that actually matters for adoption.** Validate the catalog against real code.
One "we found a real bug with this" from a known maintainer is worth more than a year of polish;
finding nothing is also a real result, and much cheaper to learn now than after a 1.0 announcement.

*Do not target GDAL/GEOS/shapely/rasterio themselves.* They are decades old, heavily fuzzed, and
carry their own edge-case corpora. A mismatch there is more likely to mean the GeoCase case
encodes a wrong expectation than that GEOS has a bug. Target the layer that **composes** those
primitives, which is where these bugs actually live and where maintainers will read an issue.

Matched to what the catalog actually holds — 104/135 vector, 60 `cross_format_canonical`, 16
formats, but only 4 `nodata` and 4 `dtype` cases — the strength is **format round-tripping and
CRS/dateline handling**, so favour I/O and tiling layers over raster-radiometry ones:

| Target | Why it fits |
|---|---|
| `pyogrio` | The vector I/O layer under modern geopandas. 16 formats × round-trip is exactly its contract. Best single fit. |
| `rio-tiler` / `titiler` | Tiling composes reprojection + nodata; dateline and polar cases bite here. |
| `stackstac`, `odc-stac` | Young, actively developed, CRS/axis-order assumptions throughout. |
| `geocube`, `rioxarray` | Vector→raster and CRS round-tripping; `rioxarray` is the more mature of the two. |
| `lonboard`, `geoarrow-python` | New Arrow/GeoArrow stack — the catalog already ships GeoArrow/Feather/Parquet cases. |
| `fiona`, `pyproj` | Older and harder targets; use only for the retrospective check below. |

**Cheaper first move — the retrospective check, no outreach required.** Before contacting anyone,
mine closed NoData / dateline / axis-order / CRS-equality issues from these projects' git history
and ask whether the catalog *would have caught them*. It is fast, needs nobody's cooperation, and
directly answers "does this cover what actually breaks in the wild." A no tells you which cases
are academic — the single most useful thing to learn before announcing 1.0. Do this first; only
then run the catalog live against the top one or two targets.

## Files

| File | Change |
|---|---|
| 9 files with the `geofacts` rename | commit as-is |
| `recipe/meta.yaml:40` | 134 → 135 (**build-breaker**) |
| `README.md`, `CHANGELOG.md`, `docs/dataset-catalog.md`, `docs/contributing/releasing.md` | case count, MB figure, truth pass |
| `pyproject.toml:7` | → `1.0.0rc2` |
| `../geofacts/pyproject.toml` | add sdist target |
| `README.md` (opening) | lead with a real edge case; demote AI framing; cut "foolproof"/"standardized" |
| `docs/plans/*` → `docs/plans/archive/` | move superseded plans |

## Verification

1. `pytest tests -q` → 1701 passed (baseline established).
2. `ruff format --check src tests && ruff check src tests && mypy src`.
3. Catalog gates under conda `geocase` env: `build_case_index.py --check`,
   `validate_catalog.py`, `generate_checksums.py --check`, `generate_catalog_pages.py --check`.
4. `mkdocs build --strict` — docs edits must not break internal links.
5. `python scripts/verify_dist.py dist/ --expected-version 1.0.0rc2` on freshly built artifacts.
6. Clean-venv install from TestPyPI passes the four assertions in step 6.5.
7. `python -c "import geofacts"` resolves from PyPI, not `../geofacts`, in that clean venv.
8. The README's new opening example is **executed**, not just written — copy-paste it into a
   scratch file against the clean-venv install and confirm it fails/passes as claimed. A broken
   headline example is worse than none.
9. `mkdocs build --strict` again after the plan archive move — relocating files breaks links.

## Risks

- **PyPI immutability.** Why `1.0.0` is not spent here. The rc2 rehearsal is the whole point.
- **Dependency ordering.** GeoCase cannot install anywhere until `geofacts` is on real PyPI.
  Step 5 strictly precedes step 6.
- **OIDC misconfiguration** surfaces as a 403 *after* the tag is cut. TestPyPI runs the
  identical job shape, so it catches this first — for both packages.
- **Browser steps are yours.** Both pending-publisher registrations need your PyPI account.
- **Packaging is not the bottleneck.** The realistic odds of sustained adoption are modest
  (~15-25%), and they are set by discovery, not by release mechanics. §8 and §9 are the parts of
  this plan with real leverage; treating the upload as the finish line is the main risk to
  guard against.
- **§9 may return bad news.** Running the catalog against a real library might catch nothing.
  That is a useful result — it says which cases are academic — and it is much cheaper to learn
  before a 1.0 announcement than after.
