#!/bin/bash
# Runs compact-restore.py on a scratch transcript, with and without a state file.
H="$(cd "$(dirname "$0")/.." && pwd)/compact-restore.py"
SLUG=-tmp-demo-project; SID=$(uuidgen | tr A-Z a-z)
SP=/private/tmp/claude-$(id -u)/$SLUG/$SID/scratchpad; T=$SP/crtest; rm -rf "$T"; mkdir -p "$T/$SLUG"
TR=$T/$SLUG/$SID.jsonl
python3 - "$TR" <<'P'
import json,sys
L=[{"type":"user","timestamp":"2026-10-06T01:00:00.000Z","message":{"role":"user","content":"first typed prompt"}},
 {"type":"user","message":{"role":"user","content":"<system-reminder>skip me</system-reminder>"}},
 {"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"Edit","input":{"file_path":"/x/a.php"}},{"type":"tool_use","name":"Write","input":{"file_path":"/x/b.php"}},{"type":"tool_use","name":"Edit","input":{"file_path":"/x/a.php"}},{"type":"tool_use","name":"Bash","input":{"command":"git commit --only a -m 'fix it'"}},{"type":"tool_use","name":"Bash","input":{"command":"~/.claude/bin/commit --by sonnet -m 'via tool' x"}},{"type":"tool_use","name":"Bash","input":{"command":"ls"}}]}},
 {"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"skip"}]}},
 {"type":"user","message":{"role":"user","content":"second typed prompt"}},
 {"type":"user","message":{"role":"user","content":"third typed prompt"}}]
open(sys.argv[1],'w').write('\n'.join(map(json.dumps,L)))
P
run(){ echo "{\"session_id\":\"$SID\",\"transcript_path\":\"$TR\",\"cwd\":\"/tmp/demo-project\",\"source\":\"compact\"}" | python3 $H; }
fail=0; chk(){ echo "$OUT" | grep -qF -- "$1" || { echo "FAIL: missing '$1'"; fail=1; }; }
nochk(){ echo "$OUT" | grep -qF -- "$1" && { echo "FAIL: unexpected '$1'"; fail=1; }; }
OUT=$(run)
chk "No state file survived compaction. Write $SP/state.md"; chk "/x/b.php"; chk "git commit --only a"
chk "via tool"; chk "second typed prompt"; chk "third typed prompt"; nochk "first typed prompt"; nochk "skip me"
[ "$(echo "$OUT" | grep -c '/x/a.php')" = 1 ] || { echo "FAIL: a.php not deduped"; fail=1; }
echo "DONE-ITEM-42" > $SP/State.md
OUT=$(run); chk "State file: $SP/State.md"; chk "DONE-ITEM-42"; nochk "No state file survived"
OUT=$(echo "{\"session_id\":\"$SID\",\"agent_id\":\"a1\",\"transcript_path\":\"$TR\",\"cwd\":\"/x\",\"source\":\"compact\"}" | python3 $H)
nochk "DONE-ITEM-42"; nochk "No state file survived"; chk "/x/b.php"  # a subagent never gets the parent state file
mkdir -p $SP/task1; echo "TASK-STATE-7" > $SP/task1/state.md  # a worker's <task>/state.md; newer than State.md
OUT=$(run); nochk "TASK-STATE-7"; chk "DONE-ITEM-42"  # the main thread never gets a worker's file
rm -f $SP/State.md; OUT=$(run); nochk "TASK-STATE-7"; chk "No state file survived"
rm -rf $SP/task1; rm -f $SP/State.md; rm -rf "$T"; rmdir "$SP" "$(dirname "$SP")" "$(dirname "$(dirname "$SP")")" 2>/dev/null
echo "bad json" | python3 $H; [ $? = 0 ] || { echo "FAIL: nonzero exit"; fail=1; }
[ $fail = 0 ] && echo "compact-restore: all assertions passed"; exit $fail
