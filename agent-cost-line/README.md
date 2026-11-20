# agent-cost-line

A hook that warns when one prompt fans out into many subagents. It counts the Agent calls since your last prompt and, at the 3rd, 5th, 10th, 15th and 20th, shows a message such as "5 agents this prompt: about 7M tokens at 30-day medians per type."

## Install

    ./install.sh agent-cost-line    # copies agent-cost-line.py to ~/.claude/hooks

Merge the snippet that `install.sh` prints into `~/.claude/settings.json`. The same command runs on `UserPromptSubmit` (resets the counter) and on `PreToolUse` with matcher `Agent` (counts):

    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "$HOME/.claude/hooks/agent-cost-line.py"}]}],
    "PreToolUse": [{"matcher": "Agent", "hooks": [{"type": "command", "command": "$HOME/.claude/hooks/agent-cost-line.py"}]}]

## Usage

The `MEDIANS` table in the script holds the median raw tokens (in millions) of one run per subagent type. The numbers shipped are examples from one machine; replace them with the medians of your own transcripts (`token-report` shows runs per subagent). Types not in the table count as `OTHER`.

Test: `python3 agent-cost-line/agent-cost-line.py --self-test`.

## How it works

State lives in `$TMPDIR/agent-cost-<session>.json`. The hook never blocks and exits 0 on any error.

## Requirements

Python 3.
