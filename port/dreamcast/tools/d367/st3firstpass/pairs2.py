# pairs2.py <iso> <out> <logs-list-file> <files...>: pairs_from_log.py, but builds each logged pair separately and
# lists the ones whose images are in none of the given archives (instead of failing the whole set).
import sys,re,tempfile,shutil,json
from pathlib import Path
T='/root/probe/lanes-20261014/st3/tree/port/dreamcast/tools'
sys.path.insert(0,T)
import prepare_native_ui as P
from assetpipe.rooms import GcIso
LINE=re.compile(r"native UI: pair missing ([0-9a-f]{8}-[0-9a-f]{8}) color=([0-9a-f]{8}-[0-9a-f]{8}) mask=([0-9a-f]{8}-[0-9a-f]{8})")
iso=GcIso(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
pairs={}
for lg in open(sys.argv[3]).read().split('\n'):
    if lg: 
        for m in LINE.finditer(open(lg,errors='replace').read()): pairs[m.group(1)]=(m.group(2),m.group(3))
src=Path(tempfile.mkdtemp()); files=[]
for f in sys.argv[4:]:
    if iso.find(f) is None: print('not on disc',f); continue
    (src/f).parent.mkdir(parents=True,exist_ok=True); (src/f).write_bytes(iso.read(f)); files.append(f)
ok=[];miss=[]
for key,(c,m) in sorted(pairs.items()):
    if (out/(key+'.re4tex')).exists(): ok.append(key); continue
    tmp=Path(tempfile.mkdtemp())/'o'
    try:
        P.prepare_model_pairs(src,files,[dict(color=c,mask=m)],tmp)
        for g in tmp.glob('*.re4tex'): shutil.copy2(g,out/g.name)
        ok.append(key)
    except Exception as e: miss.append((key,str(e)[:120]))
print('pairs',len(pairs),'built',len(ok),'unresolved',len(miss))
for k,e in miss: print('UNRESOLVED',k,e)
