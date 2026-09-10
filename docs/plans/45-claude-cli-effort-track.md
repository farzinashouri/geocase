# Plan 45 — The Effort Axis: A Second Track Whose Cost Is Rate Limits, Not Dollars

> **Status: Phases 1–5 implemented 2026-09-10. The 140-call pilot has not been
> run, so U27 is still open and the sweep's verdict is not in.**
> The track is built, gated and documented; what remains is measurement.
> A Max subscription cannot fund the bare track, and the reason is not billing —
> it is that `claude -p` has **no bare-completion mode**. Every invocation carries
> ~23 800 tokens of Claude Code harness preamble that no flag removes, which
> makes `prompt_sha256` stop describing what the model saw. But the same CLI
> exposes `--effort` (`low`/`medium`/`high`/`xhigh`/`max`), and on the
> antimeridian prompt that knob moved thinking tokens from **46 to 3 965** — an
> ~86x spread on one model, one prompt. That is an experimental axis the
> OpenRouter path cannot offer cleanly, and it answers a question the taxonomy
> was built to ask: **does more thinking rescue the trap?** This plan adds it as
> its own track, structurally prevented from being read as bare.

## Context

The question that started this was "can a Max subscription run the benchmark".
Measured on the operator's machine, `claude` 2.1.263, no API key set, Haiku 4.5:

| invocation | `input` | `cache_creation` | thinking | `total_cost_usd` |
| --- | --- | --- | --- | --- |
| default | 10 | 8 170 | 170 | 0.0205 |
| `--disallowed-tools` (all) | 10 | 22 539 | — | 0.0465 |
| `--system-prompt` (replace) + `--effort low` | 10 | 23 829 | 46 | 0.0490 |
| `--effort max`, antimeridian prompt | 10 | 3 829 | **3 965** | 0.0311 |

Three findings, and the ordering matters.

**The preamble is not removable.** `--system-prompt` is documented as replacing
the system prompt, not appending to it; it still sent 23 829 tokens. Adding
`--strict-mcp-config` and `--setting-sources ""` did not help, and disabling
every tool made the payload *larger*, not smaller. There is no flag that yields
a bare completion, because `claude -p` is the agent harness — that is what it is
for. So the run is a Claude Code run that happens to contain the task prompt.

**That disqualifies it from the bare track specifically**, not from the
benchmark. [`record.py`](../../src/geocase/benchmark/runner/record.py) pins
`prompt_sha256` across 51 committed values; under this harness the hash would
describe a prompt the model never saw in isolation, and the preamble shifts with
every CLI release, so two runs a month apart are not comparable. The bare track's
whole premise — *single-shot, no tools, no loop, maximally comparable* — is the
one thing this cannot deliver.

**Cost is notional.** `modelUsage` reports `"costBasis": "list"`. Under a
subscription those dollars are not billed; `CostTracker` and the budget abort
would be tracking a number with no referent. The real scarce resource is
throughput against interactive rate limits, which is what the existing
`RateLimiter`/`DailyQuota` already model.

**And `--effort` is the payoff.** 46 → 3 965 thinking tokens is not a tuning
detail, it is a different experiment. `trap_category` already slices results by
*which* trap a model fell into (`antimeridian`, `axis-order`, `y-flip`, …), so
the effort sweep asks a sharp question per category rather than moving a scalar.
Three models x five efforts = 15 arms, on compute the operator already pays for.

The design constraint that follows: **within-track comparisons are clean; a
comparison against bare numbers is not**, and the schema must make the second
one hard to do by accident. That is Phase 4, and it is the phase to be careful
with.

## Phase 1 — A client Protocol — **implemented 2026-09-10**

The runner has a narrow seam already: `run_bare_task`
([`bare.py:47-70`](../../src/geocase/benchmark/runner/bare.py)) touches the
client through exactly one call, `chat(model, messages, *, temperature,
max_tokens) -> ChatReply`. Everything downstream consumes `BareResult` and never
sees the client. What blocks a second provider is only that the type annotations
name the concrete class.

### 1.1 Failing test first

`tests/benchmark/test_client_protocol.py`: a stub object implementing only
`chat()` satisfies `ChatClient`, and `run_bare_task` accepts it. Fails on
`ImportError` — `runner/client.py` does not exist.

### 1.2 Extract

New `runner/client.py` holding `ChatReply` and a `ChatClient` Protocol. Retype
[`bare.py:48`](../../src/geocase/benchmark/runner/bare.py) and
`Pacing.build_client` ([`policy.py:41`](../../src/geocase/benchmark/runner/policy.py)).
`runner/openrouter.py` re-exports `ChatReply` so existing imports resolve
unchanged.

