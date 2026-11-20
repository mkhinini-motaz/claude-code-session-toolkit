# status-line

A Claude Code status line in plain bash and jq. It shows the model and effort, context load against the auto-compact window, session time, cost (dollars from Claude Code, tokens summed from the transcripts, and the subagents' estimated part), the 5-hour and 7-day plan limits with a pace projection, the git branch against its remote, then running subagents and other live sessions.

`statusline-price-fit` re-measures the dollar prices per million weighted tokens that the script uses to estimate subagent cost. Transcripts hold tokens, not dollars, so it fits one price per model family against the real session cost the status line saves.

## Install

    ./install.sh status-line    # statusline-command.sh to ~/.claude, statusline-price-fit to ~/.claude/bin

Then merge the snippet that `install.sh` prints into `~/.claude/settings.json`:

    {"statusLine": {"type": "command", "command": "bash ~/.claude/statusline-command.sh", "refreshInterval": 10}}

## Usage

Claude Code pipes a JSON object into the script on every refresh. To try it by hand:

    echo '{"model":{"display_name":"Test"}}' | bash status-line/statusline-command.sh

Refit the prices after a model or price change. It reads one project's transcripts, named by `FIT_PROJECT` (a folder under `~/.claude/projects`) or `--project DIR`:

    statusline-price-fit --project ~/.claude/projects/<project-folder> [sessions=25] [session-id-prefix-to-skip ...]

Then edit the `price` function in `statusline-command.sh`. The prices in it were fitted on one machine on 13 Nov 2026 and will not fit your account.

## How it works

- The script keeps small per-file ledgers in `~/.claude/statusline-usage` (override with `SL_STATE`) and reads only the bytes added since the last refresh. Files older than 8 days are deleted.
- The compact window comes from `autoCompactWindow` in `settings.json` or in an agent's frontmatter.
- Pace compares the used percentage of each plan window with the time elapsed, from a history file the script appends to.

## Requirements

bash, jq, awk, git; macOS (`stat -f`, BSD `date`). `statusline-price-fit` needs Python 3.
