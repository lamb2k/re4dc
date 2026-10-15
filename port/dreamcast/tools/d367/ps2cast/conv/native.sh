#!/bin/bash
# native.sh <preset>... (Git Bash): stage 2 (WSL) + finish (Windows python)
T=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261014/ps2cast/tree/port/dreamcast/tools
O=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261014/ps2cast/work/conv
L="/c/Game Dev/Emulators/ps2cast-20261014/sh/conv/logs"
for p in "$@"; do
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- env PS2CAST_HOSTCHECK=/root/probe/lanes-20261014/ps2cast/work/host-check PS2CAST_HOST_WORKSPACE_KB=${KB:-512} bash /root/probe/lanes-20261014/ps2cast/tree/port/dreamcast/tools/ps2_cast_native.sh /root/probe/lanes-20261014/ps2cast/work/conv/$p > "$L/native-$p.txt" 2>&1 || { echo "$p native FAIL"; tail -5 "$L/native-$p.txt"; continue; }
  python "$T/ps2_cast.py" finish "$O/$p" > "$L/finish-$p.txt" 2>&1 && echo "$p ok" || { echo "$p finish FAIL"; tail -4 "$L/finish-$p.txt"; }
done
