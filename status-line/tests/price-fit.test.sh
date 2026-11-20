#!/bin/bash
# statusline-price-fit in a scratch HOME: no sessions, too few sessions and proportional sessions are each refused with a clear message.
fit="$(cd "$(dirname "$0")/.." && pwd)/statusline-price-fit"
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
export HOME="$d"; P="$d/proj"; mkdir -p "$d/.claude/statusline-usage" "$P"
run() { python3 "$fit" --project "$P" 2>&1; }
out=$(run); [ $? = 1 ] && grep -q "no sessions found" <<<"$out" || { echo "FAIL: 0 sessions: $out"; exit 1; }
mk() { # id cost model output_tokens
  echo "$2 x" > "$d/.claude/statusline-usage/cost-$1"
  echo "{\"type\":\"assistant\",\"message\":{\"id\":\"m$1\",\"model\":\"$3\",\"usage\":{\"output_tokens\":$4}}}" > "$P/$1.jsonl"
}
mk s1 1.0 claude-opus-4 1000000
echo '{"type":"assistant","message":{"id":"x","model":"claude-sonnet-4","usage":{"output_tokens":5}}}' >> "$P/s1.jsonl"
out=$(run); grep -q "need at least 2" <<<"$out" && ! grep -q "0 session" <<<"$out" || { echo "FAIL: 2 sessions, 2 families: $out"; exit 1; }
# two families that always appear together in the same proportion cannot be told apart
for i in 3 4 5; do
  echo "$i x" > "$d/.claude/statusline-usage/cost-p$i"
  echo "{\"type\":\"assistant\",\"message\":{\"id\":\"a$i\",\"model\":\"claude-opus-4\",\"usage\":{\"output_tokens\":$((i*1000000))}}}
{\"type\":\"assistant\",\"message\":{\"id\":\"b$i\",\"model\":\"claude-sonnet-4\",\"usage\":{\"output_tokens\":$((i*2000000))}}}" > "$P/p$i.jsonl"
done
rm "$d/.claude/statusline-usage/cost-s1" "$P/s1.jsonl"
out=$(run); grep -q "cannot be told apart" <<<"$out" || { echo "FAIL: proportional sessions: $out"; exit 1; }
echo ok
