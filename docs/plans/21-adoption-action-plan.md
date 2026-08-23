# Plan 21 — Adoption action plan

*Written before the rename; `geospatial-spec` is now `geofacts`.*

> **Status: proposed 2026-08-15.** Execution plan, not a strategy document. It does not
> supersede [Plan 20](20-restart-spec-first.md); it sequences Plan 20's open user actions
> (U16, U17) against the concrete release and adoption blockers measured in the working tree
> and against the live PyPI artifact on 2026-08-15.

## Premise

Release readiness is **not** the blocker. Measured, not assumed:

- `geocase 1.0.0rc1` is live on PyPI. `pip install "geocase[all]"` resolves in a clean venv
  (pip selects the rc because it is the only candidate), and the README quick start runs
  verbatim: **31 passed in 14.29s**.
- The distribution pipe therefore works today. What does not work is the funnel *around* it:
  nobody knows the project exists, the `Documentation` URL on the live PyPI page 404s, the
  README describes a category rather than showing a bug, and the quick-start assertions prove
  only that files load.

One item *is* fatal, and it is new: `pyproject.toml` now declares a hard
runtime dependency on `geospatial-spec>=0.1.0`, which exists only as a local directory
(`../geospatial-spec`) with no git remote and no PyPI presence. Tagging from `main` or
`spec_gaurd` today would publish a package that cannot be installed by anyone.

Four tracks follow. A and B start together; **A is the critical path**, because nothing can be
released until it is done.

---

## Track A — Publish `geospatial-spec`

*Unblocks every release. Plan 20's U16.*

- **You:** create the GitHub repo `farzinashouri/geospatial-spec`, and claim the PyPI name
  (`geospatial-spec` was free — 404 on 2026-08-15).
- **Me:** add the `git remote` and push `../geospatial-spec` (2 commits, already green: 42
  tests, ruff + mypy strict clean, zero dependencies verified by isolated install).
- **Me:** port the release workflow from `.github/workflows/release.yml`
  — same OIDC trusted-publishing shape, no stored tokens.
- **You:** configure the PyPI trusted publisher and the `pypi` environment on the new repo.
- **Me:** tag `v0.1.0`. **You:** approve the publish run.
- **Verify:** `pip install geospatial-spec` into a clean venv; assert zero transitive
  dependencies. That property is the package's entire adoption argument (Plan 20 trap 6).
- **Me:** add `geospatial-spec >=0.1.0` to the `run:` section of `recipe/meta.yaml`,
  which currently omits it.
- **Gate:** `pip install geocase` from a clean venv against real PyPI resolves. Until this
  passes, do not tag geocase.

## Track B — The five interviews

*Runs in parallel. Yours alone. Plan 20's U17 and its Phase 2 gate.*

- **You:** run the five interviews using the instrument already scaffolded in
  [`docs/evidence/2026-fixture-interviews/`](../evidence/2026-fixture-interviews/README.md).
- Lead with Rejector B's question, not a GeoCase pitch: *what is actually preventing your
  raster tests today?*
- Record each against `TEMPLATE.md`. Do not summarize until all five are in.
- **Gate (pre-committed in Plan 20, applied as written):** if ≥3 of 5 name dependency
  injection or hardcoded paths rather than fixture fidelity, the fixture half stops and Track
  C's framing changes from "fixtures" to "spec + guard." Do not relitigate the rule after
  seeing results.

This is the cheapest thing that can invalidate the most work: five conversations against
months of building.

## Track C — README rewrite around one real bug

*Independent of A and B. This is the artifact that survives being pasted into a Slack channel.*

- **Me:** write a ~15-line runnable demo of the nodata failure — 3 of 3 evaluations named it
  and the adopter confirmed it live (`0` as both nodata and valid dark pixel; bilinear
  resample with no `src_nodata` smearing a 4.6M-pixel region). Shape: naive normalizer,
  GeoCase fixture, wrong answer, one-line fix.
- **Me:** verify the demo against the *published wheel* in a clean venv, not the working tree.
- **Me:** restructure the README top third — bug demo first, category description second.
- **Me:** flip the install section. `pip install "geocase[all]"` leads; `pip install -e ".[dev]"`
  moves to a Contributing line; drop the "when a package release is published" hedge, because
  it is published.
- **Me:** cut roadmap and unbuilt-design links from *Learn More*
  ([`plans/development-plan.md`](development-plan.md),
  [`design/case-recommendation-service.md`](../design/case-recommendation-service.md)). User
  docs only.
- **Me:** make both quick-start examples assert something a reader cares about. The dateline
  example should test dateline behavior, not `gdf.crs is not None`.

## Track D — Docs site

*Small, but it is currently a dead link on a live PyPI page.*

- **Me:** add a `gh-deploy` job to CI on pushes to `main`. **You:** enable GitHub Pages.
- **Me:** drop the `Plans` and `Design` sections from the `mkdocs.yml` nav
  and add them to `not_in_nav`. They stay in the repo as an implementation log. They must not
  be on the public site while [Plan 20](20-restart-spec-first.md) publicly argues that the
  catalog a visitor just installed should be deleted.
- **Me:** fix [`docs/index.md`](../index.md) — "Status: alpha" contradicts the README's 1.0.
- **Me:** align the case count across README, docs and `recipe/meta.yaml`: 130 `case.yaml`
  files on disk, 134 reported by `geocase.list_cases()`.
- **Verify:** `mkdocs build --strict` green; the PyPI `Documentation` URL returns 200.

## Track E — Cut `v1.0.0`

*Last, and only after Track A's gate passes.*

- **Me:** bump `version = "1.0.0"` in `pyproject.toml`; promote `CHANGELOG.md` `[Unreleased]`
  to `[1.0.0]`.
- **Me:** tag `v1.0.0`. **You:** approve TestPyPI, smoke-install from it, then approve PyPI.
- **Me:** fill the real `sha256` in `recipe/meta.yaml` from the live sdist (currently a
  placeholder of zeros).
- **conda-forge: hold.** It is a two-line submission to `staged-recipes` once the sdist is
  live, and it buys nothing while the funnel is empty. Do it when someone asks.

---

## Sequencing

| When | A (spec) | B (interviews) | C (README) | D (docs) | E (tag) |
|---|---|---|---|---|---|
| Now | start | start | start | — | — |
| After A's gate | — | — | — | start | start |
| After B reports | revisit scope | — | reframe if the gate fires | — | — |

## Explicitly out of scope

New cases, coverage gates, conda-forge submission, Plan 20 Phases 4–5 (the $20 frontier run
and the catalog deletion), and any new API surface. Plan 20 sequences the deletion after Phase
1 ships *and* Phase 2 reports — that is Tracks A and B, so the deletion is downstream of this
document, not part of it.

## Success check at 4 weeks

`pip install geospatial-spec` works; `pip install geocase` works; the docs URL resolves; the
README shows a bug in the first screen; five interviews are recorded.

That is not 10 external users. It is the precondition for having any.
