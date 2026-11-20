#!/usr/bin/env python3
"""harness-audit collector: a local, read-only scan of Claude Code transcripts and setup.

  collect.py [--project NAME|PATH] [--notes FILE] COMMAND ...
                                    --project: only that project folder (name part or path; env HARNESS_AUDIT_PROJECT); default all
                                    --notes: optional notes file (## heading, then task:/corrections:/friction:/asked twice: lines)
  collect.py scan [days]            scan the last N days (default 30); write data.json and
                                    summary.txt into <project root>/harness-audit-<date>/ and print the summary
  collect.py show KEY [KEY2 ...]    print one part of the newest data.json (dot path, e.g. tokens.by_week)
  collect.py excerpt FILE LINE [N]  print up to N (max 30) compact, redacted records around a line
  collect.py prompts FILE [MAX]     print up to MAX (max 60) prompts the user typed in one session, redacted
  collect.py checks [since] [name]  re-run the report's counts (leftopen nudges fanouts askme preamble blocked context repeats
                                    recipes) for turns after `since` (UTC prefix, e.g. 2026-11-16T12:55; default 30 days ago);
                                    askme reads prompts.tsv from the newest harness-audit-* folder. Prints; writes nothing
  collect.py prompts-all [days]     every prompt typed in the last N days (default 30), all main sessions, redacted,
                                    one per line (time, project, session, line, first 600 chars) in
                                    <project root>/harness-audit-<date>/prompts.tsv; prints the path and counts

Standard library only. It never exits non-zero: a failure prints the error and exits 0,
so a run injected into the skill cannot abort it. Nothing leaves this machine.
"""
import collections, statistics
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

HOME = Path.home()
ROOT = HOME / ".claude"
PROJECTS = ROOT / "projects"
PROJECT = None  # --project VALUE: only project folders whose name contains it (a path is turned into the folder name). None = all
NOTES = None  # --notes FILE: optional end-of-session notes file, see session_notes()


def in_project(path):
    """True when PATH (under PROJECTS) belongs to the selected project."""
    if not PROJECT:
        return True
    rel = Path(path).relative_to(PROJECTS).parts
    return bool(rel) and PROJECT in rel[0]


def take_flags(args):
    """Remove --project and --notes (and their values) from ARGS, set the globals, return the rest."""
    global PROJECT, NOTES
    rest, i = [], 0
    while i < len(args):
        if args[i] in ("--project", "--notes") and i + 1 < len(args):
            val = args[i + 1]
            if args[i] == "--project":
                PROJECT = re.sub(r"[^A-Za-z0-9]", "-", str(Path(val).expanduser().resolve())) if "/" in val or val.startswith("~") else val
            else:
                NOTES = Path(val).expanduser()
            i += 2
        else:
            rest.append(args[i])
            i += 1
    PROJECT = PROJECT or os.environ.get("HARNESS_AUDIT_PROJECT") or None
    return rest


def project_root():
    """The nearest folder at or above the shell's that holds `.claude/` (never ~), so a scan from a subfolder audits the project."""
    cwd = Path.cwd()
    return next((p for p in (cwd, *cwd.parents) if p != HOME and (p / ".claude").is_dir()), cwd)
# Record types that carry no audit signal but most of the bytes. Skipped before parsing.
SKIP = ('"type":"api-request', '"type":"file-history', '"type":"attachment"', '"type":"queue-operation"')
CLASSES = ("input", "cache_write", "cache_read", "output")
# Ordering weight only, never money: rough relative price of each token class.
WEIGHT = {"input": 1, "cache_write": 1.25, "cache_read": 0.1, "output": 5}
EDITS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READS = {"Read", "Grep", "Glob"}
# English only. A flagged message is a candidate, not proof.
CORRECTION = re.compile(
    r"^(no[\s,.!]|nope|wrong|wait|stop|don'?t |do not |that'?s not|not what|you didn'?t|you did not|"
    r"i said|i told you|i asked|again[\s,.]|undo|revert|why did you|still (not|wrong|broken|fail)|incorrect|actually[\s,])",
    re.I,
)
CONTINUE = {"continue", "keep going", "go on", "proceed", "go ahead", "carry on", "next"}
SECRET = re.compile(
    r"sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|AGE-SECRET-KEY-1[0-9A-Z]{20,}|AIza[0-9A-Za-z_-]{35}"
)
BANDS = ("<100k", "100-200k", "200-300k", "300-400k", ">400k")
LIMIT_MSG = re.compile(r"(?:hit|reached) your ([^.\n]{0,60}?limit)", re.I)
TMP_PATH = re.compile(r"(?:/private)?/(?:var/folders|tmp)/[^\s'\"]*")


def band(ctx):
    return min(ctx // 100_000, 4) if ctx < 400_000 else 4


def result_text(block):
    c = block.get("content")
    if isinstance(c, list):
        c = " ".join(b.get("text") or "" for b in c if isinstance(b, dict))
    return c if isinstance(c, str) else json.dumps(c)


def block_class(text):
    """Name of the harness refusal a tool result carries, plus a sub-group, or (None, None)."""
    if "Blocked: sleep" in text:
        return "foreground sleep blocked", ""
    if "hook error:" in text:
        return "PreToolUse hook denial", text.split("hook error:", 1)[1].strip()[:50]
    if "built-in Claude Code safety check" in text:
        return "removal safety check", ""
    if "auto mode classifier. Reason: [" in text:
        return "auto-mode classifier", text.split("auto mode classifier. Reason: [", 1)[1].split("]", 1)[0][:80]
    if "doesn't want to proceed" in text:
        return "user rejected", ""
    return None, None
MAX_POINTERS = 60  # per kind


def parse_ts(value):
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def typed_text(record):
    """Text a person typed, or '' for tool results, meta records and command wrappers."""
    if record.get("isMeta") or record.get("isCompactSummary") or record.get("isSidechain"):
        return ""
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return content.strip()
    parts = []
    for block in content or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_result":
            return ""
        if block.get("type") == "text":
            parts.append(block.get("text") or "")
    return "\n".join(parts).strip()


def words(text):
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if len(w) > 3}


def est_tokens(nbytes):
    return round(nbytes / 4)  # estimate: about four bytes per token


