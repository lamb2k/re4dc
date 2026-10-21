#!/usr/bin/env python3
"""Emit pinned atlas run arrays; source geometry remains the actual owner input."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists():raise ValueError('preserve existing runtime data')
    sums=a.candidate/'SHA256SUMS'
    if sha(sums)!='9b524ee573753dcb640cb561ba7966e56c5d57e53200c5dcbd8683f0796ad2a2':raise ValueError('candidate seal')
    for line in sums.read_text().splitlines():
        digest,name=line.split('  ',1)
        if sha(a.candidate/name)!=digest:raise ValueError('candidate changed: '+name)
    lines=['// Private generated data. Do not commit.', '#pragma once','namespace leon_atlas_data {']
    cases=[];total=0
    for actor in ('standard','pl08'):
        report=json.loads((a.candidate/actor/'report.json').read_text())
        runs=report['bindings']['runs'];rows=[]
        for i,row in enumerate(runs):
            base=a.candidate/actor/'bindings'/f'run-{i:03d}'
            prefix=actor+'_'+str(i)
            def array(name,p):
                nonlocal total
                data=p.read_bytes();total+=len(data)
                lines.append('alignas(32) static const unsigned char '+name+'[]={'+','.join(str(b) for b in data)+'};')
            array(prefix+'_stream',base/'stream.meshlets')
            isolated=row['texture']=='isolated'
            if isolated:array(prefix+'_uv',base/'uv.bin')
            uv='{'+prefix+'_uv,sizeof('+prefix+'_uv)}' if isolated else 'b.source.uv'
            rows.append('b.runs['+str(i)+']={'+uv+',{'+prefix+'_stream,sizeof('+prefix+'_stream)},'+str(row['triangles'])+','+str(int(isolated))+'};')
        key=[int(n,16) for n in report['derived_key'].split('-')]
        cases+=['if('+('b.appearance==0x100u' if actor=='standard' else 'b.appearance==0x108u || b.appearance==0x109u')+') {',
                'b.tile_crc='+str(key[0])+'u;b.tile_fnv='+str(key[1])+'u;b.run_count='+str(len(runs))+';',*rows,'return true;}']
    lines+=['inline bool populate(re4dc_atlas_split::Bundle& b) {',*cases,'return false;}','}']
    a.out.mkdir(parents=True)
    header=a.out/'leon_atlas_split_data.h';header.write_text('\n'.join(lines)+'\n')
    tex=a.out/'tex';tex.mkdir()
    for actor in ('standard','pl08'):
        report=json.loads((a.candidate/actor/'report.json').read_text())
        key=report['derived_key']
        shutil.copy2(a.candidate/actor/'candidate.re4tex',tex/(key+'.re4tex'))
    result=dict(schema='re4dc-atlas-runtime-data-1',candidate_sha256sums=sha(sums),header_sha256=sha(header),
                linked_array_bytes=total,run_ids=dict(standard=9,pl08_and_headless=13),
                source_geometry='Actual current owner input; no duplicated positions/normals/weights.',default_enabled=False)
    (a.out/'runtime-data.json').write_text(json.dumps(result,indent=2)+'\n')
    files=sorted(p for p in a.out.rglob('*') if p.is_file())
    (a.out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(a.out).as_posix()+'\n' for p in files))
    print(json.dumps(result))
if __name__=='__main__':main()