#!/bin/sh
# Fast path for img-shrink.py: every Read in every session runs this hook twice, so Python starts only
# when the payload names an image. Measured by timing 20-30 calls a run, 3 runs: 32-42 ms for this fast path, 106-178 ms for Python alone.
in=$(cat)
case "$in" in
  *.[pP][nN][gG]\"*|*.[jJ][pP][gG]\"*|*.[jJ][pP][eE][gG]\"*|*.[wW][eE][bB][pP]\"*)
    printf '%s' "$in" | exec python3 "$(dirname "$0")/img-shrink.py" ;;
esac
