// Drives a React Native debug app through Metro's debugger, with no screen taps: the iOS Simulator
// shows AppleScript no windows, so this is how the iOS walk is driven (works on Android too).
// It finds a mounted component by its text, label, placeholder or value and calls its handler.
//   node emu/rn.mjs <metroPort> texts                     every string on screen (find labels with it)
//   node emu/rn.mjs <metroPort> tap "<text or label>"     nearest onPress above the match
//   node emu/rn.mjs <metroPort> type "<label or value=…>" "<text>"   nearest onChangeText ("value=+1" finds a filled field)
//   node emu/rn.mjs <metroPort> scroll <y>                first ScrollView to y
//   node emu/rn.mjs <metroPort> go <RouteName>            navigate a navigator that has that route
//   node emu/rn.mjs <metroPort> eval "<js expression>"    anything else
// Needs a debug build and Node 22+ (global WebSocket). Screenshot with `xcrun simctl io booted screenshot x.png`.
const [port, cmd, a, b] = process.argv.slice(2);
const targets = await (await fetch(`http://localhost:${port}/json/list`)).json();
const target = targets.find((t) => /Hermes|Bridgeless|React Native/i.test(t.title + ' ' + (t.description || ''))) || targets[0];
if (! target) { console.error('no debugger target'); process.exit(1); }

const body = (want, value, mode) => `(function(){
  var hook = globalThis.__REACT_DEVTOOLS_GLOBAL_HOOK__;
  if (!hook || !hook.getFiberRoots) return 'no devtools hook';
  var roots = [];
  hook.renderers.forEach(function(_, id){ hook.getFiberRoots(id).forEach(function(r){ roots.push(r); }); });
  var want = ${JSON.stringify(want)}, mode = ${JSON.stringify(mode)}, out = [];
  function text(f){ var p = f.memoizedProps; if (typeof p === 'string') return p; if (!p) return '';
    return [p.accessibilityLabel, p['aria-label'], p.placeholder, typeof p.value === 'string' ? 'value=' + p.value : '', typeof p.children === 'string' ? p.children : ''].filter(Boolean).join(' | '); }
  function walk(f, visit){ while (f) { if (visit(f)) return true; if (f.child && walk(f.child, visit)) return true; f = f.sibling; } return false; }
  var result = 'not found: ' + want;
  roots.forEach(function(root){
    walk(root.current, function(f){
      var t = text(f), p = f.memoizedProps;
      if (mode === 'texts') { if (t && f.tag === 6) out.push(t); return false; }
      if (mode === 'scroll') { var s = f.stateNode; if (s && typeof s.scrollTo === 'function') { s.scrollTo({ y: Number(want), animated: false }); result = 'scrolled'; return true; } return false; }
      if (mode === 'go') { var n = p && p.navigation; if (n && n.getState && n.getState().routeNames.indexOf(want) >= 0) { n.navigate(want); result = 'went to ' + want; return true; } return false; }
      if (!t || t.indexOf(want) < 0) return false;
      for (var g = f; g; g = g.return) {
        var q = g.memoizedProps || {};
        if (mode === 'tap' && typeof q.onPress === 'function') { q.onPress({ nativeEvent: {} }); result = 'pressed: ' + t; return true; }
        if (mode === 'type' && typeof q.onChangeText === 'function') { q.onChangeText(${JSON.stringify(value)}); result = 'typed into: ' + t; return true; }
      }
      return false;
    });
  });
  return mode === 'texts' ? out.join('\\n') : result;
})()`;

const ws = new WebSocket(target.webSocketDebuggerUrl, { headers: { Origin: 'http://localhost:' + port } });
ws.onopen = () => ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate',
  params: { expression: cmd === 'eval' ? a : body(cmd === 'texts' ? '' : a, b, cmd), returnByValue: true } }));
ws.onmessage = (m) => { const r = JSON.parse(m.data); if (r.id !== 1) return;
  console.log(r.result?.result?.value ?? JSON.stringify(r.result ?? r.error)); ws.close(); process.exit(0); };
setTimeout(() => { console.error('timeout'); process.exit(1); }, 20000);
