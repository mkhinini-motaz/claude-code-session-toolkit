# agent-watch

Wakes the main thread when a background subagent is stuck. A stuck agent sends nothing, and an idle main thread wakes only when a background task exits. `agent-watch` runs in the background and exits on the first agent whose transcript has been silent for N minutes (default 30) while its meta file says unfinished. It never exits just because all agents are done, and ends after the session's own transcript has been silent 12 hours. The 30-minute default comes from a sample of 400 agent transcripts: a running agent's longest silence was at most 18 minutes waiting for a model reply and 4 minutes for a tool, at the 99th percentile.

A PostToolUse hook on the `Agent` tool reminds Claude to start the watcher once per session.

## Install

    ./install.sh agent-watch    # agent-watch to ~/.claude/bin, agent-watch-remind.sh to ~/.claude/hooks

## Usage

    agent-watch [--once] <session subagents dir> [minutes]

`--once` prints stuck agents now and exits (1 if any, 0 if none). Test: `bash agent-watch/tests/agent-watch.test.sh` (prints `ok`).

## Hook

Add to `~/.claude/settings.json`:

    { "hooks": { "PostToolUse": [ { "matcher": "Agent", "hooks": [ { "type": "command", "command": "~/.claude/hooks/agent-watch-remind.sh" } ] } ] } }

## Requirements

macOS (uses BSD `stat -f`), `bash`, `jq`, `pgrep`. The test also needs `timeout` (GNU coreutils).