def scan(days):
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=days)
    files = [p for p in PROJECTS.rglob("*.jsonl") if p.stat().st_mtime >= cutoff.timestamp()] if PROJECTS.exists() else []
    files = [p for p in files if in_project(p)]
    cov = {"days": days, "files_main": 0, "files_subagent": 0, "bytes": 0, "parse_failures": 0,
           "requests_without_usage": 0, "first": None, "last": None, "versions": set(), "projects": set()}
    by_week = collections.defaultdict(lambda: collections.Counter())
    by_skill, by_mcp = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    tools, tool_errors, skills_called, agents, mcp_calls = (collections.Counter() for _ in range(5))
    slash, bash_cmds = collections.Counter(), collections.Counter()
    skill_sessions, bash_sessions = collections.defaultdict(set), collections.defaultdict(set)
    sessions, pointers, flag_counts = {}, collections.defaultdict(list), collections.Counter()
    by_agent, agent_runs, denials = collections.defaultdict(collections.Counter), collections.Counter(), collections.Counter()
    flag_sessions = collections.defaultdict(set)
    cache_miss = {"requests": 0, "tokens_rewritten": 0}
    blocked = collections.defaultdict(lambda: {"count": 0, "main": 0, "subagent": 0, "sessions": set(), "groups": collections.Counter()})
    hook_texts, limit_dates, bands = collections.Counter(), collections.defaultdict(collections.Counter), {}
    runs = []

    def flag(kind, path, line, sid):
        flag_counts[kind] += 1
        flag_sessions[kind].add(sid)
        if len(pointers[kind]) < MAX_POINTERS:
            pointers[kind].append({"file": str(path.relative_to(PROJECTS)), "line": line})

    for path in files:
        sub = "subagents" in path.parts
        cov["files_subagent" if sub else "files_main"] += 1
        cov["bytes"] += path.stat().st_size
        sid = path.parent.parent.name if sub else path.stem
        s = sessions.setdefault(sid, {"file": None, "title": None, "project": None, "requests": 0, "prompts": 0,
                                      "tokens": collections.Counter(), "subagent_tokens": collections.Counter(),
                                      "edits": collections.Counter(), "reads": 0, "writes": 0, "max_error_streak": 0,
                                      "models": set(), "first": None, "last": None})
        if not sub:
            s["file"] = str(path.relative_to(PROJECTS))
        seen, tool_names, recent, streak, first_request = set(), {}, [], 0, True
        agent_type, run = None, None
        if sub:
            try:
                meta = json.loads(path.with_suffix(".meta.json").read_text())
            except Exception:
                meta = {}
            agent_type = meta.get("agentType") or "unknown"
            run = {"file": str(path.relative_to(PROJECTS)), "agent_type": agent_type, "spawn_model": meta.get("model") or "inherit",
                   "requests": 0, "tokens": 0, "max_context": 0, "models": collections.Counter(), "first": None}
            runs.append(run)
            agent_runs[agent_type] += 1
        with path.open(errors="replace") as handle:
            for n, line in enumerate(handle, 1):
                if any(marker in line[:200] for marker in SKIP):
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    cov["parse_failures"] += 1
                    continue
                kind = rec.get("type")
                if kind == "ai-title" and not sub:
                    s["title"] = rec.get("aiTitle")
                    continue
                if kind not in ("assistant", "user", "system"):
                    continue
                ts = parse_ts(rec.get("timestamp"))
                if ts and ts < cutoff:
                    continue
                if ts:
                    stamp = ts.isoformat()
                    cov["first"] = min(cov["first"] or stamp, stamp)
                    cov["last"] = max(cov["last"] or stamp, stamp)
                    s["first"] = min(s["first"] or stamp, stamp)
                    s["last"] = max(s["last"] or stamp, stamp)
                if rec.get("version"):
                    cov["versions"].add(rec["version"])
                if rec.get("cwd") and not s["project"]:
                    s["project"] = rec["cwd"]
                    cov["projects"].add(rec["cwd"])
                msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}

                if kind == "system":
                    if rec.get("hookErrors"):
                        flag("hook_error", path, n, sid)
                        errs = rec["hookErrors"]
                        for e in errs if isinstance(errs, list) else [errs]:
                            hook_texts[re.sub(r"\b[0-9a-f]{7,40}\b", "<sha>", TMP_PATH.sub("<tmp>", " ".join(str(e).split())))[:110]] += 1
                    if rec.get("subtype") == "compact_boundary":
                        flag_counts["compaction"] += 1
                        flag_sessions["compaction"].add(sid)
                    continue

                if kind == "assistant":
                    key = msg.get("id") or rec.get("requestId") or rec.get("uuid")
                    usage = msg.get("usage")
                    if key not in seen:
                        seen.add(key)
                        if not isinstance(usage, dict):
                            cov["requests_without_usage"] += 1
                        else:
                            got = {"input": usage.get("input_tokens") or 0,
                                   "cache_write": usage.get("cache_creation_input_tokens") or 0,
                                   "cache_read": usage.get("cache_read_input_tokens") or 0,
                                   "output": usage.get("output_tokens") or 0}
                            model = msg.get("model") or "unknown"
                            week = (ts - dt.timedelta(days=ts.weekday())).date().isoformat() if ts else "unknown"
                            thread = "subagent" if sub else "main"
                            for cls, value in got.items():
                                by_week[f"{week}|{model}|{thread}"][cls] += value
                                (s["subagent_tokens"] if sub else s["tokens"])[cls] += value
                                if sub:
                                    by_agent[agent_type][cls] += value
                                if rec.get("attributionSkill"):
                                    by_skill[rec["attributionSkill"]][cls] += value
                                if rec.get("attributionMcpServer"):
                                    by_mcp[rec["attributionMcpServer"]][cls] += value
                            ctx = got["input"] + got["cache_write"] + got["cache_read"]
                            b = bands.setdefault(f"{thread}|{model}", {"requests": 0, "bands": [[0, 0] for _ in BANDS]})
                            b["requests"] += 1
                            b["bands"][band(ctx)][0] += 1
                            b["bands"][band(ctx)][1] += ctx
                            if run:
                                run["requests"] += 1
                                run["tokens"] += sum(got.values())
                                run["max_context"] = max(run["max_context"], ctx)
                                run["models"][model] += 1
                                run["first"] = min(run["first"] or stamp, stamp) if ts else run["first"]
                            s["requests"] += 1
                            s["models"].add(model)
                            if not sub and not first_request and got["cache_read"] == 0 and got["input"] + got["cache_write"] > 20000:
                                cache_miss["requests"] += 1
                                cache_miss["tokens_rewritten"] += got["input"] + got["cache_write"]
                            first_request = False
                    for block in msg.get("content") or []:
                        if isinstance(block, dict) and block.get("type") == "text" and ts:
                            m = LIMIT_MSG.search(block.get("text") or "")
                            if m:
                                phrase = m.group(1).lower()
                                kind_ = "weekly" if "week" in phrase else "5-hour/session" if re.search(r"session|5|five|hour", phrase) else "model-specific"
                                limit_dates[ts.date().isoformat()][kind_] += 1
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        name, args = block.get("name") or "?", block.get("input") or {}
                        tool_names[block.get("id")] = name
                        tools[name] += 1
                        if name.startswith("mcp__"):
                            mcp_calls[name.split("__")[1]] += 1
                        elif name == "Skill":
                            skill = str(args.get("skill"))
                            skills_called[skill] += 1
                            skill_sessions[skill].add(sid)
                        elif name in ("Agent", "Task"):
                            agents[f"{args.get('subagent_type') or 'default'}|{args.get('model') or 'inherit'}"] += 1
                        elif name == "Bash":
                            head = " ".join(str(args.get("command") or "").split()[:2])[:60]
                            bash_cmds[head] += 1
                            bash_sessions[head].add(sid)
                        if name in EDITS:
                            s["writes"] += 1
                            s["edits"][str(args.get("file_path") or args.get("notebook_path"))] += 1
                        elif name in READS:
                            s["reads"] += 1
                    continue

                # kind == "user"
                content = msg.get("content")
                for block in content if isinstance(content, list) else []:
                    if not isinstance(block, dict) or block.get("type") != "tool_result":
                        continue
                    full = result_text(block)
                    cls, group = block_class(full)
                    if cls:
                        bl = blocked[cls]
                        bl["count"] += 1
                        bl["subagent" if sub else "main"] += 1
                        bl["sessions"].add(sid)
                        if group:
                            bl["groups"][group] += 1
                    body = full[:400].lower()
                    if rec.get("toolDenialKind") or "doesn't want to proceed" in body or "tool use was rejected" in body:
                        flag("tool_rejected", path, n, sid)
                        denials[str(rec.get("toolDenialKind") or "rejected by user")] += 1
                        streak = 0
                    elif block.get("is_error"):
                        tool_errors[tool_names.get(block.get("tool_use_id"), "?")] += 1
                        streak += 1
                        if streak == 3:
                            flag("error_streak", path, n, sid)
                        s["max_error_streak"] = max(s["max_error_streak"], streak)
                    else:
                        streak = 0
                if sub:
                    continue
                raw = content if isinstance(content, str) else " ".join(
                    b.get("text") or "" for b in content or [] if isinstance(b, dict) and b.get("type") == "text")
                if "[Request interrupted by user" in raw:
                    flag("interrupt", path, n, sid)
                    continue
                for command in re.findall(r"<command-name>/?([\w:.-]+)</command-name>", raw):
                    slash[command] += 1
                text = typed_text(rec)
                if not text or text.startswith("<"):
                    continue
                s["prompts"] += 1
                low = text.lower()
                if CORRECTION.match(low):
                    flag("correction", path, n, sid)
                if low.strip(" .!") in CONTINUE or (low.startswith("continue") and len(low) < 25):
                    flag("continue_prompt", path, n, sid)
                bag = words(text)
                if len(bag) >= 6 and any(len(bag & old) / len(bag | old) > 0.6 for old in recent):
                    flag("repeated_instruction", path, n, sid)
                recent = (recent + [bag])[-5:] if len(bag) >= 6 else recent

    rows = []
    for sid, s in sessions.items():
        if not s["requests"]:
            continue
        thrash = {f: c for f, c in s["edits"].items() if c >= 5}
        if thrash:
            flag_counts["edit_thrash"] += 1
            flag_sessions["edit_thrash"].add(sid)
        if s["reads"] >= 20 and s["reads"] > 10 * max(s["writes"], 1):
            flag_counts["read_heavy"] += 1
            flag_sessions["read_heavy"].add(sid)
        total = s["tokens"] + s["subagent_tokens"]
        rows.append({"session": sid, "file": s["file"], "title": s["title"], "project": s["project"],
                     "first": s["first"], "last": s["last"], "requests": s["requests"], "prompts": s["prompts"],
                     "models": sorted(s["models"]), "tokens_main": dict(s["tokens"]),
                     "tokens_subagent": dict(s["subagent_tokens"]),
                     "rank_weight": round(sum(total[c] * WEIGHT[c] for c in CLASSES)),
                     "max_error_streak": s["max_error_streak"], "edit_thrash": thrash})
    rows.sort(key=lambda r: -r["rank_weight"])

    setup = scan_setup(skills_called, slash, agents)
    out = project_root() / f"harness-audit-{dt.date.today().isoformat()}"
    out.mkdir(exist_ok=True)
    insights = ROOT / "usage-data" / "report.html"
    if insights.exists():
        shutil.copy2(insights, out / "insights-report.html")
        text = re.sub(r"(?s)<(script|style).*?</\1>", " ", insights.read_text(errors="replace"))
        (out / "insights.txt").write_text(re.sub(r"\s+\n", "\n", html.unescape(re.sub(r"<[^>]+>", "\n", text))))
        setup["insights_report"] = {"age_days": round((now.timestamp() - insights.stat().st_mtime) / 86400, 1),
                                    "text": str(out / "insights.txt")}
    cov["versions"], cov["projects"] = sorted(cov["versions"])[-3:], sorted(cov["projects"])
    cov["sessions"] = len(rows)
    weeks = {}
    for key, counter in sorted(by_week.items()):
        weeks[key] = dict(counter)
    data = {
        "note": "Substitute figures computed from local transcripts. rank_weight orders sessions; it is not money. "
                "Flags are candidates, not proof. Token estimates for files use four bytes per token.",
        "coverage": cov,
        "tokens": {"by_week_model_thread": weeks, "by_skill": {k: dict(v) for k, v in by_skill.items()},
                   "by_mcp_server": {k: dict(v) for k, v in by_mcp.items()},
                   "by_subagent_type": {k: {"runs": agent_runs[k], **dict(v)} for k, v in by_agent.items()},
                   "cache_miss_heuristic": cache_miss,
                   "context_bands": {k: {"requests": v["requests"], "bands": {BANDS[i]: {"requests": r, "context_tokens": t}
                                                                           for i, (r, t) in enumerate(v["bands"])}}
                                     for k, v in sorted(bands.items())},
                   "subagent_runs": subagent_runs(runs),
                   "top_sessions": rows[:15]},
        "tools": {"calls": dict(tools.most_common()), "errors": dict(tool_errors.most_common()),
                  "mcp_server_calls": dict(mcp_calls.most_common()), "agent_spawns": dict(agents.most_common()),
                  "bash_heads": {k: {"calls": v, "sessions": len(bash_sessions[k])} for k, v in bash_cmds.most_common(40)}},
        "skills": {"tool_calls": {k: {"calls": v, "sessions": len(skill_sessions[k])} for k, v in skills_called.most_common()},
                   "slash_commands": dict(slash.most_common())},
        "friction": {"counts": dict(flag_counts), "sessions": {k: len(v) for k, v in flag_sessions.items()},
                     "denial_kinds": dict(denials), "pointers": dict(pointers),
                     "blocked": {k: {"count": v["count"], "sessions": len(v["sessions"]), "main": v["main"], "subagent": v["subagent"],
                                     "groups": dict(v["groups"].most_common(10))} for k, v in sorted(blocked.items())},
                     "hook_error_text": dict(hook_texts.most_common(15)),
                     "limit_messages": {d: dict(c) for d, c in sorted(limit_dates.items())}},
        "sessions": [{k: r[k] for k in ("session", "file", "title", "first", "requests", "prompts", "rank_weight")} for r in rows],
        "setup": setup,
        "session_notes": session_notes(NOTES),
    }
    (out / "data.json").write_text(json.dumps(data, indent=1, default=str))
    summary = summarise(data, out)
    (out / "summary.txt").write_text(summary)
    print(summary)


