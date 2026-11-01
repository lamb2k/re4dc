#!/bin/bash
# world-blender25 Flycast runs (Git Bash), <=60 s each, <=4 at a time
set -uo pipefail
FPD='//wsl.localhost/Ubuntu-24.04/root/work/lanes/world-blender25/port/dreamcast/tools/d367/fullplay'
EVW='C:/Flycast-Evidence/re4-dreamcast/world-blender25'
EVU=/c/Flycast-Evidence/re4-dreamcast/world-blender25
FX=$EVU/fixtures
run() { # name base fixture [extra]
  local n=$1 b=$2 w=$3; shift 3
  rm -rf "${EVU:?}/${n:?}"
  python "$FPD/fp_run.py" --base "$EVW/_discs/$b" --cap "$EVW/$n" --syms "$(cat $FX/syms-$b.txt)" --seconds 60 --name wb25-$n --warp "$EVW/fixtures/$w" "$@" > "$EVU/$n.out" 2>&1
}
wave() { for j in "$@"; do eval "$j" & done; wait; }
for spec in "$@"; do eval "$spec"; done
echo RUNS-DONE
