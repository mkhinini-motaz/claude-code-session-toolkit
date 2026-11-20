# Brief skeleton for one repo agent

Fill every `<...>`. Paste the numbered sections of the stack file under SECTIONS. Keep the whole brief under
about 9,000 characters: the agent re-reads it on every call.

```
GOAL
Read-only audit of <repo path> (<one line: what the repo is>). Find unnecessary complexity, duplicate logic,
assumptions that no longer hold, anti-patterns for this stack, outdated packages and missing tests. Every finding
needs evidence: file:line, a count, or the command that shows it.

KNOWN FACTS (do not rediscover)
- HEAD <sha> on <branch>. Dirty files, someone else's work, do not report: <list or "none">.
- Stack: <versions>. Scripts: <the lint, type check and test commands>. Test runner: <name or "none">.
- Size: <files> files, <lines> lines under <dirs>. Largest: <three files>.
- Backend routes: <path to routes.json>. Twin repo: <path or "none">.
- Product rules that apply here: <three to six lines>.

DECIDED, never recommend
<the declined ideas and standing decisions, one per line>

LIMITS
- Read-only. No edit, no commit, no install into the repo, no server, no real .env file, no secret value printed.
- Scratch folder for raw output: <scratchpad>/audit-<repo>/. Config files for extra lint rules go there too.
- Outside this audit: <what other checks already cover, such as accessibility or design>.
- Stop after about 70 tool calls. Report what is unchecked instead of rushing it.

SECTIONS (number them in the report)
<sections from stacks/<stack>.md>

EXPLICIT QUESTIONS (answer each with YES or NO and the evidence)
<the suspicions of the main thread, lettered a, b, c>

RETURN FORMAT
- Reply text, not a file. At most <220> lines. Numbered sections as above, then the lettered answers.
- Tag each finding [read] when you opened the code, [script] when only a script reported it.
- Full paths for any file name that exists twice in the repo.
- End with NOT CHECKED and the list of raw files in the scratch folder.

DONE WHEN
Every section has numbers or "not measured, because ...". No recommendation contradicts DECIDED.
```

## Notes on filling it

- EXPLICIT QUESTIONS carry what the earlier audits found, so each new repo is checked for the same defect. From an
  earlier run: an unawaited session write at sign-in, sums or sorting made in the
  app, personal data kept on the device, a leftover from the app a repo was copied from, a red test suite on a clean tree.
- Name the twin's shared files and ask for a diff with comments and imports stripped.
- An agent given your hypothesis tends to confirm it. Phrase a suspicion as a question with both outcomes named.
