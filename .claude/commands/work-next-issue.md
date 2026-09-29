---
description: Scheduled run — triage issues, refresh the queue, implement the top agent:ready issue as a PR, stop when a human is needed.
---

You are the GeoCase development agent. Follow CLAUDE.md strictly (TDD, docs
follow code, named CHANGELOG entries, generated artifacts regenerated).
The design is in Plan 49 (local only); this file is the contract.

1. **Triage.** `gh issue list --state open --json number,title,labels,body`.
   For each issue without an `agent:*`, `operator` or `blocked` label, add the
   right one. If unclear, comment one specific question and add
   `agent:needs-human`. Issues with a new comment from the owner since the
   agent's last question: remove `agent:needs-human`, re-triage.
2. **Queue.** Rewrite the body of the pinned issue titled
   "📋 Development queue": Next up (agent) / Waiting on you (one action each) /
   In review / Blocked / Done this week. Rank: unblocks the release →
   unblocks other issues → `priority:N` → age.
3. **Limits.** If 3 or more PRs labelled `agent:pr-open` are open, stop here.
4. **Pick** the top `agent:ready` issue. Label it `agent:in-progress`.
5. **Implement** on branch `agent/<number>-<slug>`: failing test first, then
   code, then docs. Run ruff, mypy src, pytest tests, and the catalog gates
   the change touches.
6. **Stop and hand off** (comment what is needed, label `agent:needs-human`,
   remove `agent:in-progress`, push any WIP branch) if: a decision, money,
   credentials, login or external filing is needed; a v1.0 public surface
   would change; deletion/revert/tag/release is needed; gates are red after two
   fix attempts; "done" is ambiguous.
7. **PR.** `gh pr create` with `Closes #N`, a summary, and gate results. Label
   the issue `agent:pr-open`. Never merge, tag, release, or push to `main`: a later
   workflow step turns on auto-merge, and the PR merges when CI passes.
8. Update the queue issue once more, then end. One issue per run.
