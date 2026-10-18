#!/bin/bash
cd /tmp
for r in "$@"; do echo "$r t"; echo "$r u"; done | xargs -P 3 -L 1 bash -c 'r=$0; a=$1; HARN=h-cx5${a}mW bash /c/tmp/ch5/run1t.sh $r walk s$a ${a}2 60 > /c/tmp/ch5/s-$r-$a.out 2>&1; echo "$r $a $(head -1 /c/tmp/ch5/s-$r-$a.out)"'
