# bg

Starts background processes the safe way: the PID comes from `$!` and goes to `<scratchpad>/<name>.pid`, output to `<name>.log`, so you can list and stop them by name instead of with `pkill`.

## Install

    ./install.sh bg        # copies bg to ~/.claude/bin

## Usage

    bg start <name> [--cwd dir] -- <cmd...>
    bg ls
    bg stop <name> | --all
    bg --self-test

The folder is `BG_DIR` if set, else `/private/tmp/claude-<uid>/*/$CLAUDE_CODE_SESSION_ID/scratchpad` (Claude Code's per-session scratchpad on macOS). `start` also saves the process start time in `<name>.start`; `stop` kills the PID and its children only if that time still matches, so a reused PID is never killed, and a pid file with no start time (written by an older bg) is not stopped; `start` treats a name whose PID was reused as free. A process whose command contains an entry of `BG_KEEP` (a `:`-separated list of substrings, default `mysqld:redis-server`) is skipped as a shared server; set `BG_KEEP=` to keep nothing.

## Requirements

A POSIX shell, `pgrep`, `ps`. No hook.
