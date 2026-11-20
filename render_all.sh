#!/bin/bash
# render every story that has no video yet, two at a time
cd "$(dirname "$0")"
ls ${@:-stories/*.json} | while read f; do n=$(basename $f .json); [ -f out/$n.mp4 ] || echo $f; done |
  xargs -P 2 -I{} sh -c 'node render.js {} > /dev/null 2>&1 && echo "done {}" || echo "FAIL {}"'
echo ALL RENDERED
