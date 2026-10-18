set -euo pipefail
W=/root/probe/lanes-20261018/ch3gate/pe
D=/root/re4data/private/ps2enemy-ch34-20261018
C="/mnt/c/Game Dev/Emulators/re4-assets-private/ps2enemy-ch34-20261018"
P2=/root/re4data/private/ps2enemy-ch2-20261016
mkdir -p "$D/PE3" "$D/PE4" "$D/esl-gc" "$D/esl-ps2"
cp "$W"/PE3/* "$D/PE3/"; cp "$W"/PE4/* "$D/PE4/"; cp "$W"/gc/etc/*.esl "$D/esl-gc/"; cp "$W"/ps2/*.esl "$D/esl-ps2/"
cat > "$D/README.txt" <<'R'
PRIVATE generated game data (lane ch3gate 2026-10-18). Regenerated after the 10-17 wipe:
PE3 = ps2_enemy_ch3.py (origin/t15/int) -> was /root/probe/lanes-20261015/castle/private-include (header sha a422def7 = recorded 10-15T05:30)
PE4 = ps2_enemy_ch4.py (origin/t15/int) -> was /root/probe/lanes-20261016/ch4found/private-include (header sha 35c2af87 = recorded 10-16T23:33)
Inputs: esl-gc = GC debug disc 1 FST etc/emleon0N.esl raw; esl-ps2 = PS2 USA ISO BIO4DAT AFS emleon0N.esl raw.
Use: ch4-build.sh PE3=<this>/PE3 PE4=<this>/PE4. Never commit or publish.
R
touch "$D/KEEP"
(cd "$D" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
if [ ! -e "$P2" ]; then mkdir -p "$P2"; cp "/mnt/c/Game Dev/Emulators/re4-assets-private/ps2enemy-ch2-20261016"/* "$P2/"; touch "$P2/KEEP"; fi
(cd "$P2" && sha256sum -c SHA256SUMS)
mkdir -p "$C"; cp -r "$D"/. "$C/"
(cd "$C" && sha256sum -c --quiet SHA256SUMS && echo C-COPY-OK)
