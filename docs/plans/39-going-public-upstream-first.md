# Plan 39 — Going Public, Upstream First: The Release, the Site, and the Order the Broadcast Has to Happen In

> **Status: proposed 2026-08-31; Phase 0 done 2026-08-31 (0.1 and 0.2).** Six outward-facing actions were proposed
> together — cut a version, publish the docs site, contribute upstream, tell the
> user's manager, write an article, post on LinkedIn. Five of the six are
> **broadcast**; one is substance. This plan sequences them, and its central
> claim is that the order matters more than any individual item: **the upstream
> filings must come first, not last**, because they are the only action that
> produces *external* evidence, and every other item is a claim that gets
> stronger or weaker depending on whether that evidence exists. Phase 0 fixes the
> two things that make the current state unbroadcastable — a 404 documentation
> site and a validation report excluded from it. Phase 1 files three of the
> seventeen drafts and then **waits**. Phase 2 lands the divergence records while
> the wait runs. Phase 3 cuts `1.0.0`. Phase 4 broadcasts, in a fixed order, with
> the manager email deliberately ahead of the public posts. Phase 5 records the
> adoption input the round produced and nobody owns.
>
> **Phase 0 is done.** GitHub Pages is enabled with source *GitHub Actions*
> and <https://farzinashouri.github.io/geocase/> now serves. The unified
> validation report was **untracked** and
> excluded from the site build; it is now [`docs/validation.md`](../validation.md),
> tracked and in the nav, with `geocase_validate/` still excluded so the 17
> unfiled drafts stay unpublished.

## Context

[Plan 37](37-raster-signal-and-differential-adapters.md) and
[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) record two external
differential validation runs against ten libraries, unified in
[`docs/validation.md`](../validation.md):
**26 confirmed defects**, 19 found by the corpus, 7 by a review pass, **0 by
both**. Three runs have now established that the corpus finds real defects.

### The state this plan actually starts from

The proposal that prompted this plan was framed as "following the implementation
of plans 37 and 38". That framing is wrong about the state of the tree, and the
correction is load-bearing for the sequencing:

| claim | measured state, 2026-08-31 |
|---|---|
| Plans 37 and 38 are implemented | **Both are `proposed`.** No `known_divergences` records, no `geocase.stac`, no `compare_arrays`, no new cases. Nothing from either has landed. |
| "Publish a new version" | **`1.0.0rc3` is already on real PyPI**, not only TestPyPI — `rc1`, `rc2`, `rc3` all published, tagged `v1.0.0rc1..rc3`. So the action is `1.0.0`, not a first release. |
| "Publish the docs on GitHub Pages" | **`https://farzinashouri.github.io/geocase` returns 404.** `mkdocs.yml` names it as `site_url` and `.github/workflows/pages.yml` is committed and correct; Pages was simply never enabled in repository settings. |
| "Contribute to the open source libs" | **Nothing has been filed.** 17 ready-to-paste drafts sit in `~/projects/geocase_validator/issues/`, plus 2 round-1 reproductions in `geocase_validation/findings/`. |

Three of those four are cheap to fix and one of them — Pages — is a repository
setting with no code attached. But the fourth is the one this plan is organised
around.

### Why the upstream filings move to the front

[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) §5.1 states the risk
plainly and this plan adopts it as its premise:

> Three runs have now established that the corpus finds real defects. Zero have
> established that anyone wants them. That asymmetry is the largest open risk in
> the project and it is also the cheapest to reduce — the reports are already
> written.

Every broadcast item on the list is a claim addressed to a different audience —
a manager, an editor, a professional network — and each is materially the same
claim: *this corpus finds real bugs in software people depend on.* Today that
claim rests entirely on the author's own analysis of the author's own corpus.
One accepted upstream issue converts it into a claim a third party has agreed
with, in public, with a URL.

The converse is the actual risk. Broadcasting first stakes public credibility —
and a manager's read of the author's judgement — on a finding set that no
maintainer has yet looked at. If two of the three turn out to be known,
intentional, or wrong, that is a fact worth learning from a GitHub thread rather
than from a comment under a LinkedIn post. The filings are cheap, already
written, and reversible in a way a published article is not.

