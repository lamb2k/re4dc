#!/bin/bash
set -euo pipefail
SOURCE=/root/work/lanes/dedup-offline23-next
NEW=/root/work/lanes/dedup-offline23-memory-off
SHA=54240115d1949243752c7052d22db2c4e0308826
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
[ "$(git -C "$SOURCE" rev-parse HEAD)" = "$SHA" ]
[ ! -e "$NEW" ]
git -C "$SOURCE" worktree add --detach "$NEW" "$SHA"
git -C "$NEW" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
exec bash '/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/main-standard-memory-build-v3.sh' twin-off