def subagent_runs(runs):
    """Per-run rows and per-agent-type medians; runs with no usable request are dropped."""
    rows = [{"file": r["file"], "agent_type": r["agent_type"], "spawn_model": r["spawn_model"], "requests": r["requests"],
             "tokens": r["tokens"], "max_context": r["max_context"], "first": (r["first"] or "")[:10],
             "actual_model": r["models"].most_common(1)[0][0]} for r in runs if r["requests"]]
    types = {}
    for t in {r["agent_type"] for r in rows}:
        mine = [r for r in rows if r["agent_type"] == t]
        total = sum(r["tokens"] for r in mine)
        big = [r for r in mine if r["requests"] > 100]
        types[t] = {"runs": len(mine), "median_tokens": statistics.median(r["tokens"] for r in mine),
                    "median_requests": statistics.median(r["requests"] for r in mine), "runs_over_100_requests": len(big),
                    "over_100_token_share": round(sum(r["tokens"] for r in big) / total, 3) if total else 0}
    return {"by_type": dict(sorted(types.items(), key=lambda kv: -kv[1]["runs"])), "runs": rows}


def frontmatter(path):
    try:
        text = path.read_text(errors="replace")
    except Exception:
        return {}, 0
    match = re.match(r"(?s)^---\n(.*?)\n---\n?(.*)$", text)
    if not match:
        return {}, len(text.encode())
    fields, key = {}, None
    for line in match.group(1).splitlines():
        found = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if found:
            key = found.group(1)
            fields[key] = found.group(2).strip().strip("|>").strip()
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields, len(match.group(2).encode())