**A dispute is also a result.** [Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md)
§5.1 already says a dispute is more informative than silence; that holds here
too. The purpose of Phase 1 is not to be agreed with, it is to find out.

### What the corpus's own record says about publishing too early

[Plan 28](28-validate-geocase.md) Phase 1 found six geocase cases declaring
nodata with zero nodata pixels, and `hole_center_nodata` shipping as the inverse
of its description — in a corpus that was already being described publicly as
curated. [Plan 37](37-raster-signal-and-differential-adapters.md) recorded a
validation run reporting pyogrio **clean** while two live defects sat in the
case metadata it had already loaded. Round 2 reported **five false lonboard
findings** from one CRS equality check, caught only because every divergence was
hand-verified before write-up.

The pattern in all three is the same: the claim was made slightly before the
evidence supported it, and the correction was cheap only because nothing had been
published yet. This plan's ordering is that lesson applied to the project's own
public surface.

### What this plan does not do

- It does not implement [Plan 37](37-raster-signal-and-differential-adapters.md)
  or [Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md). Those stand as
  written and keep their own phases. Phase 2 here pulls **only** their Phase 1
  work forward, and says why.
- It does not settle the distribution question. That is
  [Plan 25](25-ship-geocase-as-a-package.md) and
  [Plan 21](21-adoption-action-plan.md); Phase 5 records the input and hands it
  over.
- It does not write the article's prose, the email's prose, or the post's prose.
  It fixes what must be true before each is written, and the order.

---

## Phase 0 — Make the current state broadcastable

Two defects make every downstream item worse, and both are small. Neither is a
code change to `src/`.

### 0.1 Enable GitHub Pages — **done 2026-08-31**

`.github/workflows/pages.yml` is committed, correct, and triggers on push to
`main` and on `workflow_dispatch`. It builds with `mkdocs build --strict` and
deploys via `actions/deploy-pages@v4`. The site 404s because **Pages is not
enabled in repository settings**, which is a browser action the workflow cannot
perform for itself — the same class of step
[Plan 36](36-rc3-release-runbook-and-crs-mismatch.md) §1 records for the PyPI
environments.

Settings → Pages → Source: **GitHub Actions**. Then `workflow_dispatch` the
workflow rather than waiting for a push, and confirm
`https://farzinashouri.github.io/geocase` serves the home page and that the
Catalog hub reaches the per-case pages.

Do this **first and unconditionally**, independent of every other decision in
this plan. Every remaining item links to that URL.

**Done 2026-08-31.** Two things turned out differently from the plan:

- **It is not only a browser action.** The REST API does it —
  `gh api -X POST repos/farzinashouri/geocase/pages -f build_type=workflow`,
  which needs no scope beyond the `repo` one `gh auth` already holds. Worth
  recording for the next repository, since §0.1 was written off as unautomatable
  on the same grounds as [Plan 36](36-rc3-release-runbook-and-crs-mismatch.md)
  §1's PyPI environments, and only one of the two actually is.
- **Enabling defaults to the wrong source.** Creation came back as
  `build_type: legacy` (branch `main`, path `/`) despite the `build_type` field,
  which would serve the repository root rather than the workflow's artifact. A
  follow-up `PUT` on the same endpoint set it to `workflow`; **verify the
  `build_type` after enabling rather than assuming the POST took.**

Verified after a `workflow_dispatch` run of `pages.yml` (run 33433829139,
`success`): the home page serves `200`, the catalog hub at
`/_generated/catalog/` serves `200`, and a per-case page
(`/_generated/catalog/cases/antimeridian_crossing_line/`) serves `200`.
`/validation/` still 404s — correct, and not a Pages defect: §0.2's
`docs/validation.md` is in the working tree and not yet on `main`, so it
publishes with the commit that lands it.

### 0.2 Promote the validation report to a published path — **done 2026-08-31**

The article recommended in Phase 4 is essentially the unified validation report,
which is already written and is the strongest prose in the repository. Two
things were wrong with where it lived:

