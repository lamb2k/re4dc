set -uo pipefail
cd /root/work/re4-dreamcast
git cat-file -t 64ce974e
git log --all --oneline -- port/dreamcast/tools/d367/st3firstpass/codex-tools-8bf46efe-st3.diff | head
B=$(git log --all --format=%H -1 -- port/dreamcast/tools/d367/st3firstpass/codex-tools-8bf46efe-st3.diff)
git ls-tree -r --name-only $B port/dreamcast/tools/d367/st3firstpass port/dreamcast/tools/d367/ch5found 2>/dev/null | head -80
git branch -r --contains $B | head
