# Ship GeoCase as an installable package

> **Status: steps 1–5 and 8 implemented (5 on 2026-08-24); steps 6–7 and 9 not started.**
> Step 5 is **done: `geofacts` is on real PyPI**, as `0.1.2` rather than the
> planned `0.1.1` — see the step for why. That clears the dependency-ordering
> blocker, so step 6 (the GeoCase TestPyPI rehearsal) is now unblocked; its own
> pending-publisher registration is still a browser step and is the user's to do.
> Step 8 (README rewrite) was taken out of order — it depends on nothing being
> published. Step 9 (plan archive, real-library validation) is untouched.

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

### 2. Fix the stale case count: 134 → 135 — **done 2026-08-23**

Mostly already fixed before this pass: `recipe/meta.yaml`, `README.md`,
`docs/dataset-catalog.md`, `docs/index.md` and `docs/contributing/releasing.md` all
read 135 already, and `scripts/validate_catalog.py:304` now gates the documented
counts against `len(get_registry())`. Two stale spots remained and were fixed:

- `.github/workflows/release.yml:50` — comment said "all 134 indexed cases";
  reworded to not name a number, since the script reads the index.
- `CHANGELOG.md` "Known numbers" (134) — left as-is: it is the historical 1.0.0
  snapshot and was correct at that release.

`docs/dataset-catalog.md:36`'s "134 are `size_class: tiny`" is **not** a stale count —
it is 134 tiny + 1 small = 135, confirmed against the registry.

The catalog grew to 135 (`geocase.list_cases()` confirms; `src/geocase/benchmark/fixtures.py:3`
already says 135) but the number is hardcoded as 134 elsewhere. **`recipe/meta.yaml:40` is a
real build-breaker** — it asserts `== 134` and would fail the conda build.

Update: `recipe/meta.yaml:40`, `README.md:5`, `CHANGELOG.md:208`,
`docs/contributing/releasing.md:59,108`, `docs/dataset-catalog.md:32`,
`.github/workflows/release.yml:50` (comment).

`scripts/verify_dist.py` reads `case-index.yaml` dynamically and needs no change — the right
pattern; prefer it over new hardcoding.

### 3. Resolve the 4.2 MB vs 2.1 MB contradiction — **done 2026-08-23, plan premise was backwards**

The plan concluded README's 4.2 MB was right because `du -sh src/geocase/data` reports
4.2 MB. That was the wrong measurement. Both numbers are real but measure different
things:

| Measurement | Value |
|---|---|
| `du -sh src/geocase/data` (apparent disk usage) | 4.2 MB |
| Real byte sum of the tree | 2.4 MB |
| Byte sum of payload files only (no `case.yaml`/`notes.md`/`checksums.sha256`) | **2.1 MB** |
| `geocase/data/**` inside the built wheel, uncompressed | 2.3 MB |

`du` is inflated by 4 KB block rounding across **572 files** in 218 directories — that
padding is ~1.8 MB and reaches no artifact. So **2.1 MB is correct** and the earlier
"correction" was right. Fixed the places still asserting 4.2 MB:

- `CHANGELOG.md` "Known numbers" and the "shrank from 36 MB" entry → 2.1 MB.
- `scripts/verify_dist.py:42` comment — said the tree is 4.2 MB and compresses ~9x;
  it is 2.1 MB and compresses ~5x. The 2 MB ceiling itself is unchanged and still has
  ~4x headroom (wheel 456 KB, sdist 272 KB).
- The CHANGELOG "Fixed" entry now records *why* the two figures differed, so this does
  not get re-reverted by the next person who runs `du`.

### 4. Truth-pass the false claims — **done 2026-08-23**

Already fixed before this pass: the "first release published to PyPI" claim (a
correction note was in place), the `project.urls` GitLab claim, the README conda hedge,
and `releasing.md:14`'s "GitLab-issued JWT" (now reads GitHub Actions).

Fixed here:

- `docs/contributing/releasing.md` — the `__version__`/`importlib.metadata` warning
  described a check `verify_dist.py` does not do. It reads `project.version` from
  `pyproject.toml` *deliberately* (see its comment at `:211-216`); the note now says so.
- `CHANGELOG.md` `## [1.0.0] — 2026-08-02` — kept the date (it is when the feature set
  was finalised) but the heading and lede now say **not yet released** outright, instead
  of leaving that to a correction blockquote below the summary line.
- `README.md:5` / `docs/index.md:9` — "Status: **1.0**" read as released; both now say
  "1.0, not yet published to PyPI — install from source for now."

**Found beyond the plan** — `docs/contributing/workflow.md` carried two more false CI
claims: it described GitLab pipeline jobs defined in `ci/catalog-validation.yml`,
`ci/core-tests.yml` and `ci/extended-tests.yml`. There is no `ci/` directory and never
was; CI is GitHub Actions. Rewrote the "CI test segmentation" section to describe the
five real jobs in `.github/workflows/ci.yml` (`tests`, `lint`, `typecheck`, `docs`,
`catalog`), and corrected the April 2026 log bullet in place.

**Gotcha for future edits:** `scripts/validate_catalog.py:304` regex-matches the literal
phrase ``N cases in `case-index.yaml` `` in `releasing.md`. Rewording that sentence to
avoid hardcoding the number breaks three tests. The gate is what keeps the number
honest, so keep the phrase and let the gate check it.

