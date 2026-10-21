set -euo pipefail
# b.sh <label> <arm> [extra knobs...] (WSL; lane cache20, after logiclod20/b.sh): one build of the release recipe
# (rr/recipe.conf CH2 line over test15/t15-build.sh's T15REC) on this tree plus extra knobs. Arms as ch2-build.sh
# (rP play, rW warp, rT trace). HW=1 adds PACE_MODE=off for hwproject. Output /root/probe/lanes/route/out-<label><arm>.
T=${TREE:-/root/work/lanes/cache20-scratch/tree}
export K=/root/work/lanes/cache20-scratch/k
mkdir -p "$K"
L=${1:?label}; A=${2:?arm}; shift 2
eval "$(grep '^CH2=' $T/port/dreamcast/tools/d367/rr/recipe.conf)"
export RC19D=/root/re4data/private/rc19s-20261019
(cd $T && git submodule update --init -q port/dreamcast/game/third_party/sh4zam)
HWX=""
[ "${HW:-0}" = 1 ] && HWX="PACE_MODE=off PC_SAMPLER_BYTES=8192"
T=$T LP=$L CH2="$CH2 $*" XON="$HWX ${XON:-}" bash $T/port/dreamcast/tools/d367/ch2/ch2-build.sh $A | cut -c1-200
