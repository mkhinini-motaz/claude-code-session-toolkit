# notes

Keeps a project's narrative docs as one small file per topic behind an index, and enforces size limits so `CLAUDE.md` and the index stay short. `CLAUDE.md` holds rules, `docs/notes/<topic>.md` holds the narrative, `docs/architecture-notes.md` indexes it (headings and links only).

## Install

    ./install.sh notes     # copies notes to ~/.claude/bin and docs-limits.sh to ~/.claude/hooks

## Usage

    notes split <file.md>            # each H1-H3 section becomes notes/<slug>.md beside the file; the file becomes the index
    notes check <index.md> [orig.md] # every link resolves, every note is linked once; with orig.md, no line was lost
    notes check-all [--edit] [path]  # the limits for the project around the current folder
    notes self-test                  # proves each limit fails when broken, on a scratch folder
    notes install-hooks <project>    # a git pre-commit hook in each repo that runs check-all on doc commits

Limits: `CLAUDE.md`, each index and each note at most 40 000 bytes; an index holds only headings and links; every link resolves; no note is orphaned. A project root is the outermost folder below your home directory with a `CLAUDE.md`; each folder in it with its own `CLAUDE.md` is a repo. `NOTES_INDEXES=name.md,other.md` changes the index file names looked for under `docs/` (default `architecture-notes.md`).

## Hook (optional)

`docs-limits.sh` runs after each edit of a `CLAUDE.md`, a note or an index and hands a failure back to Claude to fix in the same turn (exit 2). Links and orphans are left to the pre-commit hook, because a note written before its index line is a normal mid-edit state. Add to `~/.claude/settings.json`:

    { "hooks": { "PostToolUse": [ { "matcher": "Edit|Write|MultiEdit", "hooks": [ { "type": "command", "command": "~/.claude/hooks/docs-limits.sh" } ] } ] } }

## Requirements

Python 3, `jq` for the hook. The hook runs the `notes` installed next to it (`../bin/notes`), else `NOTES_BIN`, else `notes` on `PATH`.