### 5. Publish `geofacts` to TestPyPI, then PyPI — **done 2026-08-24, as 0.1.2 not 0.1.1**

All four sub-steps landed. `geofacts` is on **real PyPI** as `0.1.2` (wheel 36,748 B +
sdist 79,901 B, `requires_python >=3.11`, no runtime dependencies), and on TestPyPI
alongside `0.1.0`/`0.1.1`.

1. **Added `[tool.hatch.build.targets.sdist]`.** The include list is wider than the
   obvious `/src` + `/tests`: it also carries `/scripts` and `/vendored`, because
   `tests/test_vendored.py` regenerates the single-file copy via
   `scripts/build_vendored.py` and diffs it against `vendored/geofacts.py`. Dropping
   either turns the drift gate — the thing that makes a vendored copy safe to trust —
   into a collection error exactly where it matters, the conda-forge build, which runs
   the suite from the sdist. Verified by unpacking the sdist into a clean Python 3.11
   venv: 46 tests pass and `build_vendored.py --check` reports current.
2. Pending OIDC publishers registered on both indexes (browser step, user).
3. `workflow_dispatch` → `testpypi`, then a GitHub Release → real PyPI.

**Deviation: `0.1.2`, not `0.1.1`.** The sdist section is a source change, so shipping it
under `0.1.1` would have meant force-moving an already-pushed tag. The `0.1.x` name is
cheap and nothing consumed `0.1.1` yet, so a clean bump beat a rewritten tag.

**Gotcha for the next release:** the version is hardcoded in **three** independent places
— `pyproject.toml`, `src/geofacts/__init__.py`, and the template literal inside
`scripts/build_vendored.py` (which then propagates to `vendored/geofacts.py`, so
regenerate after bumping). `build_vendored.py --check` gates the template against the
vendored copy, but **nothing gates `pyproject.toml` against `__init__.py`** — they can
silently disagree. Worth a single-source refactor or a gate test before 0.2.0.

Downstream in geocase, the floor was raised to `geofacts>=0.1.2` in `pyproject.toml:50`
and `recipe/meta.yaml:27` so the step 6 rehearsal cannot resolve a pre-sdist wheel.

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

### 8. Rewrite the README opening (highest-leverage change in this plan) — **done 2026-08-23, ahead of steps 5–7**

Done out of order: nothing here depends on a published artifact, and steps 5–7 are
blocked on browser-side registrations.

The NoData case won over the CRS-equality one — it needs no explanation and the
numbers are violent. `geotiff_nodata_small` has 2 NoData pixels (`-9999`) out of
100; `array.mean()` returns **−152.86 m** where the masked mean is **48.08 m**.
The example was executed before being written down (verification 8, run against
the local conda env rather than a clean-venv install, which is not available until
step 6): the assertion fails with exactly the output quoted in the README, and it
needs no `import geocase` — the plugin registers via `[project.entry-points.pytest11]`.

Framing landed as planned: failure first, `test_data/sample.tif` named as the honest
competitor, AI demoted to a parenthetical closing line, status/compatibility block
moved below the example. "foolproof"/"standardized" were already absent.

**Constraint to preserve:** `scripts/validate_catalog.py:300` regex-matches
``(\d+) bundled cases`` in `README.md` — the phrase lives in the status block, so the
block can move but the sentence must not be reworded. Gate re-run green (7 documented
counts checked), as is `mkdocs build --strict`.

Not touched: `docs/index.md` carries the same status block and old lede. The plan
scopes this step to `README.md`; the site homepage is a separate call.

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
| 9 files with the `geofacts` rename | commit as-is — **done** |
| `recipe/meta.yaml:40` | 134 → 135 — was already 135; no change needed |
| `.github/workflows/release.yml:50` | drop the hardcoded 134 from the comment — **done** |
| `CHANGELOG.md` | 4.2 → 2.1 MB (×2), unreleased-status lede, measurement note — **done** |
| `scripts/verify_dist.py:42` | 4.2 MB → 2.1 MB, ~9x → ~5x in the ceiling comment — **done** |
| `docs/contributing/releasing.md` | `__version__` note → `pyproject.toml` — **done** |
| `README.md:5`, `docs/index.md:9` | status block now says not-yet-published — **done** |
| `docs/contributing/workflow.md` | replace phantom GitLab `ci/*.yml` jobs with the real GH Actions jobs — **done** |
| `pyproject.toml:7` | → `1.0.0rc2` |
| `../geofacts/pyproject.toml` | add sdist target; version → `0.1.2` — **done** |
| `../geofacts/src/geofacts/__init__.py`, `scripts/build_vendored.py`, `vendored/geofacts.py` | `__version__` → `0.1.2` (three hardcoded copies) — **done** |
| `pyproject.toml:50`, `recipe/meta.yaml:27` | `geofacts` floor `>=0.1.1` → `>=0.1.2` — **done** |
| `README.md` (opening) | lead with a real edge case; demote AI framing; status block moved below it — **done** |
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
- ~~**Dependency ordering.** GeoCase cannot install anywhere until `geofacts` is on real PyPI.
  Step 5 strictly precedes step 6.~~ **Cleared 2026-08-24** — `geofacts 0.1.2` is on PyPI and
  `pip install "geofacts>=0.1.2"` resolves from the default index in a clean venv.
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
