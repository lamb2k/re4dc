#!/usr/bin/env python3
"""Build29 raw SH-4 Make-derived TU identity and enabled-composition gates.

The independently archived integration commit is the control. Compiler input
is unmodified production source; only debug records and preprocessor line
markers are consistently disabled. No private game data, whole-image link,
console execution or measured hardware cache behavior is claimed.
"""
import argparse
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
DC=HERE.parents[2]
ROOT=DC.parents[1]
BASELINE='5f104e301f328c56a07ce9f57e3fb94d758d4999'
KNOBS=('FALLBACK_AUDIT29','FALLBACK_SCAN29')
spec=importlib.util.spec_from_file_location('b29_previous_controls',HERE.parent/'build26/build_controls.py')
previous=importlib.util.module_from_spec(spec);sys.modules[spec.name]=previous;spec.loader.exec_module(previous)
shared,profile=previous.shared,previous.profile
UNITS={name:(f'src/game/{name}.o',f'../../../src/game/{name}.cpp')
       for name in ('main','motion','atari','cloth','esp','esp_efm','trans_ot')}
UNITS.update({name:(f'platform/{name}.o',f'platform/{name}.cpp') for name in
              ('native_actor_fast','native_motion','native_ui','dvd_read_safe','audio_aica','audio_strm','gx_stub')})
UNITS.update({name:(name+'.o',name+'.cpp') for name in ('model_bridge','qa_menu','fallback_audit29')})
profile.UNITS.update(UNITS)
BASE_UNITS=tuple(unit for unit in UNITS if unit!='fallback_audit29')
QA=previous.QA
COMPOSED=['DRAW_FALLBACK_AUDIT=1','DRAW_SETUP_AUDIT=1','DRAW_SETUP_AUDIT_XLU=1',
          'ACTOR_LIGHT_FAST_ONLY=1','QA_LINK_REVIEW28=1','ACTOR_CLIP_FRONT26=1','SCENERY_CLIP_INDEXED26=1']
OFF_PROFILES={
    'plain':QA+['QA_LINK=0','DRAW_FALLBACK_AUDIT=0'],
    'audit':QA+['QA_LINK=0','DRAW_FALLBACK_AUDIT=1'],
    'composed':QA+['QA_LINK=1']+COMPOSED,
}
ON_PROFILES={
    'audit':QA+['QA_LINK=0','DRAW_FALLBACK_AUDIT=1','FALLBACK_AUDIT29=1'],
    'audit-link':QA+['QA_LINK=1','QA_LINK_REVIEW28=1','DRAW_FALLBACK_AUDIT=1','FALLBACK_AUDIT29=1'],
    'scan':QA+['QA_LINK=0','FALLBACK_SCAN29=1'],
    'scan-audit':QA+['QA_LINK=1','QA_LINK_REVIEW28=1','DRAW_FALLBACK_AUDIT=1','FALLBACK_AUDIT29=1','FALLBACK_SCAN29=1'],
    'all':QA+['QA_LINK=1','FALLBACK_AUDIT29=1','FALLBACK_SCAN29=1']+COMPOSED,
}
OBJECT_FIELDS=('PLATFORM_OBJS','GAME_OBJS','GAME_LDFLAGS')

