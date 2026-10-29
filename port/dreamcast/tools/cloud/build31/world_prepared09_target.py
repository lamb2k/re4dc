#!/usr/bin/env python3
"""Local SDK qualification of frozen EF09; no game/private-data execution."""
import argparse, hashlib, json, os, shlex, subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--tree',type=Path,required=True);p.add_argument('--baseline-tree',type=Path,required=True);p.add_argument('--baseline-output',type=Path,required=True);p.add_argument('--arms-root',type=Path,default=Path('/root/probe/lanes/route'));p.add_argument('--label',default='ef09oct29v1');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(exist_ok=False);print('runner_pid',os.getpid(),flush=True)
compiler='/opt/toolchains/dc/sh-elf/bin/sh-elf-g++'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(cmd,cwd):return subprocess.run(cmd,cwd=cwd,capture_output=True)
def cmd_for(output):
    lines=[s for s in (output/'build.log').read_text().splitlines() if 'native_static.cpp' in s and ' -c ' in s];assert len(lines)==1
    cmd=shlex.split(lines[0]);cmd[0]=compiler
    at=cmd.index('-o');del cmd[at:at+2]
    for x in ('-c','-MMD','-MP','platform/native_static.cpp'):cmd.remove(x)
    return cmd
arms={x:a.arms_root/('out-'+a.label+x+'rP') for x in ('absent','zero','plan','portal')}
base_commit='255964fdc7d22a61acff1ef59734a36ec91ebff0'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.baseline_tree,text=True).strip()==base_commit
assert not subprocess.check_output(['git','status','--porcelain'],cwd=a.baseline_tree).strip()
# Full normalized Make state: replace only exact output/tree roots, remove only the new default-zero name.
def knobs(path,tree):
    text=(path/'resolved-knobs.txt').read_text().replace(str(path),'<OUTPUT>').replace(str(tree),'<TREE>')
    return dict(l.split('=',1) for l in text.splitlines() if '=' in l and not l.startswith('#'))
bk=knobs(a.baseline_output,Path('/root/work/lanes/owner-engine-wave2-integration-20261029'))
for name in ('absent','zero'):
    k=knobs(arms[name],a.tree);assert k.pop('WORLD_PREPARED09')=='0'
    diff={key:[bk.get(key),k.get(key)] for key in bk.keys()|k.keys() if bk.get(key)!=k.get(key)}
    (a.out/(name+'-knob-differences.json')).write_text(json.dumps(diff,indent=2)+'\n');assert not diff,diff
helper=a.tree/'port/dreamcast/tools/cloud/build34/upload_compare.py'
subprocess.run(['python3',str(helper),'--baseline',str(a.baseline_output),'--arm',str(arms['absent']),'--arm',str(arms['zero']),'--output',str(a.out/'off-final.json')],check=True)
rows=[]
profiles={'release':{},'existing-plan':dict(WORLD_PART_PLAN29=1,NATIVE_PKG_HIGH=1,MOVIE_WORLD_ARENA=1,STATIC_OBJ_LIFETIME05=1),'solo-portal':dict(WORLD_PORTAL29=1,PS2_PVS=1,PS2_PVS_DEFAULT=0,PS2_INTERIOR_CULL=1,SCENERY_SUBMIT_BATCH=0,SCENERY_STREAM=0,SCENERY_CLIP_GATHER=0,SCENERY_CLIP_INDEXED26=0)}
for profile,values in profiles.items():
    header=a.out/(profile+'.h');header.write_text(''.join('#undef RE4DC_'+k+'\n#define RE4DC_'+k+' '+str(v)+'\n' for k,v in values.items()))
    for arm in ('baseline','absent','zero'):
        output=a.baseline_output if arm=='baseline' else arms[arm];tree=a.baseline_tree if arm=='baseline' else a.tree
        cmd=cmd_for(output)+['-include',str(header)]
        if arm=='zero':cmd+=['-DRE4DC_WORLD_PREPARED09=0']
        for ext,phase in [('ii',['-E','-P']),('o',['-g0','-fstack-usage','-c'])]:
            dest=a.out/(profile+'-'+arm+'.'+ext);r=run(cmd+phase+['platform/native_static.cpp','-o',str(dest)],tree/'port/dreamcast/game')
            (a.out/(profile+'-'+arm+'-'+ext+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode()[-4000:]
    for ext in ('ii','o'):
        paths=[a.out/(profile+'-'+arm+'.'+ext) for arm in ('baseline','absent','zero')]
        assert paths[0].read_bytes()==paths[1].read_bytes()==paths[2].read_bytes(),(profile,ext,'disabled identity')
        rows.append(dict(profile=profile,artifact=ext,bytes=paths[0].stat().st_size,sha256=sha(paths[0]),baseline_absent_zero_equal=True))
    print('PASS TU',profile,flush=True)
profile_spec=json.loads((a.tree/'port/dreamcast/tools/cloud/build31/world_prepared09_profiles.json').read_text())['profiles'];facts={}
for name in ('plan','portal'):
    cmd=cmd_for(arms[name]);r=run(cmd+['-E','-dM','platform/native_static.cpp'],a.tree/'port/dreamcast/game')
    (a.out/(name+'-macros.txt')).write_bytes(r.stdout);(a.out/(name+'-macros.stderr')).write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode()[-4000:]
    macros=dict(line[len('#define '):].split(' ',1) for line in r.stdout.decode().splitlines() if line.startswith('#define ') and ' ' in line[len('#define '):])
    selected=dict(s.split('=',1) for s in profile_spec[name]);resolved=knobs(arms[name],a.tree)
    for key,value in selected.items():assert resolved[key]==value,(name,key,'Make',resolved.get(key),value)
    required=['WORLD_PREPARED09','WORLD_PART_PLAN29','MOVIE_WORLD_ARENA','STATIC_OBJ_LIFETIME05']
    if name=='portal':required+=['WORLD_PORTAL29','WORLD_PORTAL_COMPLETION','PS2_PVS_BATCH_COMPOSE','SCENERY_SUBMIT_BATCH','SCENERY_STREAM','SCENERY_CLIP_GATHER','SCENERY_CLIP_INDEXED26','TA_DIRECT','PS2_WORLD_HDR_CACHE','MESH_FASTPATH','PVR_STREAM']
    for key in required:assert macros.get('RE4DC_'+key)==selected.get(key,'1'),(name,key,macros.get('RE4DC_'+key),selected.get(key,'1'))
    facts[name]={key:macros['RE4DC_'+key] for key in required}
    r=run(cmd+['-g0','-fstack-usage','-c','platform/native_static.cpp','-o',str(a.out/(name+'.o'))],a.tree/'port/dreamcast/game')
    (a.out/(name+'-object.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode()[-4000:]
    print('PASS ON facts/object',name,flush=True)
report=dict(status='PASS',scope='Full release OFF programme/overlays/allocated sections plus exact normalized resolved Make state. Actual release command TU ii/g0 identity in release, existing-plan and solo-portal source profiles. ON actual macros/Make bindings and affected objects for explicit plan/portal validation profiles only; no runtime, visual, whole-stack, hardware timing or heap acceptance.',rows=rows,on_facts=facts,baseline=base_commit,tree_tip=subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.tree,text=True).strip(),compiler=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],commands={name:cmd_for(path) for name,path in arms.items()},source_sha256=sha(a.tree/'port/dreamcast/game/platform/native_static.cpp'))
(a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS EF09 qualification',flush=True)