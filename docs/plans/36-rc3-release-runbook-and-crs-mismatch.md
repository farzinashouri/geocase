# Plan 36 — The `1.0.0rc3` Release Runbook and the `crs_mismatch` Gap

> **Status: Phase 1.1 done 2026-08-30 (the rest of Phase 1 is the user's);
> Phase 2 implemented 2026-08-30.** Two deliverables that share a deadline: the
> executable steps that get `1.0.0rc3` onto TestPyPI, and the one catalog gap
> that should close before the immutable `1.0.0` is spent. Phase 1 is a runbook
> rather than a build — most of its steps are the user's, and several cannot be
> automated at all. Phase 2 is a real build and carries the full gated-artifact
> chain.
>
> **Phase 2 outcome.** `crs_mismatch_overlay_pair` ships; the catalog is
> **154 cases**. Two things turned out differently from the plan. The count
> gate fired in **seven files** rather than the twelve *patterns* §2.4
> predicted — the twelve patterns collapse to seven files, and the error
> message is per-file, so the fix was seven edits. And the case needed no
> change to `generate_vector_fixtures.py`: that generator only builds cases
> declaring `params.canonical_source_case_id`, so like its neighbour
> `utm_zone_33n_to_32n_pair` this one is hand-authored and gated by checksum
> rather than regenerated. The naive-overlay error came out at **3359 km**;
> the case declares a 3000 km floor so the assertion is not brittle.

## Context

`1.0.0rc1` is on PyPI. `1.0.0rc2` was rehearsed on TestPyPI and installs clean;
it paid for itself by catching a `twine`/`hatchling` metadata-version skew that
would otherwise have hit the immutable real-PyPI run.

Since that rehearsal the corpus grew. [Plan 28](28-validate-geocase.md) Phase 3
added three ~10,000-feature vector cases and took the bundled payload
**2.1 MB → 5.1 MB** and the wheel **456 KB → 1.25 MB**, against
`verify_dist.py`'s 2 MB ceiling. A 2.7× artifact-size change has never been
through the release pipeline. PyPI artifacts are immutable, so the rehearsal
exists precisely to absorb that class of risk: **cut `1.0.0rc3`, not `1.0.0`.**

**Measured in this tree at `1.0.0rc3` (2026-08-30), not assumed:**

| Gate | Result |
|---|---|
| `pytest tests -q` (conda, 3.14) | 1972 passed, 37 skipped |
| `ruff format --check` / `ruff check` (`src tests`) | clean |
| `mypy src` | no issues, 100 source files |
| `build_case_index.py --check`, `validate_catalog.py`, `generate_catalog_pages.py --check`, `generate_checksums.py --check` | all green |
| `mkdocs build --strict` | green |
| `python -m build` + `verify_dist.py --expected-version v1.0.0rc3` | **passed** — wheel 1251 KB, sdist 1003 KB, 153/153 indexed cases present |

The artifact gate passing at the new size is the finding that de-risks this
release. The 3.11 leg — the supported floor, and what CI runs — has **not** been
verified locally; that is what the pull request is for.

### The version bump lands on `validation`, deliberately

`pyproject.toml` is bumped on the feature branch rather than on `main` after the
merge, so the pull request carries it: CI then verifies the built artifact
against the same `pyproject.toml` the reviewer is reading, and `main` is
tag-ready the moment it merges. `verify_dist.py` parses `project.version` out of
`pyproject.toml` — not `geocase.__version__`, which resolves through
`importlib.metadata` and would report whatever is installed.

Three files carry the number. `docs/contributing/pypi-publishing-practices.md`
also mentions `1.0.0rc2` and is **left alone**: those are historical narrative
about what that release taught, not live pins.

---

## Phase 1 — The `1.0.0rc3` runbook — **the version bump is done; the rest is the user's**

### 1.1 Bump the version — **done 2026-08-30**

- `pyproject.toml:12` — `1.0.0rc2` → `1.0.0rc3`.
- `README.md:46` and `docs/index.md:9` — the status blocks name `1.0.0rc3` as
  the in-repo candidate.

⚠️ **`scripts/validate_catalog.py` regex-matches `(\d+) bundled cases` in
`README.md`.** The status block may move, but that sentence must not be
reworded. Re-run green after the edit.

### 1.2 Land the branch and open the pull request

167 files are uncommitted: [Plan 35](35-compare-page-map-interaction-and-downloads.md)'s
work (153 regenerated case pages with linked Files sections, `catalog.css`,
`generate_catalog_pages.py`, `catalog-compare.js` tests) plus this version bump.

```bash
git add -A
git commit -m "Plan 35 compare-page fixes; bump to 1.0.0rc3"
git push -u origin validation

gh pr create --base main --head validation \
  --title "Plan 35: compare page fixes + 1.0.0rc3" \
  --body "Plan 35 (implemented 2026-08-30) plus the version bump to 1.0.0rc3."
```

### 1.3 Let CI confirm the floor, then merge

```bash
gh pr checks --watch     # catalog, tests 3.11 + 3.14, lint, typecheck, docs
gh pr merge --squash
```

**Do not skip the watch.** Local verification ran on conda/3.14; 3.11 is the
supported floor and the `.venv` CI mirror exists for exactly this reason. A
floor failure is cheap before the tag and expensive after it.

Merging to `main` also fires `pages.yml`, so the docs site deploys here — no
separate action, provided Pages is enabled (§1.6).

### 1.4 Tag from `main`

Tags are cut from `main`; the tag is what records which commit an immutable
release was built from.

```bash
git checkout main && git pull
git tag -a v1.0.0rc3 -m "GeoCase 1.0.0rc3"
git push origin v1.0.0rc3
```

`release.yml`'s tag regex matches both `v1.0.0` and `v1.0.0rc3`. Pushing the tag
runs `build` → `verify_dist.py` → `twine check` automatically.

### 1.5 Approve the upload — **`testpypi`, not `pypi`**

Both publish jobs are gated on a GitHub Environment, so the run **pauses** and
waits. Actions tab → the tag's run → approve **`testpypi`**.

That the upload is not automatic is a design decision, not a gap: cutting a tag
and performing an irreversible upload should not be the same action. Keep it.

Then verify in a clean environment:

```bash
python -m venv /tmp/gc && . /tmp/gc/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ geocase==1.0.0rc3
python -c "import geocase; print(geocase.__version__, len(geocase.__all__))"   # 1.0.0rc3 27
python -c "import geocase; print(len(geocase.list_cases()))"                   # 153
```

`--extra-index-url` is **required**: it is how `geofacts>=0.1.2` resolves from
real PyPI. TestPyPI does not carry it.

### 1.6 Browser steps that cannot be scripted

| Where | What | Gates |
|---|---|---|
| pypi.org → Publishing → Add a pending publisher | project `geocase`, owner `farzinashouri`, repo `geocase`, workflow `release.yml`, environment `pypi` | The eventual real `1.0.0`, not rc3 |
| Settings → Environments | create `pypi` with a required reviewer (`testpypi` already exists from rc2) | The real `1.0.0` |
| Settings → Pages | set source to **GitHub Actions** | The docs site deploying at §1.3 |

The environment names are not optional and must match `release.yml` exactly; a
mismatch fails the OIDC token mint with a 403 **after** the tag is cut.

### 1.7 Installing `gh` (not present on this machine)

```bash
brew install gh          # Homebrew 5.1.0 is already installed
gh auth login            # GitHub.com → HTTPS → browser
gh auth status           # confirm
```

Every `gh` command above has a browser equivalent, so this is a convenience
rather than a blocker.

---

## Phase 2 — Close `crs_mismatch` (before `1.0.0`, not before rc3) — **implemented 2026-08-30**

**Verified 2026-08-30:** no case in `src/geocase/data/` declares `crs_mismatch`.

This matters more than a missing risk type normally would. `crs_mismatch` is in
[Plan 24](24-catalog-site-on-owned-domain.md)'s pre-committed Search Console
vocabulary *and* in the README's opening prose. Ranking for a query the catalog
cannot answer spends a first impression on a miss.

The design already exists as
[Plan 27](27-close-plan-26-findings.md) §1.1's `crs_mismatch_overlay_pair` and
is **not** superseded — Plan 34 §4.2 closed the `axis_order` half of that item
via the six GML baselines and explicitly left this one owed.

### 2.1 Why no existing case closes it

`rasterize_match_wgs84_polygon` and `web_mercator_baseline` are both
single-layer. **A mismatch is a relationship between two inputs**, and no
bundled case pairs two layers in disagreeing CRSs, so neither can express it.

### 2.2 Structure — one case with a sidecar — **done**

Plan 27 left this open pending a check against the model. **Confirmed:**
`CaseMetadata`'s `files.sidecars` is `list[str]` with a `default_factory`
(`src/geocase/catalog/models.py:38`), so one case carrying both layers needs no
model change.

Prefer it over two cross-referencing cases: a relationship split across two
independently-selectable cases can be *selected apart*, and a selector that
returns half of a relationship is a footgun.

### 2.3 The fixture (TDD — failing check first) — **done**

Built as `src/geocase/data/core/vector/special/crs/crs_mismatch_overlay_pair/`.
`tests/unit/test_catalog_crs_mismatch.py` was written first and watched fail
7/7 with `KeyError: Case 'crs_mismatch_overlay_pair' not found in registry`,
then passed 7/7 once the case landed.

The footprint is 11.6E–11.8E, 59.9N–60.05N in southeastern Norway, inside UTM
zone 33N. Measured, not asserted in prose:

| Property | Value |
|---|---|
| Round-trip agreement (sidecar reprojected by its true EPSG:32633) | **0.0004 m**, against a declared 1 m tolerance |
| Naive overlay error (sidecar ordinates read as the degrees they claim) | **3359 km**, against a declared 3000 km floor |

`_check_crs_mismatch()` in `src/geocase/catalog/content.py` backs the risk type
against the bytes, following `_check_authority_axis_order()`'s precedent — it
is the only check in that module that reads a **sidecar** as well as a primary,
because a mismatch is a relationship. **The gate was verified to bite:**
rewriting the sidecar with honest degrees fails it with *"sidecar ordinates are
all within degree range, so it does not actually disagree with its declared
CRS"*.

Two layers holding the same footprint, overlaying perfectly on screen and metres
apart in reality: EPSG:4326 and EPSG:32633, with the declared-but-wrong CRS on
one. Declares `risk_types: [crs_mismatch, reprojection_error]`.

Per [`docs/adding-a-case.md`](../adding-a-case.md) the order is metadata-first,
and per `CLAUDE.md` the check comes before the fixture: write the content-gate
assertion that fails on the absent pair, watch it fail, then generate.

### 2.4 The gated-artifact chain — **done**

A new payload triggers all of it, under conda. **`generate_vector_fixtures.py`
turned out not to apply:** it builds only cases declaring
`params.canonical_source_case_id`, so this case — like `utm_zone_33n_to_32n_pair`
next to it — is hand-authored and gated by checksum instead. Its `--check` is
listed anyway because it must stay green.

```bash
python scripts/generate_vector_fixtures.py     # then --check
python scripts/build_case_index.py
python scripts/validate_catalog.py
python scripts/validate_case_content.py
python scripts/catalog_extent.py --write
python scripts/generate_checksums.py
python scripts/generate_catalog_pages.py
python scripts/generate_vector_coverage_matrix.py --output docs/_generated/vector-coverage-matrix.md
python scripts/generate_raster_coverage_matrix.py --output docs/_generated/raster-coverage-matrix.md
```

⚠️ **The case count moves 153 → 154**, gated by twelve patterns in
`_COUNT_CLAIMS` (`scripts/validate_catalog.py:358-371`) spanning **seven
files**: `README.md`, `docs/index.md`, `docs/getting-started.md`,
`docs/contributing/workflow.md`, `docs/contributing/releasing.md`,
`docs/contributing/structure-and-planning.md`, `recipe/meta.yaml`. It failed
loudly and correctly, naming all seven; all are updated.

⚠️ **`README.md`'s `(\d+) bundled cases` sentence is itself one of the gated
claims** (§1.1), so the count edit and the version edit touch the same line.
Both landed; the gate is green.

---

## Deliberately not in scope

- **Plan 28 Phases 4–5.** Phase 4's stated entry condition — *"start when a
  raster consumer reports value... do not start on the strength of one negative
  report"* — is unmet: the only raster signal is the rio-tiler run that declined.
  Phase 5 is a docs-only positioning pass (`docs/validation-findings.md`, which
  does not yet exist) with zero code impact. Neither blocks rc3.
- **Real PyPI `1.0.0` and conda-forge.** [Plan 25](25-ship-geocase-as-a-package.md)
  §7 is explicit that these are a separate pass. conda-forge is gated on the
  published sdist's sha256 regardless, so it cannot precede the upload.
- **`docs/index.md`'s lede.** Plan 25 §8 scoped the README rewrite and left the
  site homepage as a separate call. Still open, still not blocking.

---

## Verification

```bash
conda activate geocase                       # only env with osgeo

# Phase 1 — already run green at 1.0.0rc3
rm -rf dist/ && python -m build
python scripts/verify_dist.py dist/ --expected-version v1.0.0rc3
python scripts/validate_catalog.py           # the README count regex still matches
mkdocs build --strict

# Phase 2 — the gap, before and after
python -c "import geocase; print([c.id for c in geocase.list_cases() if 'crs_mismatch' in c.risk_types])"
# before: []   after: ['crs_mismatch_overlay_pair']

pytest tests -q
ruff format --check src tests && ruff check src tests
mypy src
```