def scan_setup(skills_called, slash, agents):
    cwd = project_root()
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(cwd))
    loaded = [ROOT / "CLAUDE.md", cwd / "CLAUDE.md", cwd / ".claude" / "CLAUDE.md", cwd / "CLAUDE.local.md",
              PROJECTS / slug / "memory" / "MEMORY.md"] + [p / "CLAUDE.md" for p in cwd.parents]
    rules = list((cwd / ".claude" / "rules").rglob("*.md")) + list((ROOT / "rules").rglob("*.md"))
    files = []
    for path in dict.fromkeys(loaded + rules):
        if path.is_file():
            size = path.stat().st_size
            files.append({"path": str(path), "bytes": size, "est_tokens": est_tokens(size),
                          "lines": sum(1 for _ in path.open(errors="replace")), "rule_file": path in rules})
    skills = []
    for source, base in (("user", ROOT / "skills"), ("project", cwd / ".claude" / "skills")):
        for path in base.glob("*/SKILL.md") if base.exists() else []:
            fields, body = frontmatter(path)
            name = fields.get("name") or path.parent.name
            calls = sum(v for k, v in skills_called.items() if k.split(":")[-1] == name)
            typed = sum(v for k, v in slash.items() if k.split(":")[-1] == name)
            skills.append({"name": name, "source": source, "description_chars": len(fields.get("description", "")),
                           "body_bytes": body, "model_can_invoke": fields.get("disable-model-invocation", "").lower() not in ("true", "yes", "on", "1"),
                           "calls_by_claude": calls, "typed_by_user": typed})
    skills.sort(key=lambda r: (r["calls_by_claude"] + r["typed_by_user"], -r["description_chars"]))
    defined = []
    for base in (ROOT / "agents", cwd / ".claude" / "agents"):
        for path in base.rglob("*.md") if base.exists() else []:
            fields, body = frontmatter(path)
            name = fields.get("name") or path.stem
            defined.append({"name": name, "description_chars": len(fields.get("description", "")), "body_bytes": body,
                            "spawns": sum(v for k, v in agents.items() if k.split("|")[0] == name)})
    settings = {}
    for path in (ROOT / "settings.json", cwd / ".claude" / "settings.json", cwd / ".claude" / "settings.local.json"):
        try:
            conf = json.loads(path.read_text())
        except Exception:
            continue
        hooks = {event: sum(len(group.get("hooks") or []) for group in groups if isinstance(group, dict))
                 for event, groups in (conf.get("hooks") or {}).items() if isinstance(groups, list)}
        settings[str(path)] = {"cleanupPeriodDays": conf.get("cleanupPeriodDays", "unset (default 30)"), "hooks_per_event": hooks,
                               "plugins_enabled": sum(1 for v in (conf.get("enabledPlugins") or {}).values() if v),
                               "allow_rules": len((conf.get("permissions") or {}).get("allow") or []),
                               "model": conf.get("model")}
    servers = set()
    for path in (cwd / ".mcp.json", HOME / ".claude.json"):
        try:
            servers |= set((json.loads(path.read_text()).get("mcpServers") or {}).keys())
        except Exception:
            pass
    plugins = ROOT / "plugins"
    return {"project_folder": str(cwd), "instruction_files": files, "skills": skills, "agents": defined,
            "plugin_skill_files_on_disk": sum(1 for _ in plugins.glob("**/skills/*/SKILL.md")) if plugins.exists() else 0,
            "settings": settings, "mcp_servers_configured": sorted(servers), "insights_report": None}


def summarise(d, out):
    cov, tok, fr, setup = d["coverage"], d["tokens"], d["friction"], d["setup"]
    lines = [f"harness-audit scan: {out}/data.json (read parts with: collect.py show KEY)",
             f"window {cov['days']} days | sessions {cov['sessions']} | files {cov['files_main']} main + {cov['files_subagent']} subagent | "
             f"{cov['bytes'] // 1_000_000} MB | {cov['first']} to {cov['last']}",
             f"parse failures {cov['parse_failures']} | requests without usage {cov['requests_without_usage']} | versions {cov['versions']}",
             f"insights report: {setup['insights_report'] or 'none on disk'}", "", "TOKENS by thread and class (all weeks; substitute for /usage)"]
    totals = collections.defaultdict(collections.Counter)
    for key, counter in tok["by_week_model_thread"].items():
        _, model, thread = key.split("|")
        totals[f"{thread} {model}"].update(counter)
    for key, counter in sorted(totals.items(), key=lambda kv: -sum(kv[1][c] * WEIGHT[c] for c in CLASSES)):
        if sum(counter.values()):
            lines.append(f"  {key}: " + ", ".join(f"{c} {counter[c]:,}" for c in CLASSES))
    lines.append(f"  cache-miss heuristic: {tok['cache_miss_heuristic']}")
    weight = lambda c: sum(c.get(k, 0) * WEIGHT[k] for k in CLASSES)
    for label, part in (("subagent types", tok["by_subagent_type"]), ("skills, attributed", tok["by_skill"]),
                        ("MCP servers, attributed", tok["by_mcp_server"])):
        top = sorted(part.items(), key=lambda kv: -weight(kv[1]))[:6]
        lines.append(f"  {label} (rank_weight): " + (", ".join(
            f"{k} {round(weight(v)):,}" + (f" in {v['runs']} runs" if "runs" in v else "") for k, v in top) or "none"))
    lines += ["", "TOP SESSIONS by rank_weight (not money)"]
    for r in tok["top_sessions"][:8]:
        lines.append(f"  {r['rank_weight']:>12,}  {r['requests']:>4} req  {(r['first'] or '')[:10]}  {(r['title'] or r['session'])[:60]}")
    lines += ["", "FRICTION candidates: count (sessions)"]
    lines.append("  " + ", ".join(f"{k} {v} ({fr['sessions'].get(k, 0)})" for k, v in sorted(fr["counts"].items(), key=lambda kv: -kv[1])) or "  none")
    lines.append("  denial kinds: " + (", ".join(f"{k} {v}" for k, v in fr["denial_kinds"].items()) or "none"))
    lines += ["", "BLOCKED (tool results the harness refused): count, sessions, main/subagent"]
    for k, v in sorted(fr["blocked"].items(), key=lambda kv: -kv[1]["count"]):
        top = ", ".join(f"{g!r} {c}" for g, c in list(v["groups"].items())[:3])
        lines.append(f"  {k}: {v['count']} ({v['sessions']} sessions) main {v['main']} / subagent {v['subagent']}" + (f" | {top}" if top else ""))
    if not fr["blocked"]:
        lines.append("  none")
    lines += ["", "HOOK ERROR TEXT (top 15)"] + [f"  {c:>4}  {t}" for t, c in fr["hook_error_text"].items()]
    lines += ["", "CONTEXT BANDS (requests per band, % of that row's context tokens; rows under 200 requests skipped)",
              "  row: " + " | ".join(BANDS)]
    for k, v in tok["context_bands"].items():
        if v["requests"] < 200:
            continue
        whole = sum(b["context_tokens"] for b in v["bands"].values()) or 1
        lines.append(f"  {k}: {v['requests']:,} req: " + " | ".join(
            f"{b['requests']} ({round(100 * b['context_tokens'] / whole)}%)" for b in v["bands"].values()))
    lim = fr["limit_messages"]
    lines += ["", "LIMITS (assistant messages saying a usage limit was hit)"]
    lines.append("  " + ("; ".join(f"{day} " + "/".join(f"{k} {n}" for k, n in c.items()) for day, c in lim.items()) or "none"))
    sr = tok["subagent_runs"]
    lines += ["", "SUBAGENT RUNS (type: runs, median tokens, median requests, runs over 100 requests = share of type tokens)"]
    for t, v in list(sr["by_type"].items())[:8]:
        lines.append(f"  {t}: {v['runs']} runs, {v['median_tokens']:,.0f} tok, {v['median_requests']:g} req, "
                     f"{v['runs_over_100_requests']} over 100 = {round(100 * v['over_100_token_share'])}%")
    lines.append("  spawn model != actual model: " + str(sum(1 for r in sr["runs"] if r["spawn_model"] != "inherit" and r["spawn_model"].lower() not in r["actual_model"].lower())) + " runs")
    tools = d["tools"]
    lines += ["", "TOOLS: " + ", ".join(f"{k} {v}" for k, v in list(tools["calls"].items())[:12]),
              "tool errors: " + (", ".join(f"{k} {v}" for k, v in list(tools["errors"].items())[:8]) or "none"),
              "agent spawns (type|model): " + (", ".join(f"{k} {v}" for k, v in list(tools["agent_spawns"].items())[:8]) or "none"),
              "MCP calls by server: " + (", ".join(f"{k} {v}" for k, v in tools["mcp_server_calls"].items()) or "none")]
    unused = [s for s in setup["skills"] if not s["calls_by_claude"] and not s["typed_by_user"]]
    calls = d["skills"]["tool_calls"]
    lines += ["", "SKILL CALLS by Claude (substitute for /skill-doctor): "
              + (", ".join(f"{k} {v['calls']}" for k, v in list(calls.items())[:12]) or "none"),
              "slash commands typed: " + (", ".join(f"{k} {v}" for k, v in list(d["skills"]["slash_commands"].items())[:12]) or "none"),
              f"user and project skills on disk {len(setup['skills'])}, never used in window {len(unused)} "
              f"({sum(s['description_chars'] for s in unused):,} description chars); "
              f"plugin skill files on disk {setup['plugin_skill_files_on_disk']} (disabled plugins included)",
              "", "INSTRUCTION FILES (estimated tokens; substitute for /context)"]
    for f in sorted(setup["instruction_files"], key=lambda f: -f["bytes"])[:12]:
        lines.append(f"  {f['est_tokens']:>7,}  {f['lines']:>5} lines  {'rule ' if f['rule_file'] else ''}{f['path']}")
    lines += ["", f"agents defined {len(setup['agents'])} | MCP servers configured {len(setup['mcp_servers_configured'])} | "
                  f"settings: " + "; ".join(f"{Path(p).name} retention={s['cleanupPeriodDays']} hooks={sum(s['hooks_per_event'].values())}"
                                            for p, s in setup["settings"].items())]
    return "\n".join(lines)


