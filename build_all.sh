#!/bin/bash
# wait for the running image fetch, fetch again for any slot still empty, then render all
while pgrep -f fetch_images.py >/dev/null; do sleep 20; done
for f in stories/*.json; do python3 fetch_images.py "$f"; done
for f in stories/*.json; do n=$(basename "$f" .json); [ -f "out/$n.mp4" ] || node render.js "$f"; done
echo ALL DONE
