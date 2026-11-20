# Laravel API

## Extra facts for the brief

- `php artisan route:list --json` saved once. `composer outdated --direct` and `composer audit`.
- The guards or surfaces (one per client app) and which app folders call each.
- Whether a coverage driver (pcov or Xdebug) is installed. Building one needs the owner's go.
- `php artisan tinker` needs `--execute` and `< /dev/null`, or it waits for input.

## Sections

1. METRICS: test count and result, static analysis level and baseline size, largest classes, longest methods.
2. REMOVE: routes no app, test, infra file or simulator names (run `laravel-routes.py`, then check each candidate
   by hand); classes with no reference outside tests; commands neither scheduled, called nor named in infra;
   config keys and env variables nothing reads.
3. SIMPLIFY: logic written in two places (controllers that repeat a repository, copied validation rules), one
   interface with one implementation, layers that only pass through.
4. ASSUMPTIONS THAT NO LONGER HOLD: single-tenant code, midnight or end-of-day resets, hard-coded
   ids, comments and docs that describe a removed design.
5. PRACTICE: PHP and Laravel conventions, SOLID where a class has several reasons to change, API design (verbs,
   status codes, envelopes, naming: note every plural or mixed route name).
6. DATABASE: N+1 reads on hot routes, `*_id` columns with no foreign key or index (`fk-check.php`), queries that
   need a cache, missing unique constraints behind a "check then insert".
7. QUEUE AND ERRORS: jobs dispatched inside a transaction without after-commit, static caches in the long-lived
   worker, missing retry or timeout settings, outbound HTTP with no timeout, broad `catch` blocks that hide a failure.
8. EXPOSURE: every response passes through a resource; each resource shows only what that role may see; rate
   limits per route group, with the routes that have none.
9. PACKAGES: majors behind, advisories, packages never imported.
10. TESTS: routes no test names, the write routes among them first; coverage only if a driver exists.
11. PERFORMANCE: the three slowest things a cheap change would fix, with the measurement.

## False positives seen

- A "dead" route called by a web proxy with a concatenated path, by the deployment smoke test or by the simulator.
- Scenario and simulator commands: unused by the product, used by the owner's test runs.
- A broad catch that logs and records a failed message is handling, not hiding.
- Swagger and health routes have no app caller by design.
