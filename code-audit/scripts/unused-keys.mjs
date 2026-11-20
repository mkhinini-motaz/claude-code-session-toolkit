#!/usr/bin/env node
// unused-keys.mjs <repo> --dict <file.json> [--dict ...] [--src <dir>]... [--sep :] [--out <file>]
// Translation keys that no string literal names and no dynamic prefix ('order:status:' + x, `a:${b}`) covers.
// Nested dictionaries are flattened with --sep (default ":"); flat ones pass through.
// Before listing a key as unused: it may be a message value the API returns. Grep the API for it.
import fs from 'fs'; import path from 'path'; import { execSync } from 'child_process';
const a = process.argv.slice(2); const repo = path.resolve(a[0] || '.');
const opt = { dict: [], src: [], sep: ':', out: null };
for (let i = 1; i < a.length; i += 2) { const k = a[i].slice(2); Array.isArray(opt[k]) ? opt[k].push(a[i + 1]) : (opt[k] = a[i + 1]); }
if (!opt.dict.length) { console.error('give at least one --dict'); process.exit(2); }
if (!opt.src.length) opt.src = ['src', 'pages', 'app'];
const flat = (o, p = '', out = []) => { for (const k in o) { const key = p ? p + opt.sep + k : k;
  o[k] && typeof o[k] === 'object' ? flat(o[k], key, out) : out.push(key); } return out; };
const keys = new Set(); for (const d of opt.dict) flat(JSON.parse(fs.readFileSync(path.resolve(repo, d), 'utf8'))).forEach(k => keys.add(k));
const files = execSync(`git -C "${repo}" ls-files ${opt.src.map(s => `"${s}"`).join(' ')}`, { maxBuffer: 1e9 }).toString().split('\n')
  .filter(f => /\.[cm]?[jt]sx?$/.test(f) && fs.existsSync(path.join(repo, f)));
const text = files.map(f => fs.readFileSync(path.join(repo, f), 'utf8')).join('\n');
const literals = new Set();
for (const m of text.matchAll(/(['"`])((?:\\.|(?!\1)[^\\\n])*)\1/g)) literals.add(m[2].replace(/\$\{[^}]*\}/g, '\u0000'));
const prefixes = [...new Set([...literals].filter(l => /[:._-]$/.test(l) || l.includes('\u0000')).map(l => l.split('\u0000')[0])
  .filter(p => p.length > 3 && /[:._-]/.test(p)))];
const unused = [...keys].filter(k => !literals.has(k) && !prefixes.some(p => k.startsWith(p)));
console.log(`${keys.size} keys, ${files.length} source files, ${prefixes.length} dynamic prefixes, ${unused.length} keys no code names`);
const groups = {}; for (const k of unused) { const g = k.split(opt.sep)[0]; groups[g] = (groups[g] || 0) + 1; }
console.log('by first segment: ' + Object.entries(groups).sort((x, y) => y[1] - x[1]).slice(0, 15).map(g => g.join(' ')).join(', '));
if (opt.out) { fs.writeFileSync(opt.out, unused.join('\n') + '\n'); console.log('list written to ' + opt.out); }
else console.log(unused.slice(0, 40).join('\n'));