- **It was untracked.** The other five files in `docs/geocase_validate/` are in
  git; this one had never been added, so it existed only in the working tree.
- **It was reachable at no URL.** `mkdocs.yml` `exclude_docs` removes
  `geocase_validate/` from the build entirely — not merely from the nav — with
  the recorded rationale *"external validation reports and upstream bug drafts"*
  ([Plan 30](30-unpublish-internal-docs-and-surface-catalog.md)).

That exclusion was correct while the drafts were unfiled and the findings
unconfirmed. It stops being correct the moment the report is the thing being
linked from an article, a manager email and a LinkedIn post.

Three options were considered:

1. **Drop `geocase_validate/` from `exclude_docs`.** Publishes the report *and*
   the 17 unfiled issue drafts, which is exactly what the exclusion exists to
   prevent — publishing 17 unfiled accusations against named libraries is a
   worse first impression than publishing none.
2. **Link the GitHub blob URL.** Works with no change, and the folder rules in
   [`index.md`](index.md) already require a GitHub URL rather than a relative
   path for excluded trees. But a raw markdown blob is a poor landing page for
   an article submission.
3. **Promote one page, leave the tree excluded.**

**Taken: option 3.** The report moved to [`docs/validation.md`](../validation.md),
is tracked, and is in the nav as *Validation Report* — placed after *Philosophy*
and before *Catalog*, since it is the argument for why the catalog exists.
`geocase_validate/` stays excluded as-is, so the drafts, per-case JSON and repro
scripts remain unpublished.

Three edits the move required, none of them to the report's substance:

- **Frontmatter.** Added a `description:`, matching every other published page.
- **The closing section was machine-local.** *"Where the raw material lives"*
  listed `geocase_validation/` and `geocase_validator/` as bare paths, which
  mean nothing to a public reader, and named a plan file that is not published.
  Rewritten to say plainly that the harnesses and drafts are held outside the
  repository, and to link the three relevant plans by **GitHub URL** — the form
  [`index.md`](index.md) requires, since a relative link into `plans/` fails
  `mkdocs build --strict`.
- **The one in-page anchor link** (`#the-two-methods-never-overlap`) survives the
  move unchanged; there were no other links.

**Still owed, and it is a Phase 4 edit rather than a Phase 0 one:** the report's
closing line reads *"Nothing has been filed upstream. These are drafts."* That
is accurate today and becomes false the moment Phase 1 runs. A published page
carrying it invites the reader to ask why nothing was filed — so either Phase 1
lands before the site goes live, or the line is updated with it. See §4.2.

---

## Phase 1 — File three upstream issues, then wait

This is the phase the plan exists to move to the front.
[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) §5.1 already selects
which three and why; this plan changes **when**, not **what**.

### 1.1 File exactly three

All 17 drafts are confirmed present in
`~/projects/geocase_validator/issues/`. File these three:

| draft | why this one |
|---|---|
| `odc-stac-crs-without-resolution-units.md` | The most severe finding of either round — `load(item, crs="EPSG:4326")` returns a **1×1 array** because a 10-*metre* resolution is carried unconverted into degrees. Self-contained repro, named root cause at `_mdtools.py:1166-1181`. |
| `titiler-invalid-format-500.md` | The cheapest to accept: a one-line `DEFAULT_STATUS_CODES` addition. Low-friction acceptances are worth filing precisely because they test the *channel* rather than the finding. |
| `stackstac-proj-code-unsupported.md` | The most broadly felt — it breaks the library's own documented `item_collection()` workflow against any current pystac, so the maintainer can reproduce it without the corpus or the repro. |

The remaining fourteen stay unfiled pending what these three return. Plan 38's
reasoning holds and is not re-litigated here: seventeen issues from an unknown
reporter read as automated output and get triaged as a batch; three well-formed
reports get read individually.

### 1.2 File them as a person, not as a project

Every draft is standalone — it builds its own file and imports only the library
under test, so none asks a maintainer to install geocase. Keep it that way in
the issue body: **do not link geocase in the initial report.** The issue is about
their bug, and a link to a corpus reads as promotion in a bug tracker, which is
the fastest way to have a good report dismissed.

