#!/bin/bash
set -euo pipefail
SCR=/root/work/lanes/dedup-offline23-main
export JOBS=1 SOURCE_DATE_EPOCH=1760000000
build_control(){
    local TR=$1 SHA=$2 LP=$3
    local O=/root/probe/lanes/route/out-${LP}rW
    local T=$TR/port/dreamcast/tools/d367
    local P="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/programs/candidate-route${LP}rW"
    case "$LP" in dd23af09off|dd23e17off) ;; *) exit 2;; esac
    [ "$(git -C "$TR" rev-parse HEAD)" = "$SHA" ]
    [ -z "$(git -C "$TR" status --porcelain)" ]
    [ ! -e "$O" ] && [ ! -e "$P" ]
    [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 24696061952 ]
    mkdir -p "$SCR/$LP-k"
    exec 9>"$SCR/$LP-tree.lock";flock -n 9
    . "$T/rr/recipe.conf"
    # QA labels are held fixed across the candidate and baseline identity arms.
    # Actual tree SHA remains independently recorded by the standard builder.
    K="$SCR/$LP-k" T="$TR" LP="$LP" CH2="$CH2" \
      XON='SCENERY_DEDUP=0 QA_MENU=1 WARP_AFTER_RESET=1 WORLD_METER=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 QA_TEST=23-DD3 QA_SRC=af09f0a2' \
      bash "$T/ch2/ch2-build.sh" rW
    [ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ]
    printf 'CONTROL_LINK_COMPLETE source=%s output=%s\n' "$SHA" "$O"
    exec 9>&-
}
exec > >(tee "$SCR/controls-build-launch.log") 2>&1
build_control /root/work/lanes/dedup-offline23-off af09f0a2bfd32f2ecc29bda6a71a1de42bcf2b34 dd23af09off
build_control /root/work/lanes/dedup-offline23-base e17af64a696778198474b1053cc8a37084eb2c3b dd23e17off
TOOL=/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy
for arm in dd23af09off dd23e17off;do
    "$TOOL" -R .stack -O binary "/root/probe/lanes/route/out-${arm}rW/re4dc-game.elf" "$SCR/${arm}-identity.bin"
done
cmp "$SCR/dd23af09off-identity.bin" "$SCR/dd23e17off-identity.bin"
sha256sum "$SCR/dd23af09off-identity.bin" "$SCR/dd23e17off-identity.bin" > "$SCR/OFF-IDENTITY.sha256"
printf 'ACTUAL_TARGET_KNOB_OFF_IDENTITY_PASS\n'
