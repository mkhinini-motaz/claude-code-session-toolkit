# Contributing

Ways to help, easiest first. Everyone who takes part follows the [code of conduct](CODE_OF_CONDUCT.md).

## 1. Report a bug

Open the "Bug" issue form. Name the tool, your OS, the command and its output. Remove tokens, paths with your name and private transcript text first.

## 2. Port a tool to Linux

The README says most scripts assume macOS: `/private/tmp/claude-<uid>/` scratchpads, BSD `stat` and `date`, `sips` and the keychain. Each tool's README lists what it needs under Requirements. Open the "Port" issue form to claim a tool. Keep macOS working, and prefer a fallback over a rewrite.

## 3. Propose a new tool

Open the "New tool" issue form first. A tool is one folder with a README and no shared code. To add one:

1. Create the folder, with a README that has a Requirements section.
2. Add a row to the table in `README.md`.
3. Add the tool name to `TOOLS` in `install.sh`, and a `files()` entry that lists what it copies. If it is a hook, add a `snippet()` entry too.
4. Give it a self-test, add the command to the test list in `AGENTS.md`, and add the same command to `.github/workflows/tests.yml`.
5. A test that writes state must point it at a scratch dir, never your `~/.claude`.

## Adding or changing a skill

Format: https://agentskills.io/specification. `.github/check-skills.py` checks it in CI.

- `name` is 1-64 characters (a-z, 0-9, single hyphens) and equals the folder name.
- `description` says what the skill does and when to use it. Put the use case first: the listing cuts the description at 1,536 characters. The hard limit is 1,024.
- Keep `SKILL.md` under 500 lines. Put details in `references/`.
- A skill with side effects sets `disable-model-invocation: true`.

## Bump the version

When you change anything a skill or the agent, raise `version` in `.claude-plugin/plugin.json`. Installed copies update only when the version rises.

## Pull request process

- Open the "New tool" issue form first for new work, so two people do not start the same thing.
- One change per PR.
- Use a Conventional Commits title, for example `fix: ...` or `docs: ...`.
- By contributing you agree your work is MIT licensed.

## AI-assisted changes

AI help is fine. You must be able to explain the change yourself. Say in the PR which parts an AI wrote. Run the checks yourself, do not rely on the AI's word that they pass.

## Before you open a PR

Run the checks in `AGENTS.md` from the repo root, under a scratch home:

```
export HOME=$(mktemp -d) SL_STATE=$(mktemp -d)
bash agent-watch/tests/agent-watch.test.sh
bash compact-restore/tests/compact-restore.test.sh
sh notes/tests/docs-limits.test.sh
sh bg/bg --self-test
bash tests/install.test.sh
bash status-line/tests/price-fit.test.sh
claude plugin validate .
python3 .github/check-skills.py code-audit harness-audit notion-task-pages plain-prose
```

Then each tool's own self-test. The full list is in `AGENTS.md`, and the same list runs in CI (`.github/workflows/tests.yml`).

- [ ] The tests in `AGENTS.md` pass, under a scratch `HOME`.
- [ ] `claude plugin validate .` passes if you touched a skill or the agent.
- [ ] `check-skills.py` passes (command above).
- [ ] I raised `version` if I changed a skill or the agent.
- [ ] A new tool has its README row, `install.sh` entry, `AGENTS.md` line and CI line.
- [ ] No secrets, tokens, real names or private data in fixtures, logs or screenshots.
- [ ] `install.sh` still never edits `settings.json`.
