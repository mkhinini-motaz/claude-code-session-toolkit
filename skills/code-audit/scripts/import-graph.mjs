#!/usr/bin/env node
// import-graph.mjs <repo> [--entry <path prefix>]...
// Lists tracked code files that no entry point reaches, largest first, with their importers.
//   UNREACHED  nothing imports it, or only unreached files do (a dead chain: report the chain as one set)
//   TEST-ONLY  only tests or verification scripts reach it
// Entry points: files at the repo root, pages/, app/, src/pages/, src/app/, public/, scripts/, bin/, plus every --entry prefix.
// Heuristic: string imports only. Read a file before calling it dead (dynamic paths, native config, CLI use).
import fs from 'fs'; import path from 'path'; import { execSync } from 'child_process';
const args = process.argv.slice(2); const repo = path.resolve(args[0] || '.');
const extra = []; for (let i = 1; i < args.length; i++) if (args[i] === '--entry') extra.push(args[++i]);
const CODE = /\.(tsx?|jsx?|mjs|cjs)$/;
const TEST = /(^|\/)(__tests__|__mocks__|jest|tests?|verification|e2e)\/|\.(test|spec)\.[cm]?[jt]sx?$|(^|\/)jest[.\w-]*\.[cm]?js$/;
const ENTRY = ['pages/', 'app/', 'src/pages/', 'src/app/', 'public/', 'scripts/', 'bin/', ...extra];
const files = execSync(`git -C "${repo}" ls-files`, { maxBuffer: 1e9 }).toString().split('\n')
  .filter(f => CODE.test(f) && fs.existsSync(path.join(repo, f)));
const set = new Set(files);
const SUFFIX = ['', '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.native.ts', '.native.tsx', '.android.ts', '.android.tsx',
  '.ios.ts', '.ios.tsx', '.web.ts', '.web.tsx', '/index.ts', '/index.tsx', '/index.js', '/index.jsx'];
function resolve(from, spec) {
  let bases;
  if (spec.startsWith('.')) bases = [path.normalize(path.join(path.dirname(from), spec))];
  else if (/^[@~]\//.test(spec)) bases = ['src/' + spec.slice(2), spec.slice(2)];
  else return [];
  const out = [];
  for (const b of bases) for (const s of SUFFIX) if (set.has(b + s)) out.push(b + s);
  return out;
}
const IMPORT = /(?:\bfrom\s*|\bimport\s*\(\s*|\brequire\(\s*|jest\.(?:mock|requireActual)\(\s*|\bimport\s+)['"]([^'"]+)['"]/g;
const imports = {}; const importers = {}; const lines = {};
for (const f of files) {
  const text = fs.readFileSync(path.join(repo, f), 'utf8'); lines[f] = text.split('\n').length; imports[f] = new Set();
  for (const m of text.matchAll(IMPORT)) for (const r of resolve(f, m[1])) { imports[f].add(r); (importers[r] ||= new Set()).add(f); }
}
const reach = roots => { const seen = new Set(); const stack = [...roots];
  while (stack.length) { const f = stack.pop(); if (seen.has(f)) continue; seen.add(f); for (const g of imports[f] || []) stack.push(g); }
  return seen; };
const isTest = f => TEST.test(f);
const isEntry = f => !isTest(f) && (!f.includes('/') || ENTRY.some(p => f.startsWith(p)));
const live = reach(files.filter(isEntry)); const tested = reach(files.filter(isTest));
const dead = files.filter(f => !live.has(f) && !isTest(f) && !f.endsWith('.d.ts')).sort((a, b) => lines[b] - lines[a]);
console.log(`${files.length} code files, ${live.size} reached from entry points, ${dead.length} not reached (${dead.reduce((n, f) => n + lines[f], 0)} lines)`);
for (const f of dead) {
  const by = [...(importers[f] || [])].map(g => g + (live.has(g) ? '' : isTest(g) ? ' (test)' : ' (unreached)'));
  console.log(`${String(lines[f]).padStart(5)}  ${tested.has(f) ? 'TEST-ONLY' : 'UNREACHED'}  ${f}${by.length ? '  <- ' + by.join(', ') : ''}`);
}
