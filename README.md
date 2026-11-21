# claude-code-session-toolkit

Small tools from a daily Claude Code setup, copied out as one repo with one folder per tool. They cover what tokens cost (`token-report`), docs discipline (`notes`), session hygiene (`bg`, `reap-dev-servers`, `agent-watch`, `compact-restore`), audits and prose (`code-audit`, `harness-audit`, `plain-prose`), Notion from the command line (`notion`), smaller screenshots (`img-shrink`), scripted browser checks (`browse`), Apify from the command line (`apify`), a status line (`status-line`), Android emulator and build checks (`emu`, `check-16kb`) and small helpers (`commit`, `reminders`, `agent-cost-line`, `worker-agent`). Each tool installs on its own.

| Tool | What it does |
| --- | --- |
| [`token-report/`](token-report/) | Shows where tokens go from your session transcripts: by project, model, session and subagent. Includes `subagent-cost` and an optional per-prompt hook. |
| [`notes/`](notes/) | Keeps narrative docs as one file per topic behind an index, with size limits, an edit hook and a pre-commit hook installer. |
| [`bg/`](bg/) | Starts background processes with PID files and logs in the session scratchpad, and stops them by name. |
| [`reap-dev-servers/`](reap-dev-servers/) | Stops Metro, `next dev` and jest processes that sessions left running, at session start. |
| [`agent-watch/`](agent-watch/) | Wakes the main thread when a background subagent is stuck. A script, a hook and a test. |
| [`compact-restore/`](compact-restore/) | After compaction, restores the scratchpad state file, edited files, commits and your last prompts. |
| [`code-audit/`](code-audit/) | A read-only repo audit skill with a brief template, five stack guides and ten helper scripts. |
| [`harness-audit/`](harness-audit/) | Audits how you work with Claude Code from local session history; read-only; ends with a ranked report. |
| [`plain-prose/`](plain-prose/) | A skill and checker that remove AI-writing tells from docs and reports. |
| [`notion/`](notion/) | Reads and edits Notion pages over the REST API in compact Markdown, one section at a time, instead of fetching whole pages through the MCP connector. |
| [`img-shrink/`](img-shrink/) | A Read hook that shows Claude large screenshots shrunk to 1200 px, with `img-full` for the original. macOS only. |
| [`browse/`](browse/) | A scripted headless Chrome walk: one Bash call runs a whole web check instead of 10 to 20 Playwright MCP calls. |
| [`apify/`](apify/) | Apify's REST API as short tables: search the Store, read an actor's input schema, run it with a spending cap, and print only the fields you name. |
| [`status-line/`](status-line/) | A Claude Code status line: model, context against the compact window, session time, cost, 5h and 7d plan limits with pace, git state, running subagents. `statusline-price-fit` re-measures its subagent prices. |
| [`agent-cost-line/`](agent-cost-line/) | A hook that warns with an estimated token total when one prompt starts its 3rd, 5th, 10th, 15th and 20th subagent. |
| [`worker-agent/`](worker-agent/) | A subagent definition for build and fix work: Sonnet by default, compacts at 200k, trimmed tool list, short working rules. |
| [`notion-task-pages/`](notion-task-pages/) | A skill with the section order and writing rules for a Notion task page. Pairs with `notion/`. |
| [`reminders/`](reminders/) | A SessionStart hook that shows dated reminders from a TSV file, per folder. |
| [`commit/`](commit/) | A path-scoped `git commit` for shared trees: stages only the paths you name, adds the Claude trailers, and checks the committed files. |
| [`emu/`](emu/) | Drives the Android emulator from the shell: dump the screen, tap by label, wait, screenshot, GPS and demo status bar, plus a React Native debugger driver. |
| [`check-16kb/`](check-16kb/) | Builds each Android app's release APK and checks the 16 KB page alignment that Google Play requires. |

## Install
The four skills (`code-audit`, `harness-audit`, `notion-task-pages`, `plain-prose`) and the `worker` agent install as one Claude Code plugin, inside a session (Claude Code 2.1.275 or later):

```
/plugin install session-toolkit --marketplace mkhinini-motaz/claude-code-session-toolkit
```

The other command-line tools and hooks install with `install.sh`. Clone the repo, then install the tools you want. Each folder's README says what it needs.

    ./install.sh --list                     # the tools
    ./install.sh --dry-run token-report     # show what would be copied
    ./install.sh token-report notes         # copy to ~/.claude/bin, hooks and skills

`install.sh` copies a tool's files into `~/.claude/bin`, `~/.claude/hooks`, `~/.claude/agents`, `~/.claude/emu`, `~/.claude/skills/<name>` or, for the status line, `~/.claude/statusline-command.sh`. It refuses to overwrite an existing file and never edits `settings.json`: for a hook it prints the snippet to merge in by hand. Set `CLAUDE_HOME` to install somewhere other than `~/.claude`.

## Use with other agents

The four skills are `SKILL.md` folders, a format Codex, Cursor, GitHub Copilot, Gemini CLI and OpenCode also load. All five read a project's `.agents/skills/` folder, so copying a skill folder there should work. The command-line tools and hooks are for Claude Code and are not portable. I have only tested the skills in Claude Code.

## Notes

- The tools were built with Claude Code.
- Everything reads local files (your transcripts, settings and repos), except `notion`, `apify` and `browse`, which call the services they are named for (`browse` also runs `npm install` of `playwright-core` on first use, then loads whatever page you give it).
- Most scripts assume macOS paths (`/private/tmp/claude-<uid>/...` scratchpads, BSD `stat`, `sips`, the keychain `security`). Linux may need small changes; the tools that need macOS say so under Requirements.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues labelled [`good first issue`](https://github.com/mkhinini-motaz/claude-code-session-toolkit/labels/good%20first%20issue) are a good place to start. A Linux port of a macOS-only tool is welcome.

## Credits

`plain-prose` is adapted from [`stop-slop`](https://github.com/hardikpandya/stop-slop) by Hardik Pandya (MIT, copyright 2025 Hardik Pandya); the licence text is in `plain-prose/NOTICE`.

## Licence

MIT, see `LICENSE`.
