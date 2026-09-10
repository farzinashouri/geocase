# Plan 43 — The Upstream Filing Queue, Ranked by Repo Liveness

> **Status: proposed 2026-09-06; Week 0 filings done, first response accepted
> 2026-09-06.** odc-stac#288 was confirmed by a maintainer within 12 hours —
> the first external agreement any round has produced, and the branch
> [Plan 39](39-going-public-upstream-first.md) §1.3 exists to reach.
> [Plan 42](42-round-5-consumer-selection-and-the-unfiled-backlog.md)
> Phase 1 put the 17 unfiled drafts at the head of the sequence and the first
> three are now **filed**. This plan schedules the remaining fourteen, and adds
> the criterion no prior plan applied: **is anyone still there to read it?**
> That question was not asked before filing, and asking it late cost two of the
> three originally selected drafts — one to an abandoned repository, one to a
> four-year-old duplicate. Both were caught before filing; neither would have
> been caught by re-reading the draft, because the defect in each case is real
> and the draft is correct. The failure mode is entirely external.

## Context

### The selection criterion that was missing

[Plan 38](38-six-consumer-round-2-and-the-stac-adapter.md) §5.1 selected three
drafts on **severity × cheapness to accept × breadth felt**. All three axes are
properties of the *finding*. None of them is a property of the *destination*,
and a report filed into a dead tracker produces no response no matter how good
it is — which matters because [Plan 39](39-going-public-upstream-first.md) §1.3
is explicit that **the response is the output, not the filing**.

Two of the original three failed on that axis:

| draft | what the check found |
|---|---|
| `stackstac-proj-code-unsupported.md` | Last commit **2024-08-10**; latest release the same day. Open issues include *"Has the project been abandoned?"* (8 comments, unanswered) and *"Update README.md with project status"*. The finding is **already filed as #262** (2024-11-28) with an **unmerged PR #263** carrying a fix, zero comments since. |
| `odc-stac-scale-offset-ignored.md` | Already filed as **#55** (2022-04-21), 13 comments, still open, last touched 2024-03-07. Four years old with a documented user workaround. |

Neither is a bad finding. `stackstac`'s is corroborated *by a third party who hit
it independently* — which is genuine external evidence and should be recorded as
such rather than discarded. But neither is a **filing opportunity**, and the
distinction is what this plan adds.

### Liveness is a ranking input, not a gate

A stale repo does not make a finding worthless — it makes *filing* the wrong
action for it. The three outcomes are different actions, not different
priorities:

- **live repo, no duplicate** → file
- **live repo, existing issue** → comment on the existing thread with the repro,
  do not open a second one
- **dead repo** → record the finding and the deadness; file nothing

### Measured liveness, 2026-09-06

Last-commit dates via the GitHub API. Note that `updated_at` is **not** usable
for this — it moves on stars and forks, and reports stackstac as active within
the last week. Commit dates were used throughout.

| repo | last commit | age | open issues | stars | verdict |
|---|---|---|---|---|---|
| `developmentseed/titiler` | 2026-09-04 | 2 days | 26 | 1173 | **live** |
| `developmentseed/lonboard` | 2026-09-01 | 5 days | 125 | 963 | **live** |
| `cogeotiff/rio-tiler` | 2026-09-01 | 5 days | 19 | 592 | **live** |
| `geopandas/pyogrio` | 2026-08-05 | 1 month | — | — | **live** |
| `opendatacube/odc-stac` | 2026-07-29 | 5 weeks | 17 | 202 | **live** |
| `corteva/geocube` | 2026-07-15 | 7 weeks | — | — | live-ish |
| `developmentseed/rio-stac` | 2026-04-02 | 5 months | 13 | 94 | slow |
| `geoarrow/geoarrow-python` | 2025-09-30 | 11 months | 12 | 95 | **stale** |
| `Toblerity/Fiona` | 2025-02-20 | 19 months | — | — | **stale** |
| `gjoseph92/stackstac` | 2024-08-10 | 25 months | 60 | 272 | **abandoned** |

## What was filed, 2026-09-06

Phase 1 of [Plan 42](42-round-5-consumer-selection-and-the-unfiled-backlog.md),
executed with the substitution described above.

