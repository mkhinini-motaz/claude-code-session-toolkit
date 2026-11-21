# plain-prose

A skill that removes AI-writing tells from prose people will read later (docs, READMEs, reports, plans, marketing copy), plus `check.py`, a script that flags the tells it can find as words: em dashes, throat-clearing, filler phrases, and over-long paragraphs and bullets. Rules about meaning still need a read-through.

Adapted from `stop-slop` by Hardik Pandya (MIT): see `NOTICE`.

## Install

    ./install.sh plain-prose     # copies the folder to ~/.claude/skills/plain-prose

## Usage

    ~/.claude/skills/plain-prose/check.py <file>...    # file:line: phrase: reason; exit 1 on any hit
    ~/.claude/skills/plain-prose/check.py self-test

Code blocks and inline code are skipped. Do not run it in a hook or pre-commit: a hit there would block a commit over style.

## Requirements

Python 3.
