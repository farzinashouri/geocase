# Effort track, four models at every effort level (read 2026-09-15, Fable added 2026-09-17)

> Evidence record for Plan 48 Phase 4. Source of every number:
> `python -m geocase.benchmark report --runs results/runs --by-effort`
> first run on 2026-09-15 over the fifteen `results/runs/*_effort-*`
> directories, rerun on 2026-09-17 after the Fable 5.1 arms landed.
> Haiku ran 2026-09-13, Opus 2026-09-14, Sonnet 2026-09-15, Fable 2026-09-16;
> all 23 `geo` tasks.

**Scope caveat.** Every column ran through `claude -p` and carries the Claude
Code harness preamble (`preamble: "claude-code-harness"`), so these numbers
are comparable within the effort track only. Never place them beside bare
numbers. Opus `@max` is excluded by the report (5 API failures out of 69
trials, not publishable), and so is Fable `@xhigh` (33 API failures). Haiku
`medium`/`high`/`xhigh` are k=1 and claim no reproducible-silent tasks.
Fable `@max` was not run.

## Summary table

Letters: C correct, T trapped (all controls pass, an edge returns a wrong value
silently), B broken (a control failed), L loud. Rates are over 69 trials for
k=3 columns and 23 for k=1 columns.

| Model | Effort | k | Correct | Trapped | B | L | Median s/call | Reproducibly silent (k>=3) |
|---|---|---|---|---|---|---|---|---|
| Haiku 4.5 | low | 3 | 65% | 17% | 6 | 6 | not recorded | geojson_bounds, s2_fixture |
| Haiku 4.5 | medium | 1 | 61% | 17% | 4 | 1 | not recorded | not claimed |
| Haiku 4.5 | high | 1 | 48% | 30% | 2 | 3 | not recorded | not claimed |
| Haiku 4.5 | xhigh | 1 | 57% | 22% | 4 | 1 | not recorded | not claimed |
| Haiku 4.5 | max | 3 | 58% | 19% | 12 | 4 | not recorded | buffer_m, s2_fixture |
| Sonnet 5 | low | 3 | 80% | 17% | 2 | 0 | 5.0 | buffer_m, geojson_bounds, s2_fixture, split_antimeridian |
| Sonnet 5 | medium | 3 | 83% | 14% | 2 | 0 | 6.7 | buffer_m, geojson_bounds, s2_fixture |
| Sonnet 5 | high | 3 | 87% | 13% | 0 | 0 | 17.0 | buffer_m, s2_fixture |
| Sonnet 5 | xhigh | 3 | 84% | 13% | 1 | 1 | 30.0 | buffer_m, geojson_bounds |
| Opus 5 | low | 3 | 94% | 1% | 3 | 0 | 19.9 | none |
| Opus 5 | medium | 3 | 88% | 4% | 5 | 0 | 34.5 | buffer_m |
| Opus 5 | high | 3 | 94% | 4% | 1 | 0 | 64.9 | buffer_m |
| Opus 5 | xhigh | 3 | 96% | 4% | 0 | 0 | 100.3 | buffer_m |
| Opus 5 | max | 3 | excluded | | | | | 5 API failures |
| Fable 5.1 | low | 3 | 96% | 4% | 0 | 0 | 14.7 | buffer_m |
| Fable 5.1 | medium | 3 | 96% | 4% | 0 | 0 | 23.6 | none |
| Fable 5.1 | high | 3 | 96% | 4% | 0 | 0 | 35.1 | buffer_m |
| Fable 5.1 | xhigh | 3 | excluded | | | | | 33 API failures |
| Fable 5.1 | max | | not run | | | | | |

Haiku durations are absent because that harness version did not record
`usage.duration_s`.

## Reading

1. **Model size dominates.** Trapped rate steps from 17-30% (Haiku) to 13-17%
   (Sonnet) to 1-4% (Opus and Fable). No effort level moves a model across
   those bands. Fable does not open a fourth band below Opus: all three
   published Fable arms sit at exactly 3/69 trapped, the same figure as Opus
   `medium`/`high`/`xhigh`.
