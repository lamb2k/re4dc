#!/usr/bin/env python3
"""EF11: consumed sheet Make-derived SH-4 objects and OFF identity.

Run only while holding the coordinator's target-build slot. This uses the
existing public profile/SDK-header preparation, without private assets or a
linked game. Full release programme/overlay checks remain a separate receipt.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
spec=importlib.util.spec_from_file_location('ef11_build29',HERE/'build_controls.py')
controls=importlib.util.module_from_spec(spec);sys.modules[spec.name]=controls;spec.loader.exec_module(controls)
profile=controls.profile
UNITS={'cloth':('src/game/cloth.o','../../../src/game/cloth.cpp'),
       'native_ui':('platform/native_ui.o','platform/native_ui.cpp')}
profile.UNITS.update(UNITS)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--units',nargs='+',choices=tuple(UNITS),default=tuple(UNITS))
    parser.add_argument('--baseline',default='255964fdc7d22a61acff1ef59734a36ec91ebff0')
    parser.add_argument('--sh4-cxx',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-g++',type=Path)
    parser.add_argument('--kos-root',default='/root/work/kos-re4dc-d367',type=Path)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    sdk=ROOT/'port/dreamcast/game/third_party/sh4zam';assert (sdk/'include/sh4zam/sh4zam.h').exists() or (sdk/'include').is_dir()
    toolchain={'compiler':subprocess.check_output([str(args.sh4_cxx),'--version'],text=True).splitlines()[0],
               'compiler_sha256':sha(args.sh4_cxx),'kos_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.kos_root,text=True).strip(),
               'sdk_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=sdk,text=True).strip()}
    base=out/'parent-tree';base.mkdir()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',args.baseline],cwd=ROOT))) as archive:
        archive.extractall(base,filter='data')
    builder=profile.Build(out);arms={};cache={}
    configurations=[]
    for group,deps in [('release',[]),('dependencies',['NATIVE_DRAW_OUTCOMES=1','PS2_UPLOAD_INCARNATION=1'])]:
        for arm,tree,extra in [('parent',base,[]),('absent',ROOT,[]),('zero',ROOT,['CLOTH_SHEET11=0']),
                               ('enabled',ROOT,['CLOTH_SHEET11=1'])]:
            if group=='release' and arm=='enabled':continue
            configurations.append((group+'-'+arm,tree,[*deps,*extra]))
    for name,tree,extra in configurations:
        flags,receipt,sources=profile.derive(out/name,args.sh4_cxx,args.kos_root,sdk,
            ['QA_MENU=0','QA_LINK=0','NMR_POOL_LOD=0','CLOTH_NATIVE=1',*extra],tree=tree,units=tuple(args.units))
        rows={}
        for unit,source in sources.items():
            guards=[Path(f) for f in flags[unit] if f.endswith('/koscache-p2/require_p2.h')]
            if guards:
                assert len(guards)==1
                key='parent' if tree==base else 'current'
                if key not in cache:
                    prepared=out/('cache-'+key)
                    builder.run([sys.executable,tree/'port/dreamcast/tools/d367/kos_cache_audit/prepare.py',
                                 '--kos-root',args.kos_root,'--output',prepared,'--patch',
                                 tree/'port/dreamcast/patches/kos-804b319-cache-p2.patch'],label='prepare-'+key)
                    cache[key]=prepared
                if not guards[0].parent.exists():shutil.copytree(cache[key],guards[0].parent)
            common=[*flags[unit],'-iquote',str(source.parent),'-x','c++','-']
            dest=out/(name+'-'+unit+'.o')
            builder.run([*common,'-c','-fstack-usage','-o',dest],cwd=source.parent,source=source.read_bytes(),label=name+'-'+unit)
            rows[unit]={'sha256':sha(dest),'bytes':dest.stat().st_size,**profile.sections(dest),
                        'stack':profile.stack_usage(dest.with_suffix('.su'))}
        arms[name]=rows
    checks=[{'arm':group+'-'+name,'unit':unit,'exact_object':arms[group+'-'+name][unit]['sha256']==arms[group+'-parent'][unit]['sha256']}
            for group in ('release','dependencies') for name in ('absent','zero') for unit in args.units]
    paths=[ROOT/'src/game/cloth.cpp',ROOT/'port/dreamcast/game/platform/native_ui.cpp',
           ROOT/'port/dreamcast/game/platform/include/native_effect_strip21.inc',
           ROOT/'port/dreamcast/game/platform/include/native_cloth_sheet11.inc',
           ROOT/'port/dreamcast/game/platform/include/native_cloth_sheet11.hpp',
           ROOT/'port/dreamcast/game/platform/include/cloth_strip_geometry11.hpp',
           ROOT/'port/dreamcast/game/effects30.mk',Path(__file__)]
    report={'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths},'baseline':args.baseline,'toolchain':toolchain,'arms':arms,'off_checks':checks,
            'accepted':all(row['exact_object'] for row in checks),'scope':'Public Make-derived affected TUs only; no gameplay, presentation or console timing'}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'accepted':report['accepted'],'off_objects':len(checks),'enabled_objects':len(args.units),'output':str(out)}))
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
