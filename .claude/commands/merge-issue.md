---
description: Finish one issue - commit and push its branch if needed, open the PR, wait for CI, merge, then do the post-merge housekeeping.
argument-hint: "<issue number>"
---

Nothing merges by itself (#194): the owner merges each PR with this command.
Running `/merge-issue N` is the owner's approval to commit, push, open the
PR and merge the branch of issue N, and nothing else. Plain, direct English;
the owner is a non-native speaker.

Issue: `$ARGUMENTS`. If it is empty or not a number, ask for the issue
number and stop. Below, `<N>` is the issue, `<branch>` its branch and `<PR>`
its pull request.

1. **Find the branch.**
   `gh pr list --state open --json number,title,headRefName,closingIssuesReferences`.
   Take the PR whose `closingIssuesReferences` contains issue `<N>`, or whose
   branch starts with `agent/<N>-`. If there is more than one, say so and
   stop. If there is none, look for a local branch named `*/<N>-*`
   (`git branch --show-current` first, then `git branch --list "*/<N>-*"`).
   None at all: say so and stop.
2. **Commit and push local work** (skip when the branch is only on GitHub,
   such as an agent branch with no local copy).
   1. Check out `<branch>` if it is not the current branch; if the working
      tree has changes that belong to another branch, stop and ask. You
      never commit on `main`.
   2. `git status --porcelain`. If it shows changes, list the files. Stop
      and ask if a file looks unrelated to issue `<N>`, or could hold a
      secret (`.env`, `settings.local.json`, credentials, tokens).
   3. Run the lint gate: `ruff format --check src tests plugins` and
      `ruff check src tests plugins`, plus `pytest` on the changed test
      files. If one fails, fix it (or stop and say why).
   4. `git add` the listed files by name, then commit. The message says what
      changed and ends with the line
      `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
   5. `git push -u origin <branch>` if the branch has commits that are not
      on GitHub yet.
3. **Open the PR** if there is none: `gh pr create` with the issue title,
   a body that starts with `Closes #<N>` and lists what changed and the
   local checks, ending with
   `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
4. **Wait for CI.** `gh pr checks <PR> --watch` (run it in the background
   if it may take longer than the shell timeout, and continue when it ends).
   Then check:
   `gh pr view <PR> --json title,url,isDraft,mergeable,reviewDecision,files`.
   Stop and say why if a check failed (`fail`), if `isDraft` is true, or if
   `mergeable` is `CONFLICTING`. A check that is still `pending` means wait
   longer, never merge.
5. **Show it.** The PR title and URL, the changed files, and one line per
   check. If a changed file is under `src/geocase/data/`, `metadata/`,
   `.github/` or `.claude/`, say so: those paths need a careful look.
6. **Merge.** `gh pr merge <PR> --merge`. If GitHub refuses only because a
   Code Owner review is required (the PRs are opened with the owner's own
   token, so the owner cannot approve them), run
   `gh pr merge <PR> --merge --admin`: running this command is that review.
   You never use `--admin` to skip a failed or pending check.
7. **Housekeeping** (CLAUDE.md, after every merged PR):
   1. Delete the remote branch:
      `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>`.
   2. `git checkout main && git pull --ff-only && git fetch --prune`.
      Do not delete the local branch; name it and ask.
   3. `gh issue view <N> --json state`. If it is still open, say what is
      left on it.
   4. `gh issue list --state open --search "Depends on #<N>" --json number,labels,body`.
      For each issue whose body says `Depends on #<N>` and that is labelled
      `blocked`: if it names no other open dependency, replace `blocked`
      with `agent:ready` or `operator` (the one its body fits) and comment
      "Unblocked: #<N> merged in #<PR>."
   5. Docs: check that the change left no doc wrong (CLAUDE.md, "Docs follow
      every change"), including the Playbook.
8. **Report** in a few lines: what was committed, what merged, the issue
   state, which issues were unblocked, and which local branch is left.
