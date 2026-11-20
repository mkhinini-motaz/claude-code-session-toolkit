#!/usr/bin/env node
// api-paths.mjs <routes.json> <repo> [--prefix api/v1]... [--src <dir>]...
// Path literals the app passes to its HTTP client that match no backend route.
// routes.json: `php artisan route:list --json` (or any array of {uri, method}).
// --prefix: the surfaces this app may call; the first one is the app's base path and is stripped.
// A path built by concatenation is checked piece by piece: a piece passes when some route holds it as whole segments.
// So this finds paths that cannot exist. It does not prove the rest are right: say so in the report.
import fs from 'fs'; import path from 'path'; import { execSync } from 'child_process';
const a = process.argv.slice(2); const routesFile = a[0]; const repo = path.resolve(a[1] || '.');
const prefix = [], src = []; for (let i = 2; i < a.length; i += 2) (a[i] === '--prefix' ? prefix : src).push(a[i + 1]);
if (!src.length) src.push('src', 'pages', 'app');
const raw = JSON.parse(fs.readFileSync(routesFile, 'utf8')); const all = Array.isArray(raw) ? raw : raw.routes;
const norm = u => ('/' + u).replace(/\/+/g, '/').replace(/\{[^}]+\}/g, '{}').replace(/\/$/, '');
const routes = new Set();
for (const r of all) { if (prefix.length && !prefix.some(p => r.uri.startsWith(p))) continue;
  routes.add(norm(r.uri)); for (const p of prefix) if (r.uri.startsWith(p)) routes.add(norm(r.uri.slice(p.length))); }
const list = [...routes];
const files = execSync(`git -C "${repo}" ls-files ${src.map(s => `"${s}"`).join(' ')}`, { maxBuffer: 1e9 }).toString().split('\n')
  .filter(f => /\.[cm]?[jt]sx?$/.test(f) && !/\.(test|spec)\./.test(f) && fs.existsSync(path.join(repo, f)));
const found = new Map();
for (const f of files) fs.readFileSync(path.join(repo, f), 'utf8').split('\n').forEach((line, i) => {
  if (!/(axios|fetch\(|http|request|URL|\.(get|post|put|patch|delete)\()/.test(line)) return;
  for (const m of line.matchAll(/[`'"](\/[a-zA-Z][\w\/${}.\-]*)[`'"?]/g)) {
    const u = norm(m[1].replace(/\$\{[^}]*\}/g, '{}')); if (u.length > 2 && !found.has(u)) found.set(u, `${f}:${i + 1}`); }
});
const ok = u => list.some(r => (r + '/').includes(u + '/'));
const bad = [...found].filter(([u]) => !ok(u));
console.log(`${list.length} route shapes, ${found.size} path literals, ${bad.length} match no route`);
for (const [u, where] of bad) console.log(`${u}  ${where}`);
