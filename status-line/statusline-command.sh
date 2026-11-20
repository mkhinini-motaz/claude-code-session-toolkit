#!/bin/bash
# Status line: model+effort | context vs auto-compact window | session time | cost ($ + tokens, agents' part) |
# 5h/7d plan limits with pace | git branch vs remote; then running subagents, other sessions, recap.
input=$(cat)
now=$(date +%s)
# Colors: a segment keeps its own hue until a threshold, then turns bold yellow
# (warn) or bold red (crit). lvl prints the color for a value against two limits.
WARN='220;1' CRIT='196;1'
lvl() { local v=${2%.*}; v=${v:-0}; [ "$v" -ge "$4" ] && echo "$CRIT" || { [ "$v" -ge "$3" ] && echo "$WARN" || echo "$1"; }; }

# --- model + effort ---
model=$(echo "$input" | jq -r '.model.display_name // "?"')
effort=$(echo "$input" | jq -r '.effort.level // empty')
[ -n "$effort" ] && model="$model ($effort)"

# --- context load against the auto-compact window ---
# ctx% of the 1M window says little when compaction runs at 200k-300k, so the
# load is shown against the window that triggers it: settings.json
# modelSettings.<model>.autoCompactWindow, else the global autoCompactWindow.
# An agent's own frontmatter autoCompactWindow wins for its line (compact_at).
compact_at() { # $1 model id, $2 agent type (optional)
  local a=""
  [ -n "$2" ] && a=$(grep -h -m1 '^autoCompactWindow:' ~/.claude/agents/"$2".md ~/.claude/agents/*/"$2".md 2>/dev/null | head -1 | awk '{ print $2 }')
  [ -n "$a" ] && { echo "$a"; return; }
  jq -r --arg m "$1" '.modelSettings[$m].autoCompactWindow // .autoCompactWindow // empty' ~/.claude/settings.json 2>/dev/null
}
ctx_tok=$(echo "$input" | jq -r '.context_window.total_input_tokens // empty')
ctx_win=$(echo "$input" | jq -r '.context_window.context_window_size // empty')
ctx_max=$(compact_at "$(echo "$input" | jq -r '.model.id // empty')")
ctx_max=${ctx_max:-$ctx_win}
ctx="" ctx_color=178
if [ -n "$ctx_tok" ] && [ -n "$ctx_max" ]; then
  ctx="ctx $(awk -v n="$ctx_tok" 'BEGIN { printf "%.0fk", n / 1e3 }')/$(awk -v n="$ctx_max" 'BEGIN { printf "%.0fk", n / 1e3 }')"
  ctx_color=$(lvl 178 $((ctx_tok * 100 / ctx_max)) 75 90)
fi

# --- session time ---
# Claude Code's stdin JSON has no documented duration field; derive wall-clock
# elapsed time from the transcript's first message timestamp instead. If a
# future build adds .cost.total_duration_ms, prefer that (exact, API-reported).
duration_ms=$(echo "$input" | jq -r '.cost.total_duration_ms // empty')
transcript=$(echo "$input" | jq -r '.transcript_path // empty')
secs=""
if [ -n "$duration_ms" ]; then
  secs=$((duration_ms / 1000))
elif [ -n "$transcript" ] && [ -f "$transcript" ]; then
  first_ts=$(head -1 "$transcript" 2>/dev/null | jq -r '.timestamp // empty')
  if [ -n "$first_ts" ]; then
    first_ts="${first_ts%%.*}"; first_ts="${first_ts%Z}"
    start_epoch=$(TZ=UTC date -j -f "%Y-%m-%dT%H:%M:%S" "$first_ts" "+%s" 2>/dev/null)
    [ -n "$start_epoch" ] && secs=$(( $(date +%s) - start_epoch ))
  fi
fi
time_str=""
if [ -n "$secs" ] && [ "$secs" -ge 0 ] 2>/dev/null; then
  h=$((secs / 3600)); m=$(((secs % 3600) / 60)); s=$((secs % 60))
  if [ "$h" -gt 0 ]; then time_str=$(printf '%dh%02dm' "$h" "$m"); else time_str=$(printf '%dm%02ds' "$m" "$s"); fi
fi

# --- session tokens ---
# .context_window.total_*_tokens is the current context load (the ctx% segment),
# not what the session has used, so the session total is summed from its
# transcript plus its subagents' transcripts: every token each API call billed,
# cache reads included. Usage repeats on each line of one message, so it counts
# once per message id. Only bytes added since the last refresh are read; the
# first read of a big transcript takes about a second, once.
state=${SL_STATE:-$HOME/.claude/statusline-usage}  # SL_STATE: tests
mkdir -p "$state"
find "$state" -type f -mtime +8 -delete 2>/dev/null
five_reset=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
week_reset=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')
five_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
week_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
# A session gets rate_limits only with its first API reply, and one idle past a
# reset still holds the old window. Either way the newest account-wide figures
# another session saved (the pace history below) stand in while still current.
if [ "${five_reset:-0}" -le "$now" ] || [ "${week_reset:-0}" -le "$now" ]; then
  read -r _ h5 h7 hr5 hr7 _ < <(tail -n 1 "$state/limits-history" 2>/dev/null)
  [ "${five_reset:-0}" -le "$now" ] && [ "${hr5:-0}" -gt "$now" ] && five_pct=$h5 five_reset=$hr5
  [ "${week_reset:-0}" -le "$now" ] && [ "${hr7:-0}" -gt "$now" ] && week_pct=$h7 week_reset=$hr7
fi
# Each file's ledger also keeps an estimated cost, in all and inside the current
# 5h and 7d windows, for the subagent lines below. Transcripts hold tokens, not
# dollars, so tokens are weighted (cache write 5m 1.25x, 1h 2x, cache read 0.1x,
# output 5x) and priced in $ per million weighted tokens, fitted to this
# account's .cost.total_cost_usd over 20 sessions on one machine (about 10% off
# per session). `statusline-price-fit` (installed in ~/.claude/bin) measures them again.
# Note: haiku is a guess (too little haiku use to fit); refit when a model or its price changes.
cost_jq='def price: if test("fable") then 8 elif test("sonnet") then 1.7 elif test("haiku") then 0.6 else 3.1 end;
  fromjson? | select(.type == "assistant") | .message as $m | $m.usage as $u
  | ($u.cache_creation.ephemeral_1h_input_tokens // 0) as $w1
  | [$m.id, (($u.input_tokens // 0) + ($u.cache_creation_input_tokens // 0) + ($u.cache_read_input_tokens // 0) + ($u.output_tokens // 0)),
     ((($u.input_tokens // 0) + 1.25 * (($u.cache_creation_input_tokens // 0) - $w1) + 2 * $w1 + 0.1 * ($u.cache_read_input_tokens // 0) + 5 * ($u.output_tokens // 0)) * ($m.model // "" | price) / 1e6),
     (try (.timestamp | sub("\\.[0-9]+Z$"; "Z") | fromdate) catch 0)] | @tsv'
tok=0 agents_usd=0
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  for f in "$transcript" "${transcript%.jsonl}"/subagents/*.jsonl; do
    [ -f "$f" ] || continue
    sf="$state/tok-$(basename "$f" .jsonl)"
    off=0 sum=0 last=- usd=0 r5=- u5=0 r7=- u7=0 n=0
    [ -f "$sf" ] && read -r off sum last usd r5 u5 r7 u7 n < "$sf"
    # A ledger written before the cost and call-count fields existed is read again from the start.
    [ -z "$n" ] && { off=0 sum=0 last=- usd=0 r5=- u5=0 r7=- u7=0 n=0; }
    # A window that rolled over starts this file's cost inside it from zero.
    [ "$r5" = "${five_reset:--}" ] || { r5=${five_reset:--}; u5=0; }
    [ "$r7" = "${week_reset:--}" ] || { r7=${week_reset:--}; u7=0; }
    size=$(stat -f%z "$f")
    # Skip while the writer is mid-line; the next refresh reads that line whole.
    if [ "$size" -gt "$off" ] && [ -z "$(tail -c +"$size" "$f" | head -c 1)" ]; then
      read -r sum last usd u5 u7 n < <(tail -c +$((off + 1)) "$f" | head -c $((size - off)) \
        | LC_ALL=C grep -F '"type":"assistant"' \
        | jq -rR "$cost_jq" \
        | awk -v s="$sum" -v l="$last" -v c="$usd" -v c5="$u5" -v c7="$u7" -v n="$n" \
            -v w5=$(( ${five_reset:-0} - 18000 )) -v w7=$(( ${week_reset:-0} - 604800 )) '
          $1 != l && !seen[$1]++ { s += $2; c += $3; n++; if ($4 >= w5) c5 += $3; if ($4 >= w7) c7 += $3; l = $1 }
          END { printf "%.0f %s %.4f %.4f %.4f %d\n", s, l, c, c5, c7, n }')
      echo "$size $sum $last $usd $r5 $u5 $r7 $u7 $n" > "$sf"
    fi
    tok=$((tok + sum))
    [ "$f" != "$transcript" ] && agents_usd="$agents_usd $usd"
  done
fi
agents_usd=$(echo "$agents_usd" | awk '{ for (i = 1; i <= NF; i++) s += $i } END { printf "%.2f", s }')
fmt_tok() { awk -v n="$1" 'BEGIN { if (n >= 1e6) printf "%.1fM", n / 1e6; else if (n >= 1e4) printf "%.0fk", n / 1e3; else if (n >= 1e3) printf "%.1fk", n / 1e3; else print n }'; }

# --- cost ---
# Only shown if Claude Code supplies .cost.total_cost_usd; no local per-model
# pricing table is kept here (would go stale), so its absence means no $ figure
# rather than a guessed one.
cost_usd=$(echo "$input" | jq -r '.cost.total_cost_usd // empty')
cost_str=""
[ -n "$cost_usd" ] && cost_str=$(printf '$%.2f' "$cost_usd")
if [ "$tok" -gt 0 ]; then
  if [ -n "$cost_str" ]; then cost_str="$cost_str ($(fmt_tok "$tok") tok)"; else cost_str="$(fmt_tok "$tok") tok"; fi
fi
# The real total covers subagents too; their estimated part (ledger) is split out.
[ -n "$cost_usd" ] && [ "$tok" -gt 0 ] && [ "$agents_usd" != "0.00" ] && cost_str="${cost_str%)} · agents ~\$$agents_usd)"

# --- plan rate limits ---
# Only .rate_limits.five_hour and .rate_limits.seven_day exist in the documented
# stdin JSON (plus .spend_limit, a gateway spend cap, not shown here). There is
# no true "daily" limit and no per-model ("Fable") limit field, so the 5-hour
# session window stands in for daily and the model-specific limit is skipped
# rather than invented.
fmt_reset() { date -r "$1" "+${2:-%H:%M}" 2>/dev/null; }
# --- pace: where each limit lands at its reset ---
# Every session appends the account's used % to one history file at most once a
# minute. A session idle for a while still holds the % of its last call, so each
# line keeps the freshest reading (6th field: when its session last wrote its
# transcript), and every session shows it. Not the highest: the server can lower
# used % inside a window (seen once: 7d stuck at 98% for hours while the API
# said 61%). 5h rate = change over the last hour (the window's own average when
# the history is under 10 min). 7d rate = the week's own average: whole % steps
# make an hour's change too coarse, and it spans nights as the rest of the week
# will. Projected = used % at the reset at that rate, or the time it reaches 100%
# when that comes first.
hist="$state/limits-history"
pace5="" full5="" pace7="" full7=""
if [ -n "$five_pct" ] && [ -n "$week_pct" ] && [ -n "$five_reset" ] && [ -n "$week_reset" ] && [ "$five_reset" -gt "$now" ]; then
  fresh=$now; [ -n "$transcript" ] && [ -f "$transcript" ] && fresh=$(stat -f %m "$transcript")
  read -r five_pct week_pct fresh < <(tail -n 1 "$hist" 2>/dev/null | awk -v p5="$five_pct" -v p7="$week_pct" -v r5="$five_reset" -v r7="$week_reset" -v f="$fresh" \
    '$4 == r5 && $5 == r7 && $6 + 0 > f { p5 = $2; p7 = $3; f = $6 } END { print p5, p7, f }')
  lastt=$(tail -n 1 "$hist" 2>/dev/null | cut -d' ' -f1)
  [ $((now - ${lastt:-0})) -ge 60 ] && echo "$now $five_pct $week_pct $five_reset $week_reset $fresh" >> "$hist"
  [ "$(wc -l < "$hist")" -gt 400 ] && tail -n 200 "$hist" > "$hist.$$" && mv "$hist.$$" "$hist"
  read -r pace5 full5 pace7 full7 < <(awk -v now="$now" -v p5="$five_pct" -v p7="$week_pct" -v r5="$five_reset" -v r7="$week_reset" '
    function proj(p, t0, p0, start, reset,   rate, at) {
      if (t0 == "" || now - t0 < 600) { t0 = start; p0 = 0 }
      if (now - t0 < 600) return "- -"
      rate = (p - p0) / (now - t0); at = p + rate * (reset - now)
      return sprintf("%.0f %s", at, (at >= 100 && rate > 0) ? int(now + (100 - p) / rate) : "-")
    }
    $1 >= now - 3600 && $4 == r5 && t5 == "" { t5 = $1; q5 = $2 }
    END { print proj(p5, t5, q5, r5 - 18000, r5), proj(p7, "", "", r7 - 604800, r7) }' "$hist")
fi

# This session's share of each window. The limits are account-wide, so every
# session's status line keeps a ledger file: its cost now, and its cost when each
# window opened. Share = this session's cost in the window / all sessions' cost
# in the window x the account's used_percentage. Cost, not tokens, because the
# limits weigh a cache read far below a fresh token.
# Note: usage no status line sees (claude.ai, the phone, `claude -p`, another
# machine) is spread over the local sessions, so shares overstate while that runs.
session=$(echo "$input" | jq -r '.session_id // empty')
share5="" share7="" all5="" all7=""
if [ -n "$session" ] && [ -n "$cost_usd" ] && [ -n "$five_reset" ] && [ -n "$week_reset" ]; then
  lf="$state/cost-$session"
  prev="" r5="" b5="" r7="" b7=""
  [ -f "$lf" ] && read -r prev r5 b5 r7 b7 < "$lf"
  # A window that rolled over since the last refresh starts from the last cost seen.
  # A session seen for the first time counts from zero if it started inside the
  # window, else from its cost now (what it spent before the window can't be split).
  first_base() { [ -n "$duration_ms" ] && [ $(( $(date +%s) - duration_ms / 1000 )) -ge $(( $2 - $1 )) ] && echo 0 || echo "$cost_usd"; }
  [ "$r5" = "$five_reset" ] || { r5=$five_reset; b5=${prev:-$(first_base 18000 "$five_reset")}; }
  [ "$r7" = "$week_reset" ] || { r7=$week_reset; b7=${prev:-$(first_base 604800 "$week_reset")}; }
  echo "$cost_usd $r5 $b5 $r7 $b7" > "$state/.tmp-$session" && mv "$state/.tmp-$session" "$lf"
  read -r share5 share7 all5 all7 < <(cat "$state"/cost-* | awk -v c="$cost_usd" -v r5="$r5" -v b5="$b5" -v r7="$r7" -v b7="$b7" \
    -v p5="${five_pct:-0}" -v p7="${week_pct:-0}" '
    function pos(x) { return x > 0 ? x : 0 }
    $2 == r5 { s5 += pos($1 - $3) }
    $4 == r7 { s7 += pos($1 - $5) }
    END { printf "%.1f %.1f %.4f %.4f\n", (s5 > 0 ? pos(c - b5) / s5 * p5 : 0), (s7 > 0 ? pos(c - b7) / s7 * p7 : 0), s5, s7 }')
fi

# "≈71%" = projected at reset; "full 14:10" = reaches 100% before it (crit color).
# Warn from 70% used or a projection of 90%, crit from 90% used or full before reset.
pace_str() { # $1 projected %, $2 full epoch or -, $3 date format
  [ -z "$1" ] || [ "$1" = "-" ] && return
  [ "$2" != "-" ] && { echo " full $(fmt_reset "$2" "$3")"; return; }
  echo " ≈$1%"
}
limit_color() { # $1 own color, $2 used %, $3 projected %, $4 full epoch or -
  [ -n "$4" ] && [ "$4" != "-" ] && { echo "$CRIT"; return; }
  local c; c=$(lvl "$1" "$2" 70 90)
  [ "$c" = "$1" ] && [ -n "$3" ] && [ "$3" != "-" ] && c=$(lvl "$1" "$3" 90 1000)
  echo "$c"
}
five_str="" five_color=215
if [ -n "$five_pct" ]; then
  five_str=$(printf '5h %.0f%%' "$five_pct")
  [ -n "$share5" ] && five_str="$five_str (this ${share5}%)"
  if [ -n "$five_reset" ]; then rt=$(fmt_reset "$five_reset"); [ -n "$rt" ] && five_str="${five_str}→$rt"; fi
  five_str="$five_str$(pace_str "$pace5" "$full5" "%H:%M")"
  five_color=$(limit_color 215 "$five_pct" "$pace5" "$full5")
fi
week_str="" week_color=175
if [ -n "$week_pct" ]; then
  week_str=$(printf '7d %.0f%%' "$week_pct")
  [ -n "$share7" ] && week_str="$week_str (this ${share7}%)"
  if [ -n "$week_reset" ]; then rt=$(fmt_reset "$week_reset" "%a %H:%M"); [ -n "$rt" ] && week_str="${week_str}→$rt"; fi
  week_str="$week_str$(pace_str "$pace7" "$full7" "%a %H:%M")"
  week_color=$(limit_color 175 "$week_pct" "$pace7" "$full7")
fi

# --- current directory ---
cwd=$(echo "$input" | jq -r '.cwd // empty')
dir="${cwd/#$HOME/~}"

# --- git branch vs remote (silent, no output/errors outside a repo) ---
git_str=""
git_color=78
branch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)
if [ -n "$branch" ]; then
  counts=$(git -C "$cwd" --no-optional-locks rev-list --left-right --count '@{u}...HEAD' 2>/dev/null)
  if [ -n "$counts" ]; then
    behind=$(echo "$counts" | awk '{print $1}')
    ahead=$(echo "$counts" | awk '{print $2}')
    cmp=""
    [ "$ahead" -gt 0 ] && cmp="↑$ahead"
    [ "$behind" -gt 0 ] && { cmp="${cmp}↓$behind"; git_color=208; }
    [ -z "$cmp" ] && cmp="synced"
    git_str="$branch $cmp"
  else
    git_str="$branch (no upstream)"
    git_color=208
  fi
fi

# --- background work: live PIDs in this session's scratchpad + running subagents ---
# Subagent running = meta not finished, written under 90 s ago, last record not end_turn.
# BG_DIR overrides the scratchpad (tests).
bg_str=""
if [ -n "$session" ]; then
  nbg=0 nag=0
  for f in ${BG_DIR:-/private/tmp/claude-$(id -u)/*/$session/scratchpad}/*.pid; do
    [ -f "$f" ] && kill -0 "$(cat "$f")" 2>/dev/null && nbg=$((nbg + 1))
  done
  if [ -n "$transcript" ]; then
    for f in $(find "${transcript%.jsonl}/subagents" -name '*.jsonl' -newermt '90 seconds ago' 2>/dev/null); do
      grep -q '"finished":true' "${f%.jsonl}.meta.json" 2>/dev/null && continue
      tail -n 1 "$f" | grep -q '"stop_reason":"end_turn"' && continue
      nag=$((nag + 1))
    done
  fi
  [ "$nbg" -gt 0 ] && bg_str="$nbg bg"
  [ "$nag" -gt 0 ] && bg_str="${bg_str:+$bg_str · }$nag agent$([ "$nag" -gt 1 ] && echo s)"
  [ -n "$bg_str" ] && bg_str="⏳ $bg_str"
fi

# --- assemble ---
sep=$'\033[2m|\033[0m'
seg() { [ -n "$2" ] && printf '\033[38;5;%sm%s\033[0m' "$1" "$2"; }
add() { local s="$1"; [ -n "$s" ] && out="${out:+$out $sep }$s"; }

out=""
add "$(seg 111 "$model")"
add "$(seg "$ctx_color" "$ctx")"
add "$(seg 141 "$time_str")"
add "$(seg 108 "$cost_str")"
add "$(seg "$five_color" "$five_str")"
add "$(seg "$week_color" "$week_str")"
add "$(seg 33 "$dir")"
add "$(seg "$git_color" "$git_str")"
add "$(seg 214 "$bg_str")"

printf '%s' "$out"

# --- running subagents ---
# The stdin JSON describes the main thread only, even while a subagent's view is
# open (checked in 2.1.296), so each running subagent gets its own line: type,
# model, effort, task, run time, idle time (since its transcript was last written;
# a long test run or a stuck agent), API calls (split agents near 100), context
# load against its auto-compact window, tokens billed so far, estimated cost and
# its share of the 5h and 7d limits (its estimated cost in the window / all
# sessions' cost in the window x the account's used %), all from the ledger above.
# Two or more running get a total line first. Running = meta not marked finished,
# written in the last 60 min, and its last call did not end the turn, so a killed
# agent shows red idle time, then drops off after 60 min.
fmt_dur() { [ "$1" -ge 3600 ] && printf '%dh%02dm' $(($1 / 3600)) $(($1 % 3600 / 60)) || printf '%dm' $(($1 / 60)); }
hl() { [ "$1" = 180 ] && printf '%s' "$2" || printf '\033[38;5;%sm%s\033[0;38;5;180m' "$1" "$2"; }
alines=() atot=""
if [ -n "$transcript" ] && [ -d "${transcript%.jsonl}/subagents" ]; then
  while IFS= read -r f; do
    m="${f%.jsonl}.meta.json"
    grep -q '"finished":true' "$m" 2>/dev/null && continue
    IFS=$'\t' read -r stop smodel seffort sctx < <(tail -n 50 "$f" | LC_ALL=C grep -F '"type":"assistant"' \
      | jq -rRs '[split("\n")[] | fromjson? | select(.type == "assistant")]
        | (map(select(.message.usage | (.input_tokens // 0) + (.cache_creation_input_tokens // 0) + (.cache_read_input_tokens // 0) > 0)) | last) as $u
        | [(last.message.stop_reason // "running"), ($u.message.model // "?" | sub("^claude-"; "")), ($u.effort // "-"),
           ($u.message.usage | (.input_tokens // 0) + (.cache_creation_input_tokens // 0) + (.cache_read_input_tokens // 0))] | @tsv')
    case "$stop" in end_turn|stop_sequence|"") continue ;; esac
    IFS=$'\t' read -r stype sdesc < <(jq -r '[(.agentType // "agent" | sub("^.*:"; "")), (.description // "-")] | @tsv' "$m" 2>/dev/null)
    [ ${#sdesc} -gt 32 ] && sdesc="${sdesc:0:31}…"
    ssum=0 susd=0 su5=0 su7=0 scalls=0; sf="$state/tok-$(basename "$f" .jsonl)"
    [ -f "$sf" ] && read -r _ ssum _ susd _ su5 _ su7 scalls < "$sf"
    read -r sh5 sh7 < <(awk -v a="${su5:-0}" -v b="${su7:-0}" -v s5="${all5:-0}" -v s7="${all7:-0}" -v p5="${five_pct:-0}" -v p7="${week_pct:-0}" \
      'BEGIN { printf "%.2f %.2f\n", (s5 > 0 ? a / s5 * p5 : 0), (s7 > 0 ? b / s7 * p7 : 0) }')
    atot="$atot $susd $sh5 $sh7"
    idle=$((now - $(stat -f %m "$f")))
    smax=$(compact_at "claude-$smodel" "$stype")
    line="${stype:-agent} $smodel"
    [ "$seffort" != "-" ] && line="$line ($seffort)"
    [ "$sdesc" != "-" ] && line="$line · $sdesc"
    line="$line · $(fmt_dur $((now - $(stat -f %B "$f"))))"
    [ "$idle" -ge 60 ] && line="$line · $(hl "$(lvl 180 "$idle" 300 600)" "idle $(fmt_dur "$idle")")"
    line="$line · $(hl "$(lvl 180 "${scalls:-0}" 100 150)" "${scalls:-0} calls")"
    if [ -n "$smax" ]; then
      line="$line · $(hl "$(lvl 180 $((${sctx:-0} * 100 / smax)) 75 90)" "ctx $(fmt_tok "${sctx:-0}")/$(fmt_tok "$smax")")"
    else
      line="$line · ctx $(fmt_tok "${sctx:-0}")"
    fi
    line="$line · $(fmt_tok "${ssum:-0}") tok · ~\$$(printf '%.2f' "${susd:-0}")"
    [ -n "$all5" ] && line="$line · 5h ${sh5}% · 7d ${sh7}%"
    alines+=("$line")
  done < <(find "${transcript%.jsonl}/subagents" -name '*.jsonl' -mmin -60 2>/dev/null)
fi
if [ ${#alines[@]} -ge 2 ]; then
  read -r tusd t5 t7 < <(echo "$atot" | awk '{ for (i = 1; i <= NF; i += 3) { c += $i; a += $(i + 1); b += $(i + 2) } } END { printf "%.2f %.2f %.2f\n", c, a, b }')
  total="${#alines[@]} running · ~\$$tusd"
  [ -n "$all5" ] && total="$total · 5h ${t5}% · 7d ${t7}%"
  printf '\n\033[38;5;180;1m⚙ %s\033[0m' "$total"
fi
for line in "${alines[@]}"; do printf '\n\033[38;5;180m⚙ %s\033[0m' "$line"; done

# --- other sessions on the account ---
# The limits are shared, so the rest of the account shows here: sessions working
# (main transcript written in the last 5 min, or a running agent) and running
# agents (not marked finished, written in the last 30 min), in any project. Their
# share of each limit = the account's used % minus this session's.
own="${transcript%.jsonl}"
osess=$( { find -H ~/.claude/projects -mindepth 2 -maxdepth 2 -name '*.jsonl' -mmin -5 ! -path "$transcript" 2>/dev/null | sed 's/\.jsonl$//'
  find -H ~/.claude/projects -mindepth 4 -maxdepth 4 -path '*/subagents/*.jsonl' -mmin -30 ! -path "$own/*" 2>/dev/null \
    | while IFS= read -r g; do grep -q '"finished":true' "${g%.jsonl}.meta.json" 2>/dev/null || echo "A ${g%/subagents/*}"; done; } )
oagents=$(printf '%s\n' "$osess" | grep -c '^A ')
osess=$(printf '%s\n' "$osess" | sed 's/^A //' | grep -v '^$' | sort -u | wc -l | tr -d ' ')
if [ "$osess" -gt 0 ]; then
  o="others: $osess session$([ "$osess" -gt 1 ] && echo s) · $oagents agent$([ "$oagents" -ne 1 ] && echo s)"
  [ -n "$share5" ] && o="$o · 5h $(awk -v p="$five_pct" -v s="$share5" 'BEGIN { printf "%.1f", p - s }')% · 7d $(awk -v p="$week_pct" -v s="$share7" 'BEGIN { printf "%.1f", p - s }')%"
  printf '\n\033[38;5;246m◦ %s\033[0m' "$o"
fi

# --- recap line: session title (/rename wins over auto title) + last real prompt ---
# Prompts under 20 chars ("yes", "ok") and slash commands are skipped as noise.
# Claude Code re-appends these entries all session, so the last 2MB holds them;
# grepping a whole transcript (46MB seen) with BSD grep costs ~1s per refresh.
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  meta=$(tail -c 2000000 "$transcript" | LC_ALL=C grep -E '^\{"type":"(custom-title|ai-title|last-prompt)"')
  title=$(printf '%s\n' "$meta" | jq -rs '(map(.customTitle // empty) | last) // (map(.aiTitle // empty) | last) // empty')
  prompt=$(printf '%s\n' "$meta" | jq -rs 'map(.lastPrompt // empty | select(length >= 20 and (startswith("/") | not))) | last // empty | gsub("\\s+"; " ")')
  [ ${#prompt} -gt 90 ] && prompt="${prompt:0:89}…"
  recap="${title}${title:+${prompt:+ · }}${prompt}"
  [ -n "$recap" ] && printf '\n\033[38;5;250m▸ %s\033[0m' "$recap"
fi
