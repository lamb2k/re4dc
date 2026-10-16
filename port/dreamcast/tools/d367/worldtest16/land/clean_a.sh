#!/bin/bash
# clean_a.sh (WSL): delete A's rebuildable outputs after the gates (disk hygiene rule); keep w16mrT (B stills use it).
M="/mnt/c/Game Dev/Emulators/worldtest-20261016/DELETED-20261016.txt"
P="/mnt/c/Game Dev/Emulators/re4-assets-private"
H="$P/world-agent-20260926/continuation-20260927/playability-r11-r1/programs"
# C5 experiment data kept privately (small) before its build dir goes
C5="$P/worldtest-20261016/r101-C5"; mkdir -p "$C5"
cp /root/probe/worldtest16-20261016/rooms/r101-C5/out/* /root/probe/worldtest16-20261016/rooms/r101-C5/job.log "$C5/"
(cd "$C5" && sha256sum * | grep -v SHA256SUMS > SHA256SUMS)
{
echo "## $(date '+%F %T') A landing done (t15/int 4d85debc): rebuildable outputs"
du -sh /mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/kos/_discs 2>/dev/null
echo "C:/Flycast-Evidence/re4-dreamcast/wt16land-20261016/kos/_discs (KOS/GDEMU twin master; rebuild: _tools/pk.sh)"
du -sh /root/probe/worldtest16-20261016/k/kos
echo "/root/probe/worldtest16-20261016/k/kos (package tree, rel tree, twin trees; rebuild: pk.sh)"
for l in w16mrP w16brP w16mmW fpw16sq2W fpw16sq2P; do
  [ -d /root/probe/lanes/route/out-$l ] && echo "/root/probe/lanes/route/out-$l (objdir) + programs/candidate-route$l"
done
echo "/root/probe/worldtest16-20261016/ref (worktree at 189ac886, identity reference)"
} >> "$M"
rm -rf /mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/kos/_discs /root/probe/worldtest16-20261016/k/kos
for l in w16mrP w16brP w16mmW fpw16sq2W fpw16sq2P; do rm -rf /root/probe/lanes/route/out-$l "$H/candidate-route$l"; done
cd /root/probe/worldtest16-20261016/tree && git worktree remove --force /root/probe/worldtest16-20261016/ref && echo "ref removed"
tail -12 "$M"
