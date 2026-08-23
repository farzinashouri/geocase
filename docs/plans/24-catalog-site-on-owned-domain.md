# Plan 24 — Publish the catalog on an owned domain

> **Status: proposed 2026-08-17.** A scoped implementation plan for one deliverable.
> The single roadmap remains [`development-plan.md`](development-plan.md).
>
> It **amends [Website Plan](archive/website-plan.md)**, which is largely built, and reverses two of
> its recorded architecture decisions: the rejection of Astro, and the deferral of a custom
> domain. Both reversals are argued in [Why the ground moved](#why-the-ground-moved) rather
> than assumed. Nothing else in that plan is superseded — its generator, its drift-control
> rule, and its content-cost warning all carry forward unchanged.
>
> This plan authorises publishing work only. It makes no claim that geocase has users, and
> it is not an adoption plan. See [What this is honestly for](#what-this-is-honestly-for).

## The one-line summary

The catalog site is built and has never been published. CI runs `mkdocs build --strict` at
`.github/workflows/ci.yml:88` and deletes the output. This plan renders the same generated
content as an Astro site on a domain you own, and publishes it.

## Measured starting state

Counted 2026-08-17 in this working tree, not inherited from [Website Plan](archive/website-plan.md).

| Website Plan deliverable | State |
|---|---|
| **A — catalog generator** | **Built.** `scripts/generate_catalog_pages.py`, gated at `.github/workflows/ci.yml:164` |
| Generated pages | **Committed.** 135 case + 36 risk + 16 format + 1 index = **188** |
| `Dataset` JSON-LD | **Built.** Present on all 135 case pages |
| Per-case thumbnails (was *deferred*) | **Built.** Inline SVG via `scripts/catalog_svg.py` |
| **B — landing page** | **Not built.** No `docs/index.html`, no `docs/stylesheets/` |
| **D — hosting** | **Not built.** `.github/workflows/` has `ci.yml` and `release.yml` only — no Pages deploy of any kind |

So the gap to a live site is hosting and a shell, not content generation.

Two content gaps are also measured, and both are cheaper than [Website Plan](archive/website-plan.md)
assumed:

- **119 `notes.md` files hold 12,176 words of hand-written prose that no page renders.**
  `generate_catalog_pages.py:369` mentions notes only to print the filename in a file listing.
  The prose is already structured as *Purpose / What to expect / Typical checks / Common
  failure modes*. "Common failure modes: latitude/longitude dimension swap, fill value ignored
  during analysis" is a search query; the templated sections around it are not.
- The generator's own comment concedes the rest: *"Descriptions are written for contributors,
  not searchers."* [Website Plan](archive/website-plan.md) sized rewriting them at 4–6 hours and called
  it *"the single largest determinant of whether the SEO argument pays off."* That estimate
  stands, but rendering the notes is the cheaper half of the same fix and should come first.

## Why the ground moved

[Website Plan](archive/website-plan.md) recorded its Astro rejection so it would not be relitigated.
Relitigating it anyway requires naming what changed, and three things did.

| Its reasoning then | Why it no longer holds |
|---|---|
| *"Contributors are Python developers. Adding npm to a Python repo is a real maintenance cost."* | [Plan 22](22-portfolio-direction.md) measured the contributor count at zero and the user count at zero. There is no contributor population to protect from a toolchain. |
| *"Astro/Starlight introduce a Node toolchain to buy polish rather than reach."* | The toolchain is no longer new. `~/projects/sanam_website` runs Astro 7 with MDX, `@astrojs/sitemap`, Netlify and three-locale i18n, and isolates the live domain to one file. It is a stack already operated, not one being adopted. |
| *"Custom domain — optional, deferred. github.io works fully."* | True when github.io was the only home. It is false the moment the catalog is also the portfolio artifact, because then the canonical URL has to be one you own. |

And one thing the earlier plan could not have anticipated, because it assumed a single host:

**Publishing to both GitHub Pages and an owned domain is actively harmful, not merely
redundant.** Duplicate content is not penalised, but Google picks one canonical and the other's
link equity is discarded — and it may not pick yours. The `schema.org/Dataset` JSON-LD makes it
worse than ordinary duplication: Google Dataset Search deduplicates on it and would plausibly
credit the `github.io` URL. **One published home. The owned domain.**

## Deliverable

### Phase 0 — the domain (blocking input)

The one thing this plan cannot supply. Register or nominate the domain, then follow the
`sanam_website` pattern: the live URL lives in exactly one file, and canonical tags, the
sitemap, `robots.txt` and JSON-LD `url` all read from it.

Until it is set, every phase below can be built against a Netlify preview URL. Only Phase 4
is blocked.

### Phase 1 — an Astro target in the generator

Add `--target {mkdocs,astro}` to `scripts/generate_catalog_pages.py`. The registry read, the
related-case ranking, the `MIN_HUB_CASES = 2` thin-content gate and the JSON-LD field mapping
are all target-independent and must not be duplicated — only the emitter changes.

The Astro target emits content-collection entries with typed frontmatter, and the page
templates live in the site repo. This is the split that lets the design change without
regenerating 188 files.

**URL structure**, which settles [Website Plan](archive/website-plan.md)'s open questions 1 and 2:

```
/                     landing
/catalog/             index
/catalog/cases/<id>/
/catalog/risk/<slug>/
/catalog/format/<slug>/
```

Top-level `/catalog/`, not `/_generated/catalog/`. The `_generated` prefix was honest about
provenance for a docs site and is noise in a public URL.

### Phase 2 — the site shell

An Astro site with a layout, the landing page [Website Plan](archive/website-plan.md) section B
specifies (problem statement → pytest snippet → what the catalog covers → install → links),
and the three catalog route templates. `output: 'static'`; no adapter unless a server route
is later added.

**Timeboxed, per the earlier plan's own warning:** the landing page has no objective "done".
Ship the first version.

### Phase 3 — the content pass (the part that decides whether any of this ranks)

1. Render `notes.md` into the case pages. 12,176 words of existing prose, currently invisible.
2. Rewrite case descriptions for searchers, not contributors. 4–6 hours, domain expertise,
   not automatable — [Website Plan](archive/website-plan.md) was right about this and it has not moved.

Phase 3 is not optional polish. 188 pages generated from one template with identical section
headings is the exact shape Google's helpful-content system demotes; the notes are the only
part of each page that is not templated.

### Phase 4 — canonical, sitemap, deploy

| Item | Choice |
|---|---|
| Canonical | The owned domain, emitted from the single site-config file |
| Sitemap | `@astrojs/sitemap` |
| GitHub Pages | **Not deployed.** No second copy exists, so there is nothing to canonicalise away |
| mkdocs | Keeps building under `--strict` in CI as an internal link check. Never published |
| Search Console | Register the domain property (DNS verification, which github.io could not offer) |

Once the site is live, drop the catalog from the mkdocs nav so the generator has one published
consumer. Not before — `mkdocs build --strict` is a working link gate today.

### Phase 5 — the measurement, pre-committed

This exists because [Plan 22](22-portfolio-direction.md) named the pattern: four gates, four
documents, zero users. A publishing plan with no gate repeats it.

**Ninety days after Phase 4 ships,** read Search Console:

- **Impressions on `/catalog/cases/*` from queries naming a failure mode** — nodata, dateline,
  antimeridian, CRS mismatch, invalid geometry — are the signal. Someone with the problem is
  looking for it.
- Impressions on navigational queries ("geocase") are not signal. They are you.

If the failure-mode queries are flat at ninety days, the SEO thesis is falsified and further
investment in the site stops. The pages stay up as a portfolio artifact, which is a use they
serve at zero marginal cost.

## Files

| File | Change |
|---|---|
| `scripts/generate_catalog_pages.py` | `--target {mkdocs,astro}`; render `notes.md` body into case output |
| `scripts/catalog_svg.py` | unchanged — SVG is portable across both targets |
| a new site repo (Astro) | **new** — layout, landing page, three route templates, site config |
| `.github/workflows/` | **new** — build the site, deploy to Netlify |
| `ci.yml` | extend the existing `--check` gate to cover both targets |
| `mkdocs.yml` | Phase 4 only: drop the catalog nav entry once the site is live |

The generated Astro content is committed, matching the `_generated/*-coverage-matrix.md`
precedent and keeping `--check` meaningful.

## Drift control (unchanged, and non-negotiable)

`--check` must cover the Astro target too. [Website Plan](archive/website-plan.md)'s rule stands
verbatim: *without this gate the pages silently desynchronize from the catalog on the first
case edit, and the site starts publishing assertions the code no longer makes.* Prefer a gate
over a promise.

## What this is honestly for

Recorded plainly so no later document has to discover it.

Publishing does not give geocase a use case. It does not help `passify` or `GeoCase_Studies`
either — [Plan 23](23-studies-passify-gap-audit.md) established those are two products sharing
a domain, and neither needs a fixture catalog. What publishing does is narrower:

1. **It answers the one objection [Plan 22](22-portfolio-direction.md) marks "correct, and
   unanswered"** — *the value is in the audit, not the runtime.* A published catalog delivers
   the audit to someone who takes no dependency, installs nothing, and never runs `pip`. Every
   other path in the portfolio requires adoption first. This one requires a page load.
2. **It is a portfolio artifact.** 188 pages with real prose is something to point at.
   A `1.0.0rc1` with zero users is not.
3. **It is the only passive instrument for the question the interviews were meant to answer.**
   [Plan 20](20-restart-spec-first.md) Phase 2 is still 0 of 5. Search traffic is weaker
   evidence than five conversations, but it accrues while you do something else.

The argument for it is cost, not value: the content is built and paid for, and the remaining
work is a shell and a deploy.

## What this does not authorise

New cases. A faceted filter UI. A blog. The recommendation service. Any GitHub Pages
deployment. Folding the catalog into an unrelated site — `sanam_website` is Dr Sanam Asadi
Faezi's dementia advisory site, a different person and a different audience, and 188
geospatial dataset pages would damage its topical coherence for no gain to yours.

And, per [Plan 22](22-portfolio-direction.md): no claim of adoption anywhere, including on a
résumé. Publishing pages is not users.

## Open inputs

1. **The domain.** Blocking for Phase 4 only.
2. **Site repo or this repo?** A separate repo keeps npm out of a Python project — the one
   piece of [Website Plan](archive/website-plan.md)'s reasoning that survives on its merits. The cost
   is that `--check` then spans two repos, which argues for generating into this repo and
   publishing from it. Recommend: **generate here, deploy from here**, and accept the
   `package.json`.
3. **Does Phase 3's description rewrite gate the launch, or follow it?** Launching first gets
   the pages indexed and ageing; rewriting first means the first crawl sees the better text.
   Recommend launching first — index age is the slower of the two clocks.
