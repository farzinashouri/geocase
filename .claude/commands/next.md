---
description: List the owner's open, unblocked tasks that fit the time they have now, by phase. Optional argument - a time budget such as 15m, 1h, 2h.
argument-hint: "[time budget, e.g. 30m]"
---

The owner works on GeoCase when they have time, in any order (issue #149).
Each phase is a GitHub milestone with one issue per task; a closed issue is a
done task. Your job: show what they can pick from now. Plain, direct English;
the owner is a non-native speaker.

Time budget: `$ARGUMENTS` (empty means "no limit").

1. **Read the open tasks.** For each open milestone named "Phase N: …", in
   phase order:
   `gh issue list --milestone "<title>" --state open --json number,title,labels`.
   Keep issues labelled `operator` or `agent:needs-human` (the owner's tasks).
   Drop issues labelled `blocked`.
2. **Filter by time.** Each issue has one `size:` label (`size:5m`,
   `size:30m`, `size:1h`, `size:2h`). With a budget, keep the issues whose size
   fits it. An issue with no `size:` label: estimate it and add the label.
3. **Answer** with one short list per phase: `#N title · size`, at most 5 per
   phase, smallest first, and the done/total of that milestone in the heading.
   The owner picks; do not rank or recommend unless asked. If nothing fits,
   say so and name the smallest task.
4. **When the owner picks one:** give the first concrete step (a link, a
   command, a file to open) and offer the part you can do (draft text, run a
   command, read a log).
5. **When the owner says it is done:** tick the issue's checklist and close it
   (or say what is left). Re-label every issue whose body says `Depends on #N`
   for it: `blocked` → `agent:ready` or `operator`, with a comment. Then run
   `bash .claude/statusline.sh --refresh` so the status line shows the new
   count.
