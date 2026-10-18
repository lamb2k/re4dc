set -euo pipefail
# c3g-pe.sh: regenerate PE3 / PE4 (ps2_enemy_ch3/ch4 .inc) from ISO-extracted ESLs; tools from origin/t15/int.
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3gate
W=/root/probe/lanes-20261018/ch3gate/pe
GCISO=/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso
PS2ISO="/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso"
mkdir -p "$W/gc" "$W/ps2" "$W/tools" "$W/PE3" "$W/PE4"
python3 -B "$S/../ch3regen/c3r_gcx.py" "$GCISO" "$W/gc" etc/emleon02.esl etc/emleon03.esl etc/emleon04.esl etc/emleon05.esl
python3 -B "$S/c3g_ps2esl.py" "$PS2ISO" "$W/ps2"
for x in ch3 ch4; do git -C /root/work/re4-dreamcast show origin/t15/int:port/dreamcast/tools/d367/castle/ps2_enemy_$x.py > "$W/tools/ps2_enemy_$x.py"; done
cd /tmp
python3 -B "$W/tools/ps2_enemy_ch3.py" --gc-dir "$W/gc/etc" --ps2-dir "$W/ps2" --audit-json "$W/PE3/ps2-enemy-ch3-audit.json" --header "$W/PE3/ps2_enemy_ch3_data.inc"
python3 -B "$W/tools/ps2_enemy_ch4.py" --gc-dir "$W/gc/etc" --ps2-dir "$W/ps2" --audit-json "$W/PE4/ps2-enemy-ch4-audit.json" --header "$W/PE4/ps2_enemy_ch4_data.inc"
sha256sum "$W"/gc/etc/*.esl "$W"/ps2/*.esl "$W"/PE3/* "$W"/PE4/*
echo "want PE3 a422def76eb4ca60  PE4 35c2af879af74a23"
