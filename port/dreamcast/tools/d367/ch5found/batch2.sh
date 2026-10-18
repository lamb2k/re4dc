#!/bin/bash
# round 2 batch (Git Bash): 4 Flycast runs at a time, 60 s each, harness h-cx5cmW
cd /tmp
printf '%s\n' "$@" | HARN=h-cx5cmW xargs -P 4 -I{} bash -c 'bash /c/tmp/ch5/run1.sh {} walk r2 r2a 60 > /c/tmp/ch5/r2-{}.out 2>&1; echo "{} $(head -1 /c/tmp/ch5/r2-{}.out)"'
