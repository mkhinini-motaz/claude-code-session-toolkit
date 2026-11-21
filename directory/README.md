# session-toolkit

A small, code-free part of the session toolkit for Claude Code. It holds two skills and one agent, all Markdown.

- `notion-task-pages`: section order and writing rules for a Notion task page.
- `plain-prose`: rules that strip AI-writing tells from docs, notes and READMEs. Without its checker script, it has Claude re-read the file against the rules.
- `worker`: an agent for build, fix and audit work that edits code or runs long. It runs on Sonnet and has only the file, shell, web and skill tools.

## Where it works

The two skills load in Claude Code, Cowork and chat on claude.ai. The `worker` agent loads in Claude Code and Cowork; chat skips plugin agents.

## What it runs and sends

- `notion-task-pages` holds rules only. Claude writes the page through the Notion tools you already have, so the page goes to your own Notion workspace and nowhere else.
- `plain-prose` reads the file you ask it to edit. This version has no checker script: Claude re-reads the file against the rules.
- `worker` runs the commands its task needs in your project, such as tests and builds, within the permissions you have set. It cannot start other agents or ask you questions.
- `worker` can search the web and open pages with Claude's built-in web tools. The search query is built from its task.
- Files `worker` reads can hold personal data, such as names and emails in fixtures or exports. It uses that data only in the session and stores none of it.
- The plugin has no server and no telemetry. Nothing goes to its author.

## Examples

- "Write the Notion task page for the payment retry work." (`notion-task-pages`)
- "Rewrite docs/setup.md in plain prose." (`plain-prose`)
- "Use a worker to fix the failing date tests; stop after three tries." (`worker`)

## Troubleshooting

- **The Notion page is not written.** Connect Notion first (a Notion connector), or ask for the page body as Markdown to paste.
- **No worker agent.** Check that you are in Claude Code or Cowork, then run `/agents`.

Install it from the plugin directory once it is listed. For the full set, which adds the code-audit and harness-audit skills and the command-line tools, run this inside a session:

    /plugin install session-toolkit --marketplace mkhinini-motaz/claude-code-session-toolkit

Source and issues: https://github.com/mkhinini-motaz/claude-code-session-toolkit. MIT license.

## Privacy

[Privacy policy](https://github.com/mkhinini-motaz/claude-code-session-toolkit/blob/main/PRIVACY.md): the author runs no server and collects no data.

## Support

Questions and bugs: open an issue at https://github.com/mkhinini-motaz/claude-code-session-toolkit/issues. Security problems: report them privately from the repository's Security tab (private vulnerability reporting), not in a public issue.
