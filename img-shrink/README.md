# img-shrink

A Read hook that makes screenshots cheaper. When Claude reads a PNG, JPEG or WebP whose long edge is over 1200 px, the hook points the Read at a copy shrunk to 1200 px. The original file is never changed. After the Read, the hook tells Claude the image was shrunk and how to get the original: `img-full <path>` prints the path of a full-size copy, which the hook leaves alone.

Measured on one machine (20 Nov 2026): 1,477 image reads in 14 days, and a phone screenshot dropped from about 1,475 to about 860 image tokens.

## Install

    ./install.sh img-shrink    # copies img-shrink.sh and img-shrink.py to ~/.claude/hooks and img-full to ~/.claude/bin

Then merge the hook snippet that `install.sh` prints into `~/.claude/settings.json`: the command `~/.claude/hooks/img-shrink.sh` under `PreToolUse` and `PostToolUse`, with matcher `Read`.

## How it works

- PreToolUse returns `updatedInput` with the shrunk copy's path. Copies live in `/private/tmp/claude-<uid>/img/small` and are pruned after two days.
- PostToolUse adds a one-line note naming the original size and the `img-full` command.
- `img-shrink.sh` is the hook command. It starts Python only when the payload names an image file: 32-42 ms a call against 106-178 ms for Python alone (timed over 20-30 calls a run, 3 runs), and the hook runs twice on every Read.
- Any error lets the Read go ahead unchanged.

Test: `python3 img-shrink/img-shrink.py --self-test`; `bash -n img-shrink/img-shrink.sh`.

## Requirements

macOS (`sips`, and it writes under `/private/tmp/claude-<uid>`), Python 3, a POSIX `sh`.
