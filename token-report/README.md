# token-report

Shows where Claude Code's tokens go, read from the session transcripts under `~/.claude/projects`. `subagent-cost` does the same for the subagents of one session.

## Install

    ./install.sh token-report        # from the toolkit root: copies token-report and subagent-cost to ~/.claude/bin

## Usage

    token-report [--days N] [path]   # one project's last N days (default 14): main thread against subagents, by model;
                                     # context size when the tokens were spent; costliest sessions; each subagent type;
                                     # which tools fill the main context; call counts of tools, skills and subagents
    token-report skills [--days N]   # every installed skill with its description size and how often it ran (default 30 days)
    token-report repos [--days N]    # input and output tokens per project folder and per day
    token-report hook [--over K]     # UserPromptSubmit hook, see below
    token-report self-test           # proves the counting on a scratch transcript
    subagent-cost <session id or subagents dir>   # tokens per subagent, grouped by agent type
    subagent-cost --self-test

Input tokens are everything a call reads: fresh input plus cache reads and cache writes. The weights used to order sessions are relative, never a price.

## Hook (optional)

`token-report hook` prints the context size on every prompt. Past K thousand tokens (default 300) it reminds Claude to keep a scratchpad state file current before auto-compaction. It also adds a short nudge for a prompt with a very large paste, a key-shaped string, a "do it all" request, or a long session that changes topic. It never blocks. Add to `~/.claude/settings.json`:

    { "hooks": { "UserPromptSubmit": [ { "hooks": [ { "type": "command", "command": "~/.claude/bin/token-report hook" } ] } ] } }

## Requirements

macOS and Python 3 (the hooks use `/private/tmp/claude-<uid>`). Reads local transcript files only; no network.
