#!/usr/bin/env bash
# Claude Code status line: the model, then done/total per phase milestone.
#
#   [Opus 5.5] done: P0 3/11 · P1 1/10 · P2 0/2
#
# Each phase is a GitHub milestone ("Phase N: ...") with one issue per task;
# a closed issue is a done task (issue #149). Milestones with no issues and
# milestones not named "Phase N" are left out. The milestones are read with
# `gh` at most every 10 minutes, in the background, into a cache file, so
# drawing the status line never waits on the network.
#
#   bash .claude/statusline.sh            # status line (reads JSON on stdin)
#   bash .claude/statusline.sh --refresh  # re-read the milestones now (/next)
#
# Tests set GEOCASE_MILESTONES_FILE (milestones JSON from a file, no gh) and
# GEOCASE_STATUS_CACHE (cache path).

ttl=600
max=120
cache="${GEOCASE_STATUS_CACHE:-${TMPDIR:-/tmp}/geocase-status.txt}"
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"

# Milestones JSON (an array) -> "P0 3/11 · P1 1/10".
summary='[ sort_by(.number)[]
  | select((.title | test("^Phase [0-9]+")) and (.open_issues + .closed_issues) > 0)
  | "P\(.title | capture("^Phase (?<n>[0-9]+)").n) \(.closed_issues)/\(.open_issues + .closed_issues)"
] | join(" · ")'

refresh() {
  local line
  line="$(cd "$repo_dir" && gh api "repos/{owner}/{repo}/milestones?state=all&per_page=100" --jq "$summary" 2>/dev/null)" || return 1
  printf '%s\n' "$line" >"$cache.tmp" && mv "$cache.tmp" "$cache"
}

mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; }

if [ "$1" = "--refresh" ]; then
  refresh
  exit $?
fi

input="$(cat)"
model=""
if command -v jq >/dev/null 2>&1; then
  model="$(printf '%s' "$input" | jq -r '.model.display_name // empty' 2>/dev/null)"
fi

if [ -n "$GEOCASE_MILESTONES_FILE" ]; then
  progress="$(jq -r "$summary" "$GEOCASE_MILESTONES_FILE" 2>/dev/null)"
else
  now="$(date +%s)"
  if [ ! -f "$cache" ] || [ $((now - $(mtime "$cache"))) -gt "$ttl" ]; then
    # Touch first so the redraws in the next 10 minutes do not start more fetches.
    touch "$cache"
    (refresh &) >/dev/null 2>&1
  fi
  progress="$(cat "$cache" 2>/dev/null)"
fi

[ -n "$progress" ] || progress="run /next"
line="done: $progress"
[ -n "$model" ] && line="[$model] $line"
if [ "${#line}" -gt "$max" ]; then
  line="${line:0:$((max - 1))}…"
fi
printf '%s\n' "$line"
