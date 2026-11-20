# emu

Drives the Android emulator from the shell, so a coding agent can walk an app: read the screen, tap by label, wait for a screen, take a screenshot. Everything goes through `adb`.

## Install

    ./install.sh emu    # copies the folder to ~/.claude/emu; call ~/.claude/emu/emu

Keep the files together: `emu` is a one-line wrapper around `ui.py`.

## Usage

`EMU=<adb serial>` picks the device (default `emulator-5554`) for `emu`, `ui.py`, `gps.sh`, `storelang.sh` and `demo.sh`. `python3 emu/ui.py self-test` checks the text escaping without a device.

    emu dump                      visible text and content-desc with centre coordinates
    emu tap TEXT [N]              tap the Nth element whose text contains TEXT
    emu wait TEXT [SECONDS]       wait until TEXT is on screen
    emu go X Y TEXT | go LABEL TEXT   tap until TEXT is on screen
    emu ready TEXT [SECONDS]      wait for TEXT with no bundle download or ANR dialog in the way
    emu xy X Y | type TEXT | key BACK | swipe X1 Y1 X2 Y2 [MS] | hidekb | fontscale 1.3
    emu shot NAME                 screenshot to shots/NAME.png beside the script
    emu clean                     dismiss React Native dev overlays and set the demo status bar
    emu mark / emu errors         clear logcat at the start of a walk; at the end print app crashes, JS errors and ERROR lines of the server logs named by `EMU_LOG_GLOB` (a glob such as `~/work/api/logs/*.log`)

Helpers:

- `demo.sh`: clean status bar for filming (12:30, full battery and signal).
- `gps.sh LAT LNG [LAT2 LNG2 STEPS]`: a GPS fix every 4 s, walking to a second point.
- `storelang.sh LANG PACKAGE [KEY]`: sets the language an app saved in its AsyncStorage (debug build, through `run-as`, app stopped). KEY defaults to `selected_lang`. It assumes async-storage v3 (database `AsyncStorage`, table `Storage`); v1 and v2 use `RKStorage` and `catalystLocalStorage`. The copy of the app's storage it makes is deleted when the script ends.
- `rn.mjs PORT texts|tap|type|scroll|go|eval ...`: drives a React Native debug app through Metro's debugger with no screen taps; usage at the top of the file. Needs Node 22+.

## Notes

- Never `pkill` a running `emu`: it orphans the on-device uiautomator and later dumps hang. Run `adb shell pkill -f uiautomator`.
- A dump takes 5 to 15 s on a slow emulator. Back with no keyboard showing leaves the screen; `hidekb` presses it only while the keyboard is up.
- `go` and `clean` tap at x=996 to close the React Native warning toast; change it for another screen width.
- Some apps blank screenshots (secure window); walk those with `dump` coordinates only.
- No self-test: every command needs a running emulator.

## Requirements

`adb`, Python 3, an emulator. `storelang.sh` also needs `sqlite3`.
