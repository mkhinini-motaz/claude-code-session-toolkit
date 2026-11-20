#!/usr/bin/env node
// promise-scan.mjs <repo> [--src <dir>]...
// Two counts that need a read before they become findings:
//   1. useEffect bodies that await or .then() with no cancel flag and no AbortController
//   2. .then( chains with no .catch, no .finally and no second argument
// Heuristic: an effect whose promise only writes to a store, or a chain returned to a caller that catches, is fine.
import fs from 'fs'; import path from 'path'; import { execSync } from 'child_process';
const a = process.argv.slice(2); const repo = path.resolve(a[0] || '.');
const src = []; for (let i = 1; i < a.length; i += 2) src.push(a[i + 1]); if (!src.length) src.push('src', 'pages', 'app');
const files = execSync(`git -C "${repo}" ls-files ${src.map(s => `"${s}"`).join(' ')}`, { maxBuffer: 1e9 }).toString().split('\n')
  .filter(f => /\.[jt]sx?$/.test(f) && !/\.(test|spec)\./.test(f) && fs.existsSync(path.join(repo, f)));
const lineOf = (s, i) => s.slice(0, i).split('\n').length;
let effects = 0, asyncEffects = 0, cleanups = 0, thens = 0; const noCancel = [], noCatch = [];
for (const f of files) { const s = fs.readFileSync(path.join(repo, f), 'utf8');
  for (const m of s.matchAll(/use(?:Layout)?Effect\(/g)) { effects++;
    let j = m.index + m[0].length, depth = 1; while (depth > 0 && j < s.length) { const c = s[j++]; if (c === '(') depth++; else if (c === ')') depth--; }
    const body = s.slice(m.index, j);
    if (/return\s*(\(\)\s*=>|\(\)\s*\{|function|\w+\s*;)/.test(body)) cleanups++;
    if (/\.then\(|\bawait\b/.test(body)) { asyncEffects++;
      if (!/cancel|ignore|alive|active|mounted|abort|stale|disposed|\blive\b/i.test(body)) noCancel.push(`${f}:${lineOf(s, m.index)}`); } }
  for (const m of s.matchAll(/\.then\(/g)) { thens++;
    let i = m.index, depth = 0; for (; i < s.length; i++) { const c = s[i];
      if ('([{'.includes(c)) depth++; else if (')]}'.includes(c)) { if (--depth < 0) break; } else if (c === ';' && depth === 0) break; }
    const chain = s.slice(m.index, i);
    if (!/\.catch\(|\.finally\(/.test(chain) && !/^\.then\([^)]*=>[^]*\)\s*,\s*\(?\w*\)?\s*=>/.test(chain)) noCatch.push(`${f}:${lineOf(s, m.index)}`); } }
console.log(`effects ${effects}, with a cleanup ${cleanups}, async ${asyncEffects}, async with no cancel flag ${noCancel.length}`);
console.log(noCancel.join('\n'));
console.log(`\n.then( chains ${thens}, with no .catch or .finally in the same statement ${noCatch.length}`);
console.log(noCatch.join('\n'));
