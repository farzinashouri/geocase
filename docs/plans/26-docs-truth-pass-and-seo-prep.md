# Docs Truth Pass, Plan Archival, and Host-Neutral SEO Prep

> **Proposed 2026-08-23.** Does not authorise deploying any site, registering a domain, the Astro
> target from [Plan 24](24-catalog-site-on-owned-domain.md), or the PyPI upload from
> [Plan 25](25-ship-geocase-as-a-package.md). It makes those cheaper; it does not do them.

> **Implementation status: complete except §3.4's `social` plugin, 2026-08-23.** All four phases
> executed in six commits
> (`9bb35c7`, `f657d62`, `cd985a4`, `d63888a`, `2c3c409`, `72180a2`). Every gate green:
> `build_case_index`, `validate_catalog`, both fixture gates, `generate_checksums`,
> `generate_catalog_pages`, `mkdocs build --strict`, `ruff`, `mypy`, and `pytest tests -q` at
> **1701 passed / 37 skipped**. Per-section status is marked inline below.
>
> **One deliverable is NOT done: the `social` plugin (§3.4)** — OG card generation. Zero of it
> landed, and verification step 5 was therefore not run. It is blocked on **`libcairo`**, a
> *native system library*, not a Python package: `pip install "mkdocs-material[imaging]"`
> installs cleanly and then fails at import. It is absent from both this machine and the
> `ubuntu-latest` docs runner, so enabling it unverified would have turned the `docs` gate red —
> and §3.4 itself says to confirm CI installs the extra *before* relying on it. Deferred by
> decision rather than omission, with the remaining work spelled out in §3.4's marker and in the
> roadmap's *Deferred work*. **Everything else in Phases 1–4 is done and verified.**
>
> **Three findings this plan did not anticipate**, carried into
> [Plan 27](27-close-plan-26-findings.md):
>
> 1. The plan's own verification grep found **four more stale `134`s** it had not enumerated
>    (`getting-started.md`, `contributing/workflow.md`, `releasing.md` ×2,
>    `structure-and-planning.md`), three of them also carrying a stale "780 passing tests"
>    against an actual 1701. Fixed here; the guard was widened from 3 claims to 7.
> 2. **`docs/philosophy.md` was structurally broken** — an unclosed code fence meant the whole
>    page rendered as literal markdown source. It is a named landing candidate in §3.4, so it
>    was fixed here. Nothing gates for this class of defect.
> 3. **No case declares an `axis_order` or `crs_mismatch` risk type**, though both are in
>    Plan 24's pre-committed Search Console vocabulary and both now appear in the README's
>    opening prose per §1.6. The catalog cannot rank for queries it has no case for.
>
> Two of the plan's open questions were answered by measurement:
>
> - **The vector coverage matrix's four-month stability is genuine**, not a weak `--check` gate
>   (§4). Regeneration produced no diff. The raster matrix *did* move by one row, traced to two
>   §3.3 descriptions using the word "masking" — a false positive in the generator's
>   product-family keywords, reworded rather than accepted.
> - **119 `notes.md` files, but 123 cases declare notes** (§3.1), all resolving on disk. The 119
>   figure counted files literally named `notes.md`; four cases share or differently-name theirs.

## Context

GeoCase's documentation has drifted from the code in three separate ways, and the drift is now
load-bearing:

1. **Factual staleness.** The catalog holds **135** cases (verified: `CaseRegistry(135 cases)`),
   but `README.md:5`, `CHANGELOG.md:208`, and `recipe/meta.yaml:40` all assert **134**. The
   `meta.yaml` one is an executable assertion — it will fail the conda build. The README also
   promises `pip install "geocase[all]"` and `conda install -c conda-forge geocase`, neither of
   which resolves: `geofacts>=0.1.1` is not on PyPI and there is no feedstock. `docs/index.md:5`
   says "Status: alpha" while `pyproject.toml` classifies the project `Production/Stable`.
   Two renames — `geospatial_spec` → `geofacts` and `geocase.synth` → `geocase.raster` — landed in
   code but not in the case metadata that generates the published catalog pages.

