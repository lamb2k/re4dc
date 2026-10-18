#!/bin/bash
# ch5regen gate (Git Bash): stage <room> on <arm>, 60 s Flycast boot, TEX_CHECK + CAST-GC + HALT/FAULT/MISSING summary,
# then delete the staged disc (scenario disc, capture link, lane disc cache copy). usage: c5r-gate1.sh <room> <arm>
set -euo pipefail
ROOM=${1:?room}; ARM=${2:?arm}
S=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5tex
SW=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5tex
E=/c/Flycast-Evidence/re4-dreamcast/ch5regen-20261018
H=$E/hroot/h
SC=$H/scenarios/c5t-$ROOM
D=$(MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash "$SW/c5t-stage1.sh" "$ROOM" "$ARM")
echo "$ROOM stage $D"
case "$D" in STAGED_PAYLOAD_IDENTITY_PASS*) ;; *) echo "$ROOM STAGE FAILED"; exit 1 ;; esac
DSHA=$(echo "$D" | awk '{print $2}')
echo "ch5regen gate $ROOM: arm $ARM, ch5tex fixture with rebuilt tex-ch5e d5986c3e, 60 s" > "$SC/PURPOSE.txt"
python "$H/run-emulator-novsync-i26.py" "c5t-$ROOM" --seconds 60 --period 30 > "$SC/run-stdout.txt" 2>&1 || true
C=$SC/capture
O=$C/run-output.txt
CG=$(MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- python3 /root/probe/lanes-20261018/ch5regen/game-249effe5/port/dreamcast/tools/d367/cast_gc.py "/mnt/c/Flycast-Evidence/re4-dreamcast/ch5regen-20261018/hroot/h/scenarios/c5t-$ROOM/capture/run-output.txt" --allow /root/probe/lanes-20261018/ch5regen/game-249effe5/port/dreamcast/tools/d367/castgc/allow.tsv 2>&1 | tail -1 | cut -c1-160)
echo "$CG" > "$SC/cast-gc.txt"
echo "$ROOM halt=$(grep -ac HALT "$O") fault=$(grep -ac FAULT "$O") missing=$(grep -ac 'RE4DC MISSING' "$O") texfail=$(grep -ac 'texchk: FAIL' "$O") leongc=$(grep -ac '^LEONGC f=' "$O") rooms=$(grep -aoE 'room enter [0-9a-f]+' "$O" | awk '{print $3}' | sort -u | tr '\n' ',') castgc=[$CG]" | tee "$SC/gate-summary.txt"
echo "$DSHA  disc.bin (deleted after run)" > "$SC/disc.sha256"
rm -f "$C/disc.bin" "$SC/disc/disc.bin"
rm -f "$E/disccache/$DSHA/disc.bin"