| # | repo | draft | URL | filed | response |
|---|---|---|---|---|---|
| 1 | `opendatacube/odc-stac` | `odc-stac-crs-without-resolution-units.md` | [#288](https://github.com/opendatacube/odc-stac/issues/288) | 2026-09-06 | **accepted 2026-09-06** — see below |
| 2 | `cogeotiff/rio-tiler` | `titiler-rotated-affine-propagation.md` (root cause half) | [#993](https://github.com/cogeotiff/rio-tiler/issues/993) | 2026-09-06 | _pending_ |
| 3 | `developmentseed/titiler` | `titiler-invalid-format-500.md` | [#1493](https://github.com/developmentseed/titiler/issues/1493) | 2026-09-06 | _pending_ |

All three verified open with zero comments as of 2026-09-06T11:47Z.

### Filing #1 was accepted the same day

`odc-stac#288` drew a maintainer response **within 12 hours** — two comments from
Kirill888 on 2026-09-06, the second confirming the diagnosis outright ("basically
your assessment is correct"), naming the defective lines
([`_mdtools.py:1178-1179`](https://github.com/opendatacube/odc-stac/blob/d3345ed21efddb7aa1962990b734009602334d3f/odc/stac/_mdtools.py#L1178-L1179))
and sketching a fix — `resolution = convert_resolution(_res, crs, requested_crs)`,
with `requested_crs` captured from either `crs=` or an implied query polygon.

Verified independently on 2026-09-07 (odc-stac 0.5.3, odc-geo 0.5.3, rasterio
1.5.0, pystac 1.15.2), including the half the original report did **not** cover:
`bbox=` alone yields `(1, 18, 17)` — correct, both bbox and resolution native —
while the same `bbox=` plus `crs="EPSG:4326"` collapses to `(1, 1, 1)`. The
implicit query-polygon path is real.

Two corrections to the maintainer's sketch, raised on the thread rather than
patched around:

1. **Argument order.** At line 1178 `crs` has *already* been overwritten with the
   requested CRS at 1175-1176, so the source CRS survives only in `_crs`. The
   call is `convert_resolution(_res, _crs, crs)`.
2. **A scalar resolution has no exact conversion.** 10 m is a different number of
   degrees in x than in y at latitude 40.65, and different again at 70, so any
   implementation must choose a reference point. `odc-geo`'s
   `compute_output_geobox` already made that choice — which is the argument for
   delegating rather than reimplementing, and the open question put back to the
   maintainer.

This is the **accepted** branch of the Week 2 table, reached on day 0 rather than
day 14. It also contradicts the hedge recorded in U23 that odc-stac might be
"quieter than its commit date implies": the commit date was accurate.

`stackstac-proj-code-unsupported.md` was **withdrawn from the filing set** and
replaced by the rio-tiler rotated-affine report, per the liveness check above.

### A rendering defect in filing #1 — fix before anything else

**odc-stac#288 lost every code fence.** Verified through the API: the body
contains **zero** ` ``` ` markers, so the Python reproduction and the
root-cause snippet render as prose. rio-tiler#993 (8 fences) and titiler#1493
(6) are unaffected, so this is a paste artefact on one issue rather than a
systematic problem.

This is the most severe finding of either round and its reproduction is
currently unreadable. **Edit the issue body to restore the fences.** With zero
comments on the thread, a silent edit hours after filing costs nothing; leaving
it costs the finding its evidence.

This adds a seventh standing rule: **check rendering after filing.**

## The remaining fourteen, ranked

**Action** is the column that matters more than rank. `file+wait` means open the
issue and offer a PR only if the maintainer engages; `file+PR` means the fix is
small and uncontroversial enough that withholding it only adds a round-trip;
`comment` means an issue already exists and a second one would be noise;
`record` means file nothing.

| # | library | finding | sev | repo liveness | action | why this action |
|---|---|---|---|---|---|---|
| 4 | titiler | Colormap applied to `.npy`/`.tif`; class codes unrecoverable | MED | 2d | **file+wait** | Fix is a policy call about which formats are "numeric" — theirs to make, not ours to patch. |
| 5 | lonboard | Arrow validity bitmap dropped; null geometry → NaN,NaN | MED | 5d | **file+wait** | Live repo, different maintainer group, widens the response sample beyond STAC/titiler. Semantics of "absent" are a design question. |
| 6 | rio-tiler | `ImageData.mask` breaks its documented 0/255 contract | MED-LOW | 5d | **file+PR** | Contract violation against their own docstring; fix is mechanical. Found by review, not corpus. |
| 7 | lonboard | All-empty geometry frame raises instead of drawing empty | MED | 5d | **comment** | **Partial duplicate of [lonboard#146](https://github.com/developmentseed/lonboard/issues/146)** "Handle empty/missing geometries" (open since 2023-10, 2 comments). That issue reports `compute_view` crashing on empty points; ours is the same class. Add the repro there rather than opening a competing issue. |
| 8 | titiler | Bottom-up bounds republished; corrected request 500s | MED | 2d | **comment** | Same root cause as filing #2 (rio-tiler). Add as a comment there once #2 has a reply, rather than a third titiler issue. |
| 9 | pyogrio | `fid_as_index` + Arrow crashes on GeoJSON | MED | 1mo | **file+wait** | Live. Verify against current release first — this one is from round 1 and is the oldest draft. |
| 10 | pyogrio | GPKG spatial filter + Arrow admits NULL geometry | MED | 1mo | **file+wait** | Stagger behind #9. |
| 11 | titiler | Antimeridian source → out-of-spec TileJSON | LOW-MED | 2d | **file+wait** | Low severity; file last of the titiler set so the first three land on their merits. |
| 12 | rio-stac | Inverted `proj:bbox` for bottom-up rasters | MED | 5mo | **file+PR** | Slow repo — a ready patch is the only thing likely to move it. Small, well-localised. |
| 13 | geocube | `fill` silently ignored by default point method | MED-LOW | 7wk | **file+wait** | Live-ish. **Related but distinct: [geocube#152](https://github.com/corteva/geocube/issues/152)** asks to *document* that `fill` is numeric-only; ours is that it is silently ignored. File separately and reference #152 — a behavioural report on a docs thread gets read as a docs request. |
| 14 | odc-stac | Ambiguous band alias resolved silently | MED | 5wk | **file+wait** | ~~Hold until filing #1 returns~~ — **hold released 2026-09-06**, #1 was accepted the same day. Rule 5 (one issue per repo at a time) still applies while #288 is active, so file once #288 is resolved or goes quiet. |
| 15 | geoarrow-pyarrow | `as_geoarrow()` raises on all-empty array | MED | 11mo | **file+PR** | Stale repo, small fix. PR is the only realistic path. |
| 16 | geoarrow-pyarrow | GeometryCollection builds a name its own C core rejects | LOW-MED | 11mo | **file+PR** | Same; bundle with #15 if the maintainer responds at all. |
| 17 | geoarrow-pandas | `__eq__` violates ExtensionArray contract | MED | 11mo | **file+PR** | Stale, and the fix (`zip` without length check → guard) is unambiguous. |
| — | odc-stac | `raster:bands` scale/offset ignored | MED | 5wk | **comment** | **Duplicate of [#55](https://github.com/opendatacube/odc-stac/issues/55)**, open since 2022. Add the stackstac 10 000× comparison to that thread — it is sharper evidence than anything on it. Do not open a new issue. |
| — | geoarrow-pandas | Released version broken against released geoarrow-pyarrow | MED | 11mo | **record** | Version-pair breakage; likely resolved or moot by now. Re-verify before spending anything on it. |
| — | stackstac | Rejects every `pystac.Item` (`proj:code`) | HIGH | **25mo** | **record** | Abandoned repo; already [#262](https://github.com/gjoseph92/stackstac/issues/262) with unmerged [PR #263](https://github.com/gjoseph92/stackstac/pull/263). Record the independent corroboration; file nothing. |
| — | fiona | `Object.__eq__` / `Feature.__eq__` raise (2 findings) | MED | **19mo** | **record** | Fiona is in maintenance and superseded by pyogrio in most stacks. Low return on filing. |
| — | fiona | KML/LIBKML commented out of `supported_drivers` | LOW | 19mo | **record** | Same. |

### The `file+PR` rule this table applies

A PR accompanies the issue when **all three** hold: the fix is under ~20 lines,
it involves no API design choice, and the repo is slow enough that a patch is
the difference between action and silence. Where a design decision exists
(#4's format policy, #5's null semantics), the issue goes alone — a PR that
guesses wrong on a design question is *more* work for a maintainer to review
than an issue, which inverts the intent.

This is why filing #1 (odc-stac, 1×1 array) went out **without** a PR despite
being the most severe: the fix touches geobox derivation and the right answer is
probably to delegate to `odc-geo`'s `compute_output_geobox`, which is an
architectural call belonging to people who know why the mixed path exists.

## Timeline

Anchored on **filed 2026-09-06**. [Plan 39](39-going-public-upstream-first.md)
§1.4 sets the wait at *filed plus two weeks*, and explicitly warns against
letting an empty inbox at day 10 collapse the sequence back into "broadcast
anyway".

### Week 0 — 2026-09-06 to 09-08 (done / immediate)

- [x] File #1 odc-stac, #2 rio-tiler, #3 titiler.
- [x] **Record the three URLs** — [#288](https://github.com/opendatacube/odc-stac/issues/288),
      [#993](https://github.com/cogeotiff/rio-tiler/issues/993),
      [#1493](https://github.com/developmentseed/titiler/issues/1493) — in the
      table above, per Plan 39 §1.3.
- [x] **Restore odc-stac#288's code fences.** Done — verified 4 fence markers in
      the issue body on 2026-09-07.
- [ ] **Restore the fences on the 2026-09-07 reply comment
      ([#5570058250](https://github.com/opendatacube/odc-stac/issues/288#issuecomment-5570058250)),
      which lost them the same way.** The comment also states the origin as
      `5000000` where the transform in the same comment says `4500000`, and
      credits the item to `rio_stac.create_stac_item` when it was emitted by
      `geocase.stac` — visible in the pasted JSON's `id` and `collection`
      fields, so the attribution reads as concealment rather than omission.
      Both corrected in the edit.
- [ ] Correct [`docs/validation.md`](../validation.md)'s closing line
      *"Nothing has been filed upstream. These are drafts."* — false as of
      today. Land it together with [Plan 41](41-positioning-and-the-geometry-thesis.md)
      Phase 6's correction of the finding count to the surviving irreducible
      **two**. One pass over one file.
- [ ] Add the stackstac corroboration note (#262/#263) beside
      `stackstac-proj-code-unsupported.md`.

### Week 1 — 2026-09-09 to 09-15 (the wait; do the cheap check)

**No new filings.** Three open threads is the experiment; adding more while it
runs contaminates it.

- [ ] [Plan 42](42-round-5-consumer-selection-and-the-unfiled-backlog.md) §2.1 —
      verify the `[all]` packaging fix against the environment that broke.
      TDD: confirm the assertion **fails** on `1.0.0rc3` before confirming it
      passes on `1.0.0`. A pass on both legs means the reproduction is wrong.
- [ ] Comment on `odc-stac#55` with the stackstac 10 000× comparison. This is
      not a new filing — it is evidence added to a four-year-old thread, and it
      costs nothing against the experiment.
- [ ] Re-verify drafts #9/#10 (pyogrio) against the current release, since they
      are round-1 vintage and the oldest in the backlog.

### Week 2 — 2026-09-16 to 09-22

- [ ] Day 14 (2026-09-20) is the Plan 39 entry condition for broadcast,
      **regardless of response**. Assess what came back. **The first row already
      fired on day 0** — odc-stac#288 was accepted by a maintainer within 12
      hours — so the day-14 assessment is now about the other two threads and
      about whether #288 progresses to a fix, not about whether any response
      exists:

| what happened | what it means | next |
|---|---|---|
| any issue accepted or fixed | the claim becomes third-party-agreed | proceed to Plan 39 Phase 4 broadcast, citing it |
| any issue disputed | more informative than silence | record the dispute; it changes the article's framing |
| all three silent | a null result, and a **result** | broadcast anyway per §1.4, but the article says so plainly |

- [ ] File #4 (titiler colormap) and #5 (lonboard bitmap) — one per repo, two
      different maintainer groups. Only after the day-14 assessment.

### Week 3–4 — 2026-09-23 to 10-06

- [ ] File #6 (rio-tiler mask contract, **with PR**) and #7 (lonboard empty
      frame). Stagger #7 at least three days behind #5.
- [ ] File #9 (pyogrio), then #10 three days later.
- [ ] If filing #2 (rio-tiler rotation) has any reply, add #8 (titiler
      bottom-up) as a comment on the titiler side referencing it.

### Month 2 — October 2026

- [ ] The `file+PR` tail into stale repos: #12 (rio-stac), #15/#16/#17
      (geoarrow). These are low-expectation filings; batch them, and do not let
      them consume time that Phase 3 of
      [Plan 42](42-round-5-consumer-selection-and-the-unfiled-backlog.md) needs.
- [ ] File #11, #13, #14 as capacity allows.
- [ ] **Entry condition for [Plan 42](42-round-5-consumer-selection-and-the-unfiled-backlog.md)
      Phase 3** (the Shapely-vs-pyogrio vector differential) is met once the
      first three have been filed *and* two weeks have passed — not once all
      seventeen are filed. Round 5 can start in parallel with the October tail.

## Standing rules for every filing in this queue

Carried from [Plan 39](39-going-public-upstream-first.md) §1.2 and not
re-litigated:

1. **Search the tracker first**, open *and closed*. Two of the original three
   died on this check; it is not optional and it is not expensive.
2. **Verify the repro against the current release** immediately before filing,
   so "still reproduces on the latest version" is a statement of fact.
3. **No geocase link in the body.** A corpus link in a bug tracker reads as
   promotion. If a maintainer asks how it was found, that is the moment — an
   answer to a question rather than an unsolicited pitch, and the best evidence
   Plan 39 Phase 4 can cite.
4. **No origin story either.** "Found while unit testing" does no triage work
   and invites a follow-up question that a vague answer then has to walk back.
   Keep the factual scope observations ("31 of 34 rasters collapsed") — those
   are evidence, not provenance.
5. **One issue per repo at a time.** Two on the same day reads as a dump.
6. **Record accepted / fixed / disputed / ignored** with URL and date, against
   the draft it came from.
7. **Check rendering after every post — comments included, not just filings.**
   Learned twice on the same thread: odc-stac#288's body lost every code fence
   on paste, and so did the reply comment a day later, after the rule already
   existed. A rule scoped to "filing" did not cover the comment, so widen it:

   ```bash
   gh api repos/{owner}/{repo}/issues/{n} --jq '.body' | grep -c '```'
   gh api repos/{owner}/{repo}/issues/comments/{id} --jq '.body' | grep -c '```'
   ```

8. **Re-verify every factual claim in a comment, not only in the filing.** The
   same reply carried a wrong origin (`5000000` for `4500000`) that contradicted
   the JSON pasted beneath it, and an attribution to `rio_stac` for an item
   `geocase.stac` had produced. Rules 1 and 2 were written for filings; a reply
   to a maintainer who has just engaged is where a careless claim costs most.

## Decisions taken, 2026-09-06

Recorded so they are not re-litigated. All three were open questions when this
plan was drafted; the user settled them the same day.

| was | decision | reasoning |
|---|---|---|
| U21 — which three, and their URLs | **odc-stac#288, rio-tiler#993, titiler#1493** | Filed; verified open with zero comments. The stackstac slot was replaced by rio-tiler after the liveness check. |
| U22 — file the fiona findings? | **No — `record` only** | 19 months stale and superseded by pyogrio in most stacks. The two dunder violations are real, but a dead tracker produces no response, and the response is the output. |
| U23 — comment on `odc-stac#55`? | **Yes, comment** | The two-library 10 000× divergence is sharper evidence than anything currently on that four-year-old thread, and a comment opens no competing issue. ~~Revisit only if #288 draws no response~~ — **settled 2026-09-06: #288 drew a maintainer response in 12 hours, so the repo is exactly as live as its commit date implies.** Proceed with the #55 comment as planned. |

## Implementation notes

*To be completed as filings land and responses arrive.*