Pure refactor. The whole of `tests/benchmark/` stays green with no edits — if any
test needs changing, the extraction is wrong.

**Done.** [`runner/client.py`](../../src/geocase/benchmark/runner/client.py) holds
both; `openrouter.py` re-exports `ChatReply` through an explicit `__all__`. The
extraction held: 500 existing tests passed with **no edits to any of them**, which
was the phase's own falsification condition.

One thing the plan did not name: `Pacing.build_client` builds an
`OpenRouterClient` and the quota construction inside it is needed by the second
provider too, so `Pacing.build_quota()` was split out as public. Reaching into
`_quota()` from the orchestrator would have been the alternative, and a private
call across modules is how a seam stops being a seam.

## Phase 2 — `ClaudeCliClient` — **implemented 2026-09-10**

### 2.1 Failing test first

`tests/benchmark/test_claude_cli.py` against a fake `claude` executable on
`PATH`: a well-formed envelope yields `ChatReply(content=<result>, cost=None)`;
a non-zero exit raises `ChatFailedError`; a malformed envelope raises
`ChatFailedError`, never `KeyError`.

### 2.2 Implement

`runner/claude_cli.py`. Invokes:

```
claude -p <prompt> --model <id> --effort <level> --output-format json
       --strict-mcp-config --setting-sources ""
```

- `result` → `content`; `usage` → `usage` verbatim, `thinking_tokens` included.
- **`cost=None`, always.** The list-price figure is not spend under a
  subscription; recording it would put fiction into the budget abort.
- Own timeout, generous. The 30 s read timeout that suits one OpenRouter
  completion is far too tight for ~4 000 thinking tokens at `max`.
- Non-zero exit and unparseable stdout both raise `ChatFailedError`, which the
  orchestrator already treats as a per-task failure — one bad task must not kill
  a 420-call run.
- `RateLimiter`/`DailyQuota` reused unchanged. Rate limits are the real ceiling.
- No API key. The client asserts `ANTHROPIC_API_KEY` is **absent**, so a run
  cannot silently fall through to metered billing.

**Done**, in [`runner/claude_cli.py`](../../src/geocase/benchmark/runner/claude_cli.py),
16 tests against a fake `claude` on `PATH`. Timeout is 600 s, and a missing
executable is a `ChatFailedError` rather than a `FileNotFoundError` traceback.

**One finding that changes what an analysis has to read.** The plan's Context
table reads `thinking` as a top-level usage field. It is not. Verified against
the real CLI (2.1.263, no API key, one live `--effort low` call):

```
usage.output_tokens_details.thinking_tokens = 82
```

Nested. A reader doing `usage["thinking_tokens"]` — which is exactly what the
effort axis is read off — finds nothing and takes it for **zero**, silently,
on every row. The client now lifts it to the top level, never overwriting a
top-level value if a later CLI supplies one, and leaves it **absent** rather
than defaulting to `0`: a model that reported no count did not think zero
tokens. The fixture envelope in `test_claude_cli.py` was rewritten to the real
nested shape so the test cannot pass against a shape the CLI does not emit.

Two smaller confirmations from the same live call: `total_cost_usd` came back
as `0.0193293` and is discarded from `cost` as designed (kept as
`usage.total_cost_usd_list`), and the cache-read figure was **22 333** tokens —
the preamble, in the run, exactly as Context predicted.

## Phase 3 — Effort as a config axis — **implemented 2026-09-10**

### 3.1 Failing test first

A config carrying `effort: [low, max]` on one model expands to two arms with
distinct run-dir names. Fails: no expansion exists, and both arms collide on one
directory.

### 3.2 Expand and dispatch

- `configs/models-claude-effort.yaml`: three models, `effort:` list per model,
  `provider: claude-cli`, `budget.max_usd_total: 0.0`.
- Expansion beside `_models_for_track`
  ([`orchestrator.py:55`](../../src/geocase/benchmark/runner/orchestrator.py)).
- Provider dispatch at
  [`orchestrator.py:186`](../../src/geocase/benchmark/runner/orchestrator.py),
  defaulting to `openrouter` so every existing config behaves identically.
- Effort enters the run-dir name via `_run_dir_suffix`. Without this, two efforts
  of one model collide and `--resume` skips the second as already done — a
  silent wrong result, not an error.

**Done.** `expand_effort_arms` and `_build_client` sit beside `_models_for_track`;
`run_bare_track` gained a `track=` parameter defaulting to `"bare"`, and
`--track` now accepts `effort`. The effort level lands in the run-dir name
through a separate `_arm_suffix`, not inside `_run_dir_suffix` as written: that
function partitions by *domain* and raises on a mixed-domain set, and folding an
unrelated axis into it would have made one function answer two questions.

