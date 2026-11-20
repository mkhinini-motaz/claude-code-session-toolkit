# commit

A path-scoped commit for trees that several sessions edit at once. It stages only the paths you name, so another session's half-finished edits stay out of your commit.

    commit --by opus|sonnet|fable|haiku -m <msg> [-m <paragraph>...] [--session <url>] <paths...>

It runs `git add -N` on untracked files under the paths, then `git commit --only <paths>`, appends `Co-Authored-By: Claude <model> <noreply@anthropic.com>` and `Claude-Session: <url>`, and prints `git show --stat HEAD`. The session URL comes from `--session` or `https://claude.ai/code/$CLAUDE_CODE_BRIDGE_SESSION_ID`. If the committed files differ from the changed files under the paths (a hook or a rename pulled one in or out), it exits 1 and prints how to undo: `git reset --soft HEAD~1`. It refuses `.`, `*`, `-a`, `-A` and `-u`.

The model names in `MODELS` at the top of the script are labels; edit them to match the models you use.

## Install

    ./install.sh commit    # copies commit to ~/.claude/bin

## Usage

    ~/.claude/bin/commit --by sonnet -m "Fix the parser" src/parser.py tests/parser_test.py
    python3 commit/commit --self-test

## Requirements

Python 3, git.
