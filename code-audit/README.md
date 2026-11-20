# code-audit

A read-only repo audit skill. It looks for dead code, duplicate logic, stale assumptions, anti-patterns, outdated packages and missing tests, and every finding carries evidence and the smallest change that keeps behaviour. It edits nothing, commits nothing and changes no server. You run it by hand: `/code-audit <repo|all> [focus]`.

- `SKILL.md`: the procedure (scope and cost, facts sweep, decided list, scripts first, one agent per repo, verify before relaying, judge, report).
- `brief.md`: the brief skeleton for one repo agent.
- `stacks/`: extra facts, report sections and known false positives for `laravel`, `web`, `phone`, `relay` and `infra` repos.
- `scripts/`: ten helpers that print to stdout and change nothing (import graph, unused translation keys, API paths against a route list, promise scan, function length, unloaded coverage files, ESLint counts per rule, route usage, missing foreign keys, saving agent reports). Usage table in `SKILL.md`.

## Install

    ./install.sh code-audit     # copies the folder to ~/.claude/skills/code-audit

## Requirements

Claude Code, Node for the `.mjs` scripts, Python 3 for the `.py` ones, PHP with Laravel for `fk-check.php`. `fn-length.mjs` loads `typescript` from the audited repo's own `node_modules`, so run `npm install` there first. The stack files are examples: edit them for your own stacks.
