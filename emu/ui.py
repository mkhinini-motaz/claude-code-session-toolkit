#!/usr/bin/env python3
"""Drive the Android emulator from the shell: read the screen, tap by label, wait, screenshot.
See README.md beside it. usage (EMU=<adb serial> to pick a device, default emulator-5554):
  ui.py shot NAME            screenshot to shots/NAME.png
  ui.py dump                 list visible text / content-desc with centre coordinates
  ui.py tap TEXT [N]         tap the Nth element whose text or content-desc contains TEXT
  ui.py wait TEXT [SECONDS]  wait until an element containing TEXT is on screen
  ui.py go X Y TEXT | go LABEL TEXT   tap until TEXT is on screen
  ui.py xy X Y               tap a point
  ui.py type TEXT            type into the focused field
  ui.py key KEYCODE          e.g. BACK, ENTER
  ui.py hidekb               hide the keyboard if it is showing (never navigates back)
  ui.py ready TEXT [SECONDS] wait for TEXT with no bundle download or ANR dialog in the way
  ui.py clean                dismiss the dev build's overlays and set the demo status bar
  ui.py swipe X1 Y1 X2 Y2 [MS]
  ui.py fontscale X          system font scale (1 normal, 1.3 largest before Android 14)
  ui.py mark                 start of a walk: clear logcat, remember the server logs' size
  ui.py self-test            check the text escaping, no device needed
  ui.py errors               errors since mark: app crashes and JS errors, plus ERROR lines of $EMU_LOG_GLOB files
"""
import os, re, subprocess, sys, time, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ADB = ['adb', '-s', os.environ.get('EMU', 'emulator-5554')]


def device_text(t):
    """`input text` goes through the device shell: backslash every shell character, spaces become %s."""
    return '%s'.join(re.sub(r'([^A-Za-z0-9_.,:@/+=-])', r'\\\1', w) for w in t.split(' '))


def sh(*args, **kw):
    return subprocess.run(ADB + list(args), capture_output=True, **kw)


