#!/bin/bash
# storelang.sh LANG PACKAGE [KEY] - set an app's saved language in its AsyncStorage, app stopped.
# KEY is the storage key the app reads its language from (default selected_lang). Debug builds only.
set -e
[ $# -ge 2 ] || { sed -n 2,3p "$0"; exit 2; }
PKG=$2; KEY=${3:-selected_lang}
A="adb -s ${EMU:-emulator-5554}"
cd "$(dirname "$0")"; mkdir -p rk; rm -f rk/*
trap 'rm -rf rk' EXIT  # the copy holds the app's whole storage
V=${1//\'/\'\'}; K=${KEY//\'/\'\'}  # double quotes for SQL
$A shell am force-stop $PKG
for f in AsyncStorage AsyncStorage-wal AsyncStorage-shm; do $A exec-out "run-as $PKG cat databases/$f" > rk/$f; done
sqlite3 rk/AsyncStorage "PRAGMA wal_checkpoint(TRUNCATE); INSERT OR REPLACE INTO Storage(key, value) VALUES ('$K', '$V');" >/dev/null
$A push rk/AsyncStorage /data/local/tmp/AsyncStorage >/dev/null
$A shell "run-as $PKG sh -c 'rm -f databases/AsyncStorage-wal databases/AsyncStorage-shm; cp /data/local/tmp/AsyncStorage databases/AsyncStorage'"
$A shell rm /data/local/tmp/AsyncStorage
echo "$KEY=$1"
