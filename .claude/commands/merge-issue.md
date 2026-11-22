---
description: Merge the agent's PR for one issue (after checking that CI is green), then do the post-merge housekeeping.
argument-hint: "<issue number>"
---

Agent PRs do not merge by themselves (#194): the owner merges each one with
this command. Plain, direct English; the owner is a non-native speaker.

Issue: `$ARGUMENTS`. If it is empty or not a number, ask for the issue
number and stop. Below, `<N>` is the issue and `<PR>` is its pull request.

1. **Find the PR.**
   `gh pr list --state open --json number,title,headRefName,closingIssuesReferences`.
   Take the PR whose `closingIssuesReferences` contains issue `<N>`, or whose
   branch starts with `agent/<N>-`. If there is none, or more than one, say
   so and stop.
2. **Check it.**
   `gh pr view <PR> --json title,isDraft,mergeable,reviewDecision,files`
   and `gh pr checks <PR>`. Stop and say why if a check is failing (`fail`)
   or still running (`pending`), if `isDraft` is true, or if `mergeable` is
   `CONFLICTING`.
3. **Show it.** The PR title and URL, the changed files, and one line per
   check. If a changed file is under `src/geocase/data/`, `metadata/`,
   `.github/` or `.claude/`, say so: those paths need a careful look.
4. **Merge.** `gh pr merge <PR> --merge`. If GitHub refuses only because a
   Code Owner review is required (the agent's PRs are opened with the
   owner's own token, so the owner cannot approve them), run
   `gh pr merge <PR> --merge --admin`: running this command is that review.
   You never use `--admin` to skip a failed or pending check.
5. **Housekeeping** (CLAUDE.md, after every merged PR):
   1. Delete the remote branch:
      `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>`.
      Do not delete a local branch; if one exists, name it and ask.
   2. `git checkout main && git pull --ff-only && git fetch --prune`.
   3. `gh issue view <N> --json state`. If it is still open, say what is
      left on it.
   4. `gh issue list --state open --search "Depends on #<N>" --json number,labels,body`.
      For each issue whose body says `Depends on #<N>` and that is labelled
      `blocked`: if it names no other open dependency, replace `blocked`
      with `agent:ready` or `operator` (the one its body fits) and comment
      "Unblocked: #<N> merged in #<PR>."
6. **Report** in a few lines: what merged, the issue state, and which issues
   were unblocked.
