set -euo pipefail
L=/root/probe/lanes-20261018/ch4regen
CX=/root/probe/codex-cx-fixtures-20261013
P=/root/re4data/private/cxfix-replay-20261018
if [ ! -e $CX ]; then
  mkdir -p $CX/dependencies
  ln -s $P/output $CX/output
  ln -s $P/dependencies/prepared $CX/dependencies/prepared
  ln -s $L/cxdeps-c3/source $CX/dependencies/source
  echo "ch4regen 2026-10-18: path shim for recorded scripts; output/prepared -> $P (read-only), source -> $L/cxdeps-c3/source" > $CX/README-SHIM.txt
fi
mkdir -p $L/ch4found
[ -e /root/probe/lanes-20261016/ch4found ] || { mkdir -p /root/probe/lanes-20261016; ln -s $L/ch4found /root/probe/lanes-20261016/ch4found; }
[ -e $L/ch4found/tree ] || ln -s $L/tree $L/ch4found/tree
ls -la $CX /root/probe/lanes-20261016/ | head; ls /root/probe/lanes-20261016/ch4found/
