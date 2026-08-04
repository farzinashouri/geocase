# Execution Order

The sequencing view of the road to v1.0, merging the v1.0 release strategy with the
dataset-catalog work.

> **This document owns *order*, not *scope*.** What each step contains is defined once, in
> [`development-plan.md`](development-plan.md); the detailed rationale is in
> [`archive/10-v1-release-strategy.md`](archive/10-v1-release-strategy.md)
> and [`dataset-catalog-plan.md`](dataset-catalog-plan.md). If this page and the roadmap
> ever disagree about *what* a step includes, the roadmap wins. Keeping the split this
> narrow is deliberate: four documents each claiming to say "what's next" is what made the
> July 2026 roadmap collapse necessary.

## Status

**Batches 1–5 complete, to the upload boundary.** The three irreversible release steps —
TestPyPI dry run, trusted-publishing setup, and `twine upload` — remain, deliberately left
for a human to authorize. Bundled data 36 MB → 4.2 MB; wheel 458 KB; `pytest tests -q`
green at **780 passed, 1 skipped**; ruff and mypy clean and gated; coverage measured at
**54%** in Batch 3 (non-blocking, to be re-measured before release). `import geocase`
now yields a pinned 27-name public surface, and manifest case ids resolve.

| Batch | Contents | Checkpoint | Status |
|---|---|---|---|
| **1** | Roadmap collapse + Steps 11.1–11.5 | `pytest tests -q` green, no collection error, no console script | ✅ Done |
| **2** | Step 12 — catalog shrink, alone | checksums regenerate; SQLite tests pass; wheel size | ✅ Done |
| **3** | Step 13 — quality gates **+ the 4 catalog defects** | CI green on directory runs; coverage number recorded | ✅ Done |
| **4** | Step 15 (public API) → Step 14 (manifests) | `__all__` pinned; remote-id error asserted both paths | ✅ Done |
| **5** | Step 16 — docs truth pass, **dataset catalog**, release | `mkdocs build`; wheel holds all 134 cases; TestPyPI dry run | ✅ Done to the upload boundary |

## The batches

### Batch 3 — Quality gates you can trust ✅ Done

Step 13, plus the four catalog defects surfaced by the dataset-catalog work. They belong
here rather than in Batch 5 because two of them are bugs *inside CI gates*, which is
precisely this batch's theme.

**Outcome (Aug 2026).** Ten commits, in the order below. Measured figures, none of them
inherited: ruff 223 errors in `src` + `tests` (not the 1043 the plan quoted — that was
repo-wide, including `examples/`), of which 160 W191 and 41 E501; mypy 24 errors in `src`
(not 18), every one a config artifact; coverage 54%. Three gates added — `lint`,
`typecheck`, and the orphan-case check in `validate_catalog.py` — and one job removed
(`core_tests` + `extended_tests` collapsed into `tests`). Test count 715 → 727: the
directory run picked up nothing new to *run*, but the batch added 13 tests (10 schema/model
agreement, 3 marker wiring) and deleted three empty stub modules.

Two things surfaced that the plan did not list. `catalog/validators.py` was a fourth empty
stub — a one-line docstring nothing imported, found because coverage reported it as zero
statements — deleted, and Step 8's "Done" list corrected. And `case.schema.yaml`'s
`assertions` block documented 6 of `AssertionHints`' 16 fields, missing every typed raster
expectation from plan 08; fixed alongside the `format` enum and covered by the same test.

Order within the batch mattered:

1. **`ruff format`** — whitespace only. Verified identical test output before and after
   (the only difference in the `-rA` node list was a skip's line number moving after
   reflow), so it never polluted `git blame`.
2. **`ruff check --fix`** plus hand-fixes for the residual N806/N811/E501. No E402
   appeared once the scope was `src` + `tests`; the E402s live in `scripts/`.
3. **Then** the ruff CI job. Adding the gate first would have turned CI red on 223 errors
   and made `ignore = ["W191","E501"]` tempting, which would have entrenched the mixed
   indentation permanently. Ruff is pinned exactly in the job, since `format --check`
   would otherwise fail on an upgrade rather than on code.
4. Directory-based test runs replacing the allowlist; deleted the three empty stub test
   files; mypy config fix; markers; non-blocking coverage; the 3.11/3.14 matrix from 13.4;
   and Step 9's leftover — `cases/raster.py` now goes through `loaders/rasterio_loader.py`.
5. **Catalog defects** (from [`dataset-catalog-plan.md`](dataset-catalog-plan.md)):
   the raster-matrix glob (reported 25, actual 30) and its regenerated artifact; the
   schema `format` enum, 7 → 17 values; `affine_transform_quirk` deleted. The fourth,
   the mkdocs nav omission, stays in Batch 5 with the rest of the docs pass.

**Re-measuring paid off again.** The "18 mypy errors" baseline was wrong (24), the ruff
baseline was wrong (223, not 1043), and neither error was in the direction the plan
assumed. Each of the three defects fixed here also got a gate, per the rule below: the
matrix generator now fails if its own discovery disagrees with `case-index.yaml`, a test
pins every schema enum to the Literal that enforces it, and `validate_catalog.py` fails on
any case file missing from the index.

### Batch 4 — Public API, then manifests ✅ Done

Step 15 before Step 14: `show_case` reports remote state, so the API had to exist first.

**Outcome (Aug 2026).** Three commits — Step 15; Steps 14.1–14.3; Step 14.4 — and
53 new tests (727 → 780). The public surface is 27 names, pinned against a literal in
`tests/unit/test_public_api.py`.

Both ordering constraints earned their place:

- **Step 15 first** was not merely convenient. `show_case` is the one public function
  that *describes* a remote case rather than refusing it, so writing Step 14's error
  paths without it would have left no way to inspect a manifest case at all.
