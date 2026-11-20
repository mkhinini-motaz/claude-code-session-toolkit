#!/usr/bin/env bash
# Install tools from this toolkit into ~/.claude, one at a time.
#   ./install.sh --list                 list the tools
#   ./install.sh --dry-run <tool>...    show what would be copied
#   ./install.sh <tool>...              copy; stops before copying anything if a target file exists
# Never edits settings.json: for a hook tool it prints the snippet to merge in by hand.
# Set CLAUDE_HOME to install somewhere other than ~/.claude.
set -euo pipefail
cd "$(dirname "$0")"
DEST="${CLAUDE_HOME:-$HOME/.claude}"
case "$DEST" in *'"'*|*\\*) echo "CLAUDE_HOME must not contain \" or \\"; exit 2 ;; esac
# how the hook commands name DEST: quoted (inside the JSON string) when it holds anything but plain path characters
REF="$DEST"; case "$DEST" in *[!A-Za-z0-9_./-]*) REF="\\\"$DEST\\\"" ;; esac
REF=$(printf '%s' "$REF" | sed 's/[&|\\]/\\&/g') # escaped for the sed replacement below
TOOLS="token-report notes bg reap-dev-servers agent-watch compact-restore code-audit plain-prose harness-audit notion img-shrink browse apify status-line agent-cost-line worker-agent notion-task-pages reminders commit emu check-16kb"

# tool -> "source|target" lines (target relative to $DEST)
files() {
  case "$1" in
    token-report)     echo "token-report/token-report|bin/token-report"; echo "token-report/subagent-cost|bin/subagent-cost" ;;
    notes)            echo "notes/notes|bin/notes"; echo "notes/docs-limits.sh|hooks/docs-limits.sh" ;;
    bg)               echo "bg/bg|bin/bg" ;;
    notion)           echo "notion/notion|bin/notion"; echo "notion/notion-push|bin/notion-push" ;;
    img-shrink)       echo "img-shrink/img-shrink.sh|hooks/img-shrink.sh"; echo "img-shrink/img-shrink.py|hooks/img-shrink.py"; echo "img-shrink/img-full|bin/img-full" ;;
    browse)           echo "browse/browse|bin/browse" ;;
    apify)            echo "apify/apify|bin/apify" ;;
    reap-dev-servers) echo "reap-dev-servers/reap-dev-servers|bin/reap-dev-servers" ;;
    agent-watch)      echo "agent-watch/agent-watch|bin/agent-watch"; echo "agent-watch/agent-watch-remind.sh|hooks/agent-watch-remind.sh" ;;
    compact-restore)  echo "compact-restore/compact-restore.py|hooks/compact-restore.py" ;;
    status-line)      echo "status-line/statusline-command.sh|statusline-command.sh"; echo "status-line/statusline-price-fit|bin/statusline-price-fit" ;;
    agent-cost-line)  echo "agent-cost-line/agent-cost-line.py|hooks/agent-cost-line.py" ;;
    worker-agent)     echo "worker-agent/worker.md|agents/worker.md" ;;
    reminders)        echo "reminders/reminders.py|hooks/reminders.py" ;;
    commit)           echo "commit/commit|bin/commit" ;;
    check-16kb)       echo "check-16kb/check-16kb|bin/check-16kb" ;;
    emu)              for f in emu ui.py demo.sh gps.sh storelang.sh rn.mjs; do echo "emu/$f|emu/$f"; done ;;
    code-audit|plain-prose|harness-audit|notion-task-pages)
      find "$1" -type f ! -name .DS_Store ! -name README.md ! -name '*.pyc' ! -path '*/__pycache__/*' ! -path '*/tests/*' | sort |
        while read -r f; do echo "$f|skills/$f"; done ;;
    *) return 1 ;;
  esac
}

