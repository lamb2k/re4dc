set -euo pipefail
# texture-fit cache keys (6): try the vq_native_ui VQ of the PS2 world 16-bit sources; then search the shared cx outputs
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
T=$L/game-249effe5/port/dreamcast/tools
A=$L/tools/.assets
SRC="$A/rooms-r307/rooms/r307/tex/ac9a763b-01fab0d7.re4tex $A/rooms-r31d/rooms/r31d/tex/6f5596fa-bcdd36eb.re4tex $A/rooms-r329/rooms/r329/tex/844699db-67c782fb.re4tex $A/rooms-r329/rooms/r329/tex/9bcea162-37b9364f.re4tex $A/rooms-r303/rooms/r303/tex/0ea42407-77c3d299.re4tex $A/rooms-r303/rooms/r303/tex/39a44f1b-b2fb1c41.re4tex"
rm -rf "${L:?}/tfit"
cd /tmp; python3 $S/c5r_vqkeys.py $T $L/tfit $SRC | tail -6
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $L/tfit/out
for k in ac9a763b-01fab0d7 6f5596fa-bcdd36eb 844699db-67c782fb 9bcea162-37b9364f 0ea42407-77c3d299 39a44f1b-b2fb1c41; do
  find /root/re4data/private/cxfix-replay-20261018 "/mnt/c/Game Dev/Emulators/re4-assets-private/ch3regen-20261018" "/mnt/c/Game Dev/Emulators/re4-assets-private/ch4regen-20261018" -name "$k.re4tex" 2>/dev/null | head -2
done
