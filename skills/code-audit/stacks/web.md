# Web app (Next.js, React, TypeScript)

## Extra facts for the brief

- The lint command and its ignore list. If it reads a build folder, the totals are false: lint `src` and `pages`
  with `-f json` into the scratch folder and run `eslint-by-rule.mjs` on that.
- Whether the repo has a unit test runner or only verification scripts.
- The dictionaries and their key separator. The proxy route, if the app reaches the backend through one.

## Sections

1. METRICS: type check errors, lint errors and warnings per rule with the autofix count, lines that silence a
   rule, largest files, longest components (`fn-length.mjs`).
2. REMOVE: files no page reaches (`import-graph.mjs`, or `knip`), dead chains reported as one set (action, type,
   reducer, consumer), unused exports checked against the verification scripts, packages never imported,
   translation keys (`unused-keys.mjs`, then the backend's messages), env variables against the example file.
3. SIMPLIFY: copied blocks (`jscpd`, 12 lines), helpers written several times (money parsers, date formatters),
   create and edit twins, store slices with one consumer, components defined inside components.
4. ASSUMPTIONS THAT NO LONGER HOLD: API paths against `routes.json` (`api-paths.mjs`), pages no menu or link leads
   to, leftovers of an earlier design (token storage, removed features), values the backend should compute that the
   app computes or re-sorts.
5. ANTI-PATTERNS: `any` and casts, API answers typed by a cast, effects that fetch with no cancel flag
   (`promise-scan.mjs`, then read the worst), state set in effects, index keys on lists that reorder, `<img>`,
   server-only code in the client bundle, money parsed with `parseFloat` and no check, personal data in browser
   storage or in a download.
6. TECHNIQUE STARTING NUMBERS: unhandled promises with a type-aware lint config kept in the scratch folder, what
   the error boundary records, errors under `noUncheckedIndexedAccess`, compiler rule warnings, bundle report.
7. PACKAGES: majors behind, minors, advisories, two libraries for one job.
8. TESTS: helper and class files no verification script names, the pure functions worth one check each.
9. TWIN DRIFT: shared files diffed with comments and imports stripped.

## False positives seen

- A service worker or a file in `public/` loaded by URL.
- Two files with one name: a dead component beside a live screen.
- A page with no link that holds the only path to a feature: file it as a missing link.
- Keys built from a prefix plus a server value (`user:entry:` plus a type).
- A floating promise on a helper that catches inside itself.
