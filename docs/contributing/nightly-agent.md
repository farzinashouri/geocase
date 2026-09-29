# Nightly Development Agent

GeoCase runs a semi-autonomous development agent on GitHub Actions. On
weekday nights it triages the open issues, rewrites the pinned
**📋 Development queue** issue, implements the top `agent:ready` issue on a
branch and opens a pull request. A person reviews and merges every PR. The
agent never merges, tags, releases or pushes to `main`.

This page has two parts:

- [Part 1: Setup](#part-1-setup) is for the person who installs the system on a
  repository.
- [Part 2: Working with the agent](#part-2-working-with-the-agent) is for the
  maintainer who uses it every day.

The files that make up the system:

| File | Role |
|---|---|
| `.github/workflows/agent.yml` | The scheduled job: environment, credentials, tool limits |
| `.claude/commands/work-next-issue.md` | The run prompt: what the agent does, in which order, and when it stops |
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
here. The eight steps:

1. **Triage**: label every open issue that has no `agent:*`, `operator` or
   `blocked` label. Unclear issue → one specific question as a comment plus
   `agent:needs-human`.
2. **Queue**: rewrite the pinned queue issue.
3. **Limits**: 3 or more open `agent:pr-open` PRs → stop.
4. **Pick** the top `agent:ready` issue and label it `agent:in-progress`.
5. **Implement** on `agent/<number>-<slug>`: failing test first, then code,
   then docs, then gates.
6. **Stop and hand off** when a person is needed (see
   [Stop conditions](#stop-conditions)).
7. **PR** with `Closes #N`, a summary and the gate results; label the issue
   `agent:pr-open`.
8. Update the queue again and end. One issue per run.

Because it is also a Claude Code slash command, you can run the same
procedure locally with `/work-next-issue`.

### 6. The workflow: `.github/workflows/agent.yml`

What each part does:

| Part | Setting | Why |
|---|---|---|
| Schedule | `cron: "17 1 * * 1-5"` | Weekday nights at 01:17 UTC. GitHub can start scheduled runs hours late when it is busy; the observed start is often around 07:00 UTC |
| Manual start | `workflow_dispatch` with input `mode` = `triage` (default) or `full` | Test runs without writing code |
| Concurrency | group `agent`, no cancel | Never two runs at once |
| Permissions | contents, pull-requests, issues: write; id-token: write | Used when running on the `GITHUB_TOKEN` fallback |
| Timeout | 60 minutes | Cost and runaway cap |
| Checkout | `fetch-depth: 0`, with the agent token | Full history, and pushes use the agent token |
| Environment | `setup-miniconda` from `environment.yml` | Only the conda env has GDAL/`osgeo`, which the catalog gates and `examples/` need |
| PATH step | appends `$CONDA_PREFIX/bin` to `$GITHUB_PATH` | Claude's Bash tool does not use a login shell and would otherwise not find the env |
| Action | `anthropics/claude-code-action@v1` | Runs Claude Code with the prompt |
| Turn limit | `--max-turns 120` | A typical full run uses 50–60 |

**Tool limits.** The action is non-interactive, so any tool not on
`--allowedTools` is denied. (The first dry run did nothing for this reason.)

- Allowed: `Read`, `Edit`, `Write`, `Glob`, `Grep`, and Bash for `gh`, `git`,
  `python`, `pytest`, `ruff`, `mypy`, `mkdocs`.
- Denied even though they match the allowed patterns: `gh pr merge`,
  `git tag`, `gh release`, `git push origin main`, `git push -f`,
  `git push --force`, `git revert`, `rm -rf`, `gh workflow run`.

The deny list is the hard guarantee. The prompt repeats the same rules, but
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

3. The schedule is active as soon as `agent.yml` is on the default branch.
   To pause it, disable the workflow: `gh workflow disable agent.yml`
   (`gh workflow enable agent.yml` to resume).

### Setup checklist

- [ ] `CLAUDE_CODE_OAUTH_TOKEN` secret set (`claude setup-token`)
- [ ] `AGENT_GH_TOKEN` fine-grained PAT with Contents, Pull requests, Issues: read and write
- [ ] Reminder set before the PAT expires
- [ ] Actions may create PRs; `main` protected by required checks
- [ ] Labels created; queue issue created and pinned
- [ ] `work-next-issue.md`, `agent.yml`, `agent-labels.yml` on the default branch
- [ ] Triage run and full run both checked; CI starts on the agent's PR

---

## Part 2: Working with the agent

### The daily loop

```text
you: file/label issues ──► night: agent triages, rewrites queue,
                                   implements one agent:ready issue
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
          PR opened (agent:pr-open)                  stopped (agent:needs-human)
                   │                                             │
      you: review, merge or request changes         you: answer the comment
                   │                                             │
   issue closes, labels cleared automatically      next run re-triages the issue
```

Your work each morning:

1. Open the pinned **📋 Development queue** issue. It is the single place to
   look. *Waiting on you* lists one action per item.
2. Review PRs listed under *In review*. Merge when CI is green and you agree.
3. Answer every `agent:needs-human` comment.

### Labels

Each open issue has exactly one state label and one priority label.

| Label | Meaning | Who sets it |
|---|---|---|
| `agent:ready` | Scoped, testable, no decision pending. The agent may take it | you, or triage |
| `agent:in-progress` | A run has claimed it | agent |
| `agent:pr-open` | A PR exists and waits for your review | agent |
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
- name the files, plan section or case ids involved;
- state dependencies as `Depends on #N`;
- keep it to one PR's worth of work.

If a decision is still open, label it `operator` or `decision` first and add
`agent:ready` after you decide. Write the decision as a comment on the issue,
so the agent can read it.

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

### Reviewing an agent PR

- The PR body lists what was done, what was not done, and the gate results.
- CI runs on it automatically (with `AGENT_GH_TOKEN` set).
- Merge it yourself. `Closes #N` closes the issue, and `agent-labels.yml`
  clears the labels.
- To ask for changes, comment on the PR and label the issue
  `agent:needs-human` or `agent:ready`. Or push fixes to the branch yourself.
- An agent PR that says `Refs #N` instead of `Closes #N` finished only part of
  the issue; the rest is described in the PR body.

### Running it by hand

```bash
gh workflow run agent.yml                 # triage + queue only
gh workflow run agent.yml -f mode=full    # also implement the top issue
gh run list -w Agent -L 5                 # recent runs
gh run view <id> --log                    # full log, including the agent's turns and cost
gh workflow disable agent.yml             # pause the nightly schedule
```

Scheduled runs always use `full` mode. Manual runs default to `triage`.

### Cost and limits

- Runs use the Claude subscription seat of the `CLAUDE_CODE_OAUTH_TOKEN`
  owner. The log's `total_cost_usd` (about $0.50–$1 per full run) is a list
  price estimate; the real limit is the seat's rate limit.
- GitHub Actions minutes: one run is about 7–10 minutes, most of it building
  the conda environment.
- Hard caps: 60 minutes, 120 turns, 1 PR per run, 3 open agent PRs.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Branch pushed, no PR, log says "Resource not accessible by personal access token" | PAT lacks Pull requests: write | Edit the PAT (Part 1, step 3) |
| PR opened but CI did not start | Run used `GITHUB_TOKEN` | Set or renew `AGENT_GH_TOKEN` |
| Run succeeded but did nothing | A needed tool is not in `--allowedTools` | Look for "permission denied" in the log; add the tool to `agent.yml` |
| Authentication error in the Claude step | OAuth token revoked or expired | `claude setup-token`, then `gh secret set CLAUDE_CODE_OAUTH_TOKEN` |
| Queue issue not updated | Its title changed, or it is not pinned | Restore the exact title "📋 Development queue" |
| Run started hours after 01:17 UTC | GitHub delays scheduled runs under load | Expected; no fix |
| Closed issue still has `agent:pr-open` | `agent-labels.yml` missing or failed | Check the "Agent labels" run for that issue |
