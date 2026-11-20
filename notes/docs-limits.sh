#!/bin/sh
# PostToolUse(Edit|Write|MultiEdit) hook for every project.
# After an edit to a CLAUDE.md, a docs/notes/ file or a notes index, run `notes` (the copy installed next to this hook, else NOTES_BIN or PATH)
# check-all --edit on that repo: CLAUDE.md, the index and each note at most 40 000 bytes, the index
# holding only headings and links. A failure exits 2, which hands the message back to Claude to fix
# in the same turn. Links and orphans are left to the pre-commit hook, because a note written
# before its index line is a normal mid-edit state. A file in no project (no CLAUDE.md above it,
# below home) passes untouched.
f=$(jq -r '.tool_input.file_path // ""' 2>/dev/null)
case "$f" in */stale/*|*/node_modules/*|*/vendor/*) exit 0 ;; esac
case "$f" in
  */CLAUDE.md|*/docs/notes/*.md) ;;
  *) hit=0; old=$IFS; IFS=,; set -f
     for i in ${NOTES_INDEXES:-architecture-notes.md}; do case "$f" in */docs/"$i") hit=1 ;; esac; done
     IFS=$old; set +f; [ $hit = 1 ] || exit 0 ;;
esac
bin="${NOTES_BIN:-$(dirname "$0")/../bin/notes}"
[ -x "$bin" ] || bin=$(command -v "${NOTES_BIN:-notes}" 2>/dev/null)
[ -x "$bin" ] || { echo "docs-limits: ${NOTES_BIN:-notes} not found, doc limits not checked (./install.sh notes)" >&2; exit 0; }
out=$("$bin" check-all --edit "$f" 2>&1) && exit 0
case "$out" in *Traceback*) echo "docs-limits: notes crashed, doc limits not checked:" >&2; printf '%s\n' "$out" | tail -3 >&2; exit 0 ;; esac
printf 'Doc limits broken by this edit - fix before going on:\n%s\n' \
  "$(printf '%s\n' "$out" | grep -v ': ok$')" >&2
exit 2
