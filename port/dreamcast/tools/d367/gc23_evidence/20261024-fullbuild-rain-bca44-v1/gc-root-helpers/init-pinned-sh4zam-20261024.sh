#!/usr/bin/env bash
set -euo pipefail
TREE=/root/work/lanes/gc-port23
MODULE=port/dreamcast/game/third_party/sh4zam
exec 7>"/tmp/d367-build-$(printf %s "$TREE" | md5sum | cut -c1-12).lock"
flock -n 7 || exit 2
[ "$(git -C "$TREE" rev-parse HEAD)" = 1d63cffe3a232c402418f2f2d919e7abae476957 ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
[ "$(git -C /root/work/lanes/rr/$MODULE rev-parse HEAD)" = 33fa4850cacb30dd0ad35485ef035526ec4ce782 ]
git -C "$TREE" submodule update --init --reference /root/work/lanes/rr/$MODULE "$MODULE"
[ "$(git -C "$TREE/$MODULE" rev-parse HEAD)" = 33fa4850cacb30dd0ad35485ef035526ec4ce782 ]
[ -z "$(git -C "$TREE/$MODULE" status --porcelain)" ]
[ -z "$(git -C "$TREE" status --porcelain)" ]
printf 'Pinned SH4ZAM initialized; source and submodule clean\n'