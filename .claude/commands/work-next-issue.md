---
description: Agent run — triage issues, refresh the queue, implement the top agent:ready issue as a PR, stop when a human is needed.
---

You are the GeoCase development agent. Follow CLAUDE.md strictly (TDD, docs
follow code, named CHANGELOG entries, generated artifacts regenerated).
The design is in Plan 49 (local only); this file is the contract.

**Notify the owner on every hand-off.** Whenever you add `agent:needs-human`
or `operator` to an issue, also run `gh issue edit N --add-assignee
farzinashouri` and start the comment with `@farzinashouri`. GitHub sends no
email for a label change; the assignment and the mention do.

**Use one simple command per Bash call.** No `for` loops, no `cd ...;`
prefix (you already start in the checkout), no `python3 - <<EOF` heredocs:
write the script with the Write tool, then run it. The sandbox may deny
compound commands, and every denial marks the run "needs attention".
Also no `>` redirects, not even to `/tmp`: to edit an issue body, read it
with `gh issue view N --json body --jq .body`, write the new text to
`/tmp/body.md` with the Write tool, then `gh issue edit N --body-file
/tmp/body.md`.

**You never edit files under `.claude/`.** Claude Code protects that
directory and a headless run cannot approve the prompt. If an issue needs a
change there, comment the exact diff on the issue, relabel it `operator`,
and pick the next one.

**Wait for long commands.** A Bash command that runs past 120 s is
moved to the background; a benchmark run always is. Do not end the turn then: poll
its output file (`until grep -q ... file; do sleep 30; done`) until it
finishes, and never end a run with an issue still `agent:in-progress` and no
comment on it.

1. **Triage.** `gh issue list --state open --json number,title,labels,body`.
   For each issue without an `agent:*`, `operator` or `blocked` label, add the
   right one. If unclear, comment one specific question and add
   `agent:needs-human`. Issues with a new comment from the owner since the
   agent's last question: remove `agent:needs-human`, re-triage.
   **Self-contained check** (every `agent:ready` issue, new or old):
   `docs/plans/` is not in this checkout, so the body alone must say what to
   build and what "done" means. If it only points to a plan ("See
   docs/plans/…", "Plan NN §x") without copying the section, or leaves a
   choice open, remove `agent:ready`, add `operator`, and comment naming the
   missing section or the open choice. Never pick such an issue in step 5.
2. **Queue.** Rewrite the body of the pinned issue titled
   "📋 Development queue": Next up (agent) / Waiting on you (one action each) /
   In review / Blocked / Done this week. Rank *Next up (agent)*: unblocks the
   release → unblocks other issues → `priority:N` → age. *Waiting on you* is
   **not ranked**: the owner picks any open task, in any order (#149). Group
   it by milestone ("Phase 0", "Phase 1", …, then "No phase"), each item with
   its `size:` label, and start each group with the milestone link and its
   done/total count.
   **The "Later" milestone is not listed.** It holds work no current phase
   needs (moved there on 2026-11-22). Its issues are not listed in any
   section of the queue; end the body with one line: the count of open
   "Later" issues and a link to that milestone. Do not pick them in step 5
   unless the run names one, and do not change their labels.
   **Blocking only when it is real.** Keep `blocked` only on an issue that
   cannot start until another issue is done or an outside event happens, and
   its body names that issue or event (`Depends on #N`). If the reason is gone
   or was never named, remove `blocked`, add `agent:ready` or `operator`, and
   comment why.
3. **Repair.** For each open PR on an `agent/*` branch: `gh pr checks N`.
   If a check failed, check out the branch, read `gh run view <id>
   --log-failed`, write a failing test if the cause is a code bug, fix, run
   the gates, push. Count attempts with a PR comment `agent-repair: attempt
   K`. After two attempts, or when the cause is outside the repo (secret,
   runner, network, upstream outage), hand off with `agent:needs-human`. If
   no checks have run for more than 1 hour, hand off and say that
   `AGENT_GH_TOKEN` is probably missing. A repaired PR counts as the run's
   one issue: end the run after it. In triage mode this step only reports;
   it does not push.
4. **Limits.** If 3 or more PRs labelled `agent:pr-open` are open, stop here.
5. **Pick** one issue and label it `agent:in-progress`. If the prompt
   names an issue (`Issue: N`), take that one, not the top of the queue. It must be
   open, labelled `agent:ready` and not `blocked`; otherwise comment on it
   why it was not started (start the comment with `@farzinashouri`) and end
   the run. If no issue is named, take the top `agent:ready` issue.
6. **Implement** on branch `agent/<number>-<slug>`: failing test first, then
   code, then docs. Run ruff, mypy src, pytest tests, and the catalog gates
   the change touches.
7. **Stop and hand off** (comment what is needed, label `agent:needs-human`,
   remove `agent:in-progress`, push any WIP branch) if: a decision, money,
   credentials, login or external filing is needed; a v1.0 public surface
   would change; deletion/revert/tag/release is needed; gates are red after two
   fix attempts; "done" is ambiguous.
8. **PR.** `gh pr create` with `Closes #N`, a summary, and gate results. Label
   the issue `agent:pr-open`. Never merge, tag, release, or push to `main`:
   the PR waits for the owner, who reviews it and merges it with
   `/merge-issue N` (#194).
9. Update the queue issue once more, then end. One issue per run.
