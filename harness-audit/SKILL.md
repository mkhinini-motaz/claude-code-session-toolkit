---
name: harness-audit
description: Audit how you work with Claude Code and propose changes to the setup around it. Finds recurring mistakes, repeated work, unreliable or unused harness parts and token cost from local session history. Read-only. Ends with a ranked report and builds nothing. Run it yourself with /harness-audit [days].
disable-model-invocation: true
argument-hint: "[days] [--project NAME] [--notes FILE]"
arguments: [days]
allowed-tools:
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/collect.py *)
  - Read(~/.claude/**)
  - Edit(./harness-audit-*/**)
---

# Harness audit

Audit how I work with Claude Code and propose changes to the setup around it. Four
outcomes matter equally: fewer corrections, less repeated work, more consistent and
reliable results, lower token cost. Change nothing: the run ends with a report and
my choice of what to build first.

**Run without me.** Ask nothing during the run. Where you would ask, take the
cautious default, record the assumption in the report and continue.

## Scan result

!`python3 ${CLAUDE_SKILL_DIR}/scripts/collect.py scan $ARGUMENTS`

If the block above is empty, says shell execution is disabled, or reports a
background task, run `python3 ${CLAUDE_SKILL_DIR}/scripts/collect.py scan $ARGUMENTS` yourself,
or wait and read `harness-audit-<date>/summary.txt`.

## The collector

Flags go before the command: `--project NAME|PATH` limits every command to one project folder under `~/.claude/projects` (default: all projects; env `HARNESS_AUDIT_PROJECT` does the same), `--notes FILE` reads an optional notes file.

One script does the counting, so you write none. It reads local transcripts and
setup, sends nothing anywhere, and wrote `data.json`, `summary.txt` and, when an
`/insights` report existed, `insights.txt` into `harness-audit-<date>/`.

| Command (prefix each with `python3 ${CLAUDE_SKILL_DIR}/scripts/collect.py`) | Use |
|---|---|
| `show KEY [KEY ...]` | One part of `data.json` by dot path: `coverage`, `tokens.by_week_model_thread`, `tokens.top_sessions`, `tokens.by_subagent_type`, `tools`, `skills`, `friction.counts`, `friction.pointers.<kind>`, `sessions`, `setup.instruction_files`, `setup.skills`, `setup.agents`, `setup.settings` |
| `excerpt FILE LINE [N]` | Up to 30 compact, redacted records around a flagged line |
| `checks [since] [name]` | Re-run the report's counts in one call (leftopen, nudges, fanouts, askme, preamble, blocked, context, repeats, recipes) for turns after `since` (UTC, e.g. 2026-11-16T12:55); `scan --notes FILE` also puts `session_notes` in `data.json`; `selftest` checks the record shapes |
| `prompts FILE [MAX]` | Up to 60 prompts I typed in one session, redacted |
| `prompts-all [days]` | Every prompt I typed in the window, all sessions, redacted, one per line in `harness-audit-<date>/prompts.tsv`; read it with Read in slices or grep it. This is the main source for A, B and F |

Budget, in place of my approval: at most 40 excerpts and 10 prompt lists (`prompts-all` counts as one). A question
that needs more stays open, and the report says so. Never open a transcript with
Read: single lines run to megabytes.

## Sources: command output first, substitute second

Built-in commands are the source of record, but you cannot run them. When their
output is pasted after this skill or sits on disk, quote its number, name the
command and do not recompute. Otherwise use the collector's substitute and label
every figure from it "substitute for `/x`".

| Need | Command of record | Substitute |
|---|---|---|
| What loads on every call, with sizes | `/context all` | `setup.instruction_files`, plus the skill, agent and tool lists this session loaded; token figures are estimates |
| Usage share by skill, subagent, plugin, MCP server; cache misses | `/usage` | `tokens.*` |
| Context cost and use count per skill | `/skill-doctor` | `skills.*` and `setup.skills` |
| What I work on, friction, suggestions | `/insights` | `insights.txt` if present; else `sessions`, `friction.*`, `prompts` and `excerpt` |
| Setup faults, problems in instruction files | `/doctor`, `/doctor prompt-audit` | A bundled skill: invoke it if listed, diagnosis only; else review `setup` and the files by hand |

## Evidence rules

- Read from disk: instruction and rule files, memory index, settings, hooks, skills,
  agents, plugins, MCP servers. Say which project folder the audit covers.
- With no history at all, say so and stop. Do not audit from general knowledge.
- Decisions and measurements already recorded in memory, instruction files or notes
  are settled. Reopen one only with new evidence.
- If I passed `--notes FILE` (an optional end-of-session notes file: `## heading`, then `task:`, `corrections:`,
  `friction:`, `asked twice:` lines), read it before mining transcripts, and mine only for what it does not cover.
- A flagged turn is a candidate, not proof. Read a sample before counting and
  report how many were real. The correction pattern is English only and catches
  little, so read `prompts` for the sessions that matter.
- `rank_weight` orders sessions by rough relative cost. It is not money.
- Install nothing. Privacy: transcripts and reports stay on this machine, no outside
  service or web tool, and no secret or personal detail in the report.

## Known limits: account for them and state them

- `/insights` skips one-message, headless and empty sessions, and analyses up to 200 sessions it has not seen
  before (docs: code.claude.com/docs/en/costs.md). It counts a session as seen once
  `~/.claude/usage-data/session-meta/<id>.json` exists, analysed (`facets/<id>.json`) or not. To retry skipped
  sessions, move out the meta files that have no facet, run `/insights`, and it rewrites them. Its header shows analysed against total: give the
  share covered; the collector covers the rest. It sees this machine only.
- `/usage` covers 24 hours or 7 days, is approximate and local. A share is how much
  usage a row touches, not what a fix saves; shares can pass 100% in total.
