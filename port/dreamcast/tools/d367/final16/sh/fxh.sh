# fxh.sh <warp>...: fixtures fx-r332-<warp>h with the hot-set em31 (preph-em31, banks aica-f)
L=/root/probe/lanes-20261016/final16
for w in "$@"; do V=${w}h W2=$w PREP=$L/prepem/preph-em31 bash "/mnt/c/Game Dev/Emulators/final16-20261016/sh/fx4.sh" 2>&1 | tail -1
python3 -c "
import json;r=json.load(open('$L/fixtures/r332/fx-r332-${w}h.armed.json'))['replace'];print('$w', r['em/em31.drs'], sum(1 for k,v in r.items() if 'preph-em31' in v))"; done
