# Deployment repo (Compose, Caddy, Terraform, shell scripts)

## Extra facts for the brief

- The owner's infrastructure decisions: server size, managed services declined, regions allowed,
  what the cloud account refuses, what was dropped because of it.
- Which deploy path is in use today: CI workflows or commands run from the laptop. Judge the path in use first.
- Past incidents (a full disk, a failed deploy), so the audit checks they cannot repeat.
- How the owner wants infrastructure explained. For an owner with no operations background: by layer, with the
  reason for each part.

## Limits, on top of the general ones

No cloud call, no `ssh`, no `terraform init`, `plan` or `apply`, no `compose up`. Linters run as one-off images
with the repo mounted read-only: `shellcheck`, `hadolint`, `actionlint`, `trivy config`. `terraform fmt -check`
needs no init.

## Sections, by layer

1. ACCOUNT AND NETWORK: what is reachable from outside, who can sign in, how commands reach the server.
2. SERVER: size against the sum of the containers' memory limits, disk and what can fill it (logs with no
   rotation first), first-boot script.
3. CONTAINERS: health checks, what restarts a hung container, images pinned or floating, limits measured or guessed.
4. WEB ENTRY: TLS, request size limit, timeouts, rate limit, trusted proxy headers.
5. DATA: what the backup holds and what it leaves out (secrets, env files, cache, side databases), how old a
   restore can be, whether a restore was ever run, what is lost if the server dies now.
6. DEPLOY: test gate before a build, a dump before a migration, rollback and what it does not undo, two deploys
   at once, image tags.
7. WATCHING: what raises an alert and from where. Who is told when the whole server is down.
8. SCRIPTS AND DOCS: scripts that carry on after a failed step, copied helpers, scripts no command calls,
   hard-coded laptop paths, leftovers of dropped services, docs that describe the old setup.
9. DEFAULTS AGAINST REALITY: regions, domains and sizes in the files against what runs today.

## False positives seen

- "No outage alarm": an alarm left out on purpose and documented in the README.
- "Wrong default region": each default was a fallback read after a setting, kept for another account type.
- "No test gate in the build workflow": true, and the workflow was not the path in use. The laptop release
  command had the same gap, which was the finding to file.
- Linter findings that restate a decision (a database in a container, one server) are not findings.
- A proposal for an outside monitoring service when the owner keeps monitoring first-party: file the gap as a
  question instead.
