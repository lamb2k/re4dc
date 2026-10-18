set -euo pipefail
# st3 lane f64.sh (sub-screen chap05..07 pictures, addss VQ rule) and f104/f106 (island FX library, fx_ps2_pack_st3.py)
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
G=$L/game-249effe5
T=$G/port/dreamcast/tools
export PYTHONDONTWRITEBYTECODE=1
# --- sub-screen chapters
O=$L/sschap; rm -rf "${O:?}"; mkdir -p $O
mkdir -p $O/root/ss/eng
( cd $T && python3 - "$O/root" <<'P'
import sys; sys.path.insert(0,'.')
from assetpipe.rooms import GcIso
g=GcIso('/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso')
for n in ('chap05','chap06','chap07'):
    k=[f for f in g.files if f.lower()=='ss/eng/%s.dat'%n][0]
    open(sys.argv[1]+'/ss/eng/%s.dat'%n,'wb').write(g.read(k))
P
)
printf "ss/eng/chap05.dat\nss/eng/chap06.dat\nss/eng/chap07.dat\n" > $O/m5.txt
python3 $T/prepare_native_ui.py $O/root $O/m5.txt $O/tex5 2>&1 | tail -1
BIG=$(python3 - $T $O/tex5 <<'P'
import sys,pathlib
sys.path.insert(0,sys.argv[1]); sys.path.insert(0,sys.argv[1]+'/d367'); sys.path.insert(0,sys.argv[1]+'/d367/vram')
import vq_native_ui as vq
for f in sorted(pathlib.Path(sys.argv[2]).glob('*.re4tex')):
    try: w,h,fmt,flags,_=vq.read_package(f.read_bytes())
    except ValueError: continue
    if w*h*2>=32768 and w>=64 and h>=64: print(f)
P
)
cd /tmp; [ -n "$BIG" ] && python3 $S/c5r_vqkeys.py $T $O/vqw $BIG | tail -2
# --- FX library
C=$L/fxcache; rm -rf "${C:?}"; mkdir -p $C
ls $L/fixtures/r3*/ancillary-b47c37112cf4/source/st3/*.das > $L/st3das.txt
python3 - $T $L <<'PY'
import sys,os,struct
T,L=sys.argv[1],sys.argv[2]
sys.path.insert(0,T)
import le_mirror as M
from decode_yz2 import decode
n=0
for s in open(L+'/st3das.txt').read().split():
    r=os.path.basename(s)[:-4]
    dat=L+'/tools/.assets/rooms-%s/work/%s/%s.dat'%(r,r,r)
    if not os.path.exists(dat): continue
    data=open(s,'rb').read(); pay=[]
    for pos in range(M.ENTRY_SIZE,M.HEADER_TABLE,M.ENTRY_SIZE):
        kind,size,dest,off=struct.unpack_from('>4I',data,pos)
        if kind==M.END_OF_TABLE: break
        if kind==0: pay.append((off,size))
    off,size=pay[0]
    open(L+'/fxcache/%s.gc'%r,'wb').write(bytes(decode(data[off:off+size])))
    if not os.path.exists(L+'/fxcache/%s.ps2'%r): os.symlink(dat,L+'/fxcache/%s.ps2'%r)
    n+=1
print('rooms',n)
PY
F=$L/fx; rm -rf "${F:?}"; mkdir -p $F
sed "s#cache = Path('/root/probe/lanes-20261014/st3/fxcache')#cache = Path('$C')#" $T/d367/test12fx/fx_ps2_pack_st3.py > $F/fx_ps2_pack_st3.py
cp $T/d367/test12fx/*.py $F/ 2>/dev/null || true
sed "s#cache = Path('/root/probe/lanes-20261014/st3/fxcache')#cache = Path('$C')#" $T/d367/test12fx/fx_ps2_pack_st3.py > $F/fx_ps2_pack_st3.py
grep -c "$C" $F/fx_ps2_pack_st3.py
R=$(ls $C/*.gc | xargs -n1 basename | sed 's/.gc$//' | tr '\n' ',' | sed 's/,$//')
cd $F && PYTHONPATH=$T/d367/test12fx:$T/d367:$T/d367/vram:$T python3 fx_ps2_pack_st3.py lib $L/ps2lib-st3 st3-1015 --rooms $R --no-common --enemies '' 2>&1 | tail -2
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $O $L/ps2lib-st3
