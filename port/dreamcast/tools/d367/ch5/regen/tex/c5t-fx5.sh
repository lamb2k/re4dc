set -euo pipefail
W=/root/probe/lanes-20261018/ch5tex; C=/root/probe/lanes-20261018/ch5regen
T=$C/game-249effe5/port/dreamcast/tools; V=$W/vq33
export PYTHONDONTWRITEBYTECODE=1
X=$W/fxcache; rm -rf "${X:?}"; mkdir -p $X
python3 - $T $C $W <<'PY'
import sys,os,struct,glob
T,C,W=sys.argv[1:4]
sys.path.insert(0,T)
import le_mirror as M
from decode_yz2 import decode
n=0
for s in sorted(glob.glob(C+'/fixtures/r3*/ancillary-b47c37112cf4/source/st3/*.das')):
    r=os.path.basename(s)[:-4]
    dat=None
    for base in (W,C):
        p=base+'/tools/.assets/rooms-%s/work/%s/%s.dat'%(r,r,r)
        if os.path.exists(p): dat=p; break
    if not dat: continue
    data=open(s,'rb').read(); pay=[]
    for pos in range(M.ENTRY_SIZE,M.HEADER_TABLE,M.ENTRY_SIZE):
        kind,size,dest,off=struct.unpack_from('>4I',data,pos)
        if kind==M.END_OF_TABLE: break
        if kind==0: pay.append((off,size))
    off,size=pay[0]
    open(W+'/fxcache/%s.gc'%r,'wb').write(bytes(decode(data[off:off+size])))
    os.symlink(dat,W+'/fxcache/%s.ps2'%r); n+=1
print('rooms',n)
PY
F=$W/fx; rm -rf "${F:?}"; mkdir -p $F
cp $C/fx/*.py $F/
sed -i "s#cache = Path('$C/fxcache')#cache = Path('$X')#" $F/fx_ps2_pack_st3.py
grep -c "$X" $F/fx_ps2_pack_st3.py
R=$(ls $X/*.gc | xargs -n1 basename | sed 's/.gc$//' | tr '\n' ',' | sed 's/,$//'); echo $R
cd $F
rm -rf "${W:?}/ps2lib-st3"
PYTHONPATH=$T/d367/test12fx:$T/d367:$T/d367/vram:$T python3 fx_ps2_pack_st3.py lib $W/ps2lib-st3 st3-1015 --rooms $R --no-common --enemies '' 2>&1 | grep -E "r329|r332|r333|lib:"
PYTHONPATH=$T/d367/test12fx:$T/d367:$T/d367/vram:$T python3 fx_ps2_pack_st3.py pack $V/tex-st3vq4a.pak $V/tex-st3vq4.pak $W/ps2lib-st3 --rooms $R 2>&1 | tail -1
sha256sum $V/tex-st3vq4.pak | cut -c1-16; echo want 1c55bd5318bdf301
