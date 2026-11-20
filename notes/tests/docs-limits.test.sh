#!/bin/sh
# Offline test for docs-limits.sh: a missing notes binary warns and passes; NOTES_INDEXES picks the index names.
# Uses a stub in place of notes, in a scratch dir; touches nothing else.
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
h=$(cd "$(dirname "$0")/.." && pwd)/docs-limits.sh
printf '#!/bin/sh\nexit 1\n' > "$d/fail"; chmod +x "$d/fail"
f=/x/CLAUDE.md
printf '{"tool_input":{"file_path":"%s"}}' "$f" | NOTES_BIN=/nonexistent sh "$h" 2>"$d/err"; rc=$?
[ $rc = 0 ] && grep -q 'not found' "$d/err" || { echo "FAIL: missing notes must warn and exit 0 (rc=$rc)"; exit 1; }
printf '{"tool_input":{"file_path":"%s"}}' "$f" | NOTES_BIN="$d/fail" sh "$h" 2>/dev/null; [ $? = 2 ] || { echo "FAIL: a failing check must exit 2"; exit 1; }
idx=/x/docs/map.md
printf '{"tool_input":{"file_path":"%s"}}' "$idx" | NOTES_BIN="$d/fail" sh "$h" 2>/dev/null; [ $? = 0 ] || { echo "FAIL: unlisted index must pass"; exit 1; }
printf '{"tool_input":{"file_path":"%s"}}' "$idx" | NOTES_INDEXES=a.md,map.md NOTES_BIN="$d/fail" sh "$h" 2>/dev/null; [ $? = 2 ] || { echo "FAIL: NOTES_INDEXES index must be checked"; exit 1; }
# the hook uses the notes installed next to it, not ~/.claude (as after CLAUDE_HOME=... ./install.sh notes)
mkdir -p "$d/i/hooks" "$d/i/bin"; cp "$h" "$d/i/hooks/docs-limits.sh"; cp "$d/fail" "$d/i/bin/notes"
printf '{"tool_input":{"file_path":"%s"}}' "$f" | env -u NOTES_BIN sh "$d/i/hooks/docs-limits.sh" 2>/dev/null; [ $? = 2 ] || { echo "FAIL: sibling bin/notes must be used"; exit 1; }
# a bare NOTES_BIN name is found on PATH
printf '{"tool_input":{"file_path":"%s"}}' "$f" | PATH="$d:$PATH" NOTES_BIN=fail sh "$h" 2>/dev/null; [ $? = 2 ] || { echo "FAIL: bare NOTES_BIN must resolve on PATH"; exit 1; }
# a crash (traceback) is a warning, not a limit break
printf '#!/bin/sh\necho Traceback; exit 1\n' > "$d/crash"; chmod +x "$d/crash"
printf '{"tool_input":{"file_path":"%s"}}' "$f" | NOTES_BIN="$d/crash" sh "$h" 2>/dev/null; [ $? = 0 ] || { echo "FAIL: a crash must pass"; exit 1; }
# a * in NOTES_INDEXES is not glob-expanded
touch "$d/map.md"; (cd "$d" && printf '{"tool_input":{"file_path":"%s"}}' "$idx" | NOTES_INDEXES='*' NOTES_BIN="$d/fail" sh "$h" 2>/dev/null); [ $? = 0 ] || { echo "FAIL: * must not glob"; exit 1; }
echo ok