def nodes():
    for _ in range(3):
        sh('shell', 'uiautomator', 'dump', '/sdcard/ui.xml')
        raw = sh('exec-out', 'cat', '/sdcard/ui.xml').stdout
        try:
            root = ET.fromstring(raw)
            break
        except ET.ParseError:
            time.sleep(1)
    else:
        sys.exit('could not dump the UI')
    out = []
    for n in root.iter('node'):
        label = n.get('text') or n.get('content-desc') or ''
        m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', n.get('bounds', ''))
        if not label.strip() or not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        out.append((label.strip(), (x1 + x2) // 2, (y1 + y2) // 2, n.get('clickable') == 'true'))
    return out


if len(sys.argv) < 2:
    sys.exit(__doc__)
cmd, args = sys.argv[1], sys.argv[2:]
if cmd == 'self-test':  # needs no device
    assert device_text("a b;c'd") == "a%sb\\;c\\'d" and device_text('x&y') == 'x\\&y'
    print('self-test ok')
elif cmd == 'shot':
    os.makedirs(os.path.join(HERE, 'shots'), exist_ok=True)
    path = os.path.join(HERE, 'shots', args[0] + '.png')
    open(path, 'wb').write(sh('exec-out', 'screencap', '-p').stdout)
    print(path)
elif cmd == 'dump':
    for label, x, y, c in nodes():
        print(f'{x:5d} {y:5d} {"*" if c else " "} {label[:90]!r}')
elif cmd == 'tap':
    want, nth = args[0].lower(), int(args[1]) if len(args) > 1 else 0
    hits = [n for n in nodes() if want in n[0].lower()]
    if len(hits) <= nth:
        sys.exit(f'no element matching {args[0]!r}')
    label, x, y, _ = hits[nth]
    sh('shell', 'input', 'tap', str(x), str(y))
    print(f'tapped {label!r} at {x},{y}')
elif cmd == 'wait':
    want, limit = args[0].lower(), float(args[1]) if len(args) > 1 else 30
    start = time.time()
    while time.time() - start < limit:
        if any(want in n[0].lower() for n in nodes()):
            print(f'found {args[0]!r} after {time.time() - start:.0f}s')
            break
        time.sleep(1)
    else:
        sys.exit(f'{args[0]!r} not on screen after {limit:.0f}s')
elif cmd == 'go':
    # tap a point, or the first element labelled args[0], until args[-1] shows (the app drops
    # taps while its JS thread is busy)
    target, want = args[:-1], args[-1].lower()
    start = time.time()
    while time.time() - start < 60:
        # the dev build's warning toast sits over the tab bar and swallows taps
        for label, x, y, _ in nodes():
            if 'Open debugger to view warnings' in label:
                sh('shell', 'input', 'tap', '996', str(y)); time.sleep(1); break
        if len(target) == 2 and target[0].isdigit():
            sh('shell', 'input', 'tap', *target)
        else:
            hits = [n for n in nodes() if target[0].lower() in n[0].lower()]
            if hits:
                sh('shell', 'input', 'tap', str(hits[0][1]), str(hits[0][2]))
        for _ in range(6):
            time.sleep(1)
            if any(want in n[0].lower() for n in nodes()):
                print(f'reached {args[-1]!r}'); sys.exit(0)
    sys.exit(f'never reached {args[-1]!r}')
elif cmd == 'xy':
    sh('shell', 'input', 'tap', *args)
elif cmd == 'type':
    sh('shell', 'input', 'text', device_text(args[0]))
elif cmd == 'ready':
    # wait until TEXT shows with no bundle download or ANR dialog in the way
    want, limit = args[0].lower(), float(args[1]) if len(args) > 1 else 180
    start = time.time()
    while time.time() - start < limit:
        labels = nodes()
        texts = ' | '.join(l[0] for l in labels).lower()
        if "isn't responding" in texts:
            for label, x, y, _ in labels:
                if label == 'Wait':
                    sh('shell', 'input', 'tap', str(x), str(y))
        elif 'downloading' not in texts and 'loading from' not in texts and want in texts:
            time.sleep(2); print(f'ready after {time.time() - start:.0f}s'); sys.exit(0)
        time.sleep(3)
    sys.exit(f'{args[0]!r} never ready')
elif cmd == 'clean':
    # dev-build overlays that must not reach a screenshot
    for label, x, y, _ in nodes():
        if label.startswith('Dismiss'):
            sh('shell', 'input', 'tap', str(x), str(y)); time.sleep(1)
        elif 'Open debugger to view warnings' in label:
            sh('shell', 'input', 'tap', '996', str(y)); time.sleep(1)
    subprocess.run(['bash', os.path.join(HERE, 'demo.sh')], capture_output=True)
elif cmd == 'hidekb':
    # Back only while the keyboard is up; with none showing, Back leaves the screen.
    shown = 'mInputShown=true' in sh('shell', 'dumpsys', 'input_method').stdout.decode()
    if shown:
        sh('shell', 'input', 'keyevent', 'KEYCODE_BACK')
elif cmd == 'key':
    sh('shell', 'input', 'keyevent', 'KEYCODE_' + args[0].upper())
elif cmd == 'fontscale':
    sh('shell', 'settings', 'put', 'system', 'font_scale', args[0])
elif cmd in ('mark', 'errors'):
    import glob, json
    logs = glob.glob(os.path.expanduser(os.environ.get('EMU_LOG_GLOB', '')), recursive=True) if os.environ.get('EMU_LOG_GLOB') else []  # server logs, e.g. daily files
    mark = os.path.join(HERE, 'shots', '.logmark')  # keep shots/ out of git
    if cmd == 'mark':
        sh('logcat', '-c')
        os.makedirs(os.path.dirname(mark), exist_ok=True)
        json.dump({f: os.path.getsize(f) for f in logs}, open(mark, 'w'))
    else:
        print(sh('logcat', '-d', 'ReactNativeJS:E', 'AndroidRuntime:E', '*:S').stdout.decode().strip() or 'logcat: no errors')
        seen = json.load(open(mark)) if os.path.exists(mark) else None
        bad = []
        for f in sorted(logs, key=os.path.getmtime):
            if seen is None and f != max(logs, key=os.path.getmtime):
                continue  # no mark: only today's file
            start = (seen or {}).get(f, 0)
            with open(f, errors='replace') as fh:
                fh.seek(start if start <= os.path.getsize(f) else 0)
                bad += [l.rstrip()[:300] for l in fh if ('ERROR' in l or 'CRITICAL' in l)]
        print('\n'.join(bad[-20:]) or ('server log: no errors' if logs else 'server log: EMU_LOG_GLOB not set'))
elif cmd == 'swipe':
    sh('shell', 'input', 'swipe', *args[:4], args[4] if len(args) > 4 else '400')
else:
    sys.exit(__doc__)
