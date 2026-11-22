---
description: Start the development agent on one named issue (gh workflow run agent.yml -f issue=N), after checking that the agent can take it.
argument-hint: "<issue number>"
---

The owner names one issue for the development agent to implement. The agent
has no schedule; this command starts one run on GitHub Actions. Check first,
so a run is not spent on an issue the agent will refuse. Plain, direct
English; the owner is a non-native speaker.

Issue: `$ARGUMENTS`. If it is empty or not a number, ask for the issue number
and stop.

1. **Check the issue.**
   `gh issue view <N> --json number,title,state,labels`.
   It must have state `OPEN`, the label `agent:ready`, and not the label
   `blocked`. If one fails, say which one and stop. Do not change labels:
   the owner decides whether the issue is ready.
2. **Check the workflow.**
   `gh api repos/{owner}/{repo}/actions/workflows/agent.yml --jq .state`.
   A disabled workflow cannot be started. If the state is not `active`, say
   so, give the command `gh workflow enable agent.yml`, and stop.
   You never run `gh workflow enable` yourself.
3. **Check the PR limit.**
   `gh pr list --state open --label agent:pr-open --json number`. At 3 or
   more open agent PRs the agent only triages and does not implement the
   issue. Say so, list the PRs, and ask whether to start anyway.
4. **Start the run.** `gh workflow run agent.yml -f issue=<N>`.
5. **Report.** Wait a few seconds, then
   `gh run list --workflow agent.yml --limit 1 --json databaseId,url,status`.
   Answer in three lines: the issue number and title, the run URL, and how
   to follow it (`gh run watch <id>`, or the run report on the "Agent run
   reports" issue when it ends). The run takes about 10–30 minutes; do not
   wait for it.
