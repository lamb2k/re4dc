#!/bin/bash
# ch5regen: finish + regcast (Windows python, as recorded: c5reconv/c5fin finish; regcast-st3 / regcast-boss / regcast-island).
set -euo pipefail
R=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261018/ch5regen/c16
export PS2CAST_INPUTS=$R/inputs
cd /c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
T5=$R/t5/port/dreamcast/tools; T6=$R/t6/port/dreamcast/tools; W5=$R/conv5; W6=$R/conv6
S5="soldr-1d-22fp soldr-1d-247p soldr-em1d-02 soldr-em1d-0ep soldr-em1d-0fp soldr-em1d-10p soldr-em1d-11p soldr-em1e-06p soldr-em1e-0ep soldr-em1e-0fp soldr-em1e-17p soldr-em1e-19p soldr-em1f-0ep soldr-em1f-0fp soldr-em1f-10p soldr-em1f-18p"
for n in $S5; do python "$T5/ps2_cast.py" finish "$W5/$n" > /dev/null 2>&1 || echo "finish FAIL $n"; done
for n in regen-em36-00 regen-em36-01 regen-em36-02 gunship-em3a-00 gunship-em3a-02 u3-em32-00 heli-em3d-00; do python "$T6/ps2_cast.py" finish "$W6/$n" > /dev/null 2>&1 || echo "finish FAIL $n"; done
rm -rf "${W5:?}/regcast-st3" "${W6:?}/regcast-boss" "${W6:?}/regcast-island"
a=(); for n in $S5; do a+=("$W5/$n"); done
python "$T5/ps2_cast.py" regcast "$W5/regcast-st3" ps2-overlay "${a[@]}" 2>&1 | tail -1 | cut -c1-200
python "$T6/ps2_cast.py" regcast "$W6/regcast-boss" ps2-overlay "$W6/regen-em36-00" "$W6/regen-em36-01" "$W6/regen-em36-02" 2>&1 | tail -1 | cut -c1-200
python "$T6/ps2_cast.py" regcast "$W6/regcast-island" ps2-overlay "$W6/regen-em36-00" "$W6/regen-em36-01" "$W6/regen-em36-02" "$W6/gunship-em3a-00" "$W6/gunship-em3a-02" "$W6/u3-em32-00" "$W6/heli-em3d-00" "$W5/soldr-1d-22fp" "$W5/soldr-1d-247p" "$W5/soldr-em1d-02" 2>&1 | tail -1 | cut -c1-300
echo FINDONE
