# compact-restore

A SessionStart hook for the `compact` source. After Claude Code compacts a conversation, it prints the scratchpad `state.md` of that session (a worker's `<task>/state.md` is never taken for the main thread's), the files edited, the git commits run and your last two prompts, so the next turn starts from facts on disk instead of the summary alone. If no state file survived it says so and tells Claude to write one. A subagent only gets a state file it wrote itself (`<scratchpad>/<task>/state.md`). It fails silent and never blocks a session.

The state file is `<scratchpad>/state.md` in Claude Code's per-session scratchpad (`/private/tmp/claude-<uid>/<project>/<session>/scratchpad` on macOS); keeping it current is your convention, for example via a line in `CLAUDE.md`.

## Install

    ./install.sh compact-restore    # copies it to ~/.claude/hooks

## Hook

Add to `~/.claude/settings.json`:

    { "hooks": { "SessionStart": [ { "matcher": "compact", "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/compact-restore.py" } ] } ] } }

## Test

    bash compact-restore/tests/compact-restore.test.sh    # prints "compact-restore: all assertions passed"

## Requirements

macOS (it looks in `/private/tmp/claude-<uid>`), Python 3; the test needs `uuidgen`.
