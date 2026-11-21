# Phone app (React Native, TypeScript)

## Extra facts for the brief

- Run the suite once with `--coverage --coverageReporters=json-summary` into the scratch folder, then
  `coverage-unloaded.mjs`. Without `collectCoverageFrom`, the percentage counts loaded files only.
- Which packages the native build and the Babel config use without a JavaScript import (config readers,
  worklets, screens). They are not unused.
- Integration tests that need a running backend, and what runs them.

## Sections

1. METRICS: type check, lint per rule with autofix count, suite result on a clean tree, coverage over loaded
   files and the count of files no test loads, largest files.
2. REMOVE: files no navigator or import reaches, leftovers of the app this repo was copied from (forms, alerts,
   store, language screen), type shims that hide installed types, type files for packages not installed, packages
   never imported, translation keys.
3. SIMPLIFY: the same query key written in several files, server data held in two places, copied blocks, money
   parsers, a query client with no defaults (the library retries refusals three times).
4. ASSUMPTIONS THAT NO LONGER HOLD: API paths against `routes.json`, screens registered and reachable from no
   menu, sums and sorting the backend should own, single-tenant logic, stale comments and repo guide lines.
5. ANTI-PATTERNS: unhandled promises (type-aware lint from a scratch config), the session write at sign-in not
   awaited, background work (location, sockets, timers) not stopped at sign-out, swallowed errors, components
   defined in render, index keys, long lists rendered with `.map`.
6. DATA ON THE DEVICE: where tokens live (keychain only), which personal data is written to plain storage, when it
   is cleared, console calls that reach release builds.
7. TECHNIQUE STARTING NUMBERS: unhandled and misused promises, error boundary, typed navigation, errors under
   `noUncheckedIndexedAccess`, end-to-end flows.
8. PACKAGES: majors behind, advisories, libraries used by one or two files.
9. TESTS: real failures separated from tests that time out under parallel load (rerun alone), tests that read
   source text instead of running code, money and session logic with no test.
10. TWIN DRIFT: shared classes diffed against the web twin.

## False positives seen

- Jest setup mocks and native-only packages reported as unreached or unused.
- A suite reported red because lint, type check and tests ran at once: rerun the failing files alone.
- A claim that a key is never invalidated, when the key is a shared constant.
- Tracking or socket cleanup that lives in another file than the one read.
