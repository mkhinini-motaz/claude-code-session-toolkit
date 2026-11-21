#!/usr/bin/env python3
"""Save subagent hand-back reports from a session transcript to files.

usage: save-reports.py <transcript.jsonl> <outdir> <agent-id>=<name> [<agent-id>=<name> ...]

The harness refuses a subagent's own report file, so each report arrives as reply text. This pulls the
longest hand-back of each named agent out of the transcript and writes <outdir>/report-<name>.md.
"""
import json
import pathlib
import re
import sys

if len(sys.argv) < 4:
    sys.exit(__doc__)
transcript, outdir, *pairs = sys.argv[1:]
names = dict(pair.split('=', 1) for pair in pairs)
best = {}


def walk(node):
    if isinstance(node, str):
        for match in re.finditer(r'<agent-message from="(\w+)">\n(.*?)</agent-message>', node, re.S):
            agent, text = match.groups()
            if agent in names and len(text) > len(best.get(agent, '')):
                best[agent] = text
    elif isinstance(node, dict):
        for value in node.values():
            walk(value)
    elif isinstance(node, list):
        for value in node:
            walk(value)


with open(transcript, errors='ignore') as lines:
    for line in lines:
        if 'agent-message' in line:
            try:
                walk(json.loads(line))
            except ValueError:
                pass

out = pathlib.Path(outdir)
out.mkdir(parents=True, exist_ok=True)
for agent, text in best.items():
    (out / f'report-{names[agent]}.md').write_text(text)
    print(f'saved report-{names[agent]}.md, {len(text)} chars')
for agent in names.keys() - best.keys():
    print(f'no hand-back found for {agent} ({names[agent]})')
