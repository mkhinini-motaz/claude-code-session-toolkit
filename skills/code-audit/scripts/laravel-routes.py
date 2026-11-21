#!/usr/bin/env python3
"""laravel-routes.py <routes.json> [--surface NAME=DIR[,DIR]]... [--apps DIR...] [--tests DIR]

routes.json comes from `php artisan route:list --json`.

1. Routes no app can call: a static segment of the route's path appears in no string of the apps that
   own its surface (`api/<surface>/...`, mapped with --surface; other routes are checked against every
   app). A strong candidate only: confirm in tests, deployment scripts, simulators and outside callers
   (webhooks, public pages) before calling a route dead.
2. With --tests: routes whose path no test names. A proxy for coverage when no coverage driver is installed.
"""
import json, re, subprocess, sys, collections, os

args = sys.argv[1:]
if not args: sys.exit(__doc__)
routes = json.load(open(args[0])); routes = routes if isinstance(routes, list) else routes['routes']
surfaces, apps, tests, i = {}, [], None, 1
while i < len(args):
    if args[i] == '--surface': name, dirs = args[i + 1].split('='); surfaces[name] = dirs.split(','); i += 2
    elif args[i] == '--tests': tests = args[i + 1]; i += 2
    elif args[i] == '--apps':
        i += 1
        while i < len(args) and not args[i].startswith('--'): apps.append(args[i]); i += 1
    else: sys.exit('unknown argument ' + args[i])

def source(directory, pattern):
    files = subprocess.run(['git', '-C', directory, 'ls-files'], capture_output=True, text=True).stdout.split('\n')
    return '\n'.join(open(os.path.join(directory, f), errors='ignore').read() for f in files if re.search(pattern, f) and os.path.isfile(os.path.join(directory, f)))

every = sorted(set(apps + sum(surfaces.values(), [])))
text = {d: source(d, r'^(src|pages|app|lib)/.*\.(tsx?|jsx?|mjs|dart|kt|swift)$') for d in every}
api = [r for r in routes if r['uri'].startswith('api/')]

if every:
    strong = []
    for r in api:
        parts = r['uri'].split('/'); surface = parts[1] if len(parts) > 1 else ''
        owners = surfaces.get(surface, every)
        tail = '/'.join(parts[2:] if surface in surfaces else parts[1:])
        missing = [s for s in re.split(r'/|\{[^}]+\}', tail) if s and not any(re.search(r'[\'"`/]' + re.escape(s) + r'(?![\w-])', text[d]) for d in owners)]
        if missing: strong.append((r, missing))
    print(f'{len(api)} api routes; {len(strong)} have a path segment that no owning app names:')
    for r, missing in sorted(strong, key=lambda x: x[0]['uri']):
        print(f"  {r['method'][:6]:6} {r['uri']:62} missing={missing}  {r.get('action') or ''}")

if tests:
    body = source(tests, r'^tests/.*\.php$')
    edge_l, edge_r = r'(?<![\w-])', r'(?![\w-])'
    def named(uri):
        tail = re.sub(r'^api/', '', uri); pieces = [p.strip('/') for p in re.split(r'\{[^}]+\}', tail) if p.strip('/')]
        rx = r'[^\n]{0,120}?'.join(edge_l + re.escape(p) + edge_r for p in pieces)
        rx += r'/?(?:\{\$|\$\w|\d|[\'"]\s*\.|%[ds])' if tail.rstrip('/').endswith('}') else r'(?!/[\w${])'
        return re.search(rx, body)
    own = [r for r in api if (r.get('action') or '').startswith('App')]
    unnamed = [r for r in own if not named(r['uri'])]
    total = collections.Counter(r['uri'].split('/')[1] for r in own); miss = collections.Counter(r['uri'].split('/')[1] for r in unnamed)
    print(f'\n{len(unnamed)} of {len(own)} routes are named by no test; per surface: ' + ', '.join(f'{s} {miss[s]}/{total[s]}' for s in total))
    writes = [r for r in unnamed if not r['method'].startswith('GET')]
    print(f'of those, {len(writes)} write (POST, PUT, PATCH, DELETE):')
    for r in writes: print(f"  {r['method'][:6]:6} {r['uri']}")
