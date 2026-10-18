set -euo pipefail
# st3 lane f70.sh (pairs-e1) and f93.sh (pairs-e2) via pairs2.py, then the addss.py VQ rule on the big ones
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
T=$L/game-249effe5/port/dreamcast/tools
ISO='/mnt/c/Game Dev/Emulators/Resident Evil 4 - 2004.11.25 Disc 2 (Resident Evil 4 Review Rom (GC) No Reviews Until March 05 Issues).gcm'
R="/mnt/c/Game Dev/Emulators"
export PYTHONDONTWRITEBYTECODE=1
cd /tmp
ls "$R/re4-rfp-20261015-st3e1/scenarios/"*/capture/run-output.txt "$R/re4-rfp-20261015-st3d12/scenarios/"*/capture/run-output.txt "$R/re4-rfp-20261015-st3d13/scenarios/"*/capture/run-output.txt > $L/pairlogs.txt
ls "$R/re4-rfp-20261015-st3e2/scenarios/"*/capture/run-output.txt > $L/pairlogs2.txt
F=""; for s in $(cat $L/st3das.txt); do F="$F st3/$(basename $s)"; done
E=""; for n in 300 301 303 304 305 306 307 308 309 30a 30b 30c 30d 30e 30f 310 311 312 315 316 317 318 31a 31b 31c 31d 320 321 325 326 327 329 330 331 332 333; do E="$E Evd/r${n}s00.evd"; done
python3 $S/c5r_pairs2.py "$ISO" $L/pairs-e1 $L/pairlogs.txt $F $E em/em1d.drs em/em1e.drs em/em1f.drs em/em36.drs em/em3b.drs em/em25.drs em/pl08.drs etc/core.das ss/cmn/ss_oc301.dat 2>&1 | grep -v "^not on disc" | tail -3
python3 $S/c5r_pairs2.py "$ISO" $L/pairs-e2 $L/pairlogs2.txt $F em/em1d.drs em/em1e.drs em/em1f.drs em/em36.drs em/pl08.drs etc/core.das 2>&1 | grep -v "^not on disc" | tail -3
BIG=$(python3 - $T $L/pairs-e1 $L/pairs-e2 <<'P'
import sys,pathlib
sys.path.insert(0,sys.argv[1]); sys.path.insert(0,sys.argv[1]+'/d367'); sys.path.insert(0,sys.argv[1]+'/d367/vram')
import vq_native_ui as vq
for d in sys.argv[2:]:
    for f in sorted(pathlib.Path(d).glob('*.re4tex')):
        try: w,h,fmt,flags,_=vq.read_package(f.read_bytes())
        except ValueError: continue
        if w*h*2>=32768 and w>=64 and h>=64: print(f)
P
)
rm -rf "${L:?}/pairs-evq"
[ -n "$BIG" ] && python3 $S/c5r_vqkeys.py $T $L/pairs-evq $BIG | awk '{print $4}' | sort | uniq -c
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $L/pairs-e1 $L/pairs-e2 $L/pairs-evq/out
