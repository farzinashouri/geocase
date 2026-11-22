---
description: How the GeoCase development agent triages issues, keeps the queue and opens pull requests on GitHub Actions.
---

# Development Agent

GeoCase runs a semi-autonomous development agent on GitHub Actions. It runs
only when the maintainer starts it (the nightly schedule was removed on
2026-11-22). Each run triages the open issues, rewrites the pinned
**📋 Development queue** issue, implements one `agent:ready` issue (the one
you name, or the top of the queue) on a branch and opens a pull request.
The PR waits for you: you review it and merge it with `/merge-issue N`
(#194). Nothing merges by itself, and the agent never merges, tags, releases
or pushes to `main`.

This page has two parts:

- [Part 1: Setup](#part-1-setup) is for the person who installs the system on a
  repository.
- [Part 2: Working with the agent](#part-2-working-with-the-agent) is for the
  maintainer who uses it every day.

The files that make up the system:

| File | Role |
|---|---|
| `.github/workflows/agent.yml` | The job: environment, credentials, tool limits |
| `.claude/commands/work-next-issue.md` | The run prompt: what the agent does, in which order, and when it stops |
| `.claude/commands/run-issue.md` | `/run-issue N`: checks issue N and starts a run on it |
| `.claude/commands/merge-issue.md` | `/merge-issue N`: commits and pushes issue N's branch if needed, opens the PR, waits for CI, merges, then the housekeeping |
| `.github/workflows/agent-labels.yml` | Removes the `agent:*` labels when an issue closes |
| `CLAUDE.md` | Project rules the agent follows (TDD, docs follow code, CHANGELOG, gates) |
| `tests/unit/test_agent_workflow.py`, `tests/unit/test_agent_labels_workflow.py` | Pin the structure of both workflows, so a careless edit fails CI |

---

## Part 1: Setup

Do the steps in order. Steps 1–4 are one-time account and repository settings.
Steps 5–7 put files in the repository. Step 8 tests the whole setup.

### 1. Prerequisites

- A GitHub repository where you are an admin.
- A Claude subscription (Pro or Max) for the account that pays for the runs.
  The agent runs on this subscription seat, not on API credit.
- On your machine: the `gh` CLI (logged in with `gh auth login`) and the
  `claude` CLI.
- A CI workflow (`ci.yml`) that runs the project's gates on `pull_request`.

### 2. Credential 1: `CLAUDE_CODE_OAUTH_TOKEN` (Claude access)

This token lets the action run Claude Code on your subscription.

1. On your machine run:

    ```bash
    claude setup-token
    ```

    It opens a browser login and prints a long-lived OAuth token.
2. Store it as a repository secret:

    ```bash
    gh secret set CLAUDE_CODE_OAUTH_TOKEN
    ```

    Paste the token when asked. Do not put it in any file.

If the token is revoked or the subscription ends, the "Run Claude" step fails
with an authentication error. Run `claude setup-token` again and replace the
secret.

### 3. Credential 2: `AGENT_GH_TOKEN` (GitHub access)

The agent needs a GitHub token to push branches, open PRs, and edit issues and
labels. The workflow uses `AGENT_GH_TOKEN` when it exists and falls back to the
built-in `GITHUB_TOKEN` otherwise:

```yaml
GH_TOKEN: ${{ secrets.AGENT_GH_TOKEN || github.token }}
```

**Why a personal token:** GitHub does not start other workflows from events
created by `GITHUB_TOKEN`. A PR opened with it gets no CI run until someone
pushes to it. A PR opened with a personal token triggers `ci.yml` normally.

Create a **fine-grained personal access token**
(GitHub → Settings → Developer settings → Personal access tokens →
Fine-grained tokens → Generate new token):

| Field | Value |
|---|---|
| Resource owner | The account or organization that owns the repository |
| Expiration | Up to one year. Put a reminder in your calendar before it expires |
| Repository access | Only select repositories → this repository |
| **Contents** | Read and write (push branches) |
| **Pull requests** | Read and write (`gh pr create`) |
| **Issues** | Read and write (labels, comments, the queue issue) |
| Metadata | Read (GitHub requires it) |
| Workflows | Read and write, only if the agent may edit `.github/workflows/*`; otherwise leave it off |

Store it:

```bash
gh secret set AGENT_GH_TOKEN
```

The PRs and comments appear under the token owner's account.

**Common failure:** `gh pr create` fails with "Resource not accessible by
personal access token" while `git push` works. The token has Contents but not
Pull requests. Edit the token and add **Pull requests: Read and write**.
Editing permissions keeps the token value, so the secret does not change.

### 4. Repository settings

1. **Settings → Actions → General → Workflow permissions:** select "Read and
   write permissions" and tick **"Allow GitHub Actions to create and approve
   pull requests"**. The `GITHUB_TOKEN` fallback needs this to open PRs.
2. **Protect `main`** (Settings → Rules → Rulesets). GeoCase uses the
   `main_protected` ruleset: it requires the CI checks (tests 3.11/3.14, lint,
   typecheck, catalog, floor, docs) before merging. The admin role can bypass
   it, so the maintainer can still push small changes directly. The agent's
   token does not need to bypass it, because the agent never pushes to `main`.
   An agent PR merges only when you merge it and these checks pass.
3. **Create the labels.** The system uses them as a state machine (see
   [Labels](#labels)):

    ```bash
    gh label create agent:ready       --description "Scoped, testable, no decision pending"
    gh label create agent:in-progress --description "Claimed by an agent run"
    gh label create agent:needs-human --description "Agent stopped; the comment says what is needed"
    gh label create agent:pr-open     --description "Agent PR awaiting review"
    gh label create operator          --description "Only the owner can do it (seat, money, identity, decision)"
    gh label create blocked           --description "Waits on another issue, a decision or funding"
    gh label create priority:1 --description "Rank 1"
    gh label create priority:2 --description "Rank 2"
    gh label create priority:3 --description "Rank 3"
    ```

4. **Create and pin the queue issue.** The prompt finds it by its exact title:

    ```bash
    gh issue create --title "📋 Development queue" --body "The agent rewrites this body on every run."
    gh issue pin <number>
    ```

### 5. The run prompt: `.claude/commands/work-next-issue.md`

This file is the contract for each run. The workflow's prompt only says
"Follow .claude/commands/work-next-issue.md exactly", so all behaviour lives
here. The nine steps:

1. **Triage**: label every open issue that has no `agent:*`, `operator` or
   `blocked` label. Unclear issue → one specific question as a comment plus
   `agent:needs-human`.
2. **Queue**: rewrite the pinned queue issue.
3. **Repair** each red `agent/*` PR: read `gh run view <id> --log-failed`,
   fix (a failing test first when it is a code bug), run the gates, push.
   Each attempt is a PR comment `agent-repair: attempt K`. After two
   attempts, when the cause is outside the repository (a secret, the runner,
   the network, an upstream outage), or when no checks have run for more
   than one hour (`AGENT_GH_TOKEN` probably missing), it hands off with
   `agent:needs-human`. A repair counts as the run's one issue. In triage
   mode the step only reports.
4. **Limits**: 3 or more open `agent:pr-open` PRs → stop.
5. **Pick** the named issue (it must be open, `agent:ready` and not
   `blocked`, or the run comments why and ends), or else the top
   `agent:ready` issue, and label it `agent:in-progress`.
6. **Implement** on `agent/<number>-<slug>`: failing test first, then code,
   then docs, then gates.
7. **Stop and hand off** when a person is needed (see
   [Stop conditions](#stop-conditions)).
8. **PR** with `Closes #N`, a summary and the gate results; label the issue
   `agent:pr-open`.
9. Update the queue again and end. One issue per run.

Because it is also a Claude Code slash command, you can run the same
procedure locally with `/work-next-issue`.

### 6. The workflow: `.github/workflows/agent.yml`

What each part does:

| Part | Setting | Why |
|---|---|---|
| Trigger | `workflow_dispatch` only; no schedule | The owner starts each run (nightly runs ended 2026-11-22) |
| Input `mode` | `triage` (default) or `full` | Test runs without writing code |
| Input `issue` | an issue number, or empty | Implement that issue instead of the top of the queue; forces `full` mode |
| Concurrency | group `agent`, no cancel | Never two runs at once |
| Permissions | contents, pull-requests, issues: write; id-token: write | Used when running on the `GITHUB_TOKEN` fallback |
| Timeout | 180 minutes | Cost and runaway cap; bare-track benchmark runs against rate-limited free models need more than an hour |
| Checkout | `fetch-depth: 0`, with the agent token | Full history, and pushes use the agent token |
| Environment | `setup-miniconda` from `environment.yml` | Only the conda env has GDAL/`osgeo`, which the catalog gates and `examples/` need |
| PATH step | appends `$CONDA_PREFIX/bin` to `$GITHUB_PATH` | Claude's Bash tool does not use a login shell and would otherwise not find the env |
| Action | `anthropics/claude-code-action@v1` | Runs Claude Code with the prompt |
| Turn limit | `--max-turns 250` | A typical full run uses 50–60; #25 used 144 |
| No merge step | nothing in the workflow merges or turns on auto-merge (#194) | You merge each PR with `/merge-issue N` |

**Tool limits.** The action is non-interactive, so any tool not on
`--allowedTools` is denied. (The first dry run did nothing for this reason.)

- Allowed: `Read`, `Edit`, `Write`, `Glob`, `Grep`, and Bash for `gh`, `git`,
  `python`, `pytest`, `ruff`, `mypy`, `mkdocs`, and the shell helpers
  `python3`, `ls`, `grep`, `head`, `sed`, `cat`, `tail`, `cd`, `for`, `echo`. The helpers were
  added after the 2026-10-01 run on #25 had 18 commands denied, mostly pipes
  through them, and its retries pushed it past the old 120-turn cap. Every
  command in a pipe or `;` chain must be allowed. `cd`, `for` and `echo`
  were added after the 2026-10-03 triage run was denied a `cd ...; for n in
  ...` loop and a `python3 - <<EOF` heredoc. `work-next-issue.md` also asks
  for one simple command per Bash call, so a denial is rarer in the first
  place. It also forbids shell `>` redirects (`--add-dir /tmp` covers the
  Write tool, not a redirect; denied on 2026-10-05 and 2026-10-06) and edits
  under `.claude/`, which Claude Code protects and a headless run cannot
  approve: such an issue goes to `operator` with the diff in a comment.
- `--add-dir /tmp`: file access outside the checkout is otherwise denied.
  The OpenRouter preflight writes `/tmp/openrouter/status.txt`, and benchmark
  runs log to `/tmp`; the 2026-10-02 run on #67 could not start its benchmark
  run without it.
- Denied even though they match the allowed patterns: `gh pr merge`,
  `git tag`, `gh release`, `git push origin main`, `git push -f`,
  `git push --force`, `git revert`, `rm -rf`, `gh workflow run`.

`gh pr merge` stays denied to the model on purpose: only you merge, with
`/merge-issue N`. The deny list is the hard guarantee. The prompt repeats the same rules, but
the deny list is what enforces them.

### 7. The label cleanup: `.github/workflows/agent-labels.yml`

Runs on `issues: closed` and removes the four `agent:*` labels. Triage reads
open issues only, so without this job a merged PR would leave `agent:pr-open`
on its closed issue forever. It uses the built-in `GITHUB_TOKEN`; no secret is
needed.

### 8. Test the setup

1. **Triage-only run** (writes no code):

    ```bash
    gh workflow run agent.yml            # mode defaults to triage
    gh run watch
    ```

    Check that unlabelled issues got labels and the queue issue body was
    rewritten.

2. **Full run** (tests the PR step and the token):

    ```bash
    gh workflow run agent.yml -f mode=full
    ```

    Check that a branch `agent/<n>-<slug>` was pushed, a PR was opened by the
    token owner, and **CI started on the PR by itself**. If CI did not start,
    the run fell back to `GITHUB_TOKEN`: check that `AGENT_GH_TOKEN` exists.

3. There is no schedule: nothing runs until you start it. A disabled
   workflow cannot be started, so keep it enabled
   (`gh workflow enable agent.yml`).

### Setup checklist

- [ ] `CLAUDE_CODE_OAUTH_TOKEN` secret set (`claude setup-token`)
- [ ] `AGENT_GH_TOKEN` fine-grained PAT with Contents, Pull requests, Issues: read and write
- [ ] Reminder set before the PAT expires
- [ ] Optional: `OPENROUTER_API_KEY` secret for bare-track benchmark issues (`gh secret set OPENROUTER_API_KEY --body "$OPENROUTER_API_KEY"`); give the key a credit limit on OpenRouter, since the agent spends it unattended
- [ ] Actions may create PRs; `main` protected by required checks
- [ ] Labels created; queue issue created and pinned
- [ ] `work-next-issue.md`, `agent.yml`, `agent-labels.yml` on the default branch
- [ ] Triage run and full run both checked; CI starts on the agent's PR

---

## Part 2: Working with the agent

### The daily loop

```text
you: file/label issues ──► you start a run: agent triages, rewrites queue,
                                   implements one agent:ready issue
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
          PR opened (agent:pr-open)                  stopped (agent:needs-human)
                   │                                             │
      CI green → you review, /merge-issue N         you: answer the comment
      CI red → repair, or you fix it
                   │                                             │
   issue closes, labels cleared automatically      next run re-triages the issue
```

Your work after each run:

1. Open the pinned **📋 Development queue** issue. It is the single place to
   look. *Waiting on you* lists one action per item, grouped by phase
   milestone and **not ranked**: pick any task, in any order. Each phase is a
   GitHub milestone with one issue per task and a `size:` label (`size:5m`,
   `size:30m`, `size:1h`, `size:2h`); a closed issue is a done task. Work that
   no current phase needs sits in the **Later** milestone: the queue does not
   list it, only its count and a link at the end. In Claude
   Code, `/next 30m` lists the open, unblocked issues that fit 30 minutes,
   ordered by `mvp`, then priority, then size, with all their labels, and
   recommends one to solve next; and
   the project status line (`.claude/statusline.sh`) shows done/total per
   phase, e.g. `P0 5/19 · P1 2/25 · P2 0/11`. An issue is `blocked` only
   when its body names the issue or event it waits for.
2. Read what merged since your last run (*Done this week*), and look at any PR under
   *In review* that did not merge: its CI failed. The agent's Repair step
   tries two fixes and then hands off with `agent:needs-human`, so a red PR
   with no such comment has not been looked at yet. No email tells you about
   it.
3. Answer every `agent:needs-human` comment.

### Email notifications

- **Merges and new PRs:** watch the repo with *All Activity*.
- **Failed runs:** in GitHub settings → Notifications → Actions, enable email
  for failed workflows only. A manual run notifies the person who started it.
- **Waiting on you:** when the agent adds `agent:needs-human` or `operator`, it
  assigns the issue to the owner and @mentions them. Both are made with
  `AGENT_GH_TOKEN`, the owner's own token, so GitHub sends no email for them.
  The run report carries the question instead: every open
  `agent:needs-human` issue is listed under **Needs you** (link, title and the
  first line of the last comment), and the header says `🙋 Needs you: N`.
  The same section lists every open `agent/*` PR that is red or has no checks,
  with the name of the failing check (Plan 53, #95), and a line when the limit
  of 3 open PRs stopped the run.
- **Every run:** each run comments a verdict (`✅ healthy` or `⚠️ needs
  attention: …`, with turns, duration, permission denials and the final
  message) on the pinned **Agent run reports** issue, which the workflow
  creates if missing. Subscribe to that issue for one email per run. The
  comment is posted as `github-actions[bot]`, not with `AGENT_GH_TOKEN`:
  GitHub never emails you about comments made with your own token. A failed
  agent step now also fails the job
  (`scripts/agent_run_report.py`).

### Labels

Each open issue has exactly one state label and one priority label.

| Label | Meaning | Who sets it |
|---|---|---|
| `agent:ready` | Scoped, testable, no decision pending. The agent may take it | you, or triage |
| `agent:in-progress` | A run has claimed it | agent |
| `agent:pr-open` | A PR exists; it waits for your `/merge-issue N` | agent |
| `agent:needs-human` | The agent stopped; its last comment says what it needs | agent |
| `operator` | Only you can do it: money, accounts, identity, public posts, decisions | you, or triage |
| `blocked` | Waits on another issue, a date or funding (`Blocked by #N`, `Not before YYYY-MM-DD`) | you, or triage |
| `priority:1..3` | Rank; 1 is highest | you, or triage |

Topic labels (`benchmark`, `release`, `seo`, `upstream`, `decision`, …) are
extra and do not affect the agent.

### How the agent picks work

The queue is ranked in this order:

1. issues that unblock the release,
2. issues that unblock other issues,
3. `priority:N`,
4. age (oldest first).

It implements only the top `agent:ready` issue, one per run. When 3 agent PRs
are already open, it only triages and updates the queue, so unreviewed PRs
slow the agent down on purpose.

### Writing an issue the agent can do

An issue is `agent:ready` when a person could finish it without asking you
anything:

- say what "done" means, as a checklist;
- name the files and case ids involved;
- **copy the plan section into the body.** `docs/plans/` is gitignored, so
  the agent's checkout does not contain it; a body that only says "See
  docs/plans/…" is not ready. Triage removes `agent:ready` from such issues
  and asks for the section;
- state dependencies as `Depends on #N`;
- keep it to one PR's worth of work.

If a decision is still open, label it `operator` or `decision` first and add
`agent:ready` after you decide. Write the decision as a comment on the issue,
so the agent can read it.

The **Agent task** issue form (`.github/ISSUE_TEMPLATE/agent_task.yml`) asks
for exactly these parts: *Goal*, *Files to touch*, *Done when* (starting
with the failing test) and *Out of scope*, plus *Depends on*. It labels the
issue `agent:ready` and `priority:2`.

### Choosing what it works on

The agent works only when you start it, one issue per run. Pick an
`agent:ready` issue and name it. In Claude Code:

```text
/run-issue 182
```

`/run-issue` checks that the issue is open, `agent:ready` and not `blocked`,
that the workflow is enabled, and that fewer than 3 agent PRs are open. Then
it starts the run and gives you the run URL. Without Claude Code, start the
run directly:

```bash
gh workflow run agent.yml -f issue=182
```

Before the next run, check two things: no `agent:needs-human` issue is
waiting for your answer, and fewer than 3 agent PRs are open. At 3 open PRs
the agent only triages and does not implement the issue.

### Stop conditions

The agent stops, comments, labels `agent:needs-human` and pushes any partial
branch when:

- the work needs a decision, money, credentials, a browser login, or an
  external filing (upstream issues are always posted by a person);
- it would change a v1.0 public surface (`__all__`, fixtures, markers, a
  `risk_types` term without an alias);
- it needs a deletion, a revert, a tag or a release;
- gates are still red after two fix attempts;
- the issue does not say clearly what "done" means.

**To continue:** reply on the issue. On the next run, triage sees your new
comment, removes `agent:needs-human` and re-triages the issue. If the answer
makes it ready, you can also set `agent:ready` yourself.

### Merging agent PRs

- The PR body lists what was done, what was not done, and the gate results.
- CI runs on it automatically (with `AGENT_GH_TOKEN` set).
- Nothing merges by itself (#194). Review the diff, then in Claude Code:

    ```text
    /merge-issue 182
    ```

    It finds the open PR that closes issue 182 (or, for your own work, the
    local branch `*/182-*`). If the branch has uncommitted changes or no PR,
    it lists the files, runs the lint gate, commits, pushes and opens the PR
    with `Closes #182`. It waits for CI, stops if a check failed, shows the
    changed files and checks, and merges. Then it deletes the remote branch,
    updates your local `main`, checks that the issue closed, and unblocks
    issues that said `Depends on #182`. Running it is your approval for that
    commit, push and merge.
    `Closes #N` closes the issue, and `agent-labels.yml` clears the labels.
- A PR that changes a path listed in `.github/CODEOWNERS` (case data, the
  case indices, `tests/fixtures/expected_hashes.yaml`, `.github/`, `.claude/`)
  needs a Code Owner review. Agent PRs are opened with `AGENT_GH_TOKEN`, so
  their author is your own account, and GitHub does not let an author
  approve their own PR. `/merge-issue` then merges with the admin bypass
  (`--admin`): running it is your review. It never uses `--admin` to skip a
  failed or pending check.
- To ask for changes, comment on the PR and label the issue
  `agent:needs-human` or `agent:ready`. Or push fixes to the branch yourself.
- An agent PR that says `Refs #N` instead of `Closes #N` finished only part of
  the issue; the rest is described in the PR body.

### Running it by hand

```bash
gh workflow run agent.yml -f issue=182   # implement issue #182 (must be agent:ready)
gh workflow run agent.yml                 # triage + queue only
gh workflow run agent.yml -f mode=full    # also implement the top issue
gh run list -w Agent -L 5                 # recent runs
gh run view <id> --log                    # full log, including the agent's turns and cost
```

A run with `issue` set always uses `full` mode. Without it, runs default to
`triage`.

### Cost and limits

- Runs use the Claude subscription seat of the `CLAUDE_CODE_OAUTH_TOKEN`
  owner. The log's `total_cost_usd` (about $0.50–$1 per full run) is a list
  price estimate; the real limit is the seat's rate limit.
- GitHub Actions minutes: one run is about 7–10 minutes, most of it building
  the conda environment.
- Hard caps: 180 minutes, 250 turns, 1 PR per run, 3 open agent PRs.
- Every agent PR waits for your merge, so nothing reaches `main` without
  you. Open PRs count against the limit of 3: merge or close them, or the
  agent only triages.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Branch pushed, no PR, log says "Resource not accessible by personal access token" | PAT lacks Pull requests: write | Edit the PAT (Part 1, step 3) |
| PR opened but CI did not start | Run used `GITHUB_TOKEN` | Set or renew `AGENT_GH_TOKEN` |
| Run succeeded but did nothing | A needed tool is not in `--allowedTools` | Look for "permission denied" in the log; add the tool to `agent.yml` |
| Run succeeded after ~30 turns, issue left `agent:in-progress`, no branch or comment | Unknown (seen on benchmark issues #70, #67) | Download the run's `agent-transcript` artifact (kept 14 days) and read the last turns |
| Authentication error in the Claude step | OAuth token revoked or expired | `claude setup-token`, then `gh secret set CLAUDE_CODE_OAUTH_TOKEN` |
| Queue issue not updated | Its title changed, or it is not pinned | Restore the exact title "📋 Development queue" |
| PR has green CI but did not merge | Expected: agent PRs wait for you (#194) | Review it, then `/merge-issue N` |
| Closed issue still has `agent:pr-open` | `agent-labels.yml` missing or failed | Check the "Agent labels" run for that issue |
| Runs only triage and update the queue, report says nothing is wrong | 3 agent PRs are open, often with red CI | Fix or close the red PRs (`gh pr list --label agent:pr-open`, then `gh pr checks <n>`) |
| PR has `agent-repair: attempt 2` and `agent:needs-human` | Repair step gave up | Read the handoff comment; fix the branch yourself |
| Repair hands off saying no checks ran | Agent PRs opened with `GITHUB_TOKEN` do not trigger CI | Set or renew `AGENT_GH_TOKEN` |

---

## Planned changes

These are planned and not implemented yet. The sections above describe the
current behaviour. When a change lands, its text moves into the sections above.

### A monitoring agent (Plan 52, #84, blocked)

A second workflow, `agent-monitor.yml`, starts when an Agent run ends and its
report is not healthy. It reads the report and the run log and sorts the cause
(a tool not on the allowlist, the turn limit, authentication, the
environment, a model error, a code bug). It posts the diagnosis under that
run's report comment. When the fix is in the repository, it opens a PR on
`agent/monitor-<run_id>` labelled `agent:needs-human`. These PRs never
auto-merge. When the fix is not in the repository, it files an `operator`
issue. A monitor PR that edits `.github/workflows/*` needs `AGENT_GH_TOKEN`
with Workflows: Read and write.