Three things the plan did not specify, each a place the output would otherwise
have lied:

- `plan_run` expands arms too, so `--dry-run` reports **15 arms / 345
  invocations** rather than 3 models, and names each arm `id @effort`.
- `print_plan` takes an effort branch. The generic path printed
  `est UNKNOWN (no pricing: in config)` fifteen times, which invites someone to
  add a `pricing:` block and get a dollar estimate for spend that does not
  exist. It now says the cost is not estimated and why, and names the real
  ceiling.
- `Pacing.describe(track=)` likewise: the bare line quotes `Retry-After`
  handling, and `claude -p` returns no such header.

A bad `effort:` level is caught in `main` and exits **2 under `--dry-run`**,
before any invocation is spent, rather than raising mid-sweep.

## Phase 4 — Provenance that cannot be misread — **implemented 2026-09-10**

The load-bearing phase.

### 4.1 Failing test first

Two assertions. First: an effort run's `run.json` carries `track: "effort"`,
`provider: "claude-cli"`, `effort`, and `harness_version`. Second, and the one
that matters: **every existing record under `results/runs` regenerates
byte-identically** with the new defaults. A checksum diff, not an eye check —
`module_sha256` is recorded provenance and these trees are ruff-excluded
precisely to stay stable.

### 4.2 Parameterise

[`record.py:155-161`](../../src/geocase/benchmark/runner/record.py) hardcodes
three literals: `"provider": "openrouter"`, `"track": "bare"`, `"protocol":
"openrouter-chat"`. They become parameters keeping today's values as defaults.
Effort runs additionally write:

- `effort: <level>`
- `harness_version: "claude-cli/2.1.263"` — the preamble is a function of the
  CLI release, so a record without it is not reproducible. **Implemented as a
  runtime probe, not the literal written here.** `detect_cli_version()` reads
  `claude --version` (cached per process) and falls back to `"unknown"` when
  the CLI is absent or its output does not parse. A hardcoded `2.1.263` is
  correct exactly until the operator's CLI updates, and then it makes the
  record *confidently wrong* about the one thing the field exists to pin —
  worse than the silence it was added to fix. An admitted `unknown` beats a
  stale number that reads as measured.
- `preamble: "claude-code-harness"` — the explicit marker that this is **not** a
  bare completion

`PROTOCOLS` ([`manual.py:43`](../../src/geocase/benchmark/runner/manual.py))
already contains `claude-code` for the manual track; the new protocol string
follows that precedent rather than inventing a parallel vocabulary.

Without 4.2's markers someone eventually reads a 15-arm effort table beside
OpenRouter bare numbers and concludes something false about a model. The marker
is the deliverable; the fields around it are bookkeeping.

**Done**, with the regeneration check green over all ten committed runs. The
three literals are parameters with today's values as defaults, and the three
effort fields are written **only when passed** — omitted from a bare record
rather than emitted as `null`, because a null `preamble` reads as "checked,
there was none", which is a claim this module cannot make about a run it did
not observe. That is also what keeps the bare bytes identical.

`cost_usd` on an effort record is `None`, not `0.0`. A zero reads as
"measured, and it was free".

**The 4.1 check had to be written differently than specified, and the reason
is worth recording.** The obvious implementation — re-run `backfill_bare_record`
over each committed run and diff — **fails on five of the ten runs before any
of this plan's changes**, verified by running it against the tree at `HEAD`.
`backfill` reconstructs a record from the `*.meta.json` files alone, and those
carry no `model.label`, so `"Poolside Laguna S 2.1 (free)"` comes back as
`"poolside/laguna-s-2.1:free"`. That is a pre-existing property of `backfill`,
not a shape change, and pinning it would have pinned the wrong thing. The test
rebuilds through `write_bare_record` with each record's own inputs instead, so
it fails if and only if the *shape* moves. Worth knowing separately:
`backfill_bare_record` is lossy, and re-running it over `results/runs` would
silently rewrite five labels.

## Phase 5 — Docs, and the comparability statement — **implemented 2026-09-10**

- This plan's row in [`index.md`](index.md).
- The methodology doc states plainly: **effort-track results are comparable
  within the track only.** Same harness, same preamble, varying only model and
  effort. Against bare numbers they are not, and the reason is the preamble, not
  the provider.
- `CLAUDE.md` benchmark section notes the second track and that its cost column
  is intentionally empty.

