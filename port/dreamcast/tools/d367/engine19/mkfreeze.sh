set -euo pipefail
# mkfreeze.sh <scene> <tick>: k/<scene>f<tick>-warp.txt = the scene's warp plus "freeze <tick>"
K=/root/probe/lanes-20261019/engine19/k
SC=${1:?}; T=${2:?}
{ tr -d '\r' < "$K/$SC-warp.txt" | sed "s/^name .*/name e19-$SC-f$T/"; echo "freeze $T"; } > "$K/${SC}f$T-warp.txt"
cat "$K/${SC}f$T-warp.txt"
