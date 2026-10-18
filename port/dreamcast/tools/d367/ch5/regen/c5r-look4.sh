set -euo pipefail
cd /root/work/re4-dreamcast
for c in 8bf46efe 6b93fc4c 90606dcf 249effe5 2636b322; do printf '%s ' $c; git cat-file -t $c 2>/dev/null || echo missing; done
git branch -r | grep -iE 'st3|ch5|codex-ps2|island' | head -20
ls /mnt/c/Game\ Dev/Emulators/re4dc-recovery/gitdig18/ | head -40
ls -d /root/probe/codex-* 2>/dev/null
ls /root/probe/lanes-20261018/ch4regen | head -30
ls /root/probe/lanes-20261018/ch3regen | head -30