def show(keys):
    newest = sorted(project_root().glob("harness-audit-*/data.json"))
    if not newest:
        print("no data.json here; run: collect.py scan")
        return
    data = json.loads(newest[-1].read_text())
    for key in keys:
        node = data
        for part in key.split("."):
            node = node.get(part, f"no key {part}") if isinstance(node, dict) else f"no key {part}"
        text = json.dumps(node, indent=1, default=str).splitlines()
        print(f"## {key}\n" + "\n".join(text[:250]) + (f"\n... {len(text) - 250} more lines" if len(text) > 250 else ""))


def excerpt(file, line, count=30):
    path = (PROJECTS / file).resolve()
    if PROJECTS.resolve() not in path.parents:
        print("excerpt reads transcripts under ~/.claude/projects only")
        return
    count, start, shown = min(int(count), 30), max(1, int(line) - 8), 0
    clean = lambda value, size: SECRET.sub("[redacted]", " ".join(str(value).split()))[:size]
    with path.open(errors="replace") as handle:
        for n, raw in enumerate(handle, 1):
            if n < start or any(marker in raw[:200] for marker in SKIP):
                continue
            if shown >= count:
                break
            try:
                rec = json.loads(raw)
            except Exception:
                continue
            if rec.get("type") not in ("assistant", "user"):
                continue
            content = (rec.get("message") or {}).get("content")
            blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content or []
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                kind = block.get("type")
                mark = ">>" if n == int(line) else "  "
                if kind == "text" and (block.get("text") or "").strip():
                    print(f"{mark}L{n} {rec['type']}: {clean(block['text'], 400)}")
                elif kind == "tool_use":
                    print(f"{mark}L{n} call {block.get('name')}: {clean(json.dumps(block.get('input')), 180)}")
                elif kind == "tool_result":
                    print(f"{mark}L{n} result {'ERROR' if block.get('is_error') else 'ok'}: {clean(json.dumps(block.get('content')), 200)}")
                else:
                    continue
                shown += 1


def prompts(file, limit=60):
    path = (PROJECTS / file).resolve()
    if PROJECTS.resolve() not in path.parents:
        print("prompts reads transcripts under ~/.claude/projects only")
        return
    shown = 0
    with path.open(errors="replace") as handle:
        for n, raw in enumerate(handle, 1):
            if shown >= min(int(limit), 60):
                break
            if any(marker in raw[:200] for marker in SKIP):
                continue
            try:
                rec = json.loads(raw)
            except Exception:
                continue
            text = typed_text(rec) if rec.get("type") == "user" else ""
            if text and not text.startswith("<") and "[Request interrupted" not in text:
                print(f"L{n}: {SECRET.sub('[redacted]', ' '.join(text.split()))[:240]}")
                shown += 1


def prompts_all(days=30):
    """Every typed prompt of the window in one file, so a whole-history read is one command, not a script per audit."""
    cutoff = dt.datetime.now().timestamp() - int(days) * 86400
    out = project_root() / f"harness-audit-{dt.date.today().isoformat()}"
    out.mkdir(exist_ok=True)
    rows = 0
    with (out / "prompts.tsv").open("w") as dest:
        for path in sorted(p for p in PROJECTS.glob("*/*.jsonl") if in_project(p)):  # main sessions only: subagents live one folder deeper
            if path.stat().st_mtime < cutoff:
                continue
            with path.open(errors="replace") as handle:
                for n, raw in enumerate(handle, 1):
                    if '"user"' not in raw or any(marker in raw[:200] for marker in SKIP):
                        continue
                    try:
                        rec = json.loads(raw)
                    except Exception:
                        continue
                    text = typed_text(rec) if rec.get("type") == "user" else ""
                    if not text or text.startswith(("<", "Caveat:", "This session is being continued")) or "[Request interrupted" in text:
                        continue
                    text = SECRET.sub("[redacted]", " ".join(text.split()))
                    dest.write(f"{(rec.get('timestamp') or '')[:16]}\t{path.parent.name}\t{path.stem[:8]}\tL{n}\t{text[:600]}\n")
                    rows += 1
    print(f"{out / 'prompts.tsv'}: {rows} prompts. Read it with Read (offset/limit) or grep; never open a transcript.")


# ---- checks: the counts behind a harness-audit report, re-run in one call (was scans.py) ----
# Transcript format is internal: if a count drops to 0 after a Claude Code update, run `selftest` and check the record shapes.


def session_notes(path=None):
    """Entries of the optional --notes FILE. One entry per `## <heading>` line, then lines `task: ...`, `corrections: ...`,
    `friction: ...`, `asked twice: ...` (all optional). No file given or found: []."""
    if not path or not path.exists():
        return []
    keys = {"task": "task", "corrections": "corrections", "friction": "friction", "asked twice": "ask_twice"}
    entries, cur = [], None
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("## "):
            cur = {"date": line[3:].strip(), "task": "", "corrections": "", "friction": "", "ask_twice": ""}
            entries.append(cur)
            continue
        key, _, rest = line.partition(":")
        if cur is not None and key.strip().lower() in keys:
            cur[keys[key.strip().lower()]] = rest.strip()
    return entries


def ck_records(path):
    with open(path, errors='replace') as fh:
        yield from ck_lines(fh)


def ck_lines(fh):
    for line in fh:
        try:
            yield json.loads(line)
        except ValueError:
            pass


def ck_mains():
    return [str(p) for p in PROJECTS.glob('*/*.jsonl') if in_project(p)]


def ck_subs():
    return [str(p) for p in PROJECTS.glob('*/*/subagents/*.jsonl') if in_project(p)]


def ck_prompt_text(o):
    """Text of a typed prompt, or None for tool results, meta records and notifications."""
    if o.get('type') != 'user' or o.get('isMeta') or o.get('isSidechain'):
        return None
    c = o['message']['content']
    if isinstance(c, list) and any(isinstance(x, dict) and x.get('type') == 'tool_result' for x in c):
        return None
    s = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text')
    if not s.strip() or s.startswith(('<local-command', '<task-notification')) or "hasn't heard" in s:
        return None
    return s


def ck_turns(since):
    """Main-thread turns after SINCE: prompt, UserPromptSubmit hook output, assistant texts, tool names."""
    for f in ck_mains():
        cur = None
        for o in ck_records(f):
            p = ck_prompt_text(o)
            if p is not None:
                if cur and cur['ts'] >= since:
                    yield cur
                cur = {'f': f, 'ts': o.get('timestamp', ''), 'p': p, 'hook': '', 'texts': [], 'tools': []}
            elif cur is None:
                continue
            elif o.get('type') == 'attachment' and (o.get('attachment') or {}).get('hookEvent') == 'UserPromptSubmit':
                cur['hook'] += str(o['attachment'].get('content', ''))
            elif o.get('type') == 'assistant' and not o.get('isSidechain'):
                for b in o['message'].get('content', []):
                    if b.get('type') == 'text':
                        cur['texts'].append(b['text'])
                    elif b.get('type') == 'tool_use':
                        cur['tools'].append(b['name'])
        if cur and cur['ts'] >= since:
            yield cur


