#!/bin/bash
set -euo pipefail
REPO=/root/work/lanes/dedup-offline23-integration
NEXT=/root/work/lanes/dedup-offline23-next
[ ! -e "$NEXT" ]
[ -z "$(git -C "$REPO" status --porcelain)" ]
BASE=$(git -C "$REPO" rev-parse origin/t15/int)
[ "$BASE" = 28da09802$(git -C "$REPO" rev-parse origin/t15/int | cut -c10-) ]
git -C "$REPO" worktree add -b wip/dedup-offline23-next-20261023 "$NEXT" af09f0a2bfd32f2ecc29bda6a71a1de42bcf2b34
git -C "$NEXT" merge --no-edit "$BASE"
git -C "$NEXT" push -u origin wip/dedup-offline23-next-20261023
git -C "$NEXT" rev-parse HEAD
git -C "$NEXT" status --short
