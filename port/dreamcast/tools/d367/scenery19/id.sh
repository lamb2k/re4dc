set -euo pipefail
OC=/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy
W=/root/work/lanes/scenery19-scratch/k/id; mkdir -p $W
A=/root/probe/lanes/route/out-a9brP; B=/root/probe/lanes/route/out-a9krP
$OC -O binary -R .stack $A/re4dc-game.elf $W/a.bin; $OC -O binary -R .stack $B/re4dc-game.elf $W/b.bin
sha256sum $W/a.bin $W/b.bin | cut -c1-16
cmp $W/a.bin $W/b.bin && echo IMAGE-SAME || echo IMAGE-DIFF
n=0; d=0; for o in $A/*.ovl; do n=$((n+1)); cmp -s $o $B/$(basename $o) || { d=$((d+1)); echo "DIFF $(basename $o)"; }; done; echo "overlays $n diff $d"
cmp -s $A/syms.txt $B/syms.txt && echo syms-same || echo syms-diff
for a in a9prP a9prT a9pmW a9phrW; do grep -c "ACTOR_PLAN=1" /root/probe/lanes/route/out-$a/candidate.txt | sed "s/^/$a ACTOR_PLAN=1 count /"; done
for a in a9krP a9krT a9kmW a9khrW; do grep -c "ACTOR_PLAN=1" /root/probe/lanes/route/out-$a/candidate.txt | sed "s/^/$a ACTOR_PLAN=1 count /" || true; done
grep -o "LEON_CLOTH_DRAWN=1\|PS2_HDR_SETS=128\|LEON_HEADLESS=1\|FX_MIST_PS2=1\|ROUTE_SOON_RETURN=1\|LEON_SKIN_SLOTS=2\|MOVIE_AUDIO_PRIME=1\|ROOM_LEFTOVER_FIT=1\|PS2_WORLD_SOURCE_TEX_VQ=1\|HAZE_SPRITE_CUT=1\|PS2_CH2_ENEMY=1" /root/probe/lanes/route/out-a9krP/candidate.txt | sort -u | tr '\n' ' '; echo
grep -o "PACE_MODE=off\|PC_SAMPLER_BYTES=8192" /root/probe/lanes/route/out-a9phrW/candidate.txt | sort -u | tr '\n' ' '; echo