- Name each command whose output was missing, and whether a substitute covered its
  question or the question stays open.
- Claude Code deletes transcripts and reports after `cleanupPeriodDays` (default
  30). `coverage` and `setup.settings` show the window and the setting: say how much
  history survived.
- The transcript format is internal and changes between versions. `coverage` shows
  parse failures and requests without usage: report both.
- Skill counts cover user and project skills. Plugin skill files on disk include
  disabled plugins, so take loaded plugin skills from this session's own list.
- Other devices and claude.ai chats are not covered.

## What to find

A named command means its output or its substitute.

**A. How I work.** From `/insights`, session titles and `prompts`: task types,
projects, habits. Add: what I expect from a result (format, depth, proof, tone,
where I push back) and instructions I keep repeating that no file records.

**B. Recurring mistakes.** From `/insights`: friction points, counts, examples.
From `friction`: corrections, repeated instructions, "continue" prompts, interrupts,
rejected or denied tool calls, error streaks, edit thrash, hook errors. Also look
for work reported done that was not. Note each sampled excerpt freely, group the
notes into categories, then count sessions, not messages. Class each category
against my setup: a rule existed and was broken; no rule; one-off. A problem that
stopped after its rule or hook was added is not a finding. Name Claude's own
recurring mistakes plainly.

**C. Repeated work.** From `/insights`, session titles and `tools.bash_heads`:
recurring task types and command sequences. Add: workflows, calculations, research
steps and deliverables rebuilt from nothing when an earlier version existed. No
judgment needed: script or hook. Judgment but the same steps: skill or template.
Fresh reasoning each time: leave it.

**D. The harness.** From `/doctor`, `/skill-doctor`, `/context all`, `setup` and
`friction` (hook errors, denial kinds): faults, weak instructions, unused skills
and agents, heavy items. Add: for each part (instructions, skills, scripts,
integrations, hooks, context management, delegation and model choice), what is
unreliable (not followed, never triggers, fails silently) and what is missing. Test
every always-loaded rule: relevant? followed? only restating the code or Claude's
defaults? stale? A rule costs tokens on every call, so it stays only if evidence
shows it changes behaviour.

**E. Token cost.** From `/usage`, `/context all`, `/skill-doctor` and `tokens`:
totals by week, model, thread and token class; shares by skill, MCP server and
subagent type; cache misses; the costliest sessions and why; item sizes. Look for an
expensive model doing cheap work, redundant calls and reads, and outputs longer than
the task needed.

**F. My habits that cost.** From `prompts-all` and `tokens.top_sessions`: what I do
that makes the work worse or dearer, each with counts and two examples. Look at least
for: sessions that run for days and change topic; large pastes (size in tokens, and what
happened to the context after); secrets pasted into chat; broad "do all" requests with no
budget or first slice; ambiguous answers ("yes" to a two-part question); asking "is it
done?" (a sign the replies do not say what is left). For each, say what I should do
instead in one line, and whether a prompt hook, a rule or nothing should advise me at the
moment it happens. Check that advice already in place (a hook or a rule) fires and is
followed, the way B checks rules.

## Valuing a finding

- Gain, in the unit that fits: corrections prevented per week, my turns or minutes
  saved, the same task giving the same result, or tokens.
- Cost: effort to build, upkeep, what it adds to every call.
- Token findings: a low and a high figure with the assumption that separates them;
  overlapping savings counted once. Give tokens by class and share of the measured
  total. Add money at API list price only if you can name the price list.
- Model and delegation findings: cost per finished task, rework included. A cheaper
  route that causes one more correction is not a saving.
- Mark every number: command (name it), collector key (name it), or estimate
  (basis).

## Proposals: built-in first

Name the built-in that already does it: `/usage` fix shortcut, `/doctor` fixes,
`/skills` to switch a skill off, `/mcp` to disable a server,
`/fewer-permission-prompts`, `/memory`, `/effort`, `/model`, compaction
instructions, hooks, skills, subagents. Go custom only where none fits, and say
which you ruled out. Prefer removing over adding, and a hook or script over a rule.

## Report

Write `report.md` in the `harness-audit-<date>/` folder the scan created.

1. Coverage and limits: what came from a command, what from a substitute, what
   stays unseen, and every assumption made in place of asking me. List the commands
   I should run myself to replace substitutes with real figures.
2. Working profile: preferences, expectations, recurring priorities, each backed by
   an observation; what memory lacks and what my behaviour contradicts.
3. Findings A to F, ranked by frequency and impact, a real example each. For B,
   two examples per category, so I can dispute it.
4. Roadmap grouped as quick wins; skills and templates; scripts and tools; harness
   and context; persistent instructions; longer-term automation. Per entry:
   problem, change, frequency, gain, effort, priority. Rank across groups by
   return, feasibility and lasting effect.
5. Top five, each with: what changes and why, benefits and drawbacks; the narrowest
   home that covers it (hook, script, skill, path-scoped rule, project file, user
   file, memory); a draft or the exact built-in command; and the proof: today's
   number and its source, the same measurement re-run on a named date, the movement
   expected, the result that means revert. For a skill, a with-and-without
   comparison (`claude plugin eval` or skill-creator). For a rule, three to five
   replay prompts from real failed turns, one where it must not fire, each run
   more than once.
6. Rejected ideas, one line each.
7. Next audit: when to re-run, whether retention should be longer, whether a short
   end-of-session note would replace transcript mining.

Do not pad the list and do not cap it.

## Boundaries

Read-only except the report folder. Do not create, install, enable or edit skills,
scripts, hooks, settings, memory or instruction files, and do not apply a fix a
command or skill proposes. End in chat with the report path, the top five
findings in one line each, then every other roadmap item in one line each. Build nothing until I name one.
