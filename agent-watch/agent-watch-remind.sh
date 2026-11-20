#!/usr/bin/env bash
# PostToolUse (Agent): after a spawn, remind the main thread to start agent-watch in
# the background unless one already watches this session, so a stuck agent wakes it.
set -u
payload=$(cat)
sid=$(printf '%s' "$payload" | jq -r '.session_id // empty')
tp=$(printf '%s' "$payload" | jq -r '.transcript_path // empty')
[ -n "$sid" ] && [ -n "$tp" ] || exit 0
dir="$(dirname "$tp")/$sid/subagents"
pgrep -f "agent-watch $dir" >/dev/null && exit 0
aw="$(dirname "$0")/../bin/agent-watch"; [ -x "$aw" ] || aw=agent-watch  # the installed copy, else PATH
msg="No agent-watch runs for this session. Start it once with Bash run_in_background, in the batch of your next calls (not a call of its own): $aw $dir"
jq -nc --arg m "$msg" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$m}}'
