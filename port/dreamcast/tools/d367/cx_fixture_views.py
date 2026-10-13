#!/usr/bin/env python3
"""Clone an entry fixture into new named heading views without changing assets."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-fixture',type=Path,required=True)
    ap.add_argument('--view-set',required=True)
    ap.add_argument('--presets',type=Path,default=Path(__file__).with_name('cx_view_presets.json'))
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--arm-tool',type=Path,required=True)
    ap.add_argument('--candidate-dir',type=Path,required=True)
    ap.add_argument('--arm-label',required=True)
    a=ap.parse_args()
    a.out=a.out.resolve()
    repo=Path(__file__).resolve().parents[4]
    if a.out == repo or repo in a.out.parents:
        ap.error('generated fixtures must stay outside the repository')
    registry=json.loads(a.presets.read_text())
    if registry['schema'] != 're4dc-cx-view-presets/1':
        raise ValueError('unsupported preset schema')
    spec=registry['view_sets'][a.view_set]
    fixture=json.loads(a.source_fixture.read_text())
    source_warp=Path(fixture['replace']['dc/warp.txt'])
    original=source_warp.read_text()
    room=spec['room']
    if spec['source_view'] != 'entry' or not re.search(r'^room 0x'+room[1:]+r'$',original,re.M):
        raise ValueError('preset requires an entry fixture in '+room)
    if re.search(r'^(act|dead|kill) ',original,re.M):
        raise ValueError('source warp is not a still entry fixture')
    heading=re.findall(r'^ang ([^\s]+)$',original,re.M)
    if len(heading) != 1:
        raise ValueError('source warp needs exactly one heading')
    entry_angle=float(heading[0])
    if not math.isfinite(entry_angle):
        raise ValueError('invalid source heading')
    provenance=fixture.get('provenance',{}).get('cx_room',{})
    if provenance.get('room') != room or provenance.get('camera_delta_radians') != 0:
        raise ValueError('source fixture lacks original room-entry provenance')
    outputs=[]
    for view in spec['views']:
        if not re.fullmatch(r'[a-z0-9-]+',view['name']):
            raise ValueError('invalid view name')
        name='cx-'+room+'-'+view['name']
        paths={key:a.out/(name+extension) for key,extension in
               [('warp','.txt'),('unarmed','.unarmed.json'),('armed','.armed.json'),('log','.arm.log')]}
        if any(p.exists() for p in paths.values()):
            raise ValueError('view output already exists: '+name)
        delta=float(view['heading_delta_radians'])
        if not math.isfinite(delta):
            raise ValueError('invalid view delta')
        angle=(entry_angle+delta+math.pi)%(2*math.pi)-math.pi
        outputs.append((name,paths,delta,angle))
    a.out.mkdir(parents=True,exist_ok=True)
    results=[]
    for name,paths,delta,angle in outputs:
        text=re.sub(r'^name .*$', 'name '+name,original,flags=re.M)
        text=re.sub(r'^ang [^\s]+$', 'ang %.10f'%angle,text,flags=re.M)
        paths['warp'].write_text(text)
        data=copy.deepcopy(fixture)
        data['replace']['dc/warp.txt']=str(paths['warp'].resolve())
        data['provenance']['cx_room']['camera_delta_radians']=delta
        data['provenance']['cx_view_variation']=dict(
            source_fixture=str(a.source_fixture.resolve()), source_fixture_sha256=sha(a.source_fixture),
            source_warp=str(source_warp),source_warp_sha256=sha(source_warp),
            presets=str(a.presets.resolve()),presets_sha256=sha(a.presets),view_set=a.view_set,
            entry_angle_radians=entry_angle,heading_delta_radians=delta,heading_radians=angle)
        paths['unarmed'].write_text(json.dumps(data,indent=2)+'\n')
        with paths['log'].open('w') as log:
            subprocess.run([sys.executable,str(a.arm_tool),str(paths['unarmed']),str(paths['armed']),
                            a.arm_label,'--candidate-dir',str(a.candidate_dir)],
                           check=True,stdout=log,stderr=subprocess.STDOUT)
        final=json.loads(paths['armed'].read_text())
        missing=[key for key,path in final['replace'].items() if not Path(path).is_file()]
        if missing:
            raise ValueError('missing fixture source: '+str(missing))
        changed=[key for key in fixture['replace'] if final['replace'].get(key)!=fixture['replace'][key]]
        if set(changed)-{'dc/warp.txt'}:
            raise ValueError('source fixture differs from requested overlay arm: '+str(changed))
        results.append(dict(name=name,warp=str(paths['warp']),fixture=str(paths['armed']),
            fixture_sha256=sha(paths['armed']),heading_delta_radians=delta,heading_radians=angle,
            changed_replacements=changed,all_sources_present=True))
    report=a.out/(a.view_set+'.json')
    report.write_text(json.dumps(dict(views=results,acceptance='STATIC_PATHS_AND_ARM_ONLY'),indent=2)+'\n')
    print(report)


if __name__=='__main__':
    main()