2. **Effort is flat within a model.** Sonnet spans 17% to 13% across four
   levels; Opus spans 1% to 4% with `low` the best arm; Fable is 4% at every
   level. This extends the U27 negative (Plan 45, Haiku) to Sonnet, Opus and
   Fable.
3. **Effort costs real time.** Sonnet is 6x slower per call from `low` to
   `xhigh`, Opus 5x, Fable 2.4x from `low` to `high`. Sonnet `@xhigh` is
   slower than Opus `@low` and traps roughly 13x as often. Fable is faster
   than Opus at the same level (`high`: 35s against 65s per call) with the
   same trapped rate.
4. **The surviving traps are the same across models.** `buffer_m`
   (antimeridian) traps every model at nearly every level, Fable included
   (every trial at `low` and `high`, two of three at `medium`). `s2_fixture`
   (product-spec) and `geojson_bounds` (antimeridian) trap Haiku and Sonnet
   in every trial and neither Opus nor Fable ever. These are the catalog's
   strongest signal.
5. **Fable is the cleanest column.** Zero broken and zero loud trials across
   207 calls; the only non-`C` letters are the seven antimeridian traps
   (`buffer_m` x6, `area_m2` x1). Opus, by contrast, carries 3-5 broken
   trials at `low`/`medium` (`tag_points`, `to_rfc7946`).

## Ranking by a combined index (silent and loud failures)

The Reading above ranks on trapped rate alone, which ignores `B` and `L`. A
loud failure is cheaper than a silent one (a failing control or an exception
is visible; a wrong value is not), but it is still a failure. The **failure
index** below charges every trial and weights silent failures at twice the
loud ones:

```
index = 1 - (T + 0.5 * (B + L)) / n
```

`1.000` is every trial correct; `Correct` is what the index collapses to
when all failures are weighted equally, so both are shown. Counts are exact
from the task x model matrix (letters per trial, `n` = 69 for k=3, 23 for
k=1). Excluded arms (Opus `@max`, Fable `@xhigh`) are not ranked.

| Rank | Model | Effort | k | Correct | T | B | L | Silent | Loud (B+L) | Index |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Opus 5 | low | 3 | 65/69 | 1 | 3 | 0 | 1% | 4% | 0.964 |
| 2 | Opus 5 | xhigh | 3 | 66/69 | 3 | 0 | 0 | 4% | 0% | 0.957 |
| 2 | Fable 5.1 | low | 3 | 66/69 | 3 | 0 | 0 | 4% | 0% | 0.957 |
| 2 | Fable 5.1 | medium | 3 | 66/69 | 3 | 0 | 0 | 4% | 0% | 0.957 |
| 2 | Fable 5.1 | high | 3 | 66/69 | 3 | 0 | 0 | 4% | 0% | 0.957 |
| 6 | Opus 5 | high | 3 | 65/69 | 3 | 1 | 0 | 4% | 1% | 0.949 |
| 7 | Opus 5 | medium | 3 | 61/69 | 3 | 5 | 0 | 4% | 7% | 0.920 |
| 8 | Sonnet 5 | high | 3 | 60/69 | 9 | 0 | 0 | 13% | 0% | 0.870 |
| 9 | Sonnet 5 | xhigh | 3 | 58/69 | 9 | 1 | 1 | 13% | 3% | 0.855 |
| 10 | Sonnet 5 | medium | 3 | 57/69 | 10 | 2 | 0 | 14% | 3% | 0.841 |
| 11 | Sonnet 5 | low | 3 | 55/69 | 12 | 2 | 0 | 17% | 3% | 0.812 |
| 12 | Haiku 4.5 | low | 3 | 45/69 | 12 | 6 | 6 | 17% | 17% | 0.739 |
| 13 | Haiku 4.5 | medium | 1 | 14/23 | 4 | 4 | 1 | 17% | 22% | 0.717 |
| 14 | Haiku 4.5 | max | 3 | 40/69 | 13 | 12 | 4 | 19% | 23% | 0.696 |
| 15 | Haiku 4.5 | xhigh | 1 | 13/23 | 5 | 4 | 1 | 22% | 22% | 0.674 |
| 16 | Haiku 4.5 | high | 1 | 11/23 | 7 | 2 | 3 | 30% | 22% | 0.587 |

