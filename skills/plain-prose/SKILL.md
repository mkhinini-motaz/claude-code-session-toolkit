---
name: plain-prose
description: Strip AI-writing tells from prose that people will read later: docs/notes, README and CLAUDE.md files, wiki pages, artifacts, reports, plans, and English or French marketing copy. Use when drafting or editing such text; runs a checker script on the file. Not for chat replies or code.
---

# Plain prose

Readers spot machine-written text by a handful of habits, and each one costs trust. This skill removes them from text that persists. Adapted from Hardik Pandya's `stop-slop` (MIT), keeping the rules that make text clearer and dropping the arbitrary ones (no adverbs at all, no sentence starting with a Wh- word, two items instead of three).

Chat replies are out of scope: this is for text that persists.

## Rules

1. **State the point first.** No throat-clearing ("Here's the thing", "It turns out", "Let me be clear") and no meta-commentary ("In this section we…", "As we'll see"). The text moves; it does not announce its own structure.
2. **Name the specific thing.** "The implications are significant" says nothing: write the implication. Replace "significant", "many" and "often" with the number when you have it.
3. **Name who acts.** Data does not tell, markets do not reward, decisions do not emerge: a person reads, buys, decides. Use the passive only when the actor is unknown or does not matter.
4. **Say the second half directly.** Drop the reflex contrast ("It isn't X, it's Y", "not just X but also Y") and the negative build-up ("Not a…, not a…, but a…"). Keep a contrast only when the reader holds the wrong belief.
5. **Plain words.** No leverage, seamless, robust, landscape, deep dive, unlock, delve, empower, streamline, game-changer. No intensifiers (really, truly, genuinely, fundamentally, crucially).
6. **No em dashes.** Use a colon, a comma, a full stop or brackets.
7. **No pull-quote endings.** A paragraph does not need a punchy last line. Do not stack short fragments for drama.
8. **Trust the reader.** No "and that's okay", no "think about it", no rhetorical question answered in the next sentence.
9. **Every number carries its unit:** TND, %, orders a day, minutes. A bare figure loses its meaning once the reader scrolls past the table header.
10. **Open a page with its answer** in one or two lines; detail follows. Cut repeated figures and side scenarios, and offer the long version instead of printing it.
11. **Explain technical work by what changes for the reader first,** then the mechanism.

## Check

After writing or editing the file, run:

```
${CLAUDE_SKILL_DIR}/check.py <file>...
```

It prints `file:line: phrase: reason` for each tell outside code, and exits 1 if it finds any. Rewrite each hit, or keep it when it is the plainest way to say the thing (a quoted title, a term of art). The script finds words, not meaning: rules 2, 3, 7, 9, 10 and 11 still need a read-through. `check.py self-test` proves the patterns.