def ck_leftopen(since):
    n = ok = earlier = 0
    for t in ck_turns(since):
        if len(t['tools']) < 5:
            continue
        n += 1
        last = t['texts'][-1] if t['texts'] else ''
        ok += 'Left open' in last
        earlier += 'Left open' not in last and any('Left open' in x for x in t['texts'])
    print(f'leftopen: {n} turns with 5+ tool calls; last text has "Left open" {ok}; only an earlier text {earlier}; '
          f'none {n - ok - earlier} (read these: mid-run turns with agents still running are not misses)')


def ck_nudges(since):
    fired, followed = collections.Counter(), collections.Counter()
    checks = {'topic': ('if this prompt starts a topic', r'fresh session|/wrap|new session'),
              'broad': ('Broad request', r'M tokens|median|first slice|go-ahead|estimat'),
              'paste': ('KB paste', r'pbpaste'), 'secret': ('token-shaped', r'transcript|password manager')}
    ctx = 0
    for t in ck_turns(since):
        ctx += 'Context: ' in t['hook']
        for k, (pat, follow) in checks.items():
            if pat in t['hook']:
                fired[k] += 1
                followed[k] += bool(re.search(follow, ' '.join(t['texts']), re.I))
    print(f'nudges: {ctx} prompts carried the context line; fired {dict(fired)}; reply matched {dict(followed)}')


def ck_fanouts(since):
    rows = []
    for t in ck_turns(since):
        a = t['tools'].count('Agent')
        if a >= 3 and not t['p'].startswith('This session is being continued'):
            cost = bool(re.search(r'\bM tokens|million tokens|median|estimated cost|about \d+M', ' '.join(t['texts']), re.I))
            rows.append((t['ts'][:16], a, cost))
    print(f'fanouts: {len(rows)} new turns spawned 3+ agents; with a cost line {sum(r[2] for r in rows)}; '
          f'5+ agents without one {sum(1 for r in rows if r[1] >= 5 and not r[2])}')


def ck_askme(since):
    pat = re.compile(r'ask me|ask the questions|questions to me|ask more questions|reask|re-ask|didnt decline', re.I)
    found = sorted(project_root().glob('harness-audit-*/prompts.tsv'))
    rows = [l.split('\t') for l in open(found[-1], errors='replace') if l[:16] >= since[:16]] if found else []
    hits = [r for r in rows if len(r) > 4 and pat.search(r[4])]
    print(f'askme: {len(hits)} prompts in {len({r[2] for r in hits})} sessions ask Claude to put its questions '
          f'(from the newest harness-audit-*/prompts.tsv; run collect.py prompts-all first)')


def ck_preamble(since):
    """Size of the fixed attachments at the start of the newest worker transcripts."""
    files = sorted((f for f in ck_subs()), key=os.path.getmtime)[-20:]
    sizes = collections.defaultdict(list)
    for f in files:
        for i, o in enumerate(ck_records(f)):
            if i > 12:
                break
            a = o.get('attachment') or {}
            if a.get('type') == 'instructions':
                for x in a['files']:
                    sizes[os.path.basename(x['path']) + ' (' + x.get('type', '') + ')'].append(len(x['content']))
            elif a.get('type') in ('skill_listing', 'deferred_tools_delta', 'hook_additional_context'):
                sizes[a['type']].append(len(json.dumps(a)))
    for k, v in sorted(sizes.items()):
        print(f'preamble: {k}: median {sorted(v)[len(v) // 2]} bytes over {len(v)} subagent runs')


def ck_blocked(since):
    by = collections.defaultdict(collections.Counter)
    for f in ck_subs() + ck_mains():
        th = 'sub' if '/subagents/' in f else 'main'
        for o in ck_records(f):
            if o.get('timestamp', '') < since or o.get('type') != 'user':
                continue
            c = o['message'].get('content')
            for b in c if isinstance(c, list) else []:
                if isinstance(b, dict) and b.get('type') == 'tool_result' and b.get('is_error'):
                    t = b.get('content')
                    t = (t if isinstance(t, str) else json.dumps(t)).lower()
                    for k, p in (('sleep', 'sleep'), ('git add -A', 'git add -a'), ('shared edit', 'another session may own'),
                                 ('destructive', 'destructive or unwanted'), ('edit before read', 'has not been read yet')):
                        if p in t:
                            by[o['timestamp'][:10]][f'{th}:{k}'] += 1
                            break
    for d in sorted(by):
        print('blocked:', d, dict(by[d]))


def ck_context(since):
    b = collections.defaultdict(collections.Counter)
    for f in ck_mains():
        for o in ck_records(f):
            if o.get('type') != 'assistant' or o.get('isSidechain') or o.get('timestamp', '') < since:
                continue
            m = o['message']
            u = m.get('usage') or {}
            c = u.get('input_tokens', 0) + u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0)
            b[(m.get('model'), o['timestamp'][:10])]['>400k' if c > 4e5 else '300-400k' if c > 3e5 else '<300k'] += 1
    for k in sorted(b, key=str):
        print('context:', k, dict(b[k]))


def ck_sid(f):
    """Main session id for a main or subagent transcript."""
    parts = f.split('/')
    return parts[-3] if '/subagents/' in f else os.path.basename(f)[:-6]


def ck_norm(cmd):
    cmd = cmd.replace(str(Path.cwd()) + '/', '').replace(str(HOME) + '/', '~/')
    cmd = re.sub(r'(?:/private)?/tmp/claude-\d+/\S*', '<scratch>', cmd)
    cmd = re.sub(r'\b[0-9a-f]{7,40}\b', '<sha>', cmd)
    cmd = re.sub(r'"[^"]*"|\'[^\']*\'', '<s>', cmd)
    return re.sub(r'\b\d+\b', '<n>', cmd)


CK_TRIVIAL = {'cd', 'grep', 'sed', 'cat', 'ls', 'head', 'tail', 'echo', 'wc', 'find', 'sort', 'uniq', 'cut', 'tr', 'awk',
           'printf', 'true', 'test', '[', 'xargs', 'rg', 'date', 'pwd', 'sleep', 'for', 'do', 'done', 'if', 'then', 'fi',
           'while', 'jq', 'diff', 'mkdir', 'rm', 'cp', 'mv', 'touch', 'stat', 'file', 'basename', 'dirname', 'export', 'set',
           'python3', 'node', 'tee', 'kill', 'wait', 'du', 'df', 'which', 'command', 'type', 'read', 'shasum', 'else', 'exit'}


def ck_repeats(since):
    """Repeated shell steps and repeated agent-brief lines: candidates for scripts, skills or worker.md."""
    seg_s, seg_c, py_s, brief_s, brief_c = (collections.defaultdict(set), collections.Counter(), collections.defaultdict(set),
                                            collections.defaultdict(set), collections.Counter())
    for f in ck_mains() + ck_subs():
        sid = ck_sid(f)
        for o in ck_records(f):
            if o.get('type') != 'assistant' or o.get('timestamp', '') < since:
                continue
            for b in o['message'].get('content', []):
                if b.get('type') != 'tool_use':
                    continue
                if b['name'] == 'Bash':
                    cmd = b['input'].get('command', '')
                    m = re.search(r'python3 (?:-I )?- <<.?EOF.?\n(.*)', cmd, re.S)
                    if m:
                        body = [l for l in m.group(1).splitlines() if l.strip() and not l.startswith(('import', 'from'))]
                        if body:
                            py_s[ck_norm(body[0])[:90]].add(sid)
                        continue
                    for seg in re.split(r'&&|\|\||;|\||\n', cmd):
                        w = ck_norm(seg.strip()).split()
                        if not w or w[0] in CK_TRIVIAL or '=' in w[0]:
                            continue
                        key = ' '.join(w[:3])
                        seg_s[key].add(sid)
                        seg_c[key] += 1
                elif b['name'] == 'Agent':
                    for line in str(b['input'].get('prompt', '')).splitlines():
                        line = ck_norm(line.strip())
                        if len(line) > 40:
                            brief_s[line[:140]].add(sid)
                            brief_c[line[:140]] += 1
    print('repeats: shell steps used in 6+ sessions (calls, sessions):')
    for k, v in sorted(seg_s.items(), key=lambda kv: -len(kv[1]))[:70]:
        if len(v) >= 6:
            print(f'  {seg_c[k]:5} {len(v):3}  {k[:110]}')
    print('repeats: inline python first lines in 3+ sessions:')
    for k, v in sorted(py_s.items(), key=lambda kv: -len(kv[1]))[:25]:
        if len(v) >= 3:
            print(f'  {len(v):3}  {k}')
    print('repeats: agent-brief lines in 8+ briefs (briefs, sessions):')
    for k, v in sorted(brief_c.items(), key=lambda kv: -kv[1])[:45]:
        if v >= 8:
            print(f'  {v:4} {len(brief_s[k]):3}  {k}')


