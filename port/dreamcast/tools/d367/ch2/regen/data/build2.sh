set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen; cd $L/t-int
T=$L/t-int K=$L/k LP=crc XON="NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=30" bash port/dreamcast/tools/d367/ch2/ch2-build.sh mW > $L/k/build-crcmW.log 2>&1
tail -1 $L/k/build-crcmW.log | cut -c1-120
T=$L/t-int/port/dreamcast/tools/d367
for w in s-siegek e-r111; do python3 $T/test11/t11-fix.py crcmW $L/fix/$w-crcmW.json --data ch2,cast16 --warp $T/ch2/warps/$w.txt 2>/dev/null | tail -1 | cut -c1-80; done
python3 - <<'P'
import glob, json, os
P = '/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/programs/candidate-routecrcmW'
for f in glob.glob('/root/probe/lanes-20261017r/ch2regen/fix/*-crcmW.json'):
    d = json.load(open(f))
    for o in glob.glob(P + '/*.ovl'): d['replace']['dc/' + os.path.basename(o)] = o
    json.dump(d, open(f, 'w'), indent=1)
print('overlays set')
P
