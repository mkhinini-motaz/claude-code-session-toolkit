#!/usr/bin/env node
// coverage-unloaded.mjs <coverage-summary.json> <repo> [--src src]
// A coverage percentage counts only the files a test loads. This lists the files no test loads at all,
// largest first, and the loaded files under 20% of lines. Make the summary with:
//   npx jest --coverage --silent --coverageReporters=json-summary --coverageDirectory=<scratch>/coverage
import fs from 'fs'; import path from 'path'; import { execSync } from 'child_process';
const a = process.argv.slice(2); const summary = JSON.parse(fs.readFileSync(a[0], 'utf8')); const repo = path.resolve(a[1] || '.');
const src = a[2] === '--src' ? a[3] : 'src';
const files = execSync(`git -C "${repo}" ls-files "${src}"`, { maxBuffer: 1e9 }).toString().split('\n')
  .filter(f => /\.[jt]sx?$/.test(f) && !f.endsWith('.d.ts') && !/\.(test|spec)\.|__tests__|__mocks__/.test(f) && fs.existsSync(path.join(repo, f)));
const lines = f => fs.readFileSync(path.join(repo, f), 'utf8').split('\n').length;
const cov = {}; for (const [k, v] of Object.entries(summary)) if (k !== 'total') cov[path.relative(repo, k)] = v;
const unloaded = files.filter(f => !cov[f]).map(f => [lines(f), f]).sort((x, y) => y[0] - x[0]);
const t = summary.total;
console.log(`reported: lines ${t.lines.pct}%, statements ${t.statements.pct}%, branches ${t.branches.pct}%, functions ${t.functions.pct}%`);
console.log(`${files.length} source files, ${files.length - unloaded.length} loaded by a test, ${unloaded.length} loaded by none (${unloaded.reduce((n, x) => n + x[0], 0)} lines)`);
console.log('largest files no test loads:'); for (const [n, f] of unloaded.slice(0, 15)) console.log(`${String(n).padStart(5)}  ${f}`);
const low = files.filter(f => cov[f] && cov[f].lines.pct < 20).map(f => [lines(f), f, cov[f].lines.pct]).sort((x, y) => y[0] - x[0]);
console.log(`loaded but under 20% of lines: ${low.length}`); for (const [n, f, p] of low.slice(0, 10)) console.log(`${String(n).padStart(5)}  ${f}  ${p}%`);