If a maintainer asks how it was found, that is the moment the corpus gets
mentioned, and it is a far better moment — an answer to a question rather than an
unsolicited pitch. That exchange, if it happens, is also the single best piece of
evidence Phase 4 can cite.

### 1.3 Record what comes back, against each draft

Accepted / fixed / disputed / ignored, with the issue URL and the date, recorded
beside the draft it came from. This is the phase's actual output — not the
filing, the **response**. Plan 38 §5.1 already asks for this; Phase 4 depends on
it.

### 1.4 The wait is the experiment, not dead time

Maintainer response is typically 1–4 weeks and may be zero. Phase 2 runs during
it. Do not let an empty inbox at day 10 collapse the sequence back into
"broadcast anyway" — a null result is a result, and it should change the article's
framing rather than be omitted from it.

**Entry condition for Phase 4 is not "all three accepted".** It is *"the three
have been filed and at least two weeks have passed"*, so that the article can
state accurately what happened, including nothing.

### 1.5 Verify the coverage-probe table before quoting it anywhere

[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) Context carries a
table asserting **zero tests mentioning rotation or a bottom-up affine** in
stackstac, odc-stac, titiler, lonboard and geoarrow-pyarrow — and states its own
method limit: *"this is a keyword probe, not a semantic audit. A test could
construct a rotated transform without using the words 'rotate' or 'skew'."*

That number is about to be put in front of the maintainers of those five
libraries, in an issue thread or an article. **Confirm it by reading before
quoting it**, and carry the method limit with it wherever it goes. Plan 38's
Verification already requires this; it is repeated here because Phase 4 is where
the temptation to quote it unqualified actually arrives.

---

## Phase 2 — Land the divergence records while the wait runs

Pull **only** Phase 1 of Plans 37 and 38 forward. Not their adapters, not their
new cases.

### 2.1 Why this subset, and why now

Three reasons it is the right work for the waiting period:

- It is the only **bug-risk** item on the whole outward-facing list. Both
  transform conventions that produced the most severe findings of both rounds are
  carried by exactly one case each, and nothing gates them. A future fixture
  regeneration that quietly normalises `rotated_two_islands` north-up or
  `bottom_up_dem_small` top-down would silently delete the corpus's only coverage
  of its most productive axis — and would do so *after* the axis has been
  publicly claimed as the corpus's central result.
- It is small, TDD, and adds **no cases**, so it cannot move the case count and
  does not fire the seven-file count gate
  ([Plan 36](36-rc3-release-runbook-and-crs-mismatch.md) §2 measured it).
- It makes the release in Phase 3 honest: a `1.0.0` shipping the cases that found
  26 defects, with the divergences recorded and the conventions gated, is a
  defensible thing to point an article at.

### 2.2 Scope, by reference

- [Plan 37](37-raster-signal-and-differential-adapters.md) §1.1, §1.2, §1.3 —
  the two rio-tiler records, regeneration, and
  `tests/unit/test_transform_conventions.py`.
- [Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) §1.1, §1.2, §1.3 —
  the nine case/consumer records, the extended convention gate (scales, offsets,
  colormaps, the unwrapped dateline bound), and regeneration.

Both plans specify the failing test first and both must be watched fail. Follow
each plan's own text; this phase adds no new requirements to them.

**Deliberately still out of scope here:** `geocase.stac`, `compare_arrays`, the
option-pair matrix, the CRS-aware predicate, and all four new cases. Those are
Phase 3 decisions in Phase 3 of *this* plan, below.

### 2.3 Mark both plans as partially implemented

Per CLAUDE.md's progress rule: flipping only the phases that landed, in both
plan docs and both `index.md` rows — `Phase 1 implemented YYYY-MM-DD; Phases 2-N
pending`. A plan doc reading "proposed" after its Phase 1 shipped is the bug that
rule exists to prevent.

---

## Phase 3 — Cut `1.0.0`, not another release candidate

### 3.1 The version decision, with the reasoning

**Ship `1.0.0`.** The case for a fourth release candidate is weak:

