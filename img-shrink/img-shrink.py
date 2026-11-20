#!/usr/bin/env python3
"""Smaller screenshots for Read (macOS: uses sips). PreToolUse: a .png/.jpg/.jpeg/.webp whose long edge passes
1200 px is read from a shrunk copy (sips -Z 1200) in /private/tmp/claude-<uid>/img/small; the original is never touched.
PostToolUse: tells Claude the image was shrunk and how to read the original (`img-full <path>`, installed in bin/), whose
copy lives in .../img/full, which this hook leaves alone. Measured 20 Nov: 1,477 image reads in 14 days; a phone
shot drops from about 1,475 to about 860 image tokens. Test: img-shrink.py --self-test."""
import hashlib, json, os, shlex, subprocess, sys, time

EDGE = 1200
BASE = f"/private/tmp/claude-{os.getuid()}/img"
_d = os.path.dirname(os.path.abspath(__file__))  # img-full next to this file, else in ../bin (an install), else on PATH
IMGFULL = next((p for p in (_d + "/img-full", _d + "/../bin/img-full") if os.path.exists(p)), "img-full")
SMALL, FULL = BASE + "/small", BASE + "/full"
EXT = (".png", ".jpg", ".jpeg", ".webp")

def dims(p):
    r = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", p], capture_output=True, text=True)
    v = [int(l.split()[-1]) for l in r.stdout.splitlines() if "pixel" in l]
    return tuple(v) if len(v) == 2 else None

def small_path(p):
    st = os.stat(p); k = hashlib.sha1(f"{p}|{st.st_mtime_ns}|{st.st_size}".encode()).hexdigest()[:16]
    name = os.path.basename(p); name = name.rsplit(".", 1)[0] + ".png" if name.lower().endswith(".webp") else name
    return f"{SMALL}/{k}-{name}"

def prune():
    cut = time.time() - 2 * 86400
    for d in (SMALL, FULL):
        for e in os.scandir(d) if os.path.isdir(d) else []:
            try:  # ctime: a reused copy is touched in pre(), and a copy keeps its source's mtime; a parallel prune may win
                if e.stat().st_ctime < cut: os.unlink(e.path)
            except OSError: pass

def pre(inp):
    p = inp.get("file_path", "")
    if not p.lower().endswith(EXT) or os.path.realpath(p).startswith(BASE) or not os.path.isfile(p): return None  # /tmp is /private/tmp
    wh = dims(p)
    if not wh or max(wh) <= EDGE: return None
    s = small_path(p)
    if os.path.exists(s) and os.path.exists(s + ".json"):
        os.utime(s); os.utime(s + ".json")  # in use again: prune() leaves it two more days
    else:
        os.makedirs(SMALL, exist_ok=True); prune()
        tmp = f"{SMALL}/.{os.getpid()}-{os.path.basename(s)}"  # written aside, then renamed: a parallel Read never sees half a file
        cmd = ["sips", "-Z", str(EDGE), p, "--out", tmp] + (["-s", "format", "png"] if p.lower().endswith(".webp") else [])
        if subprocess.run(cmd, capture_output=True).returncode or not os.path.exists(tmp): return None
        with open(tmp + ".json", "w") as f: json.dump({"src": p, "w": wh[0], "h": wh[1]}, f)
        os.replace(tmp + ".json", s + ".json"); os.replace(tmp, s)
    return {**inp, "file_path": s}

def post(inp):
    p = inp.get("file_path", "")
    if not p.startswith(SMALL):
        if not p.lower().endswith(EXT) or not os.path.isfile(p): return None
        p = small_path(p)
    try: m = json.load(open(p + ".json"))
    except (OSError, ValueError): return None
    wh = dims(p) or ("?", "?")
    return (f"Image shown shrunk to {wh[0]}x{wh[1]} (original {m['w']}x{m['h']}, {m['src']}). If small text or detail is hard "
            f"to read, run `{shlex.quote(IMGFULL)} {shlex.quote(m['src'])}` and Read the path it prints.")  # a ' in a name breaks plain quotes

def main():
    try:
        d = json.load(sys.stdin)
        if d.get("tool_name") != "Read": return
        ev = d.get("hook_event_name"); inp = d.get("tool_input") or {}
        if ev == "PreToolUse":
            new = pre(inp)
            if new: print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": new}}))
        elif ev == "PostToolUse":
            note = post(inp)
            if note: print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": note}}))
    except Exception:
        pass  # never block a Read

def self_test():
    import tempfile
    t = tempfile.mkdtemp(); big, tiny = t + "/big.png", t + "/tiny.png"
    subprocess.run(["sips", "-z", "2400", "1080", "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericDocumentIcon.icns",
                    "-s", "format", "png", "--out", big], capture_output=True)
    subprocess.run(["sips", "-Z", "300", big, "--out", tiny], capture_output=True)
    n = pre({"file_path": big}); assert n and n["file_path"].startswith(SMALL), n
    assert max(dims(n["file_path"])) == EDGE, dims(n["file_path"])
    assert pre({"file_path": tiny}) is None and pre({"file_path": t + "/x.txt"}) is None
    assert "img-full" in post(n) and "~/.claude" not in post(n) and "img-full" in post({"file_path": big})
    full = subprocess.run([IMGFULL, big], capture_output=True, text=True).stdout.strip()
    assert full.startswith(FULL) and pre({"file_path": full}) is None and dims(full) == (1080, 2400), full
    assert os.path.getsize(big) and dims(big) == (1080, 2400)  # original untouched
    # the full copy is not the original's inode; a same-named image in the same second writes
    # nothing into the first original; a /tmp/... path to a full copy is not shrunk; prune spares a copy made now
    # from an old file (a hard link or a clone keeps the source's mtime)
    os.makedirs(t + "/b"); other = t + "/b/big.png"; open(other, "wb").write(b"not the original")
    f2 = [subprocess.run([IMGFULL, x], capture_output=True, text=True).stdout.strip() for x in (big, other)]
    assert os.stat(full).st_ino != os.stat(big).st_ino and f2[0] != f2[1] and dims(big) == (1080, 2400), f2
    assert pre({"file_path": full.replace("/private/tmp/", "/tmp/", 1)}) is None
    os.utime(big, (time.time() - 9 * 86400,) * 2); old = subprocess.run([IMGFULL, big], capture_output=True, text=True).stdout.strip()
    os.utime(old, (time.time() - 9 * 86400,) * 2); prune(); assert os.path.exists(old)
    assert not [x for x in os.listdir(SMALL) if x.startswith(f".{os.getpid()}-")]  # no half-written copy left
    q = t + "/it's'; touch x; '.png"; os.link(big, q); nq = pre({"file_path": q}); assert shlex.quote(q) in post(nq), post(nq)
    for x in (nq["file_path"], nq["file_path"] + ".json"): os.unlink(x)
    import shutil; shutil.rmtree(t)
    for x in [n["file_path"], n["file_path"] + ".json", full, old] + f2:
        try: os.unlink(x)
        except OSError: pass
    print("img-shrink self-test ok")

if __name__ == "__main__":
    self_test() if sys.argv[1:] == ["--self-test"] else main()