2. **Planning-folder decay.** `docs/plans/` holds 20 active plans. Plans 13, 15 and 16 are built
   but still headed "Proposed"; 14 is rejected; 19 is superseded; 12 is reversed by 24. Meanwhile
   `development-plan.md` — which `docs/plans/index.md` calls "the single roadmap" — was last
   touched 2026-08-03, still describes a v1.0 that shipped, and knows nothing of Plans 14–25.
   The folder's own stated rule ("Supersede, don't delete") is not being followed.

3. **Zero SEO surface.** 188 generated catalog pages exist with `schema.org/Dataset` JSON-LD and
   per-page `description:` front matter — genuinely good raw material — but `mkdocs.yml` declares
   no `plugins:` block at all, no hand-written page carries a `description:`, there is no favicon,
   logo, robots.txt, or social-card config, and the site has never been deployed. Separately,
   **119 `notes.md` files** of hand-written per-case prose (Plan 24 measures 12,176 words) are
   never rendered — `generate_catalog_pages.py:369` only emits the *filename* as a link. That is
   the single largest body of indexable, differentiated content in the repo, and it is invisible.

**Outcome:** every user-facing document states something true; dead plans are archived with
honest status banners and one current roadmap survives; and the SEO groundwork is laid in a
**host-neutral** way so it is not invalidated when the canonical domain is finally chosen.

**Decided constraints (from the user):**
- *Host-neutral SEO prep only.* Plan 24 forbids a GitHub Pages deployment (Google Dataset Search
  dedupes on the JSON-LD `url`, and a `github.io` copy risks being credited as canonical).
  So: **do not** change `mkdocs.yml:site_url`, `pyproject.toml`'s `Documentation` URL, or the
  values baked into the 135 committed case pages. Do make the host a single configurable input.
- *Full truth pass*, including contributing docs and the interview template.
- *Archive dead plans and rewrite the roadmap.*

**Out of scope:** deploying any site; registering a domain; the Astro target from Plan 24; the
PyPI/TestPyPI upload from Plan 25. This plan makes those cheaper, it does not do them.

---

## Phase 1 — Truth pass (user-facing first)

### 1.1 The case count: 134 → 135

> ✅ **Done.** All three corrected. `recipe/meta.yaml`'s was the build-breaking one. `git log -S` confirmed 134 was accurate at 1.0.0, so the historical entry stands and the growth is recorded under `Unreleased`. The suggested guard was built: `validate_catalog.py` now gates **7** documented counts against `len(get_registry())` — the 3 named here plus 4 this plan missed.

Three places, one of which is executable:

- `recipe/meta.yaml:40` — `assert len(geocase.list_cases()) == 134`. **Build-breaking.**
- `README.md:5`
- `CHANGELOG.md:208` — this line is inside a released-version section. Do **not** rewrite history:
  leave the 1.0.0 entry's number as the count at that release, and instead correct it only if it
  was wrong *at that time*. Verify with `git log -S'134 bundled cases'` before touching it; if the
  count genuinely was 134 at 1.0.0, add an `Unreleased` note recording the growth to 135 rather
  than editing the historical entry.

Guard against recurrence: the count is derivable. Consider having `scripts/validate_catalog.py`
assert the README and `meta.yaml` numbers match `len(get_registry())`, so this is gated like the
other generated artifacts rather than re-drifting. (Cheap: the registry is already imported there.)

### 1.2 Install claims that do not resolve

> ✅ **Done.** conda block hedged; `releasing.md`'s "GitLab-issued JWT" corrected to GitHub Actions OIDC; CHANGELOG's false PyPI publication and GitLab URLs corrected as dated notes rather than rewritten history.

