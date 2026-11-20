# worker-agent

A subagent definition for build, fix, test-and-fix and audit work. Compared with the default general-purpose agent it:

- compacts at 200k tokens instead of 400k (`autoCompactWindow`);
- runs on Sonnet unless the spawn passes `model` (for example opus for review);
- drops the tools that only the main thread needs (Agent, Artifact, plan mode, cron, user questions), which keeps about 3k tokens off every call;
- carries short working rules: a state file for compaction, short command output, no `sleep`, a hand-back format.

## Install

    ./install.sh worker-agent    # copies worker.md to ~/.claude/agents

Spawn it with `subagent_type: "worker"`. No hook.

## Usage

Edit the rules in `worker.md` to fit your repos. The rules point at `bg` and `commit` from this toolkit, and at a git guard that blocks `git stash` and `git checkout -- <path>` in shared trees; drop those lines if you do not use them.

## Requirements

Claude Code with custom agents. The `disallowedTools` names match one Claude Code version; remove any your version does not know.