- **The risk rc3 was spent on is retired, and was measured, not assumed.**
  [Plan 36](36-rc3-release-runbook-and-crs-mismatch.md) cut rc3 specifically
  because [Plan 28](28-validate-geocase.md) Phase 3 took the payload 2.1 → 5.1 MB
  and the wheel 456 KB → 1.25 MB after the rc2 rehearsal, and PyPI is immutable.
  It then measured green: wheel 1251 KB, sdist 1003 KB, 153/153 cases.
- **The compatibility surfaces have not moved.** CLAUDE.md pins two: the pytest
  workflow (fixtures and markers) and `__init__.py`'s `__all__`. Neither Phase 2
  above nor Plans 37/38 Phase 1 touches either — `known_divergences` is an
  existing model field and the new tests are tests.
- **Three external runs have exercised the corpus harder than any release
  rehearsal would.** 154 cases read by ten libraries across two independent
  rounds is a stronger integration signal than a fourth rc sitting on TestPyPI
  waiting for nobody to install it.
- **An rc cannot be cited.** Every broadcast item in Phase 4 says "pip install
  geocase". `1.0.0rc3` requires `--pre`, which is friction at exactly the moment
  a reader's interest is highest, and it signals *not finished* to a manager and
  an editor both.

### 3.2 The one real question: what is in `1.0.0`'s public surface

PyPI is immutable and `1.0.0` is where the compatibility promise starts, so this
must be settled deliberately rather than by default.

[Plan 37](37-raster-signal-and-differential-adapters.md) Phase 2 adds
`compare_arrays` to `differential.py`;
[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) Phase 2 adds a new
`geocase.stac` module. **Ship `1.0.0` without both**, and here is why that is
safe rather than merely faster:

`differential` is already documented in CLAUDE.md as *"not in `__all__` — a
submodule import, like `geocase.raster`"*. `geocase.stac` can join it on exactly
the same terms in `1.1`. Both are **additive**: adding a module and adding a
function to a non-`__all__` module breaks no pinned surface, so neither needs to
precede `1.0.0` to avoid a breaking change later.

The alternative — hold `1.0.0` for a month while Plans 37 and 38 build their
adapters — trades a shipped release for a more complete one, at the exact moment
the project's largest open risk is *external interest*, not internal
completeness. A `1.0.0` that exists beats a `1.0.0` that is finished.

**Record this as a decision, not an omission**, in the release notes: the
differential adapter protocol and the STAC adapter are `1.1`, and the plans that
build them are named.

### 3.3 The mechanics are already written

[Plan 36](36-rc3-release-runbook-and-crs-mismatch.md) Phase 1 is the runbook and
it is executable as-is with the version string changed: version bump on a branch
so the pull request carries it and CI verifies the artifact against the same
`pyproject.toml` a reviewer reads, the 3.11-floor CI watch that a local
conda/3.14 run cannot substitute for, merge, tag from `main`, approve the
environment.

Two differences from rc3, both browser steps:

- The tag is `v1.0.0`, which routes to the **`pypi`** environment rather than
  `testpypi`. `release.yml` already has both jobs, each gated on an environment
  approval, with the recorded rationale that *"cutting a tag and uploading should
  not be the same action, because the upload cannot be undone."*
- `1.0.0` is final: there is no rc4 to correct it with. Run the full gate list in
  Verification below before tagging, not after.

### 3.4 Do not skip the rehearsal just because rc3 was green

rc3 was green *at rc3*. Phase 2 lands `known_divergences` records on eleven
cases, which moves every per-case catalog page and both content gates. Re-run
`verify_dist.py` and confirm the case count is unchanged at **154** before the
tag.

---

## Phase 4 — Broadcast, in a fixed order

Entry condition: Phase 0 done, Phase 1 filed **and** at least two weeks elapsed,
Phase 3 tagged and on PyPI. The order within this phase is not arbitrary and is
the second-most important claim in this plan after "upstream first".

### 4.1 The manager email — **before** the public posts

Ahead of the article and the post, for two reasons that have nothing to do with
courtesy:

