#!/bin/bash
# conv.sh <preset>... : stage 1 (Windows python) convert into /root/probe/lanes-20261014/ps2cast/work/conv/<preset>
T=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261014/ps2cast/tree/port/dreamcast/tools
O=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261014/ps2cast/work/conv
L="/c/Game Dev/Emulators/ps2cast-20261014/sh/conv/logs"; mkdir -p "$L"
for p in "$@"; do
  python "$T/ps2_cast.py" convert "$p" "$O/$p" --ps2-iso "C:/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso" ${TOL:+--bone-tol $TOL} > "$L/convert-$p.txt" 2>&1 && echo "$p convert ok" || { echo "$p convert FAIL"; tail -6 "$L/convert-$p.txt"; }
done
