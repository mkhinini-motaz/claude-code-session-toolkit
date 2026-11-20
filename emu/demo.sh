#!/bin/bash
# Clean status bar for filming: 12:30, full battery, full signal, no notification icons.
A="adb -s ${EMU:-emulator-5554}"
d() { $A shell am broadcast -a com.android.systemui.demo -e command "$@" >/dev/null; }
$A shell settings put global sysui_demo_allowed 1
d enter; d clock -e hhmm 1230; d battery -e level 100 -e plugged false
d network -e wifi show -e level 4; d network -e mobile show -e datatype none -e level 4
d notifications -e visible false
