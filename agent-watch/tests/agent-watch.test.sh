#!/usr/bin/env bash
# Runs ../agent-watch (this copy) against fake subagent folders; exits 1 on any wrong verdict.
W="$(cd "$(dirname "$0")/.." && pwd)/agent-watch"
export AGENT_WATCH_POLL=1
T=$(mktemp -d)
fail=0
# macOS has no `timeout` unless coreutils is installed: a perl stand-in that also exits 124
command -v timeout >/dev/null || timeout() {
  perl -e '$s = shift; $p = fork // die; if (!$p) { exec @ARGV or exit 127 }
    $SIG{ALRM} = sub { kill "TERM", $p; exit 124 }; alarm $s; waitpid $p, 0; exit($? >> 8)' "$@"
}
ago() { touch -t "$(date -v-"$2"M +%Y%m%d%H%M.%S)" "$1"; }
agent() { # dir id finished(true|null) minutes-ago
  mkdir -p "$1"
  printf '{"agentType":"worker","description":"d %s","finished":%s}' "$2" "$3" > "$1/agent-$2.meta.json"
  ago "$1/agent-$2.jsonl" "$4"
}
check() { # expected-exit expected-text(or "") args...
  want=$1 text=$2; shift 2
  out=$(timeout 10 "$W" "$@" 2>&1); rc=$?
  { [ $rc = "$want" ] && { [ -z "$text" ] || printf '%s' "$out" | grep -q "$text"; }; } || { echo "FAIL $*: rc=$rc $out"; fail=1; }
}
agent "$T/s1/subagents" a1 null 45; agent "$T/s1/subagents" a2 true 90
check 1 "a1 worker" --once "$T/s1/subagents" 30
check 1 "a1 worker" "$T/s1/subagents" 30           # the watcher exits on a stuck agent
agent "$T/s2/subagents" b1 true 5; agent "$T/s2/subagents" b2 null 900
check 0 "" --once "$T/s2/subagents" 30             # finished and long-dead agents are not stuck
agent "$T/s3/subagents" c1 null 2; ago "$T/s3.jsonl" 800
check 0 "" "$T/s3/subagents" 30                    # session silent 12 h: the watcher ends
agent "$T/s4/subagents" d1 true 2; ago "$T/s4.jsonl" 1
timeout 3 "$W" "$T/s4/subagents" 30 >/dev/null 2>&1
[ $? = 124 ] || { echo "FAIL watcher exited although the session is live and nothing is stuck"; fail=1; }
rm -rf "$T"
[ $fail = 0 ] && echo "ok"
exit $fail
