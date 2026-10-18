#!/bin/bash
set -uo pipefail
cd /root/work/re4-dreamcast
for b in wip/ch2regen-20261017 wip/ch3regen-20261018 wip/ch4regen-20261018 wip/regen17-20261017; do
  echo "== $b"; git log --oneline -2 "origin/$b"
  git ls-tree -r --name-only "origin/$b" | grep -i "regen" | grep -iE "gate|boot|harness|stag|flycast|run" | head -12
done
