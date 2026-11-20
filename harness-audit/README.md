# harness-audit

A Claude Code skill that audits how you work with Claude Code. It reads your local session history and ends with a ranked report: recurring mistakes, repeated work, unused or unreliable parts of your setup, and where tokens go. It proposes changes and builds nothing.

## What it reads

- Session transcripts: `~/.claude/projects/*/*.jsonl`, and the subagent transcripts beside them.
- Your setup: `CLAUDE.md` files, rules, settings, skills, agents and MCP configuration under `~/.claude` and the current project.
- Optional: a notes file you pass with `--notes`, and an `/insights` report if one exists.

## Read-only, nothing leaves your machine

The script uses only the Python standard library, makes no network calls and never edits your transcripts or setup. Its only output is a `harness-audit-<date>/` folder in your project (`data.json`, `summary.txt`, `prompts.tsv`, and the `report.md` Claude writes). Prompts and commands are redacted (your home folder becomes `~`, common secret formats are masked) before they are shown.

## Install

From the toolkit root:

    ./install.sh harness-audit     # copies it to ~/.claude/skills/harness-audit

## Run

In Claude Code:

    /harness-audit            # last 30 days, all projects
    /harness-audit 14         # last 14 days
    /harness-audit 30 --project my-app

The skill only runs when you call it. It scans, reads samples, then writes `report.md`.

Script flags, if you run it yourself (`python3 ~/.claude/skills/harness-audit/scripts/collect.py ...`):

- `scan [days]`: scan the last N days (default 30).
- `--project NAME|PATH`: only one project folder. NAME is any part of the folder name under `~/.claude/projects`; a path is converted to that name. Environment variable `HARNESS_AUDIT_PROJECT` does the same. Default: all projects.
- `--notes FILE`: optional end-of-session notes. Format: a `## heading` line per session, then optional lines `task: ...`, `corrections: ...`, `friction: ...`, `asked twice: ...`. They appear as `session_notes` in `data.json`.
- `show KEY`, `excerpt FILE LINE`, `prompts FILE`, `prompts-all [days]`, `checks [since] [name]`: look at parts of the result.
- `selftest`: checks the transcript record shapes the counts rely on. Run it with `python3 -I collect.py selftest`.

## Requirements

Python 3 (written and tested on 3.15; nothing version-specific is used beyond `pathlib` and `datetime`, but older versions are untested). Claude Code transcripts are an internal format, so a Claude Code update can break counts; `coverage` in the output shows parse failures, and `selftest` helps find what changed. Transcripts older than your `cleanupPeriodDays` setting (default 30) are already deleted, so the audit sees only what survived.

Built with Claude Code.
