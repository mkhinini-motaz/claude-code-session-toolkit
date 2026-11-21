#!/usr/bin/env python3
"""SessionStart hook (matcher: compact): after compaction, put the scratchpad state file, the files edited,
the commits run and the user's last two prompts back into context. Fails silent: never blocks a session."""
import glob, json, os, re, sys
from datetime import datetime

CAP, STATE_CAP = 8000, 6000
STATE = '[sS][tT][aA][tT][eE].md'
EDITS = {'Edit', 'Write', 'MultiEdit', 'NotebookEdit'}


SCRATCH = re.compile(r'/private/tmp/claude-\d+/[^/\s"]+/[^/\s"]+/scratchpad')


def find_state(sid, written, scratch):
    # Only this session's files: other sessions in the same project keep their own state.md.
    if written and os.path.exists(written):
        return written
    # The main thread owns <scratchpad>/state.md; a worker's <scratchpad>/<task>/state.md is never its own.
    hits = glob.glob(f'/private/tmp/claude-*/*/{sid}/scratchpad/{STATE}')
    if not hits and scratch:  # after /clear the scratchpad folder id differs from session_id
        hits = glob.glob(f'{scratch}/{STATE}')
    return max(hits, key=os.path.getmtime) if hits else None


def is_commit(cmd, cwd):
    return bool(re.search(r'\bgit\b[^|;&\n]*\bcommit\b|\bbin/commit\b', cmd.split('<<')[0]))


def main():
    p = json.load(sys.stdin)
    sid, tp, cwd = p['session_id'], p['transcript_path'], p.get('cwd') or ''
    # A subagent shares its parent's session_id and quotes its scratchpad: restore only a state file it wrote itself.
    sub = bool(p.get('agent_id')) or '/subagents/' in tp
    slug = os.path.basename(os.path.dirname(tp))
    edits, commits, prompts, t0, written, scratch = [], [], [], None, None, None
    for line in open(tp, errors='replace'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if t0 is None and d.get('timestamp'):
            t0 = datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00')).timestamp()
        m = d.get('message') or {}
        c = m.get('content')
        if d.get('type') == 'assistant' and isinstance(c, list):
            for b in c:
                if b.get('type') != 'tool_use':
                    continue
                i = b.get('input') or {}
                hit = SCRATCH.search(json.dumps(i))
                if hit:
                    scratch = hit.group(0)
                if b.get('name') in EDITS:
                    f = i.get('file_path') or i.get('notebook_path')
                    if f:
                        if re.search(r'/scratchpad/([^/]+/)?state\.md$' if sub else r'/scratchpad/state\.md$', f, re.I):
                            written = f
                        if f in edits:
                            edits.remove(f)
                        edits.append(f)
                elif b.get('name') == 'Bash' and is_commit(i.get('command') or '', cwd):
                    commits.append(' '.join((i['command']).split())[:160])
        elif d.get('type') == 'user' and m.get('role') == 'user' and not d.get('isMeta') and not d.get('isCompactSummary'):
            if isinstance(c, list):
                c = ' '.join(b.get('text', '') for b in c if b.get('type') == 'text')
            c = (c or '').strip() if isinstance(c, str) else ''
            if c and not c.startswith('<') and not c.startswith('This session is being continued'):
                prompts.append(c)
    path = (written if written and os.path.exists(written) else None) if sub else find_state(sid, written, scratch)
    out = ['[compact-restore] The conversation was just compacted. Working state recovered from disk:']
    if path:
        s = open(path, errors='replace').read()
        if len(s) > STATE_CAP:
            s = '...(cut, start of file omitted)\n' + s[-STATE_CAP:]
        out += [f'\n## State file: {path}', s]
    if edits:
        out += ['\n## Files edited this session (oldest first, last 40)'] + edits[-40:]
    if commits:
        out += ['\n## Git commits run'] + commits[-10:]
    if prompts:
        out += ['\n## User\'s last prompts (verbatim)'] + [q[:600] for q in prompts[-2:]]
    if not path and not sub:
        exp = f'{scratch or f"/private/tmp/claude-{os.getuid()}/{slug}/{sid}/scratchpad"}/state.md'
        out.append(f'\nNo state file survived compaction. Write {exp} now from the summary and the list above, marking each '
                   'open item run / read / assumed and each approach that failed with why, and check each against `git status` before acting on it.')
    print('\n'.join(out)[:CAP])


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        pass
