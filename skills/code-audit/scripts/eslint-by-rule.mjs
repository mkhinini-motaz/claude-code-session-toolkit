#!/usr/bin/env node
// eslint-by-rule.mjs <eslint.json>
// Counts per rule from `npx eslint . -f json -o <scratch>/eslint.json`, with how many `--fix` would clear,
// the worst file per rule, and the count of eslint-disable comments ESLint reports as unused.
import fs from 'fs';
const report = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); const rules = {}; let errors = 0, warnings = 0;
for (const file of report) for (const m of file.messages) {
  const r = (rules[m.ruleId || '(parse or config)'] ||= { n: 0, err: 0, fix: 0, files: {} });
  r.n++; if (m.severity === 2) { r.err++; errors++; } else warnings++; if (m.fix) r.fix++;
  r.files[file.filePath] = (r.files[file.filePath] || 0) + 1;
}
console.log(`${errors} errors, ${warnings} warnings, ${Object.keys(rules).length} rules, ${report.filter(f => f.messages.length).length} files`);
console.log('count  errors  autofix  rule  (worst file)');
for (const [name, r] of Object.entries(rules).sort((x, y) => y[1].n - x[1].n)) {
  const [worst, n] = Object.entries(r.files).sort((x, y) => y[1] - x[1])[0];
  console.log(`${String(r.n).padStart(5)}  ${String(r.err).padStart(6)}  ${String(r.fix).padStart(7)}  ${name}  (${worst.split('/').slice(-2).join('/')} ${n})`);
}
