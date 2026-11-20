#!/usr/bin/env python3
"""SessionStart: show the rows of ~/.claude/reminders.tsv whose date has come, in sessions under the row's folder.
Test: echo '{"cwd":"'$HOME'/work/app"}' | REMINDERS_TODAY=2026-12-01 ~/.claude/hooks/reminders.py"""
import datetime, json, os, sys

f = os.path.expanduser("~/.claude/reminders.tsv")
try: cwd = json.load(sys.stdin).get("cwd") or os.getcwd()
except Exception: cwd = os.getcwd()
today = os.environ.get("REMINDERS_TODAY") or datetime.date.today().isoformat()
due = []
for line in (open(f, encoding="utf-8") if os.path.exists(f) else []):
    if line.startswith("#") or not line.strip(): continue
    d, folder, text = (line.rstrip("\n").split("\t") + ["", ""])[:3]
    root = os.path.realpath(os.path.expanduser(folder)) if folder else ""
    here = os.path.realpath(cwd)
    if d <= today and (not root or here == root or here.startswith(root + os.sep)): due.append(f"{d}: {text}")
if due:
    msg = "Due: " + " | ".join(due)
    ctx = msg + " Tell the user in one line in your first reply. Delete the row from ~/.claude/reminders.tsv once it is done."
    print(json.dumps({"systemMessage": msg, "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}))