CK_RECIPES = {
    'worktree add': r'git (?:-C \S+ )?worktree add', 'vendor/node_modules copy into worktree': r'cp -R\w* \S*(?:vendor|node_modules)',
    'worktree remove': r'worktree remove', 
    'fetch': r'git (?:-C \S+ )?fetch',
    
    
    'git status sweep': r'git (?:-C \S+ )?status --short', 'dev server start': r'npm run dev|next dev|npx expo start|react-native start',
    'pid file write': r'echo \$! *> *\S+\.pid', 'wait loop (until)': r'\buntil\b', 'port check lsof': r'lsof -nP -iTCP|lsof -i *:',
    'curl remote': r'curl[^|;]*https://',
    'adb raw': r'\badb\b', 
    'phpunit filter': r'--filter', 'test summary grep': r'grep[^|;]*(?:Tests:|FAIL|passed)',
    'phpstan': r'phpstan', 'php -l': r'php -l', 'pint': r'\bpint\b', 'tsc': r'tsc --noEmit', 'eslint/lint': r'eslint|npm run -s lint|npm run lint',
    'verify:a11y/design/axe': r'verify:(?:a11y|design|axe|speed)', 'jest/vitest': r'\bjest\b|vitest|npm (?:run -s )?test',
    
    'make target': r'\bmake [a-z-]+', 'docker compose': r'docker compose|docker-compose', 'aws cli': r'\baws [a-z]',
    'mysql client': r'\bmysql\b', 
    'gh cli': r'\bgh [a-z]', 
    'image tools (sips/magick/ffmpeg)': r'\bsips\b|magick|ffmpeg|cwebp',
    'pdf text': r'pdftotext|pdfinfo', 'python inline replace': r'open\(p\)\.read\(\)|\.read_text\(\)', 'ps aux': r'ps aux',
    'kill by pid file': r'kill \$\(cat', 
    'npm ci/install': r'npm (?:ci|install|i)\b', 'composer': r'\bcomposer\b', 'xcrun/ios': r'xcrun|simctl', 'jq': r'\bjq\b',
}


def ck_recipes(since):
    """Calls and sessions per recognisable step, all window and the last 7 days, main and subagent."""
    import datetime
    week = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    pats = {k: re.compile(v) for k, v in CK_RECIPES.items()}
    calls, sess, sub, recent = collections.Counter(), collections.defaultdict(set), collections.Counter(), collections.defaultdict(set)
    for f in ck_mains() + ck_subs():
        sid, th = ck_sid(f), '/subagents/' in f
        for o in ck_records(f):
            ts = o.get('timestamp', '')
            if o.get('type') != 'assistant' or ts < since:
                continue
            for b in o['message'].get('content', []):
                if b.get('type') != 'tool_use' or b['name'] != 'Bash':
                    continue
                cmd = re.sub(r"<<-?\s*'?(\w+)'?\n.*?\n\1\b", '<<heredoc', b['input'].get('command', ''), flags=re.S)
                for k, p in pats.items():
                    if p.search(cmd):
                        calls[k] += 1
                        sess[k].add(sid)
                        sub[k] += th
                        if ts >= week:
                            recent[k].add(sid)
    print(f'recipes: step: calls (share in subagents), sessions; sessions since {week[:10]}')
    for k in sorted(calls, key=lambda k: -len(sess[k])):
        print(f'  {k:40} {calls[k]:6} ({100 * sub[k] // calls[k]:3}% sub) {len(sess[k]):4} sess  {len(recent[k]):3} recent')



CHECKS = dict(leftopen=ck_leftopen, nudges=ck_nudges, fanouts=ck_fanouts, askme=ck_askme, preamble=ck_preamble, blocked=ck_blocked,
              context=ck_context, repeats=ck_repeats, recipes=ck_recipes)