- `README.md:26-36` — the `pip install "geocase[all]"` block is hedged ("When a package release is
  published"), the conda block is **not**. Hedge the conda block identically, or cut it until a
  feedstock exists. Plan 25 §4 flags the same line.
- `docs/contributing/releasing.md` — Plan 25 records it claims a "GitLab-issued JWT"; the actual
  `release.yml` uses GitHub OIDC trusted publishing. Correct the mechanism.
- `CHANGELOG.md` — Plan 25 records it claims a PyPI publication that never happened and URLs
  pointing at GitLab. Correct both.

### 1.3 `docs/index.md` status contradiction

> ✅ **Done.** Matched to the README (`1.0`, same two-surface compatibility sentence).

`docs/index.md:5` says "Status: alpha"; `pyproject.toml` says `Development Status :: 5 -
Production/Stable` and `README.md:5` says "Status: **1.0**". Pick one — recommend matching the
README (`1.0`, with the same two-surface compatibility sentence) so the site home and the repo
front door agree. This is also the page most likely to be a search landing page, so it is worth
getting right in Phase 3 anyway.

### 1.4 The two renames

> ✅ **Done.** Preset paths verified against the source before writing: `geocase.raster.presets.sentinel1_grd` / `.sentinel2_l2a`. `name: geocase-synthetic` was left alone — a source name, not a module path. Interview template renamed; plans 19/20/21 got the one-line note, no body edits.

**`geocase.synth` → `geocase.raster`** — 5 hits in case metadata, which is what generates the
published pages:

- `src/geocase/data/core/raster/multispectral_s2_like_small/case.yaml` — `:8` (description), `:72`
  (`provenance.synth: geocase.synth.sentinel2_l2a`)
- `src/geocase/data/core/raster/sar_dualpol_small/case.yaml` — `:6`, `:64`
- `src/geocase/data/core/raster/sar_vv_small/case.yaml` — `:6`, `:62`
- `src/geocase/data/core/raster/multispectral_mixed_resolution_small/case.yaml` — `:65`

New values: `geocase.raster.presets.sentinel2_l2a` / `.sentinel1_grd` — **verify the exact callable
paths against `src/geocase/raster/presets/sentinel1.py` and `sentinel2.py`** before writing them
in; the ported functions may not have kept their names.

⚠️ Changing a `case.yaml` triggers the gated-artifact rule in `CLAUDE.md`. After editing, run the
regeneration commands in Phase 4 and commit the results.

Leave the historical notes in `src/geocase/raster/__init__.py:3` and
`presets/sentinel1.py:3` / `sentinel2.py:8` alone — those correctly document the rename.

**`geospatial-spec` → `geofacts`** — the live hits are almost all inside plan documents
(`20`: 25 hits, `21`: 9, `19`: 12). Under "supersede, don't delete", **do not rewrite plan bodies**
— a plan is a dated record of what was proposed. Two exceptions:

- `docs/evidence/2026-fixture-interviews/TEMPLATE.md:39` — a *user-facing instrument* still asking
  interviewees about "geocase/geospatial-spec". Rename it; it goes in front of real people.
- `docs/plans/index.md:21-22` — the index is a *current-state* document, not a record. Update its
  Plan 19/18 descriptions to name `geofacts` and `geocase.raster`, with the old name in
  parentheses on first mention.

For the plan bodies, add a single italic note near the top of Plans 19, 20, and 21:
*"Written before the rename; `geospatial-spec` is now `geofacts`."* One line each, no body edits.

### 1.5 Undocumented surfaces

> ✅ **Done.** `geofacts`, the benchmark and `geocase.raster` are all in the README now, and the bare `contributing/releasing.md` path is fixed to `docs/contributing/releasing.md`.

`README.md` mentions neither `geofacts` (a hard runtime dependency) nor `geocase.raster` nor the
benchmark. Add `geofacts` to the dependency note; add one line each linking
`docs/benchmark/quickstart.md` and the raster primitive from "Learn More". Also fix `README.md:90`,
which links `contributing/releasing.md` as a bare relative path — that resolves on the docs site
but 404s on GitHub. Use the full `docs/contributing/releasing.md` path (README is read on GitHub
far more than on the site, and it is not in the mkdocs nav).

### 1.6 The README is the only SEO surface that exists today

> ✅ **Done, narrowly as scoped.** Only the false statements were corrected — Plan 25 §8 still owns the rewrite. The failure-mode vocabulary (nodata, antimeridian, CRS mismatch, axis order) is now in the opening prose. That surfaced finding 3 above: two of those four terms have no case behind them.

Per the measurement in [§3.2](#32-make-the-site-url-a-single-input-and-keep-the-catalog-unpublished-until-the-domain-exists):
the repo page is the **one** GeoCase URL search engines currently index. The docs site is
unpublished and the `docs/` Markdown is not indexable. That changes how two items should be
ranked:

- **[Plan 25](25-ship-geocase-as-a-package.md) §8's README rewrite** — "lead with a concrete
  failing edge case", demote the AI framing, cut "foolproof"/"standardized" — is doing **SEO work
  right now**, not just persuasion work. It is the only page where wording affects what a searcher
  can find, and it will stay that way until the owned domain launches. Treat it as higher priority
  than any of the Phase 3 site items, and sequence it early.
- That rewrite is owned by Plan 25, so **do not duplicate it here.** This plan's Phase 1 only
  corrects the README's *false* statements (§1.1–1.2, §1.5). If Plan 25 executes first, rebase
  these edits onto its rewritten text rather than reverting it.

The corollary: the failure-mode vocabulary that Plan 24 pre-commits to measuring in Search Console
— nodata, dateline/antimeridian, CRS mismatch, axis order — should appear in the README's opening
prose, not only in the case catalog. Today it appears in neither.

---

## Phase 2 — Plans: archive and re-roadmap

### 2.1 Correct status headers, then move

> ✅ **Done**, with recommendation (b) on Plan 16 — archived, its U7/U9/U10 carried into the roadmap. `dataset-catalog.md` was checked and had shipped (17 KB), so its plan archived as Complete. `execution-order.md` was archived too (see §2.2), making it **10** active plans, not the 11 predicted.

Move to `docs/plans/archive/` **with a status banner added at the top of each file** (matching the
existing banner style in `archive/01`–`10`), and confirm `mkdocs.yml`'s existing
`not_in_nav: plans/archive/*.md` still covers them:

| Plan | Banner to add |
|---|---|
| `11-distribution-pypi-and-conda.md` | Superseded by [Plan 25](25-ship-geocase-as-a-package.md) (2026-08-23) |
| `12-docs-site-publication.md` | **Reversed by [Plan 24](24-catalog-site-on-owned-domain.md)** — GitHub Pages is now explicitly ruled out |
| `13-cross-format-canonical-convergence.md` | Implemented 2026-08-09 (header currently still says "Proposed") |
| `14-reposition-as-correctness-library.md` | Rejected — Step 0 gate fired 2026-08-09 |
| `15-geocase-as-benchmark.md` | Implemented 2026-08-10 |
| `16-generalize-beyond-geospatial.md` | Phases 0–4 built 2026-08-10; U7/U9/U10 open — **see note** |
| `19-spec-table-separate-repo.md` | Superseded by [Plan 20](20-restart-spec-first.md) |

**Judgment call on 16:** it has three open user actions (U7, U9, U10). Archiving a plan with live
open items buries them. Either (a) keep 16 active until U7/U9/U10 close, or (b) archive it and
carry the three open items into the rewritten roadmap's "Open user actions" table. **Recommend (b)**
— the roadmap is where open items belong, and it keeps the active folder to plans that are
actually driving work.

Also archive `website-plan.md` (Plan 24 explicitly "amends, reversing its Astro rejection") and
`dataset-catalog-plan.md` if its deliverable shipped — check `docs/dataset-catalog.md` (17 KB,
exists) before deciding; if it shipped, archive as Complete.

**Remaining active:** `development-plan.md` (rewritten), `execution-order.md`, `17`, `18`, `20`,
`21`, `22`, `23`, `24`, `25`, `index.md`. That is 11 down from 20.

### 2.2 Rewrite `development-plan.md`

> ✅ **Done**, ~120 lines. `execution-order.md` was folded in and archived rather than given parallel treatment — leaving it active would have kept two sequencing documents, which is the thing this folder's own rules forbid.

Currently 26 KB of a completed v1.0 roadmap. Replace with a short current-state document:

- **Where the project stands** — 135 cases, v1.0.0rc1, unpublished; the four things measured true
  by Plans 22/23/25 (four gates, four documents, zero users; packaging is not the bottleneck;
  discovery is).
- **Active sequence** — 25 (ship the package) → 24 (catalog site on an owned domain) → 21's
  remaining tracks, with 20 named as the overarching frame and 22 as the portfolio constraint.
- **Open user actions** — one table: the domain nomination (blocks 24), the `geofacts` PyPI upload
  (blocks 25), U7/U9/U10 from Plan 16, and anything still open in 20/21.
- **Decision log** — one line per archived plan and why, preserving the outcomes that the current
  `index.md` table already states well. Much of that prose can move here verbatim.

Keep it under ~200 lines. `execution-order.md` also references v1.0 batches — either fold it into
the roadmap or give it the same treatment; do not leave two stale sequencing documents.

### 2.3 Update `docs/plans/index.md` and `archive/index.md`

> ✅ **Done.** Both tables rebuilt; "Rules for this folder" preserved verbatim.

Rebuild both tables to match the new split. Preserve the existing "Rules for this folder" section
verbatim — it is the reason this cleanup is happening, and it is correct.

---

## Phase 3 — SEO groundwork (host-neutral)

### 3.1 Render the `notes.md` prose — the highest-value item here

> ✅ **Done.** 123 cases (not 119 — see the status banner) render prose under `## Notes`, placed after the assertions table. Leading H1 dropped, headings demoted one level, fenced code left untouched; the 12 cases without notes render with the section absent. **The budgeted friction did not materialise:** not one notes file contains a relative link, so no link rewriting was needed.

**119 files, ~12,176 words** of hand-written per-case explanation currently reachable only as a
filename in a bullet (`scripts/generate_catalog_pages.py:369`). This is the only differentiated,
non-templated content the catalog has; without it, 135 case pages are boilerplate variants that
search engines will treat as thin content.

Change `generate_catalog_pages.py` to read each case's `notes.md` and inline its body into the
case page under a stable heading (e.g. `## Notes`), after the assertions table and before Related
Cases. Considerations:

- Strip any leading `#` H1 from the notes file so the page keeps one H1.
- Demote heading levels inside notes so they nest under `##`.
- Notes are Markdown already, so no escaping is needed — but they may contain relative links that
  must be rewritten relative to the generated page's location, or `mkdocs build --strict` will
  fail on them. This is the likeliest source of friction; budget for it.
- Cases without a `notes.md` (135 − 119 = 16) must render cleanly with the section absent.

This regenerates all 135 case pages — expect a large, mechanical diff.

### 3.2 Make the site URL a single input — and keep the catalog unpublished until the domain exists

> ✅ **Done.** `DEFAULT_SITE_URL` reads `GEOCASE_SITE_URL`, value unchanged; `mkdocs.yml:site_url` and `pyproject.toml`'s `Documentation` URL untouched; the 135 committed pages still carry the placeholder. The CI guard is built and verified **both ways** — passes clean, and catches an injected `mkdocs gh-deploy` step.

**Measured state (2026-08-23).** Nothing is at risk yet, and that is the asset this section
protects:

| Surface | Status | Indexable? |
|---|---|---|
| `farzinashouri.github.io/geocase/` | **404** — no `gh-pages` ref on origin | No — does not exist |
| `github.com/farzinashouri/geocase` | 200, public, indexed | Yes — the README, as one page |
| `raw.githubusercontent.com/.../*.md` | 200, `text/plain` | No — not indexed as content |
| The 188 generated catalog pages | Built in CI, output discarded | **Never served anywhere** |

So the `docs/` tree is effectively invisible to search engines today: GitHub's Markdown blob views
carry `noindex`, and raw serves plain text. The only indexed surface is the repo page itself.

**Why this matters more than it looks.** Every generated case page embeds `schema.org/Dataset`
JSON-LD whose `url` and `isPartOf.url` come from `DEFAULT_SITE_URL`
(`scripts/generate_catalog_pages.py:33`, `_json_ld` at `:240`). Google Dataset Search deduplicates
on that field. If those 135 pages are ever served from `github.io` *before* the owned domain
exists, the `github.io` URL can be credited as canonical — and it would then be the older, more
linked of the two. Duplicate content across two hosts you own is not a penalty; the hazard is
that Google picks the canonical, not you, and it favours what it saw first. Publishing on the
owned domain first means correct canonical on first index: no migration, no `rel=canonical`
retrofit, no Search Console change-of-address.

**Therefore:**

- Do **not** change `DEFAULT_SITE_URL`'s value. Make it overridable — read `GEOCASE_SITE_URL` from
  the environment with the current constant as the default — so retargeting later is one env var
  and one regeneration rather than an edit-and-audit of 135 committed pages.
- `mkdocs.yml:site_url` and `pyproject.toml`'s `Documentation` URL stay as they are.
- **Guard against accidental deployment.** The realistic failure here is a slip, not a decision:
  someone enabling Pages in repo settings, or a `mkdocs gh-deploy` step arriving in a workflow.
  Add a comment above `DEFAULT_SITE_URL` stating that the value is a placeholder and that serving
  these pages from it is the one thing [Plan 24](24-catalog-site-on-owned-domain.md) forbids. For
  actual teeth, add a CI check that fails if a `gh-pages` ref appears on origin or if `gh-deploy`
  appears in `.github/workflows/` — cheap, and it converts a silent, expensive mistake into a
  build failure.

Note that `mkdocs build --strict` in CI stays exactly as it is: it is an internal link checker,
and its output is discarded. That is compatible with everything above.

### 3.3 Descriptions written for searchers

> ✅ **Done, 21 cases.** All under the 155 cap, verified against the generated pages: none truncated. No `axis_order` or `crs_mismatch` case exists to rewrite (finding 3). Two rewrites had to be reworded because "masking" tripped the raster matrix's Mask keyword. Remaining ~114 deferred and noted in the roadmap.

`generate_catalog_pages.py:43-44` carries its own admission: *"Descriptions are written for
contributors, not searchers."* The `DESCRIPTION_FIELDS` fallback chain
(`description` → `behavioral_goal` → `title`) is sound; the source strings are the problem, and
they live in 135 `case.yaml` files.

Do **not** attempt all 135 here. Scope this to the ~20 cases whose risk types match the queries
Plan 24 pre-commits to measuring — nodata, dateline/antimeridian, CRS mismatch, axis order. For
those, rewrite `description` to lead with the failure a searcher would type, staying inside
`MAX_META_DESCRIPTION = 155`. Leave the rest for a later pass; note the remainder in the roadmap.

(Editing `case.yaml` again triggers the Phase 4 regeneration — batch this with Phase 1.4.)

### 3.4 `mkdocs.yml` and hand-written page metadata

> ⚠️ **Partial — 5 of 6 bullets. `social` is NOT done and nothing for it landed.**
>
> **Done and verified in the built HTML:** the explicit `plugins:` block with `search` listed
> (so site search did not silently disappear), `description:` front matter on all seven landing
> candidates, `docs/assets/` with favicon and logo wired via `theme.favicon`/`theme.logo`, the
> `repo_name` org fix, the `extra:` social links, and the nav gap — which was real, so
> `evidence/2026-fixture-interviews/*` is now in `not_in_nav`. One snag the plan did not
> predict: the descriptions needed **quoting**, because "...case catalog: 135 curated..." has a
> colon that YAML reads as a mapping.
>
> **Not done — the `social` plugin, i.e. OG card generation.** Zero of it landed: it is absent
> from `plugins:`, and `pillow`/`cairosvg` were deliberately *not* added to the `docs` extra,
> because shipping dependencies for a plugin that cannot be enabled is dead weight. The blocker
> is **`libcairo`**, a native system library (not a Python package) absent from both this
> machine and the `ubuntu-latest` docs runner. `pip install "mkdocs-material[imaging]"` succeeds
> and then fails at import with `cannot load library 'libcairo.2.dylib'`. Enabling it unverified
> would turn the `docs` gate red. **Remaining work:** an `apt-get install libcairo2-dev
> libfreetype6-dev libffi-dev` step in the CI `docs` job, `pillow`/`cairosvg` added to the
> `docs` extra, then `social` added to `plugins:` — and the plan's own instruction to *"confirm
> CI's `docs` job installs that extra before relying on it"* is what is being honoured by not
> doing this blind. Consequently **verification step 5 (social cards) was not run**:
> `site/assets/images/social/` is not populated and no page carries an `og:image` tag.

- Add an explicit `plugins:` block. Declaring it **disables the implicit default `search`**, so
  `search` must be listed explicitly or site search silently disappears. Then add `social` for OG
  card generation (needs the `pillow`/`cairosvg` deps — add to the `docs` extra in
  `pyproject.toml`, and confirm CI's `docs` job installs that extra before relying on it).
- Add `description:` front matter to the hand-written landing candidates: `docs/index.md`,
  `getting-started.md`, `philosophy.md`, `case-discovery.md`, `dataset-catalog.md`,
  `adding-a-case.md`, `testing-your-function-with-geocase.md`. Match the generated pages' style
  and the 155-char cap.
- Add `docs/assets/` with a favicon and logo, wired via `theme.favicon` / `theme.logo`. Absent
  today; both are cheap and both appear in search results.
- Fix `repo_name: fashouri/geocase` — the org does not match `repo_url`'s `farzinashouri/geocase`.
- Add an `extra:` block with social links.
- **Nav gap:** `docs/evidence/2026-fixture-interviews/*` is in neither `nav` nor `not_in_nav`.
  Verify against `mkdocs build --strict` whether this currently warns; if so, add it to
  `not_in_nav` (it is an internal instrument, not a doc page).

### 3.5 `pyproject.toml` metadata

> ✅ **Done.** Five keywords to twelve; `Documentation` URL left alone.

Keywords are five and thin: `geospatial, testing, gis, pytest, test-cases`. Add the failure-mode
terms that people actually search — `nodata`, `crs`, `antimeridian`, `raster`, `vector`,
`fixtures`, `geotiff`. Leave the `Documentation` URL alone (§3.2).

---

## Phase 4 — Regenerate the gated artifacts

> ✅ **Done.** The watch-item resolved in the plan's favour: `vector-coverage-matrix.md` regenerated with **zero diff** — its four-month stability is genuine, not a weak gate. The *raster* matrix moved one row, traced to §3.3 wording rather than a pre-existing bug, and reworded away.

Any `case.yaml` or generator change makes the CI `catalog` job fail until artifacts are
regenerated and committed. Run under the **conda `geocase` env** (needs `osgeo`):

```bash
conda activate geocase
python scripts/build_case_index.py
python scripts/validate_catalog.py
python scripts/generate_checksums.py
python scripts/generate_catalog_pages.py
python scripts/generate_vector_coverage_matrix.py --output docs/_generated/vector-coverage-matrix.md
python scripts/generate_raster_coverage_matrix.py --output docs/_generated/raster-coverage-matrix.md
```

One thing to watch: `docs/_generated/vector-coverage-matrix.md` last changed 2026-04-19, four
months before the case pages it summarizes. Either it is genuinely stable or its `--check` gate is
weaker than assumed. If regeneration produces a large unexplained diff there, investigate before
committing — it may be a pre-existing bug rather than this plan's doing.

---

## Verification

```bash
conda activate geocase

# gates must all pass clean
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
python scripts/generate_raster_fixtures.py --check
python scripts/generate_vector_fixtures.py --check
python scripts/generate_checksums.py --check
python scripts/generate_catalog_pages.py --check
mkdocs build --strict          # catches broken links from archive moves + inlined notes
ruff format --check src tests && ruff check src tests
mypy src
pytest tests -q
```

Then, specifically:

1. **Count** — `python -c "import geocase; assert len(geocase.list_cases()) == 135"`, and grep the
   repo for a remaining `134`: `grep -rn '134' README.md recipe/ CHANGELOG.md docs/`.
2. **Renames** — `grep -rn 'geocase\.synth' src/geocase/data/` returns nothing;
   `grep -rn 'geospatial-spec' docs/evidence/` returns nothing.
3. **Notes rendering** — open `docs/_generated/catalog/cases/<a case with notes>.md` and confirm
   the prose body is present, not just a filename link; confirm a case *without* notes renders
   with no empty section.
4. **Archive moves** — `mkdocs build --strict` passing is the real check (it fails on any doc that
   still links a moved plan). Also confirm no moved file is left in `nav:`.
5. **Social cards** — after `mkdocs build`, confirm `site/assets/images/social/` is populated;
   spot-check one page's `og:image` meta tag.
6. **Site URL untouched** — `grep -rn 'github.io' mkdocs.yml pyproject.toml docs/_generated/ | wc -l`
   should be unchanged from before the work, confirming the host-neutral constraint held.
7. **Still unpublished** — the constraint that protects the future domain's canonical URL:

   ```bash
   git ls-remote --heads origin | grep gh-pages          # must return nothing
   grep -rn 'gh-deploy' .github/workflows/               # must return nothing
   curl -s -o /dev/null -w '%{http_code}\n' \
     https://farzinashouri.github.io/geocase/            # must stay 404
   ```

## Suggested commit split

1. Truth pass (Phase 1) — no generated-artifact churn except the `case.yaml` renames.
2. Plan archival + roadmap rewrite (Phase 2) — pure docs moves.
3. Generator change: inline `notes.md` + env-configurable site URL (Phases 3.1–3.2) + regenerated
   pages. Large diff, isolated.
4. Searcher-facing descriptions (3.3) + regeneration.
5. mkdocs/pyproject metadata, assets, keywords (3.4–3.5).
