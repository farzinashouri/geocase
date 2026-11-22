---
description: List the open, unblocked issues of each phase milestone (mvp first, all labels) and recommend one to solve next. Optional argument - a time budget such as 15m, 1h, 2h.
argument-hint: "[time budget, e.g. 30m]"
---

The owner works on GeoCase when they have time, in any order (issue #149).
Each phase is a GitHub milestone with one issue per task; a closed issue is a
done task. Your job: show what is open in each phase and recommend one issue.
Plain, direct English; the owner is a non-native speaker.

Time budget: `$ARGUMENTS` (empty means "no limit").

1. **Read the open issues.** For each open milestone named "Phase N: …", in
   phase order:
   `gh issue list --milestone "<title>" --state open --json number,title,labels,body`.
   Drop issues labelled `blocked`. Keep every other issue, whatever its state
   label: `agent:ready`, `operator` and `agent:needs-human` all show.
2. **Filter by time.** Each issue has one `size:` label (`size:5m`,
   `size:30m`, `size:1h`, `size:2h`). With a budget, keep the issues whose size
   fits it. An issue with no `size:` label: estimate it and add the label.
3. **Answer** with one short list per phase, the done/total of that milestone
   in the heading, at most 7 issues per phase.
   Sort order: `mvp` → priority → size. That is: `mvp` issues first, then the
   rest; inside each group,
   `priority:1` before `2` before `3` (no priority label last); for the same
   priority, smallest size first (no size label last). Each line is
   `#N title · ` followed by all its labels, e.g.
   `#151 Write the pilot email · mvp, operator, priority:1, size:30m`.
   If a phase has more than 7, say how many are not shown; also say how many
   blocked issues hidden, e.g. "5 more not shown, 17 blocked issues hidden".
   Name an issue whose body says `Depends on #N` for an open issue but has no
   `blocked` label, so the owner can fix the label. If nothing fits the
   budget, say so and name the smallest issue.
4. **Recommend one issue** after the lists, as
   `**Recommended:** #N title — <one-sentence reason>`. Pick from the issues
   that are not `blocked`, in this order: `mvp` before the rest → lower phase
   number → unblocks the most other issues (their body says `Depends on #N`) →
   `priority:1` before `2` before `3` → smallest size. Say who does it: the
   owner (`operator`, `agent:needs-human`), or Claude in this session
   (`agent:ready`).
5. **When the owner picks one:** give the first concrete step (a link, a
   command, a file to open) and offer the part you can do (draft text, run a
   command, read a log).
6. **When the owner says it is done:** tick the issue's checklist and close it
   (or say what is left). Re-label every issue whose body says `Depends on #N`
   for it: `blocked` → `agent:ready` or `operator`, with a comment. Then run
   `bash .claude/statusline.sh --refresh` so the status line shows the new
   count.
