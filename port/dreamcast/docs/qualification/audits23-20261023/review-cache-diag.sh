set -euo pipefail
review_repo=/root/work/lanes/audits23
review_sha=59b6d8225cf49de184e33d7a70d0e1c8d239be34
review_ram=$(mktemp -d /dev/shm/audits23-review-XXXXXX)
git -C "$review_repo" archive "$review_sha" port/dreamcast/tools/d367/kos_cache_audit port/dreamcast/patches/kos-804b319-cache-p2.patch port/dreamcast/game/ui_bridge.cpp port/dreamcast/game/kos_cache_p2.mk port/dreamcast/game/platform/kos_cache_p2_diag.cpp port/dreamcast/game/platform/include/kos_cache_p2_diag.h port/dreamcast/docs/KOS_CACHE_P2_DIAG_20261023.md | tar -x -C "$review_ram"
review_git=$(git -C "$review_repo" rev-parse --absolute-git-dir)
printf 'gitdir: %s\n' "$review_git" >"$review_ram/.git"
PYTHONDONTWRITEBYTECODE=1 python3 "$review_ram/port/dreamcast/tools/d367/kos_cache_audit/test_cache_diag.py" >"$review_ram/controls.log" 2>&1
cat "$review_ram/controls.log"
printf 'RAM_REVIEW=%s\n' "$review_ram"
