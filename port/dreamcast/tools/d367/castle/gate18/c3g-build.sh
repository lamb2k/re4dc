set -euo pipefail
# c3g-build.sh: CH4REC mW arm (ch4-build.sh) on lane tree, recovered PE2/PE3/PE4, fresh objdir (label c3gmW).
T=/root/probe/lanes-20261018/ch3gate/tree
O=/root/probe/lanes/route/out-c3gmW
[ -e "$O" ] && { echo "objdir $O exists: refusing (fresh objdir required)"; exit 1; }
export T K=/root/probe/lanes-20261018/ch3gate/k LP=c3g
export PE2=/root/re4data/private/ps2enemy-ch2-20261016
export PE3=/root/re4data/private/ps2enemy-ch34-20261018/PE3
export PE4=/root/re4data/private/ps2enemy-ch34-20261018/PE4
bash "$T/port/dreamcast/tools/d367/ch4found/ch4-build.sh" mW
ls "$O"; cat "$O/elf.sha256"; echo "missing bytes: $(wc -c < "$O/missing.txt")"
