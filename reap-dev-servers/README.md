# reap-dev-servers

Stops dev servers that sessions started and never stopped: Metro (`react-native start`), `next dev`, React Native devtools and jest runs. They keep running after a session ends and can pile up for weeks.

A process is stopped, with its children, only when its command matches those patterns, it is older than `--hours` (default 12), neither it nor a child holds an established TCP connection, and (for Metro) no Android emulator runs. Anything else, such as a database or an API server, is never touched. To protect a matching one, set `REAP_KEEP` to a `:`-separated list of substrings of its command line. Stops are logged to `~/.claude/logs/reap-dev-servers.log`.

## Install

    ./install.sh reap-dev-servers     # copies it to ~/.claude/bin

## Usage

    reap-dev-servers [--hours N] [--dry-run]
    reap-dev-servers self-test        # also --self-test; any other argument prints usage, exit 2

## Hook

Run it at every session start. Add to `~/.claude/settings.json`:

    { "hooks": { "SessionStart": [ { "hooks": [ { "type": "command", "command": "~/.claude/bin/reap-dev-servers" } ] } ] } }

## Requirements

Python 3, `ps`, and `lsof` for the connection check (macOS or Linux; tested on macOS).
