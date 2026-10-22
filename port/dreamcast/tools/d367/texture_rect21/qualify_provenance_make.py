#!/usr/bin/env python3
"""Resolve the actual existing WORLD_RECT21 make block, without a compiler."""
from pathlib import Path
import argparse,hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
MK=HERE.parents[2]/'game/game30.mk'
def block(s):return s.split('WORLD_RECT21 ?= 0\n',1)[1].split('\n# PS2_WORLD_HDR_CACHE',1)[0]
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('preserve existing evidence')
    a.out.mkdir()
    current='WORLD_RECT21 ?= 0\n'+block(MK.read_text())
    old=subprocess.check_output(['git','show','a6c4d0c6d9e558fca343042dbc5453ba07e5dec9:port/dreamcast/game/game30.mk'],cwd=ROOT,text=True)
    old='WORLD_RECT21 ?= 0\n'+block(old)
    makefiles={}
    for label,part in [('original',old),('current',current)]:
        text='OBJDIR := obj\nPS2_WORLD_DRAW := 1\nPS2_WORLD_MESH := 1\nMESH_DIRECT := 1\n'+part
        text+='\n.PHONY: all obj/platform/native_ui.o obj/platform/native_static.o\nall: obj/platform/native_ui.o obj/platform/native_static.o\nobj/platform/native_ui.o obj/platform/native_static.o:\n\t@printf "%s:%s\\n" "$@" "$(PLATFORM_CPPFLAGS)"\n'
        makefiles[label]=a.out/(label+'.mk');makefiles[label].write_text(text)
    rows={}
    cases={'default':[],'off':['WORLD_RECT21=0'],'on':['WORLD_RECT21=1'],'bad2':['WORLD_RECT21=2'],'badword':['WORLD_RECT21=x'],'badempty':['WORLD_RECT21='],'badmulti':['WORLD_RECT21=0 1'],'nodraw':['WORLD_RECT21=1','PS2_WORLD_DRAW=0'],'nomesh':['WORLD_RECT21=1','PS2_WORLD_MESH=0'],'nodirect':['WORLD_RECT21=1','MESH_DIRECT=0']}
    for label,mk in makefiles.items():
        rows[label]={}
        for name,extra in cases.items():
            cmd=['make','--no-print-directory','-s','-f',str(mk),'all',*extra]
            r=subprocess.run(cmd,capture_output=True,text=True)
            rows[label][name]=dict(command=cmd,rc=r.returncode,stdout=r.stdout,stderr=r.stderr)
    for name in ('default','off'):
        assert rows['current'][name]['rc']==0
        assert rows['current'][name]['stdout']==rows['original'][name]['stdout']==rows['current']['default']['stdout']
        assert '-DRE4DC_WORLD_RECT21' not in rows['current'][name]['stdout']
    assert rows['current']['on']['rc']==0
    flags=dict(x.split(':',1)for x in rows['current']['on']['stdout'].splitlines())
    assert flags=={'obj/platform/native_ui.o':'-DRE4DC_WORLD_RECT21=1','obj/platform/native_static.o':'-DRE4DC_WORLD_RECT21=1'}
    assert all(rows['current'][k]['rc']!=0 for k in cases if k not in('default','off','on'))
    report=dict(actual_block_sha256=hashlib.sha256(current.encode()).hexdigest(),
                scope='Actual make block resolution only, no compiler/fullbuild',
                default_explicit0_original_exact=True,on_resolves_native_static_and_ui=True,invalid_prerequisites_refused=True,cases=rows)
    (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print('actual make block: defaults exact; ON both TUs; all 7 invalid/prerequisites refused')
if __name__=='__main__':main()