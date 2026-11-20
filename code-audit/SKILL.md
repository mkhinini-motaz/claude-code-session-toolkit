---
name: code-audit
description: Audit one repo or several for dead code, duplicate logic, stale assumptions, anti-patterns, outdated packages and missing tests. Every finding carries evidence and the smallest change that keeps behaviour. Read-only. Run by hand with /code-audit <repo|all> [focus].
disable-model-invocation: true
argument-hint: "[repo|all] [focus]"
arguments: [target, focus]
allowed-tools:
  - Bash(node ${CLAUDE_SKILL_DIR}/scripts/*)
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)
  - Read(${CLAUDE_SKILL_DIR}/**)
---

# Code audit

Audit `$target` (a repo folder, or `all`), with `$focus` as an optional narrower question. The audit reads and
measures. It edits no repo file, commits nothing and changes no server. Each finding ends as a proposal the owner
accepts or declines.

Built from a multi-repo audit in which agents read the repos and used about 35M input tokens in total.
The lessons of that run are the rules below.

## 1. Scope and cost, before any agent

- Start with one repo, the backend if there is one. The other repos are judged against it (routes, events, rules).
- Order for `all`: the backend first, then the clients that call it.
- One repo agent costs 1.9M to 6.5M input tokens (median 4.0M), 25 to 68 tool calls and 4 to 9 minutes. Filing the
  findings from the main thread costs about as much again. State that cost before three or more agents start.
- Check free disk before a run that installs packages or builds coverage.

## 2. Facts sweep, in the main thread

One Bash batch per repo. The result goes into the brief as KNOWN FACTS, so the agent does not spend calls on it.

- HEAD, branch, and the dirty files. List dirty files as "someone's work in progress, do not report".
- File and line counts under the source folders, the largest files.
- Runtime and framework versions, the scripts of `package.json` or `composer.json`, the test runner, the linters
  installed, the CI workflows.
- For a backend: export the route list once (`php artisan route:list --json > routes.json`). Every client app audit
  reuses that file.
- Which tools are on the machine (`knip`, `jscpd`, `shellcheck`, coverage drivers). Never install a tool the
  permission system refused; record it as not measured.

## 3. The decided list

Collect what the owner already decided or declined: the `CLAUDE.md` files, the memory index, decision notes, archived
tasks. Put it in every brief under "DECIDED, never recommend". An audit that proposes a declined idea reads as
analysis and is noise.

After the reports arrive, search memory and the notes again for the subject of every High finding before filing it.
In one audit two "gaps" in the deployment report were choices the owner had made days earlier.

## 4. Scripts first

Run these from the main thread before or beside the agents. Each prints to stdout and changes nothing.

| Script | Usage | Finds | Known false positives |
| --- | --- | --- | --- |
| `import-graph.mjs` | `<repo> [--entry <prefix>]...` | files no entry point reaches | files loaded by URL, by native code or by a config string |
| `unused-keys.mjs` | `<repo> --dict <file.json>... [--src <dir>]... [--sep :]` | translation keys with no literal and no dynamic prefix | keys the backend sends as message values |
| `api-paths.mjs` | `<routes.json> <repo> [--prefix api/v1]...` | path literals that match no backend route | asset paths, the app's own proxy |
| `promise-scan.mjs` | `<repo> [--src <dir>]...` | async effects with no cancel flag, `.then` chains with no `.catch` | poll loops that clean up another way |
| `fn-length.mjs` | `<repo> [--top 15]` | the longest functions, with the repo's own TypeScript | one-component screens |
| `coverage-unloaded.mjs` | `<coverage-summary.json> <repo>` | source files no test loads | none: this is the honest coverage base |
| `eslint-by-rule.mjs` | `<eslint.json>` | counts per rule, autofix count, worst file | a lint run that reads a build folder |
| `laravel-routes.py` | `<routes.json> --surface NAME=DIR,DIR --tests <api repo>` | routes no owning app names, routes no test names | callers in infra, simulators, outsiders |
| `fk-check.php` | `php artisan tinker --execute="require '<path>';" < /dev/null` | `*_id` columns with no foreign key or index | polymorphic and external ids |
| `save-reports.py` | `<transcript.jsonl> <outdir> <agent-id>=<name>...` | saves each agent's hand-back as a file | none |

## 5. One agent per repo

- Agent type `session-toolkit:worker` (or `worker` when installed with `install.sh worker-agent`), model `sonnet`, read-only. A twin pair gets one agent per repo in the same message, and both
  briefs ask for the drift between the twins.
- Build the brief from `brief.md` plus the stack file under `stacks/` (`laravel`, `web`, `phone`, `relay`, `infra`).
- The report comes back as reply text: the harness refuses a subagent's report file. Save it at once with
  `save-reports.py`, then work from the saved file.
- Raw tool output goes to a scratch folder per agent. The report names the folder.
- While other agents run, a finished one gets a two-line note. The full answer comes once, after the last.

## 6. Verify before relaying

Recheck by grep or by running the command: every High finding, and at least one claim per report. Then mark each
finding "rechecked by hand" or "reported by the agent, not rechecked". Known ways a claim is wrong:

- A "dead" file that a page, a test, a verify script or a URL loads. Two files with the same name in different
  folders: always write the full path.
- A page nothing links to. It may be a missing link (a defect), not dead code.
- A gap that the deployment layer covers, or that the owner chose. A "default" that is a fallback read after a
  setting. A workflow that is not the path in use (builds may run from the laptop).
- A stated cause for a failing test. Rerun the test alone and read the assertion. Tests that time out only under
  parallel load are flaky, not red.
- Coverage percentages that count only the files a test loads.
- Translation keys used through a dynamic prefix or sent by the backend as a value.
- A route with "no caller" when paths are concatenated, or called by infra, tests, simulators or outsiders.
- An "unused" class wired by the framework (auto-registered commands, listeners, config strings), an "unused"
  package used by the native build or the Babel config.
- A claim about what the server returns, made from app code only.
- Money worries about float parsing. Test by exhaustion before reporting.

When a recheck of yours turns out wrong, correct the record where you wrote it and tell the owner plainly.

## 7. Judge each finding

- Sort into remove, simplify, refactor, or stale assumption. Give the evidence (`file:line`, a count, a command).
- Propose the smallest change that keeps behaviour. A change a user could notice (refusing input accepted today,
  a new error message) is an open question for the owner, never a silent part of a cleanup.
- A technique the code does not use (a lint rule set, an error boundary, a stricter compiler flag) gets a comparison
  task first, with the starting number measured today. Adopt only on a measured gain.
- Lint: record warnings per rule and the autofix count. Check that the lint run ignores build folders before
  trusting its total.
- Shared rules of the product (who computes what, who sees which personal data) are checked in every app: sums and
  sorting made in an app, personal data kept on a device, words the owner banned.

## 8. Report and file

The answer to the owner: what was checked and how, findings by weight with evidence, what was not checked, what
waits for a decision (one decision per question, with a recommendation).

In the task tracker: one parent task per audit, one sub-task per group of findings. Search for duplicates first,
archived tasks included, and read the body of any umbrella task in the same area. Update an existing task instead
of filing beside it. Each page separates what was rechecked from what was only reported.

## Hard limits

- No edit, commit, push or deploy. No code change without the owner's go, however small.
- Never open a real `.env` file. Never print a secret value in a report or a scratch file.
- Deployment repos: no cloud call, no `ssh`, no `terraform init`, `plan` or `apply`, no `compose up`. Linters run
  as one-off images on a read-only mount.
- No project code, logs or personal data to an outside service or a free model.
- A refused permission stays refused. Report the measurement as missing.
