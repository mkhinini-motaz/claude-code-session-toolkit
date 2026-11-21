# Privacy

Last updated 21 November 2026. This covers the session-toolkit plugin and the tools in this repository.

- The author runs no server and collects nothing. Nothing has telemetry, analytics or an account.
- What Claude reads while you use the plugin goes to Anthropic as part of your conversation, under your Claude plan's terms and [Anthropic's privacy policy](https://www.anthropic.com/legal/privacy).
- `notion-task-pages` writes pages through the Notion tools you already have, to your own Notion workspace.
- `worker` runs the commands its task needs in your project, within the permissions you have set.
- `worker` can search the web and open pages with Claude's built-in web tools. The search query is built from its task.
- The tools that call a service (`notion`, `apify`) run on your machine and send your own token only to that service.
- Logs and reports the tools write stay on your machine.

Questions: open an issue at https://github.com/mkhinini-motaz/claude-code-session-toolkit/issues.
