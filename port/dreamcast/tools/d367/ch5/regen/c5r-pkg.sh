set -euo pipefail
# cx_room_fixtures.prepare_room package step (convert_room_bins prelit MAINSCENARIO) in the st3 tool tree (le_mirror bc4523fb545b)
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
T=$L/tools/port/dreamcast/tools
export PYTHONDONTWRITEBYTECODE=1
one() {
  r=$1; A=$L/fixtures/$r/ancillary-bc4523fb545b
  mkdir -p $A/package
  [ -e $A/source ] || cp -a $L/fixtures/$r/ancillary-b47c37112cf4/source $A/source
  ( cd /tmp && nice python3 $T/convert_room_bins.py $A/package/MAINSCENARIO.re4mesh --owner 0xff --smd $A/source/st3/$r.das \
    --lod --lod-min-gain 0.4 --lod-max-levels 4 --lod-eps 24,48,96,192,384 --lod-share --class-auto --color prelit > $A/package.log 2>&1 ) || tail -3 $A/package.log
  echo "$r $(sha256sum $A/package/MAINSCENARIO.re4mesh | cut -c1-16)"
}
export -f one; export L T
printf '%s\n' "$@" | xargs -P4 -I{} bash -c 'one {}'
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $L/fixtures
