# AGENTS.md

Small, separate tools for Claude Code, one folder per tool. Tools share no code; each folder's README says what it needs.

- Install a tool: `./install.sh <tool>` (`--dry-run` shows what it copies, `--list` names the tools).
- Tests (run from the repo root; a test that writes state points it at a scratch dir, never your `~/.claude`):
  - Shell: `agent-watch/tests/agent-watch.test.sh`, `compact-restore/tests/compact-restore.test.sh`, `sh notes/tests/docs-limits.test.sh` (missing `notes` warns and passes; the `notes` next to the hook, else `NOTES_BIN`, else `PATH`, is used; `NOTES_INDEXES` is honoured; a crash warns and passes), `sh bg/bg --self-test` (includes PID reuse and a pid file with no start time), `bash tests/install.test.sh` (install.sh into an odd `CLAUDE_HOME`), `bash status-line/tests/price-fit.test.sh`.
  - Python: `python3 notion/notion --self-test`, `python3 notion/notion-push --self-test`, `python3 img-shrink/img-shrink.py --self-test`, `python3 apify/apify --self-test`, `python3 agent-cost-line/agent-cost-line.py --self-test`, `python3 commit/commit --self-test`, `python3 notes/notes self-test`, `python3 token-report/token-report self-test`, `python3 token-report/subagent-cost --self-test`, `python3 reap-dev-servers/reap-dev-servers self-test` (any other argument, or an `--hours` that is nan, infinite or negative, prints usage and exits 2), `python3 skills/plain-prose/check.py self-test`, `python3 -I skills/harness-audit/scripts/collect.py selftest`, `python3 emu/ui.py self-test` (no device).
  - Node: `node browse/browse --self-test`.
  - Usage text only: `python3 status-line/statusline-price-fit` (exits 1, no self-test).
  - Status line: `echo '{"model":{"display_name":"Test"}}' | SL_STATE=$(mktemp -d) bash status-line/statusline-command.sh`; without `SL_STATE` it writes to `~/.claude/statusline-usage`.
  - `reminders`, `emu` (apart from `ui.py self-test`) and `check-16kb` have no self-test: see their READMEs.
- The main thread's state file is `<scratchpad>/state.md`, a worker's is `<scratchpad>/<task>/state.md`; `compact-restore` never hands one to the other, and `worker-agent/worker.md` says the same.
- CI: `.github/workflows/tests.yml` runs the list above on macOS with a scratch `HOME`.
- The skills in `skills/code-audit/`, `skills/harness-audit/`, `skills/notion-task-pages/` and `skills/plain-prose/` also ship as one plugin (`.claude-plugin/`), together with the `worker` agent. Check it after a change: `claude plugin validate .`