**Done.** [`docs/benchmark/quickstart.md`](../benchmark/quickstart.md) gains an
*Effort track* section under a heading widened from two tracks to three, and
**two** new rules rather than one: the comparability statement, and *the effort
track's cost column is intentionally empty*, which is a separate way to misread
the same records. The comparability rule prints the record's own marker fields
inline, so a reader learns to look for `preamble` rather than to remember a
page. The `CLAUDE.md` `benchmark/` bullet carries the same two statements.

Also corrected while in the file: *"until several models across both tracks have
run"* now names the bare and agentic tracks and says the effort track **cannot**
lift that caveat, since every arm of it is a Claude model by construction — the
standing single-family weakness is one the new track makes worse, not better.

## Verified end to end, 2026-09-10

Not just unit tests against a fake. One real task through the real
orchestrator, real CLI, no API key:

```
python -m geocase.benchmark run --config <one-arm>.yaml \
  --track effort --domain geo --tasks area_m2 --out <tmp>
```

```text
track=effort: 1 arms x 1 trials x 1 tasks = 1 CLI invocations, serial
claude-haiku-4-5 trial 1 area_m2: code received (spent $0.0000)
  area_m2                CORRECT
```

and the record it wrote:

```json
{"run_id": "2026-09-10_claude-haiku-4-5_effort-low",
 "track": "effort", "protocol": "claude-code", "effort": "low",
 "harness_version": "claude-cli/2.1.263", "preamble": "claude-code-harness",
 "cost_usd": null, "model": {"provider": "claude-cli"}}
```

`harness_version` was **detected from the running binary**, not read from a
constant. The task meta carries `thinking_tokens: 8881` — the lift working on
a real task, on the number the entire axis is read off — alongside
`cost_usd: null` with the discarded list price preserved as
`usage.total_cost_usd_list: 0.0762086`.

The first live run also caught a naming defect the unit test had missed: the
run dir came out `..._effort_effort-low`, because the arm suffix repeated the
track name. Fixed to `..._effort-low`, and the test tightened — it had asserted
`endswith("_effort-low")`, which the doubled name *also* satisfies, so it was
passing on a name nobody wanted.

## Sequencing note

Phase 1 is safe and unblocks everything; it can land alone. Phase 4 should not
land without its regeneration check green.

A full sweep is 28 tasks x 3 models x 5 efforts x 1 trial ~= **420 invocations**,
serial, against interactive rate limits — and while it runs the operator's own
Claude Code seat is competing for the same budget. Start with **one model across
five efforts (~140 calls)** and confirm the effort signal is real before
committing to 15 arms. If `low` and `max` produce the same `trap_category`
profile, the axis is not worth the remaining ten arms and this plan should stop
at that measurement.

## Open questions

- **U27 — is the effort signal real per trap category, or only in aggregate?**
  The 46 → 3 965 spread is one prompt, one model, one observation. It shows the
  knob moves; it does not show it changes an *outcome*. The Phase 5 pilot is
  designed to answer this, and a negative answer kills Phases 3–4.
- **U28 — does the preamble contaminate the traps? Probed 2026-09-10: no,
  on the best evidence the CLI permits.** Scanned a 27 847-character
  self-report of the harness prompt (`claude 2.1.263`, Haiku 4.5, no API key)
  against 34 terms — `coordinate`, `axis order`, `antimeridian`, `EPSG`,
  `mercator`, `geodesic`, `y-flip`, `nodata`, `winding`, units, and the rest.
  **One hit, and it is a false positive:** the English word *"bearing"* in
  prose about how a memory should shape suggestions, not a compass bearing.
  Zero hits on every geospatial term. So the preamble is general coding
  guidance, as assumed, and does not name anything the traps test.

  **The caveat is the method, and it is not small.** This is a *self-report*,
  not a captured wire payload. The CLI exposes no flag that dumps the system
  prompt: `--debug-file` writes 14 KB of TLS and plugin logging and never
  carries it, and `--system-prompt` replaces rather than reveals. A model
  paraphrasing or truncating its own instructions could drop the very sentence
  that matters. The length is reassuring — 27 847 characters is the right
  order for the ~23 800-token preamble — but *consistent with complete* is not
  *verified complete*. Closing this properly needs a logging proxy, which is
  out of scope here. Treat the answer as **negative with moderate confidence**,
  and re-probe when the CLI version moves, since the preamble moves with it.
- **U29 — should the bare track still get an Anthropic API provider?** The
  Protocol from Phase 1 makes it ~60 lines, and it is the only way to get Claude
  models into the *bare* numbers. Deliberately out of scope here; a $5–10 top-up
  covers a full sweep.