- **14.2 + 14.3 atomic** held exactly as predicted. `materialize_case` now checks
  `is_remote()` before the `case_roots_by_id` lookup; without that check the cache —
  built from `case-index.yaml` alone — misses every manifest id and raises
  `No case root found`, which is what the pytest plugin's path would have surfaced.
  A test asserts that string is *absent* from both error paths.

Two things the plan did not anticipate:

- **Reading the env var inside `get_registry` is only half of 14.1.** The singleton
  still returned the registry built before a test monkeypatched `GEOCASE_MANIFESTS`.
  The resolved manifest paths are now part of the cache key.
- **`catalog/roots.py` cannot be re-exported from `geocase.catalog`.** It is the one
  catalog module importing `geocase.cases`, and `cases/base.py` imports
  `catalog/models.py`; eager re-export makes `import geocase` circular. Import it
  directly.

Per the gate-over-promise rule, each change got one: `__all__` is pinned, a test asserts
the plugin and the API share one `materialize_case` object (so the duplicate
`lru_cache` cannot return), and `validate_catalog.py` now opens `extended-manifests/`
— catching shadowed ids, cross-manifest duplicates, malformed digests, and dangling
`bundled_analog` references, while letting the 7 `replace_me` placeholders warn.

### Batch 5 — Docs, dataset catalog, release ✅ Done to the upload boundary

**Outcome (Aug 2026).** Everything through local artifact verification is done; the
irreversible steps — TestPyPI dry run, trusted-publishing setup, and `twine upload` — are
deliberately left for a human to authorize, since PyPI artifacts are immutable.

Measured, not inherited: **134 cases** (103/30/1) and **780 passed, 1 skipped** both
reproduced. The public surface is **27 names, not the 26** that four documents quoted —
`__version__` is exported too. That figure was corrected in all five places.

Two defects surfaced that no gate was watching, both of the same kind the batch was
supposed to end:

- **The generated catalog pages were stale by 127 files.** They predated the
  `MIN_HUB_CASES` thin-content rule and the shape-rendering change, and nothing checked
  them. `generate_catalog_pages.py --check` is now in `ci/catalog-validation.yml`.
- **Every case page linked its risk hubs one directory too high** (`../../risk/` from
  `catalog/cases/`), producing **187 broken links**. Nothing caught it because
  `mkdocs build` was never run with `--strict` in CI, and the generated pages were not in
  the nav. Fixed in the generator; `mkdocs build --strict` is now clean.

Per the gate-over-promise rule, the narrative page got one too: `validate_catalog.py` now
extracts every backticked snake_case token from `docs/dataset-catalog.md` and fails if it
is not a known case id — verified by planting a typo. That is the drift-control mechanism
`dataset-catalog-plan.md` required, and it covers 18 ids today.

The plan's geographic section needed correcting against the fixtures rather than
transcribing: only the **Point** baseline is at Copenhagen (the other five sit at
10–11.5°E, 49.8–51°N), the "UTM 33N tile" is at **40.65°N**, not Scandinavia, and
`optical_polar_small` lands at **64.4°N** — it exercises the polar stereographic
projection without being near a pole. Re-measuring paid off for the fourth batch running.

Also fixed: `project.urls` and `mkdocs.yml` pointed at GitHub while `origin` is GitLab.

Step 16, plus the dataset-catalog page. The page waits until here because its §7
(Remote / non-bundled) documents exactly the surface Batch 4 rewrites — writing it earlier
guarantees rewriting it.

Within the batch: land the generated per-case tables and their `--check` gate *before*
writing the narrative page, so the prose is built on verified data.

Release mechanics come last: `CHANGELOG.md` (noting the CLI entry-point removal as a
breaking change), version and classifier bumps, wheel-content verification, `twine check`,
TestPyPI dry run, then upload.

## Hard constraints

These are non-negotiable regardless of how the work is grouped.

| Constraint | Why |
|---|---|
| Step 11.1 before any release | Cannot publish a broken console-script entry point. |
| Step 12 before the first upload | PyPI artifacts are immutable; 36 MB would set a baseline that cannot be walked back. ✅ satisfied |
| Ruff normalization before the ruff gate | Otherwise the fix is to suppress the rules. |
| Step 13.4 before release | Classifiers and `requires-python` are published metadata. |
| Step 15 before Step 14.2 | `show_case` reports remote state. ✅ satisfied |
| **Steps 14.2 + 14.3 atomic** | Split, the internal `KeyError` masks the actionable error. ✅ satisfied |
| Batch 4 before the dataset-catalog page | §7 describes the surface Batch 4 changes. |
| Generated tables before the catalog narrative | The prose must rest on gated facts. |

## Two rules learned from Batches 1–4

**Verify the plan's empirical claims before acting on them.** Step 12's headline numbers
reproduced exactly (6844 KB → 240 KB), but its supporting argument did not survive
checking, and four separate figures across the planning documents were wrong — the case
count (130 vs 134), the raster count (26 vs 30), the format-enum size (16 vs 17), and the
`tiny` threshold headroom. Re-measure; do not inherit a number.

**Prefer a gate over a promise.** Every problem these batches fixed was something no gate
was watching: an unreachable console script, a 6.7 MB "tiny" fixture, a coverage matrix
counting 25 of 30. When a batch corrects a fact, add the check that keeps it corrected.

## If the priority is a fast first upload

Batches 1, 4, and 5 alone are sufficient to publish. All five are now done to the upload
boundary, so this section is retained only as a record of the reasoning. Batch 3 is what makes the release
*trustworthy* rather than merely *installable*, and it is the batch that prevents the next
round of drift — skipping it is a decision to accept that drift, not a way to avoid the
cost.
