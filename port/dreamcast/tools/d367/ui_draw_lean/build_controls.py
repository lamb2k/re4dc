#!/usr/bin/env python3
"""Independent-base OFF preprocessing/object identity for the UI draw lane.

The base is materialized with git archive and its own Make/header expansion.
Each selected translation unit is compiled in baseline/absent/explicit-zero/ON
forms; unchanged units also require ON identity. No game executable is linked.
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
import build_profile as p
BASELINE='d5c1ceab9e06461462669b3ce1d28a379747a74a'


def normalize(flags,profile,root):
    return [word.replace(str(profile),'<PROFILE>').replace(str(root),'<SOURCE>') for word in flags]


def headers(row,profile):
    return {str(Path(path).relative_to(profile)):value for path,value in row['generated_headers'].items()}


def run(args):
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    tree=out/'baseline-tree';tree.mkdir()
    archive=subprocess.check_output(['git','archive',args.baseline],cwd=p.ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:source.extractall(tree,filter='data')
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    units=args.unit or list(p.PRIMARY_UNITS);variants=args.variant or list(p.PROFILES)
    with p.source_tree(tree):
        old_flags,old_profile=p.derive(out/'baseline-profile',cxx,kos,sdk,variants=variants,units=units)
    current={arm:p.derive(out/(arm+'-profile'),cxx,kos,sdk,variants=variants,units=units,lean=lean)
             for arm,lean in (('absent',None),('zero',0),('on',1))}
    watched=[p.DC/'game/game30.mk',*[ (p.DC/'game'/p.SPECIFICATIONS[unit][1]).resolve() for unit in units]]
    hashes={str(path.relative_to(p.ROOT)):p.sha(path) for path in watched}
    builder=p.Build(out);production={};make_checks={};off=inactive=0
    for variant in variants:
        production[variant]={};make_checks[variant]={}
        for unit in units:
            flags=old_flags[variant][unit]
            reference=normalize(flags,out/'baseline-profile',tree)
            reference_headers=headers(old_profile['profiles'][variant][unit],out/'baseline-profile')
            defines_knob=False
            for arm,(new_flags,new_profile) in current.items():
                actual=normalize(new_flags[variant][unit],out/(arm+'-profile'),p.ROOT)
                if arm=='on':
                    defines_knob=actual.count('-DRE4DC_UI_DRAW_LEAN=1')==1
                    if defines_knob:actual.remove('-DRE4DC_UI_DRAW_LEAN=1')
                assert actual==reference,(variant,unit,arm,'Make flags')
                assert headers(new_profile['profiles'][variant][unit],out/(arm+'-profile'))==reference_headers,(variant,unit,arm,'headers')
            make_checks[variant][unit]=dict(off_flags_identical=True,headers_identical=True,on_defines_knob=defines_knob)
            rows={}
            for arm in ('baseline','absent','zero','on'):
                source=((tree if arm=='baseline' else p.ROOT)/'port/dreamcast/game'/p.SPECIFICATIONS[unit][1]).resolve()
                selected=flags if arm=='baseline' else current[arm][0][variant][unit]
                extra=['-DRE4DC_UI_DRAW_LEAN=0'] if arm=='zero' else []
                label=f'{variant}-{unit}-{arm}'
                for suffix,phase in (('ii',['-E','-P']),('o',['-c','-fstack-usage'])):
                    target=out/(label+'.'+suffix)
                    builder.run([*selected,*extra,'-x','c++','-',*phase,'-o',target],
                        cwd=source.parent,source=source.read_bytes(),label=label+'-'+suffix)
                    row=dict(bytes=target.stat().st_size,sha256=p.sha(target))
                    if suffix=='o':row.update(p.sections(target),stack_usage=p.stack_usage(target.with_suffix('.su')))
                    rows[arm+'.'+suffix]=row
                    if arm in ('absent','zero'):
                        assert target.read_bytes()==(out/(f'{variant}-{unit}-baseline.'+suffix)).read_bytes(),(label,suffix,'OFF identity')
                        off+=1
                    if arm=='on' and not defines_knob:
                        assert target.read_bytes()==(out/(f'{variant}-{unit}-baseline.'+suffix)).read_bytes(),(label,suffix,'unchanged ON unit')
                        inactive+=1
                if arm in ('baseline','on'):
                    (out/(label+'.disassembly.txt')).write_bytes(builder.run([str(cxx).removesuffix('g++')+'objdump',
                        '-drC',out/(label+'.o')],label=label+'-objdump'))
            production[variant][unit]=rows
            print('PASS',variant,unit,flush=True)
    assert any(row['on_defines_knob'] for units in make_checks.values() for row in units.values()),'Make does not wire the knob'
    for source,digest in hashes.items():assert p.sha(p.ROOT/source)==digest,(source,'changed during qualification')
    result=dict(status='PASS',baseline=args.baseline,knob='UI_DRAW_LEAN',scope=__doc__,source_sha256=hashes,
        compiler=builder.run([cxx,'--version'],label='compiler').decode().splitlines()[0],
        production=production,make_identity=make_checks,baseline_profile=old_profile,
        profiles={arm:profile for arm,(_,profile) in current.items()},
        off_identity_comparisons=off,unchanged_on_comparisons=inactive)
    (out/'build-controls.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','sh4-cxx','kos-root','sdk-root'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--baseline',default=BASELINE)
    parser.add_argument('--unit',action='append',choices=list(p.SPECIFICATIONS))
    parser.add_argument('--variant',action='append',choices=list(p.PROFILES))
    r=run(parser.parse_args());print(json.dumps(dict(status=r['status'],off_identity_comparisons=r['off_identity_comparisons'],unchanged_on_comparisons=r['unchanged_on_comparisons'])))


if __name__=='__main__':main()
