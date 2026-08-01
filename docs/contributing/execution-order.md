# Execution Order

The sequencing view of the road to v1.0, merging the v1.0 release strategy with the
dataset-catalog work.

> **This document owns *order*, not *scope*.** What each step contains is defined once, in
> [`development-plan.md`](development-plan.md); the detailed rationale is in
> [`../plans/archive/10-v1-release-strategy.md`](../plans/archive/10-v1-release-strategy.md)
> and [`dataset-catalog-plan.md`](dataset-catalog-plan.md). If this page and the roadmap
> ever disagree about *what* a step includes, the roadmap wins. Keeping the split this
> narrow is deliberate: four documents each claiming to say "what's next" is what made the
> July 2026 roadmap collapse necessary.

## Status

**Batches 1–2 complete.** Bundled data 36 MB → 4.2 MB; wheel 458 KB; `pytest tests -q`
green on both Python 3.11 and 3.14.

| Batch | Contents | Checkpoint | Status |
|---|---|---|---|
| **1** | Roadmap collapse + Steps 11.1–11.5 | `pytest tests -q` green, no collection error, no console script | ✅ Done |
| **2** | Step 12 — catalog shrink, alone | checksums regenerate; SQLite tests pass; wheel size | ✅ Done |
| **3** | Step 13 — quality gates **+ the 4 catalog defects** | CI green on directory runs; coverage number recorded | ⬜ **Next** |
| **4** | Step 15 (public API) → Step 14 (manifests) | `__all__` pinned; remote-id error asserted both paths | ⬜ |
| **5** | Step 16 — docs truth pass, **dataset catalog**, release | `mkdocs build`; wheel holds all 134 cases; TestPyPI dry run | ⬜ |

## The batches

### Batch 3 — Quality gates you can trust ⬜ Next

Step 13, plus the four catalog defects surfaced by the dataset-catalog work. They belong
here rather than in Batch 5 because two of them are bugs *inside CI gates*, which is
precisely this batch's theme.

Order within the batch matters:

1. **`ruff format`** — whitespace only. Verify identical test output before and after, so
   it never pollutes `git blame`.
2. **`ruff check --fix`** plus hand-fixes for the residual N806/N811/E402/E501.
3. **Then** add the ruff CI job. Adding the gate first turns CI red on 1043 errors and
   makes `ignore = ["W191","E501"]` tempting, which would entrench the mixed indentation
   permanently.
4. Directory-based test runs replacing the allowlist; delete the three empty stub test
   files; mypy config fix; markers; non-blocking coverage.
5. **Catalog defects** (from [`dataset-catalog-plan.md`](dataset-catalog-plan.md)):
   fix the raster-matrix glob (reports 25, should be 30) and regenerate the gated
   artifact; extend the schema `format` enum from 7 to 17 values; resolve
   `affine_transform_quirk`.

**Re-measure first.** Do not trust the "18 mypy errors" baseline — `python_version` moved
from `3.9` to `3.11` in Batch 1, which should remove the bogus pattern-matching parse
error, so the real number is unknown.

### Batch 4 — Public API, then manifests ⬜

Step 15 before Step 14: `show_case` reports remote state, so the API has to exist first.

**Steps 14.2 and 14.3 must land in the same commit.** 14.3's `lru_cache` path raises an
internal-sounding `KeyError` that defeats 14.2's clear error message, so shipping them
separately ships a worse experience than shipping neither.

### Batch 5 — Docs, dataset catalog, release ⬜

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
| Step 15 before Step 14.2 | `show_case` reports remote state. |
| **Steps 14.2 + 14.3 atomic** | Split, the internal `KeyError` masks the actionable error. |
| Batch 4 before the dataset-catalog page | §7 describes the surface Batch 4 changes. |
| Generated tables before the catalog narrative | The prose must rest on gated facts. |

## Two rules learned from Batches 1–2

**Verify the plan's empirical claims before acting on them.** Step 12's headline numbers
reproduced exactly (6844 KB → 240 KB), but its supporting argument did not survive
checking, and four separate figures across the planning documents were wrong — the case
count (130 vs 134), the raster count (26 vs 30), the format-enum size (16 vs 17), and the
`tiny` threshold headroom. Re-measure; do not inherit a number.

**Prefer a gate over a promise.** Every problem these batches fixed was something no gate
was watching: an unreachable console script, a 6.7 MB "tiny" fixture, a coverage matrix
counting 25 of 30. When a batch corrects a fact, add the check that keeps it corrected.

## If the priority is a fast first upload

Batches 1, 4, and 5 alone are sufficient to publish. Batch 3 is what makes the release
*trustworthy* rather than merely *installable*, and it is the batch that prevents the next
round of drift — skipping it is a decision to accept that drift, not a way to avoid the
cost.