def checks(since=None, which="all"):
    """Print every check (or the one named) for turns after SINCE (an ISO UTC prefix such as 2026-11-16T12:55; default 30 days ago)."""
    since = since or (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M")
    for name, fn in CHECKS.items():
        if which in ("all", name):
            fn(since)


def selftest():
    """Smallest check of the counting rules: a request split over two lines counts once, and flags fire."""
    import contextlib, io, os, tempfile
    global ROOT, PROJECTS
    with tempfile.TemporaryDirectory() as tmp:
        ROOT, PROJECTS = Path(tmp) / ".claude", Path(tmp) / ".claude" / "projects"
        (PROJECTS / "-demo").mkdir(parents=True)
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        usage = {"input_tokens": 10, "cache_creation_input_tokens": 20, "cache_read_input_tokens": 30, "output_tokens": 40}
        reply = lambda blocks: {"type": "assistant", "timestamp": now, "message": {"id": "a1", "model": "m", "usage": usage, "content": blocks}}
        said = lambda text: {"type": "user", "timestamp": now, "message": {"content": text}}
        failed = {"type": "user", "timestamp": now, "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": True}]}}
        records = [said("please add the export button to the settings page"), reply([{"type": "text", "text": "ok"}]),
                   reply([{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "npm test"}}]),
                   failed, failed, failed, said("no, that is wrong"), said("continue")]
        err = lambda text: {"type": "user", "timestamp": now, "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": text}]}}
        texts = ["Blocked: sleep 30 is not allowed", "PreToolUse:Bash hook error: [x] Another session may own this file", "built-in Claude Code safety check",
                 "denied by the auto mode classifier. Reason: [too risky]", "The user doesn't want to proceed with this tool use."]
        ok = {"type": "user", "timestamp": now, "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "fine"}]}}
        more = [x for t in texts for x in (err(t), ok)] + [
            {"type": "system", "timestamp": now, "hookErrors": ["boom at /private/var/folders/ab/cd/x.sh  failed"]},
            {"type": "assistant", "timestamp": now, "message": {"id": "lim", "model": "m", "usage": usage,
             "content": [{"type": "text", "text": "You've hit your weekly limit"}]}},
            {"type": "assistant", "timestamp": now, "message": {"id": "big", "model": "m", "content": [],
             "usage": {"input_tokens": 1, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 350000, "output_tokens": 1}}},
            said("key AGE-SECRET-KEY-1" + "Q" * 30)]
        sub = PROJECTS / "-demo" / "s2" / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-a.jsonl").write_text("\n".join(json.dumps(
            {"type": "assistant", "timestamp": now, "message": {"id": f"r{i}", "model": "actual-x", "usage": usage, "content": []}})
            for i in range(101)) + "\n" + json.dumps(err("Blocked: sleep 5")) + "\n")
        (sub / "agent-a.meta.json").write_text(json.dumps({"agentType": "worker", "model": "sonnet"}))
        (sub / "agent-orphan.meta.json").write_text("{}")
        (PROJECTS / "-demo" / "s2.jsonl").write_text("\n".join(json.dumps(r) for r in more) + "\n")
        (PROJECTS / "-demo" / "s1.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\nnot json\n")
        (Path(tmp) / "deep" / "sub").mkdir(parents=True)
        os.chdir(Path(tmp) / "deep" / "sub")  # a scan from a subfolder still writes and reads at the project root
        with contextlib.redirect_stdout(io.StringIO()):
            scan(30)
        data = json.loads(next(Path(tmp).glob("harness-audit-*/data.json")).read_text())
        assert not list((Path(tmp) / "deep").rglob("harness-audit-*")), "output nested under the shell's folder"
        assert Path(data["setup"]["project_folder"]).resolve() == Path(tmp).resolve(), data["setup"]["project_folder"]
    session, flags = next(r for r in data["tokens"]["top_sessions"] if r["session"] == "s1"), data["friction"]["counts"]
    assert session["tokens_main"] == {"input": 10, "cache_write": 20, "cache_read": 30, "output": 40}, session["tokens_main"]
    assert session["requests"] == 1 and session["prompts"] == 3, session
    assert data["coverage"]["parse_failures"] == 1, data["coverage"]
    assert flags.get("correction") == 1 and flags.get("continue_prompt") == 1 and flags.get("error_streak") == 1, flags
    assert {k: v for k, v in data["tools"]["errors"].items() if k != "?"} == {"Bash": 3}, data["tools"]["errors"]
    bl = data["friction"]["blocked"]
    assert {k: v["count"] for k, v in bl.items()} == {"foreground sleep blocked": 2, "PreToolUse hook denial": 1, "removal safety check": 1,
                                                       "auto-mode classifier": 1, "user rejected": 1}, bl
    assert bl["foreground sleep blocked"]["subagent"] == 1 and bl["foreground sleep blocked"]["main"] == 1, bl
    assert list(bl["PreToolUse hook denial"]["groups"]) == ["[x] Another session may own this file"], bl
    assert "too risky" in bl["auto-mode classifier"]["groups"], bl
    assert data["friction"]["hook_error_text"] == {"boom at <tmp> failed": 1}, data["friction"]["hook_error_text"]
    assert data["friction"]["limit_messages"] == {now[:10]: {"weekly": 1}}, data["friction"]["limit_messages"]
    cb = data["tokens"]["context_bands"]["main|m"]
    assert cb["requests"] == 3 and cb["bands"]["<100k"]["requests"] == 2 and cb["bands"]["300-400k"]["requests"] == 1, cb
    runs = data["tokens"]["subagent_runs"]
    assert len(runs["runs"]) == 1 and runs["runs"][0]["requests"] == 101 and runs["runs"][0]["actual_model"] == "actual-x", runs
    assert runs["runs"][0]["spawn_model"] == "sonnet" and runs["by_type"]["worker"]["runs_over_100_requests"] == 1, runs
    assert runs["by_type"]["worker"]["over_100_token_share"] == 1.0, runs
    assert SECRET.search("AGE-SECRET-KEY-1" + "Q" * 30), "age key not matched"
    assert SECRET.search("AIza" + "B" * 35), "Google key not matched"
    with tempfile.TemporaryDirectory() as tmp:
        ROOT, PROJECTS = Path(tmp) / ".claude", Path(tmp) / ".claude" / "projects"
        (PROJECTS / "-demo").mkdir(parents=True)
        (Path(tmp) / ".claude" / "x").mkdir()
        os.chdir(tmp)
        lines = [{"type": "user", "timestamp": now, "message": {"content": t}} for t in
                 ("fix the cart", "<command-name>/clear</command-name>", "key AIza" + "C" * 35)]
        (PROJECTS / "-demo" / "s3.jsonl").write_text("\n".join(json.dumps(r) for r in lines) + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            prompts_all(30)
        got = next(Path(tmp).glob("harness-audit-*/prompts.tsv")).read_text().splitlines()
        assert len(got) == 2 and got[0].endswith("\tfix the cart") and "AIza" not in got[1], got
    # checks: the record shapes the counts rely on (typed prompt, UserPromptSubmit attachment, tool_use, tool_result error, subagent file)
    with tempfile.TemporaryDirectory() as tmp:
        ROOT, PROJECTS = Path(tmp) / ".claude", Path(tmp) / ".claude" / "projects"
        proj = PROJECTS / "-home-demo-project"
        (proj / "s4" / "subagents").mkdir(parents=True)
        (ROOT / "logs").mkdir()
        notes = ROOT / "logs" / "notes.md"
        notes.write_text("## 2026-11-17 demo\ntask: t\ncorrections: none\nfriction: f\nAsked twice: nothing\n")
        assert session_notes(notes) == [{"date": "2026-11-17 demo", "task": "t", "corrections": "none", "friction": "f", "ask_twice": "nothing"}], session_notes(notes)
        use = lambda name, inp: {"type": "assistant", "timestamp": now, "message": {"id": "u", "model": "m", "usage": usage,
                                 "content": [{"type": "tool_use", "id": "t", "name": name, "input": inp}]}}
        hook = {"type": "attachment", "timestamp": now, "attachment": {"hookEvent": "UserPromptSubmit", "content": "Context: 90k. if this prompt starts a topic unrelated"}}
        recs = [said("do the big thing"), hook, use("Agent", {"prompt": "x"}), use("Agent", {"prompt": "x"}), use("Agent", {"prompt": "x"}),
                use("Bash", {"command": "git worktree add ../w && cp -Rc vendor ../w/vendor"}), use("Bash", {"command": "ls"}),
                reply([{"type": "text", "text": "done. Left open: nothing"}]),
                {"type": "user", "timestamp": now, "message": {"content": [{"type": "tool_result", "tool_use_id": "t", "is_error": True, "content": "Blocked: sleep 30"}]}}]
        (proj / "s4.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        (proj / "s4" / "subagents" / "agent-b.jsonl").write_text(json.dumps(
            {"type": "attachment", "attachment": {"type": "instructions", "files": [{"path": "/x/CLAUDE.md", "type": "User", "content": "abcd"}]}}) + "\n")
        (Path(tmp) / ".claude" / "x").mkdir(exist_ok=True)
        os.chdir(tmp)
        (Path(tmp) / "harness-audit-2026-11-17").mkdir()
        (Path(tmp) / "harness-audit-2026-11-17" / "prompts.tsv").write_text(now[:16] + "\tp\ts4\t1\tplease ask me the questions\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            checks(now[:10])
        out = buf.getvalue()
        for want in ("leftopen: 1 turns with 5+ tool calls; last text has \"Left open\" 1", "nudges: 1 prompts carried the context line; fired {'topic': 1}",
                     "fanouts: 1 new turns spawned 3+ agents; with a cost line 0; 5+ agents without one 0", "askme: 1 prompts in 1 sessions",
                     "preamble: CLAUDE.md (User): median 4 bytes over 1", "blocked: " + now[:10] + " {'main:sleep': 1}",
                     "context: ('m', '" + now[:10] + "') {'<300k': 6}", "worktree add", "vendor/node_modules copy into worktree"):
            assert want in out, (want, out)
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:2] == ["selftest"]:  # outside the catch-all: a failed check must exit non-zero
        selftest()
        sys.exit(0)
    try:
        args = take_flags(sys.argv[1:])
        if args[:1] == ["show"]:
            show(args[1:] or ["coverage"])
        elif args[:1] == ["prompts"] and len(args) >= 2:
            prompts(*args[1:3])
        elif args[:1] == ["checks"]:
            checks(*args[1:3])  # since, then an optional single check name
        elif args[:1] == ["prompts-all"]:
            prompts_all(next((int(a) for a in args[1:] if a.isdigit()), 30))
        elif args[:1] == ["excerpt"] and len(args) >= 3:
            excerpt(*args[1:4])
        elif not args or args[0] == "scan":
            days = next((int(a) for a in args[1:] if a.isdigit()), 30)
            scan(days)
        else:
            print(__doc__)
    except Exception as error:  # never abort the skill that injected this run
        print(f"harness-audit collector failed: {type(error).__name__}: {error}")
    sys.exit(0)