def probe(out,tree,kos,sdk,options):
    out.mkdir(parents=True,exist_ok=False)
    fields=(*KNOBS,'QA_MENU','QA_LINK','DRAW_FALLBACK_AUDIT',*OBJECT_FIELDS)
    query=out/'query.mk'
    query.write_text('.PHONY: b29-state\nb29-state:\n\t@:\n'+
                     '\n'.join(f'$(info B29_STATE {k}=$({k}))' for k in fields)+'\n')
    command,_=profile.make_command(out,tree,kos,sdk,options,'b29-state')
    command[3:3]=['-f','Makefile','-f',str(query)]
    result=subprocess.run(command,cwd=tree/'port/dreamcast/game',capture_output=True,text=True)
    output=result.stdout+result.stderr;(out/'make.log').write_text(output)
    state=dict(line[len('B29_STATE '):].split('=',1) for line in output.splitlines() if line.startswith('B29_STATE '))
    return dict(command=command,returncode=result.returncode,state=state,error=output[-3000:] if result.returncode else None)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','sh4-cxx','kos-root','sdk-root','toolchain-receipt'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--baseline',default=BASELINE)
    parser.add_argument('--only',choices=('off','on'))
    parser.add_argument('--composition',help='Preliminary single profile; omit for complete qualification')
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    cxx,kos,sdk=args.sh4_cxx.resolve(),args.kos_root.resolve(),args.sdk_root.resolve()
    builder=profile.Build(out);prefix=str(cxx).removesuffix('g++')
    toolchain=previous.verify_toolchain(builder,cxx,kos,sdk,args.toolchain_receipt.resolve())
    baseline=subprocess.check_output(['git','rev-parse',args.baseline],cwd=ROOT,text=True).strip()
    tree=out/'baseline-tree';tree.mkdir()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',baseline],cwd=ROOT))) as archive:
        archive.extractall(tree,filter='data')
    paths=[(DC/'game'/source).resolve() for _,source in UNITS.values()]
    paths += [Path(__file__),HERE.parent/'build26/build_controls.py',HERE.parent/'build24/build_controls.py',
              HERE.parent/'build18/build_profile.py',DC/'game/Makefile',DC/'build-public.sh',
              DC/'tools/d367/build-r21.sh',DC/'tools/d367/rr/recipe.conf',
              DC/'tools/d367/kos_cache_audit/prepare.py',DC/'patches/kos-804b319-cache-p2.patch',
              *sorted((DC/'game').glob('*.mk'))]
    frozen={str(p.relative_to(ROOT)):profile.sha(p) for p in paths}
    artifacts,recipes,flag_rows,states,closures,links,cache={},{},{},{},{},{},{}
    disabled,enabled,rejected=[],[],[]

    def compile_unit(name,unit,flags,sources,source_tree,zeros=()):
        source=sources[unit]
        guards=[Path(f) for f in flags[unit] if f.endswith('/koscache-p2/require_p2.h')]
        if guards:
            assert len(guards)==1
            key='baseline' if source_tree==tree else 'current'
            if key not in cache:
                prepared=out/('kos-cache-'+key)
                builder.run([sys.executable,source_tree/'port/dreamcast/tools/d367/kos_cache_audit/prepare.py',
                             '--kos-root',kos,'--output',prepared,'--patch',
                             source_tree/'port/dreamcast/patches/kos-804b319-cache-p2.patch'],label='prepare-cache-'+key)
                cache[key]=json.loads((prepared/'prepare.json').read_text())
            destination=guards[0].parent
            if not destination.exists():shutil.copytree(out/('kos-cache-'+key),destination)
            for p in (guards[0],destination/'tree/kernel/arch/dreamcast/include/arch/cache.h'):
                recipes[name]['profiles'][unit]['generated_headers'][str(p)]=profile.sha(p)
        common=[*flags[unit],*['-DRE4DC_'+k+'=0' for k in zeros],'-iquote',str(source.parent)]
        row={}
        for suffix,phase in (('ii',['-E','-P']),('o',['-c','-fstack-usage','-MMD','-MF',out/f'{name}-{unit}.d'])):
            dest=out/f'{name}-{unit}.{suffix}'
            builder.run([*common,'-x','c++','-',*phase,'-o',dest],cwd=source.parent,
                        source=source.read_bytes(),label=f'{name}-{unit}-{suffix}')
            row[suffix]=dict(bytes=dest.stat().st_size,sha256=profile.sha(dest))
            if suffix=='o':
                row[suffix].update(profile.sections(dest),stack_usage=profile.stack_usage(dest.with_suffix('.su')))
                deps=shared.dependencies(out/f'{name}-{unit}.d',source_tree,source.parent)
                closures.setdefault(name,{})[unit]=deps
                if source_tree==ROOT:
                    for p,digest in deps.items():
                        assert frozen.get(p,digest)==digest,(p,'input changed during gate')
                        frozen[p]=digest
        artifacts.setdefault(name,{})[unit]=row

    if args.only!='on':
        for kind,options in OFF_PROFILES.items():
            if args.composition and kind!=args.composition:continue
            for arm,zeros in (('baseline',()),('absent',()),('zero',KNOBS)):
                name=kind+'-'+arm;source_tree=tree if arm=='baseline' else ROOT
                extra=[k+'=0' for k in zeros]
                flags,recipes[name],sources=profile.derive(out/name,cxx,kos,sdk,options+extra,tree=source_tree,units=BASE_UNITS)
                flag_rows[name]=flags
                for unit in BASE_UNITS:
                    if arm!='baseline':
                        before=[shared.normalized(f,out/(kind+'-baseline'),tree) for f in flag_rows[kind+'-baseline'][unit]]
                        after=[shared.normalized(f,out/name,ROOT) for f in flags[unit]]
                        assert before==after,(name,unit,'disabled Make flags changed')
                    compile_unit(name,unit,flags,sources,source_tree,zeros)
                    if arm!='baseline':
                        for suffix in ('ii','o'):
                            assert (out/f'{name}-{unit}.{suffix}').read_bytes()==(out/f'{kind}-baseline-{unit}.{suffix}').read_bytes(),(name,unit,suffix)
                            disabled.append(dict(profile=kind,control=arm,unit=unit,artifact=suffix,identical=True))
                    print('PASS',name,unit,flush=True)
                states[name]=probe(out/(name+'-make'),source_tree,kos,sdk,options+extra)
                assert states[name]['returncode']==0,states[name]
                if arm!='baseline':
                    assert all(states[name]['state'][k]=='0' for k in KNOBS),states[name]
                    for field in OBJECT_FIELDS:
                        assert shared.normalized(states[name]['state'][field],out/(name+'-make'),ROOT)==shared.normalized(
                            states[kind+'-baseline']['state'][field],out/(kind+'-baseline-make'),tree),(name,field)
    if args.only!='off':
        for kind,options in ON_PROFILES.items():
            if args.composition and kind!=args.composition:continue
            name='on-'+kind
            units=BASE_UNITS+(('fallback_audit29',) if 'FALLBACK_AUDIT29=1' in options else ())
            flags,recipes[name],sources=profile.derive(out/name,cxx,kos,sdk,options,units=units)
            for unit in units:compile_unit(name,unit,flags,sources,ROOT)
            combined=out/(name+'-combined.o')
            builder.run([prefix+'ld','-m','shlelf','-r',*[out/f'{name}-{unit}.o' for unit in units],'-o',combined],label=name+'-link')
            undefined=builder.run([prefix+'nm','-u','-C',combined],label=name+'-undefined').decode()
            assert not [line for line in undefined.splitlines() if 'fa29' in line or 'fallback29' in line or 'scan29' in line],undefined
            links[name]=dict(sha256=profile.sha(combined),new_hooks_resolved=True,
                             scope='Relocatable link; ordinary game/KOS/prior diagnostic references remain unresolved')
            states[name]=probe(out/(name+'-make'),ROOT,kos,sdk,options)
            assert states[name]['returncode']==0,states[name]
            for knob in KNOBS:assert states[name]['state'][knob]==str(int(knob+'=1' in options)),(name,knob,states[name])
            enabled.append(dict(profile=kind,compiled_units=list(units),new_hooks_resolved=True))
            print('PASS enabled',kind,flush=True)
    for knob in KNOBS:
        for value in ('','2','0 1'):
            state=probe(out/f'reject-{len(rejected)}',ROOT,kos,sdk,QA+[knob+'='+value])
            assert state['returncode']!=0,(knob,value,'bad assignment accepted')
            rejected.append(dict(knob=knob,value=value,**state))
    for missing in ('QA_MENU=0','DRAW_FALLBACK_AUDIT=0'):
        state=probe(out/f'reject-{len(rejected)}',ROOT,kos,sdk,ON_PROFILES['audit']+[missing])
        assert state['returncode']!=0,(missing,'audit prerequisite accepted')
        rejected.append(dict(missing=missing,**state))
    prerequisites=[(ON_PROFILES['audit-link']+['QA_LINK_REVIEW28=0'],'QA_LINK_REVIEW28=0')]
    prerequisites += [(ON_PROFILES['scan']+[key+'=0'],key+'=0') for key in
                      ('NATIVE_ACTOR_FAST','NATIVE_ACTOR','MODEL_STREAM_FIX','NATIVE_ACTOR_PRELIT')]
    for options,missing in prerequisites:
        state=probe(out/f'reject-{len(rejected)}',ROOT,kos,sdk,options)
        assert state['returncode']!=0,(missing,'new knob prerequisite accepted')
        rejected.append(dict(missing=missing,**state))
    release=probe(out/'release-make',ROOT,kos,sdk,['NMR_POOL_LOD=0'])
    assert release['returncode']==0,release
    assert all(release['state'][k]=='0' for k in KNOBS),release
    assert 'fallback_audit29.o' not in release['state']['PLATFORM_OBJS'],release
    assert frozen=={p:profile.sha(ROOT/p) for p in frozen},'compiler/build inputs changed during gate; rerun'
    assert disabled or enabled,'empty profile selection'
    report=dict(status='PASS',scope=__doc__,baseline=baseline,gate_half=args.only or 'both',composition=args.composition,
                source_sha256=frozen,knobs=KNOBS,**toolchain,off_identity_comparisons=len(disabled),
                disabled_identity=disabled,enabled_compiles=enabled,artifacts=artifacts,profiles=recipes,
                dependency_sha256=closures,make_states=states,partial_links=links,make_rejections=rejected,
                kos_cache_preparations=cache,release_state=release,
                validation_only_overrides=dict(NMR_POOL_LOD=0,reason='Private selected Ganado LOD inputs unavailable; same override on control and candidate.'))
    (out/'target-controls.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',off_comparisons=len(disabled),enabled=len(enabled),receipt=str(out/'target-controls.json'))))

if __name__=='__main__':main()