1. **Employment and IP.** Personal-time work on public open source is
   ordinarily uncontroversial, but the question of whether an employer has a
   claim on it, or a policy about publishing under one's own name, is one to
   surface **privately, by the author, first** — not to have raised by someone
   else after a LinkedIn post has been seen. If there is any friction, it is far
   cheaper here.
2. **A manager who reads about it publicly first has been mildly embarrassed**,
   and that is a wholly avoidable cost for something that reflects well.

What the email should contain, shortest form that survives:

- **Lead with the outcome, not the project.** *"I found and reported N defects in
  widely-used geospatial libraries"* — a defect count in named, depended-upon
  software is legible to a manager in a way "I built a test corpus" is not.
- **State plainly that it is personal-time work on public open source**, with
  the PyPI and Pages links. Do not bury this.
- **Name whichever of the ten libraries are in the team's own stack**, if any.
  This is the line that turns it from a hobby into demonstrated relevant
  expertise, and it is the only line that has any chance of changing what work
  comes the author's way.
- **Whatever Phase 1.3 recorded**, stated accurately — including "filed, no
  response yet". A manager who later sees a dispute on one of the three should
  have heard the caveat from the author first.

### 4.2 The article

The text is 90% written:
[`docs/validation.md`](../validation.md).
It has a thesis, a number, and evidence, which is more than most published
technical writing has. Do not dilute it into a project announcement.

**Where to publish, ranked for this specific piece:**

1. **Own site — the Phase 0.2 published page — then submit to Hacker News.**
   Keeps canonical ownership, and *"we found 26 bugs in 10 geospatial libraries,
   and code review found none of the same ones"* carries itself as a title. The
   piece is technical enough not to need a venue's audience.
