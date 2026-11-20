#!/usr/bin/env node
// fn-length.mjs <repo> [--src <dir>]... [--top 15]
// Longest functions and components, measured with the repo's own TypeScript parser.
import fs from 'fs'; import path from 'path'; import { execSync } from 'child_process'; import { createRequire } from 'module';
const a = process.argv.slice(2); const repo = path.resolve(a[0] || '.');
const src = []; let top = 15; for (let i = 1; i < a.length; i += 2) a[i] === '--top' ? (top = +a[i + 1]) : src.push(a[i + 1]);
if (!src.length) src.push('src', 'pages', 'app');
const ts = createRequire(path.join(repo, 'package.json'))('typescript');
const files = execSync(`git -C "${repo}" ls-files ${src.map(s => `"${s}"`).join(' ')}`, { maxBuffer: 1e9 }).toString().split('\n')
  .filter(f => /\.[jt]sx?$/.test(f) && !f.endsWith('.d.ts') && fs.existsSync(path.join(repo, f)));
const out = [];
for (const f of files) {
  const sf = ts.createSourceFile(f, fs.readFileSync(path.join(repo, f), 'utf8'), ts.ScriptTarget.Latest, true, /x$/.test(f) ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  (function visit(n) {
    if ((ts.isFunctionDeclaration(n) || ts.isArrowFunction(n) || ts.isFunctionExpression(n) || ts.isMethodDeclaration(n)) && n.body) {
      const from = sf.getLineAndCharacterOfPosition(n.getStart()).line, to = sf.getLineAndCharacterOfPosition(n.end).line;
      const name = n.name?.getText() || (n.parent && n.parent.name && n.parent.name.getText && n.parent.name.getText()) || '(anonymous)';
      out.push([to - from + 1, `${f}:${from + 1}`, name]); }
    ts.forEachChild(n, visit); })(sf);
}
out.sort((x, y) => y[0] - x[0]);
console.log(`${out.length} functions in ${files.length} files; over 150 lines: ${out.filter(x => x[0] > 150).length}; over 100: ${out.filter(x => x[0] > 100).length}; over 50: ${out.filter(x => x[0] > 50).length}`);
for (const [n, where, name] of out.slice(0, top)) console.log(`${String(n).padStart(5)}  ${where}  ${name}`);
