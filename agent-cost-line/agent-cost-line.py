#!/usr/bin/env python3
"""Fan-out cost line. UserPromptSubmit resets a per-session counter; PreToolUse(Agent) appends the
agent type and, at the 3rd, 5th, 10th, 15th and 20th agent of a prompt, shows the user a systemMessage.
Never blocks, never errors out. `--self-test` runs the logic in a temp dir."""
import json, os, sys, tempfile

# Median raw tokens per run, millions, per subagent type: measured on one machine over 30 days (20 Nov 2026).
# These are examples: replace them with the medians of your own agents' transcripts.
MEDIANS = {"worker": 1.6, "general-purpose": 1.1, "Explore": 0.4, "fork": 14.0}
OTHER = 2.5
STEPS = (3, 5, 10, 15, 20)


def handle(ev, tmp):
    sid = str(ev.get("session_id") or "x").replace("/", "_")
    path = os.path.join(tmp, f"agent-cost-{sid}.json")
    name = ev.get("hook_event_name")
    if name == "UserPromptSubmit":
        if os.path.exists(path):
            os.remove(path)
        return None
    if name != "PreToolUse" or ev.get("tool_name") != "Agent":
        return None
    try:
        runs = json.load(open(path))
    except Exception:
        runs = []
    runs.append((ev.get("tool_input") or {}).get("subagent_type") or "general-purpose")
    json.dump(runs, open(path, "w"))
    if len(runs) not in STEPS:
        return None
    total = sum(MEDIANS.get(r, OTHER) for r in runs)
    return {"systemMessage": f"{len(runs)} agents this prompt: about {total:.0f}M tokens at 30-day medians per type."}


def self_test():
    with tempfile.TemporaryDirectory() as d:
        base = {"session_id": "t"}
        agent = {**base, "hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {"subagent_type": "worker"}}
        assert handle({**base, "hook_event_name": "UserPromptSubmit"}, d) is None
        outs = [handle(agent, d) for _ in range(3)]
        assert outs[0] is None and outs[1] is None, outs
        assert outs[2] and "3 agents" in outs[2]["systemMessage"], outs
        handle({**base, "hook_event_name": "UserPromptSubmit"}, d)
        assert handle(agent, d) is None  # counter was reset
    print("agent-cost-line self-test: ok")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        try:
            out = handle(json.load(sys.stdin), os.environ.get("TMPDIR") or "/tmp")
            if out:
                print(json.dumps(out))
        except Exception:
            pass
        sys.exit(0)
