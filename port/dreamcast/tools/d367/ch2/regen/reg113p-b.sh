# reg113p-b.sh (Git Bash): ps2cast convch2.sh + nativech2.sh replay for one preset (lane ch2regen)
set -euo pipefail
P=${1:?preset}; TREE=${2:-t-ecf2a44a}
L=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261017r/ch2regen
T=$L/$TREE/port/dreamcast/tools
O=$L/ps2cast/conv-ch2
LOG="/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch2regen/logs"; mkdir -p "$LOG"
export PS2CAST_INPUTS=$L/ps2cast/inputs-ch2
export RE4_CAST_BUNDLE=$L/tools/cast_bundle.py
python "$T/ps2_cast.py" convert "$P" "$O/$P" --ps2-iso "C:/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso" > "$LOG/convert-$P.txt" 2>&1 || { echo "$P convert FAIL"; tail -6 "$LOG/convert-$P.txt"; exit 1; }
echo "$P convert ok"
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- env PS2CAST_HOSTCHECK=/root/probe/lanes-20261017r/ch2regen/ps2cast/host-check2 PS2CAST_HOST_WORKSPACE_KB=${KB:-512} bash /root/probe/lanes-20261017r/ch2regen/$TREE/port/dreamcast/tools/ps2_cast_native.sh /root/probe/lanes-20261017r/ch2regen/ps2cast/conv-ch2/$P > "$LOG/native-$P.txt" 2>&1 || { echo "$P native FAIL"; tail -5 "$LOG/native-$P.txt"; exit 1; }
python "$T/ps2_cast.py" finish "$O/$P" > "$LOG/finish-$P.txt" 2>&1 || { echo "$P finish FAIL"; tail -4 "$LOG/finish-$P.txt"; exit 1; }
echo "$P native+finish ok"