What changes once loud failures count:

1. **The model bands do not move.** Opus and Fable occupy 0.92-0.96, Sonnet
   0.81-0.87, Haiku 0.59-0.74. No effort level crosses a band on the index
   either, so the U27 negative survives the combined measure.
2. **Loud failures are a Haiku problem.** Haiku carries 17-23% loud trials
   against 0-7% for every other model; on the combined index Haiku `@max`
   drops below Haiku `@medium` (k=1) because of its 12 broken trials, which
   the trapped-only reading hid. Haiku's index gap to Sonnet is as much loud
   as silent.
3. **Opus `@low` still leads, but by less.** Its one trap is the best silent
   figure on the track, and the three broken `tag_points` trials cost it
   only 0.022 at half weight. Fable's three arms tie with Opus `@xhigh` at
   0.957 with zero loud trials; on `Correct` alone (equal weights) Fable and
   Opus `@xhigh` are ahead of Opus `@low` (66/69 against 65/69). The 1-2
   ranking is therefore a choice of weight, not a measured difference.
4. **Within Sonnet and Opus the index ordering follows trapped rate** except
   Opus `@medium`, which its 5 broken trials (`tag_points` x3, `tile_bounds`
   x2) push to last among the published Opus arms.

Sensitivity: at loud weight 0.25 Opus `@low` widens its lead (0.975); at
weight 1.0 (plain `Correct`) Fable and Opus `@xhigh` lead. Every ordering in
between keeps the three model bands intact.

## Tasks correct in every trial of every arm

Three of 23 tasks were `C` in all 16 published columns (Haiku 5, Sonnet 4,
Opus 4, Fable 3; 43 trials each):

| Task | trap_category |
|---|---|
| dedupe_geoms | canonical-equality |
| segment_intersection | collinearity |
| wkt_from_latlon | axis-order |

These three trap categories therefore carry no discriminating signal on this
track and are candidates for a harder variant or for retirement from the
`geo` domain when the task set is next revised.

Near misses, correct everywhere except one trial: `label_point` (one L,
Sonnet xhigh), `sample_at` (one B, Haiku max), `length_m` and `position_at`
(one L each, Haiku max).

## Quota state at the time of reading

On 2026-09-15 `.geocase_quota_claude.json` read `{"date": "2026-09-15",
"count": 337}` of a 400/day ceiling. On 2026-09-17 it read `{"date":
"2026-09-17", "count": 45}`, so 355 requests remained. The Fable `@xhigh`
refill (33 calls), the Opus `@max` retry (5 calls) and one full `@max` arm
(69 calls) all fit on 2026-09-17.

## Loose ends in `results/runs`

- `2026-09-14_claude-opus-5_effort-max`: 5 tasks failed at the API and are
  unscored; rerun the same command to retry only those.
- `2026-09-16_claude-fable-5-1_effort-xhigh`: 33 trials failed at the API and
  are unscored; rerun `configs/models-claude-effort-fable.yaml` to refill them.
- `2026-09-15_claude-opus-5_effort-low`, `2026-09-15_claude-fable-5-1_effort-low`,
  `2026-09-17_claude-fable-5-1_effort-low`: stray directories with no
  `run.json` (a `generated/` tree only); the report skips them. Discard or
  complete.
- Sonnet `@max` and Fable `@max` were not run; both configs have `max` dropped
  from their `effort` list with a comment saying how to add it back.
