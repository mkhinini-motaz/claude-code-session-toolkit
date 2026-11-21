#!/bin/bash
# install.sh into a scratch CLAUDE_HOME with an odd name: the printed snippets stay valid JSON and name that folder.
cd "$(dirname "$0")/.." || exit 1
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
export HOME="$d/home"; mkdir -p "$HOME"
CLAUDE_HOME="$d/odd a&b|c" ./install.sh img-shrink notes status-line >"$d/out" || { echo "FAIL: install rc"; exit 1; }
[ -f "$d/odd a&b|c/hooks/img-shrink.sh" ] || { echo "FAIL: not installed"; exit 1; }
grep -q '^{' "$d/out" || { echo "FAIL: no snippet"; exit 1; }
grep '^{' "$d/out" | python3 -c '
import json, sys
for l in sys.stdin:
    c = json.dumps(json.loads(l))
    assert "odd a&b|c" in c and "~/.claude" not in c, c
' || { echo "FAIL: snippet"; exit 1; }
CLAUDE_HOME='a"b' ./install.sh --dry-run notes >/dev/null; [ $? = 2 ] || { echo "FAIL: quote in CLAUDE_HOME must be refused"; exit 1; }
CLAUDE_HOME="$d/c" ./install.sh plain-prose >/dev/null || { echo "FAIL: skill install"; exit 1; }
[ -f "$d/c/skills/plain-prose/SKILL.md" ] && [ -f "$d/c/skills/plain-prose/check.py" ] || { echo "FAIL: skill not at skills/plain-prose"; exit 1; }
[ -z "$(find "$HOME" -type f)" ] || { echo "FAIL: wrote into HOME"; exit 1; }
echo ok