# tool -> settings.json hook snippet (empty for tools with no hook)
snippet() {
  case "$1" in
    token-report) echo '{ "hooks": { "UserPromptSubmit": [ { "hooks": [ { "type": "command", "command": "~/.claude/bin/token-report hook" } ] } ] } }' ;;
    notes)        echo '{ "hooks": { "PostToolUse": [ { "matcher": "Edit|Write|MultiEdit", "hooks": [ { "type": "command", "command": "~/.claude/hooks/docs-limits.sh" } ] } ] } }' ;;
    reap-dev-servers) echo '{ "hooks": { "SessionStart": [ { "hooks": [ { "type": "command", "command": "~/.claude/bin/reap-dev-servers" } ] } ] } }' ;;
    agent-watch)  echo '{ "hooks": { "PostToolUse": [ { "matcher": "Agent", "hooks": [ { "type": "command", "command": "~/.claude/hooks/agent-watch-remind.sh" } ] } ] } }' ;;
    compact-restore) echo '{ "hooks": { "SessionStart": [ { "matcher": "compact", "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/compact-restore.py" } ] } ] } }' ;;
    status-line)  echo '{"statusLine": {"type": "command", "command": "bash ~/.claude/statusline-command.sh", "refreshInterval": 10}}' ;;
    agent-cost-line) echo '{ "hooks": { "UserPromptSubmit": [ { "hooks": [ { "type": "command", "command": "~/.claude/hooks/agent-cost-line.py" } ] } ], "PreToolUse": [ { "matcher": "Agent", "hooks": [ { "type": "command", "command": "~/.claude/hooks/agent-cost-line.py" } ] } ] } }' ;;
    reminders)    echo '{ "hooks": { "SessionStart": [ { "matcher": "startup|clear", "hooks": [ { "type": "command", "command": "python3 ~/.claude/hooks/reminders.py", "timeout": 5 } ] } ] } }' ;;
    img-shrink)   echo '{ "hooks": { "PreToolUse": [ { "matcher": "Read", "hooks": [ { "type": "command", "command": "~/.claude/hooks/img-shrink.sh", "timeout": 10 } ] } ], "PostToolUse": [ { "matcher": "Read", "hooks": [ { "type": "command", "command": "~/.claude/hooks/img-shrink.sh", "timeout": 10 } ] } ] } }' ;;
  esac
}

[ $# -gt 0 ] || { sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
DRY=0; WANT=()
for a in "$@"; do
  case "$a" in
    --list) for t in $TOOLS; do [ -e "$t" ] && echo "$t"; done; exit 0 ;;
    --dry-run) DRY=1 ;;
    -*) echo "unknown option: $a"; exit 2 ;;
    *) files "$a" >/dev/null 2>&1 && [ -e "$a" ] || { echo "unknown tool: $a (see --list)"; exit 2; }; WANT+=("$a") ;;
  esac
done
[ ${#WANT[@]} -gt 0 ] || { echo "name at least one tool (see --list)"; exit 2; }

pairs=()
for t in "${WANT[@]}"; do while IFS= read -r l; do pairs+=("${l%%|*}|$DEST/${l#*|}"); done < <(files "$t"); done

clash=0
for p in "${pairs[@]}"; do [ -e "${p#*|}" ] && { echo "exists: ${p#*|}"; clash=1; }; done
[ $clash = 1 ] && [ $DRY = 0 ] && { echo "Nothing copied. Move those files aside or merge them by hand."; exit 1; }

for p in "${pairs[@]}"; do
  src="${p%%|*}"; dst="${p#*|}"
  if [ $DRY = 1 ]; then echo "$src -> $dst$([ -e "$dst" ] && echo ' (exists: a real install would stop)')"; else mkdir -p "$(dirname "$dst")"; cp -p "$src" "$dst"; fi
done
echo "${#pairs[@]} files $([ $DRY = 1 ] && echo 'would be copied' || echo copied) to $DEST"
for t in "${WANT[@]}"; do
  s=$(snippet "$t" | sed "s|~/.claude|$REF|g") # snippets are written for ~/.claude
  [ -n "$s" ] && printf '\n%s: add this to %s/settings.json (merge with what is there):\n%s\n' "$t" "$DEST" "$s"
done
exit 0
