set -uo pipefail
cd /root/work/re4-dreamcast
git log --all --oneline -- port/dreamcast/tools/build_ps2_assets.py | head
ls /root/probe/lanes-20261018/ch4regen/cxtree-b47/port/dreamcast/tools/build_ps2_assets.py /root/probe/lanes-20261018/ch4regen/cxtree-*/port/dreamcast/tools/ps2_assets 2>&1 | head
G=/root/probe/lanes-20261018/ch4regen/cxarchive.git
[ -d $G ] && git -C $G log --all --oneline -- port/dreamcast/tools/build_ps2_assets.py | head
[ -d $G ] && git -C $G for-each-ref --format='%(refname)' | grep -i ps2 | head
ls /mnt/c/Users/Public/ps2/DVD/ 2>&1 | head
