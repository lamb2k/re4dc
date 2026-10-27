#!/usr/bin/env python3
"""Master an immutable fixed-fixture GDI with real files on high-density track3.

normal_master.py TREE MANIFEST IP OUT --twin BUILD --warp WARP [--pad PAD]
Unlike the shared fp_master, this owned adapter does not redirect fixture file
extents into track1. run_fixed.py refuses fixtures differing from this receipt.
The input tree is read only; all temporary/staged data is owned by this call.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

FULLPLAY=Path(__file__).resolve().parents[1]/'fullplay'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('tree','manifest','ip','out'):ap.add_argument(name,type=Path)
    ap.add_argument('--twin',type=Path);ap.add_argument('--warp',type=Path,required=True)
    ap.add_argument('--pad',type=Path)
    a=ap.parse_args()
    if a.out.exists():raise ValueError('Use a new output directory')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    fixtures={}
    for name,path,limit in (('warp',a.warp,2047),('pad',a.pad,4095)):
        data=path.read_bytes().replace(b'\r',b'') if path else b''
        if len(data)>limit:raise ValueError(f'{name} exceeds its fixed fixture budget')
        dest=a.out.parent/(a.out.name+f'.fixed-{name}.txt');dest.write_bytes(data)
        fixtures[name]=dict(file=str(dest),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    original=FULLPLAY/'fp_master.sh';text=original.read_text()
    text=re.sub(r'^here=.*$',f'here={FULLPLAY}',text,count=1,flags=re.M)
    needle='  head -c $FIXB /dev/zero > $WORK/cdroot/$f'
    assert text.count(needle)==1
    text=text.replace(needle,needle+'\n  case "$f" in\n'
                      '    dc/warp.txt) dd if="$FIXED_WARP_SOURCE" of="$WORK/cdroot/$f" conv=notrunc status=none ;;\n'
                      '    dc/padscript.txt) dd if="$FIXED_PAD_SOURCE" of="$WORK/cdroot/$f" conv=notrunc status=none ;;\n'
                      '  esac')
    lines=text.splitlines();redirect=[s for s in lines if s.startswith('python3 $here/fp_iso.py redirect ')]
    assert len(redirect)==3,redirect
    lines=[s for s in lines if s not in redirect]
    # Keep the inherited staging cleanup confined to validated, owned paths.
    lines=[re.sub(r'\$([A-Z][A-Z0-9_]*)',r'${\1:?}',s) if 'rm -' in s else s for s in lines]
    helper=a.out.parent/(a.out.name+'.normal-master.sh');helper.write_text('\n'.join(lines)+'\n')
    env=dict(os.environ,PRUNE_AUTO='0',RE4DC_STAGE_EXT4='0',
             FIXED_WARP_SOURCE=fixtures['warp']['file'],FIXED_PAD_SOURCE=fixtures['pad']['file'])
    cmd=['bash',str(helper),str(a.tree),str(a.manifest),str(a.ip),str(a.out)]
    if a.twin:cmd.append(str(a.twin))
    subprocess.run(cmd,env=env,check=True)
    spec=importlib.util.spec_from_file_location('fp_iso',FULLPLAY/'fp_iso.py')
    iso=importlib.util.module_from_spec(spec);spec.loader.exec_module(iso)
    track=iso.Track(a.out/'track03.iso',45000)
    root,_=iso.volume_roots(track);entries={p:(lba,n) for p,lba,n,isdir,_,_ in iso.walk(track,root) if not isdir}
    for name,record in fixtures.items():
        path='/dc/warp.txt' if name=='warp' else '/dc/padscript.txt'
        lba,n=entries[path]
        data=Path(record['file']).read_bytes()
        assert lba>=45000 and n==8192
        assert track.read_bytes(lba,n)==data+bytes(n-len(data)),path
        record.update(location='track03.iso',lba=lba,padded_bytes=n)
    track.f.close()
    base=a.out/'base.json';metadata=json.loads(base.read_text())
    metadata.update(fixture_transport='fixed-high-density-v1',fixed_fixtures=fixtures,
                    normal_master_source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                    normal_master_adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    base.write_text(json.dumps(metadata,indent=2)+'\n')
    print('FIXED HIGH-DENSITY VERIFIED',json.dumps(fixtures))


if __name__=='__main__':main()
