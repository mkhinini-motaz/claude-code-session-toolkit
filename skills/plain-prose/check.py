#!/usr/bin/env python3
"""Flags AI-prose tells in text files: skills/plain-prose/check.py FILE... (exit 1 when anything is found).

A paragraph over 80 words or a bullet over 35 is a length warning: printed, never counted in the exit code
(do not run it in a hook or pre-commit: a hit there would block a commit over style).
Code blocks and inline code are skipped. A hit is a prompt to rewrite, not a ban: keep a phrase
only when it is the plainest way to say the thing.
"""
import re, sys

TELLS = [
    (r"—", "em dash: use a colon, comma, full stop or brackets"),
    (r"\b[Hh]ere'?s (the thing|what|why|how|that|this)\b", "throat-clearing: state the point"),
    (r"\b(It turns out|The (uncomfortable |simple |real )?truth is|Let me be clear|Make no mistake|Let that sink in|Full stop\.)", "throat-clearing or emphasis crutch"),
    (r"\b(It'?s worth noting|At its core|At the end of the day|When it comes to|In today'?s|In a world where|The reality is)\b", "filler phrase"),
    (r"\b(Let me walk you through|In this section,? we|As we'?ll see|The rest of this)\b", "meta-commentary: let the text move"),
    (r"\b(really|truly|genuinely|fundamentally|inherently|crucially|importantly|interestingly|literally|honestly)\b", "intensifier: cut it or give the fact"),
    (r"\b(leverag\w*|seamless\w*|robust|navigat\w+ (the |this )?(challenge|complexit|landscape)\w*|landscape|deep dive|game[- ]changer|unlock\w*|delve\w*|empower\w*|streamlin\w+|cutting[- ]edge|holistic|synerg\w+)\b", "jargon: use the plain word"),
    (r"\b(isn'?t|is not|wasn'?t|not) (?!just |only |merely )[^.;:]{1,40}[,;.] (it'?s|it is|but|it was)\b", "binary contrast: state the second half directly"),
    (r"\bnot (just|only) [^.]{1,40} but (also )?", "additive hedge: say both plainly"),
    (r"\b(The (implications|stakes|consequences) (are|is) (significant|high|real)|The reasons are structural)", "vague declarative: name the specific thing"),
    (r"\b(the data (tells|shows) us|the market rewards|a decision emerges|the conversation (moves|shifts))\b", "false agency: name who does it"),
]
FENCE = re.compile(r"^\s*(```|~~~)")
CODE = re.compile(r"`[^`]*`")

BULLET = re.compile(r"^\s*([-*+]|\d+[.)])\s")
MAX_PARA, MAX_BULLET = 80, 35
warned = 0


def long_blocks(lines):
    """Yield (first line number, kind, words) for each paragraph over 80 words and bullet over 35; tables, headings and code skipped."""
    block, in_code = None, False  # block: [start, kind, words]

    def end():
        if block and block[2] > (MAX_BULLET if block[1] == "bullet" else MAX_PARA):
            return (block[0], block[1], block[2])

    for n, line in enumerate(lines, 1):
        if FENCE.match(line):
            in_code = not in_code
        text = line.strip()
        skip = in_code or FENCE.match(line) or text.startswith(("|", "#", ">")) or not text
        bullet = not skip and BULLET.match(line)
        if skip or bullet:
            hit = end()
            if hit:
                yield hit
            block = None
        if skip:
            continue
        count = len(CODE.sub("x", BULLET.sub("", text)).split())
        if bullet:
            block = [n, "bullet", count]
        elif block:
            block[2] += count
        else:
            block = [n, "para", count]
    hit = end()
    if hit:
        yield hit


def check(path):
    global warned
    hits, in_code = 0, False
    with open(path, errors="replace") as f:
        lines = f.readlines()
    for n, kind, count in long_blocks(lines):
        print(f"{path}:{n}: warning: {kind} of {count} words (limit {MAX_BULLET if kind == 'bullet' else MAX_PARA}): split it")
        warned += 1
    if True:
        for n, line in enumerate(lines, 1):
            if FENCE.match(line):
                in_code = not in_code
                continue
            if in_code:
                continue
            text = CODE.sub("", line)
            for pat, why in TELLS:
                for m in re.finditer(pat, text):
                    print(f"{path}:{n}: {m.group(0)!r}: {why}")
                    hits += 1
    return hits

def self_test():
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):  # fixtures print their hits
        _self_test()
    print("self-test ok")

def _self_test():
    import tempfile, os
    good = "The report lists 12 open issues. Each has an owner.\n```\nx — y really\n```\n"
    bad = "Here's the thing: it's really seamless — not just fast, but also cheap.\n"
    for text, want in ((good, 0), (bad, 5)):
        global warned
        warned = 0
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as t:
            t.write(text)
        got = check(t.name)
        os.unlink(t.name)
        assert got == want and warned == 0, (text, got, want, warned)
    long_para, long_bullet = "word " * 81 + "\n", "- " + "word " * 36 + "\n"
    ok = "word " * 80 + "\n\n- " + "word " * 35 + "\n\n| " + "a " * 90 + "|\n\n```\n" + "word " * 99 + "\n```\n"
    for text, want in ((long_para, 1), (long_bullet, 1), (ok, 0), (long_para + "\n" + long_bullet, 2)):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as t:
            t.write(text)
        warned = 0
        assert check(t.name) == 0 and warned == want, (text[:20], warned, want)
        os.unlink(t.name)

if __name__ == "__main__":
    if sys.argv[1:] == ["self-test"]:
        self_test()
        sys.exit(0)
    if not sys.argv[1:]:
        sys.exit(__doc__)
    total = sum(check(p) for p in sys.argv[1:])
    print((f"{total} hit(s)" if total else "clean") + (f", {warned} length warning(s)" if warned else ""))
    sys.exit(1 if total else 0)
