#!/bin/bash
# Feed the emulator a GPS fix every 4 s. usage: gps.sh LAT LNG [LAT2 LNG2 STEPS]
# With a second point, walks from the first to the second in STEPS fixes and then stays there.
A="adb -s ${EMU:-emulator-5554}"
lat=$1; lng=$2; lat2=${3:-$1}; lng2=${4:-$2}; steps=${5:-1}
i=0
while true; do
  f=$(python3 -c "import sys; lat,lng,lat2,lng2,i,steps=map(float,sys.argv[1:]); t=min(i/steps,1); print(f'{lng+(lng2-lng)*t:.6f} {lat+(lat2-lat)*t:.6f}')" "$lat" "$lng" "$lat2" "$lng2" $i "$steps")
  $A emu geo fix $f >/dev/null 2>&1
  i=$((i+1)); sleep 4
done