2. **[Cloud-Native Geospatial Forum](https://cloudnativegeo.org/) blog.** The
   *correct* audience: STAC, COG, odc-stac, stackstac and titiler are core CNG
   ecosystem tooling, and they accept community posts. Highest signal per unit of
   effort of any venue here.
3. **The communities where the maintainers actually read** — Pangeo Discourse,
   the STAC Slack, OSGeo/GeoPandas discuss. Not "publishing", but this is where a
   maintainer who might adopt the corpus will see it.

Skip Medium and Towards Data Science: wrong audience, paywall friction, and the
venue itself makes careful technical work read as content marketing.

**Two editorial notes on the existing text:**

- **The title oversells relative to the body.** *"What ten geospatial libraries
  got wrong"* is adversarial; the content is careful, fair to the libraries, and
  explicitly notes that *"neither library wins"* in its best comparison. Lead
  with the method instead — **the two methods never overlap** is the more
  interesting claim, the less inflammatory one, and the one that will get cited.
  A defect count invites a defensive reading from exactly the maintainers whose
  goodwill Phase 1 is trying to earn.
- **The closing line must be corrected before publication.** It currently reads
  *"Nothing has been filed upstream. These are drafts."* After Phase 1 that is
  false, and it is the single most load-bearing sentence in the document for a
  reader deciding whether to take it seriously. Replace it with what was filed,
  where, and what came back.

### 4.3 LinkedIn, last and shortest

Link the article; do not reproduce it. The hook that works is the **zero-overlap
finding**, not the defect count — a count reads as dunking on other people's
libraries, the zero reads as a method insight, and the second is both truer to
the work and better for the author.

One concrete example earns its place. The odc-stac finding is the most visceral:
*a ten-metre pixel became a ten-degree pixel, and a 16×16 raster came back as a
single cell.*

---

## Phase 5 — Record the adoption input nobody owns

[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) §5.3 flags a
distribution question and explicitly declines to settle it, handing it to
[Plan 25](25-ship-geocase-as-a-package.md) and
[Plan 21](21-adoption-action-plan.md). It has not been picked up, and this plan
will not settle it either — but it should not be lost between three documents.

The input, restated so it survives:

> Nobody downloads a corpus; people do add a dev-dependency. The strongest
> adoption argument round 2 produced is that **the corpus's best cases are
> missing from the test suites of every library it was run against** — zero of
> five have a test mentioning rotation or a bottom-up affine. The delivery shape
> that acts on that directly is a `pytest` fixture pack a library adds to its own
> CI in one line, not a dataset a consumer must discover, download and write a
> harness against.

### 5.1 Why this is the real follow-up to Phase 1

If any of the three filed issues is accepted, the natural next message in that
same thread is *"here is a two-line dev-dependency that would have caught this."*
That is a far stronger adoption path than an article, because it arrives with the
bug as its evidence, in front of a maintainer who has just agreed the bug is
real, at the moment they are deciding what to do about it.

**It requires the fixture pack to exist**, which it does not. Phase 5's
deliverable is therefore a decision recorded in
[Plan 21](21-adoption-action-plan.md) or
[Plan 25](25-ship-geocase-as-a-package.md) — with a row in
[`index.md`](index.md) — about whether that pack is built, and if so when. Not
built here.

### 5.2 Do not let Phase 4 substitute for it

An article and a post are broadcast; they produce readers. A fixture pack in a
consumer's CI produces a *user*. Three runs have produced no users, and Phase 4
is not designed to change that. Recording the distinction is the point of this
phase.

---

## Verification

**Phase 0**
- `https://farzinashouri.github.io/geocase` returns 200 and serves the home page;
  the Catalog hub reaches a per-case page.
- `mkdocs build --strict` passes with the promoted validation page in the nav,
  and no relative link from a published page into `plans/` or `geocase_validate/`.

**Phase 1**
- Three issue URLs recorded, with dates, against their drafts; the other
  fourteen remain unfiled.
- No filed issue body links geocase.
- The Plan 38 coverage-probe table has been confirmed by reading, not only by
  grep, before it appears in any issue or article.

**Phase 2**
- `tests/unit/test_known_divergences.py` and
  `tests/unit/test_transform_conventions.py` each fail first, then pass.
- `python scripts/build_case_index.py --check`, `scripts/validate_catalog.py`,
  `scripts/validate_case_content.py`,
  `scripts/generate_catalog_pages.py --check` all green.
- Case count unchanged at **154**.
- Plans 37 and 38 and both `index.md` rows reflect Phase 1 implemented.

**Phase 3**
- Full gate list green under the conda env before tagging:

```bash
conda activate geocase
pytest tests -q
python scripts/build_case_index.py --check
python scripts/validate_catalog.py
python scripts/validate_case_content.py
python scripts/generate_checksums.py --check
python scripts/generate_catalog_pages.py --check
ruff format --check src tests && ruff check src tests
mypy src
mkdocs build --strict
python scripts/verify_dist.py   # case count 154, wheel/sdist sizes
```

- CI green on the 3.11 floor, from the pull request — not from a local 3.14 run.
- `v1.0.0` tagged from `main`; the `pypi` environment approved as a separate,
  deliberate action.
- Release notes name the `1.1` deferral of `geocase.stac` and `compare_arrays`,
  and the plans that build them.

**Phase 4**
- The manager email precedes the article and the post.
- The published report's closing line states what was filed and what came back,
  and no longer says "Nothing has been filed upstream."
- The coverage-probe table, wherever quoted, carries its stated method limit.

**Phase 5**
- The fixture-pack decision is recorded in Plan 21 or Plan 25 with an `index.md`
  row, or explicitly declined there with a reason.

---

## Sequencing summary

| when | phase | blocking? |
|---|---|---|
| day 0 | 0.1 enable Pages | no — do immediately, unconditionally |
| day 0–1 | 1.1–1.2 file three issues | **blocks Phase 4** |
| ~~day 0–1~~ **done** | 0.2 promote the report to `docs/validation.md` | blocks 4.2 |
| week 1–3 | 2 divergence records + convention gates | blocks Phase 3 |
| week 1–3 | 1.5 verify the coverage probe | blocks 4.2 |
| week 3–4 | 3 cut `1.0.0` | blocks Phase 4 |
| week 4+ | 4.1 manager email | blocks 4.2, 4.3 |
| week 4+ | 4.2 article, then 4.3 LinkedIn | — |
| any time | 5 record the fixture-pack decision | no |

The only hard rule in the table: **nothing in Phase 4 ships before Phase 1 has
been filed and given time to answer.**
