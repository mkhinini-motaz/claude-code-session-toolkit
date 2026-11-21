# session-toolkit

A small, code-free part of the session toolkit for Claude Code. It holds two skills and one agent, all Markdown.

- `notion-task-pages`: section order and writing rules for a Notion task page.
- `plain-prose`: rules that strip AI-writing tells from docs, notes and READMEs. Without its checker script, it has Claude re-read the file against the rules.
- `worker`: an agent for build, fix and audit work that edits code or runs long. It compacts earlier and drops the tools a worker does not need.

Install it from the plugin directory once it is listed. For the full set, which adds the code-audit and harness-audit skills and the command-line tools, run this inside a session:

    /plugin install session-toolkit --marketplace mkhinini-motaz/claude-code-session-toolkit

Source and issues: https://github.com/mkhinini-motaz/claude-code-session-toolkit. MIT license.
