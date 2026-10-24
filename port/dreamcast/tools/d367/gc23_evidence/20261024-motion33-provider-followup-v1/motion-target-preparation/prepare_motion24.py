"""PREPARATION ONLY: git/file reads and source export; no SDK command exists here."""
from pathlib import Path
import argparse, hashlib, json, os, shlex, subprocess, tempfile

TREE=Path('/root/work/lanes/gc-motion24')
ORIGINAL=Path('/root/work/lanes/gc-port23')
PARENT='870789095c4c14fbdbf22043447b249063d2ec3a'
CURRENT='aab201ceac0e18107f64a3212398afe916793327'
RUNTIME='fce285ddd77ced898b40f49ae310b91a539b7b5d'
FROZEN_TEST='5e6b7d8c0f76e7431f1a7787459faa41fb0b507c'
FULL=Path('/root/work/lanes/gc-port23-full-target2-scratch')
SEALED=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-port23-20261023/full-target-static1d63-current')
OWN=Path(__file__).resolve().parent
PREFIX='port/dreamcast/game/'
UNITS=['platform/native_ui.cpp','platform/native_model.cpp','platform/native_actor_fast.cpp','model_bridge.cpp']
HELPER='platform/gc_asset_motion_unknown.cpp'
RUNTIME_DIFF={PREFIX+x for x in UNITS+[HELPER,'platform/include/gc_asset_motion_unknown.h','platform/include/native_actor_leon_pipe.inc','gc_asset_gate.mk']}
SDK=Path('/root/work/kos-re4dc-d367')
TOOLS=Path('/opt/toolchains/dc/sh-elf/bin')
CAP=256*1024**2

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def git(*args,binary=False):
    # This is the sole process entry point. No SDK/wrapper/version/Make query.
    return subprocess.check_output(['git','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(TREE),*args],text=not binary)

def commands(arm):
    rows={}
    for line_number,line in enumerate((FULL/arm/'build.log').read_text().splitlines(),1):
        if not line.startswith('kos-c++ '):continue
        args=shlex.split(line)
        if '-c' not in args:continue
        unit=args[args.index('-c')+1]
        if unit not in UNITS+['platform/gc_asset_gate.cpp']:continue
        if unit in rows:raise ValueError('duplicate actual command '+unit)
        rows[unit]={'args':args,'line':line_number,'raw':line}
    if set(rows)!=set(UNITS+['platform/gc_asset_gate.cpp']):raise ValueError('missing actual compile')
    return rows

def deps(path):
    text=path.read_text().replace('\\\n',' ')
    # Stop at the first phony -MP target, retaining only the actual first rule.
    return shlex.split(text.split('\n',1)[0].split(':',1)[1])

def canonical(args,arm):
    result=[]
    for arg in args:
        if arg.startswith(('-DRE4DC_GC_ASSET_GATE=','-DRE4DC_GC_ASSET_CATALOG_SHA256=',
            '-DRE4DC_GC_ASSET_COARSE_LEON=','-DRE4DC_GC_ASSET_LEON_HAND_PACK=')):continue
        result.append(arg.replace(str(FULL/arm/'out/obj'),'@GENERATED'))
    result[result.index('-o')+1]='@OUTPUT'
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true',required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    head=git('rev-parse','HEAD').strip();current=git('rev-parse',CURRENT).strip()
    if head!=current or git('status','--porcelain').strip():raise ValueError('current tree not exact clean aab')
    metadata=set(git('diff','--name-only',FROZEN_TEST,current).splitlines())
    if metadata!={'port/dreamcast/tools/d367/gc_port23/MOTION-UNKNOWN24.md','port/dreamcast/tools/d367/gc_port23/motion24-host-summary.json'}:raise ValueError('frozen source/tests changed outside exact metadata files')
    if git('diff','a132648e8199b50a5ac51cec4d339fe7dbc60135',PARENT,'--','port/dreamcast/game').strip():raise ValueError('parent runtime not a132')
    for tree,expected in [(ORIGINAL,'1d63cffe3a232c402418f2f2d919e7abae476957'),(Path('/root/work/lanes/gc-catalog24'),PARENT)]:
        base=['git','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(tree)]
        if subprocess.check_output(base+['rev-parse','HEAD'],text=True).strip()!=expected or subprocess.check_output(base+['status','--porcelain'],text=True).strip():raise ValueError('frozen original tree changed '+str(tree))
    if git('diff',RUNTIME,current,'--','port/dreamcast/game').strip():raise ValueError('runtime differs from fce')
    parent=git('rev-parse',PARENT).strip();changed=git('diff','--name-only',parent,current).splitlines()
    runtime={name for name in changed if not name.startswith('port/dreamcast/tools/')}
    if runtime!=RUNTIME_DIFF:raise ValueError('runtime scope mismatch '+str(runtime))
    pins={};source_pins={};old_dependencies={};generated={};project=set()
    def pin(path):
        path=Path(path);key=str(path)
        row={'bytes':path.stat().st_size,'sha256':sha(path)}
        if key in pins and pins[key]!=row:raise ValueError('input changed during preparation '+key)
        pins[key]=row;return row
    seal=json.loads((SEALED/'SHA256-MANIFEST.json').read_text())
    for name,row in seal.items():
        got=pin(SEALED/name)
        if got!=row:raise ValueError('sealed full-link receipt mismatch '+name)
    receipt=json.loads((SEALED/'receipt.json').read_text())
    pin(SEALED/'SHA256-MANIFEST.json')
    if receipt['source']!='1d63cffe3a232c402418f2f2d919e7abae476957':raise ValueError('wrong full-normal source')
    for name,expected in receipt['pins'].items():
        if pin(name)['sha256']!=expected:raise ValueError('sealed full input drift '+name)
    full_harness=OWN.parents[1]/'gc-port23/full-target-static1d63-r2-20261024.py'
    pin(full_harness)
    if "SOURCE_DATE_EPOCH='1760000000'" not in full_harness.read_text():raise ValueError('historical fixed epoch changed')
    actual={arm:commands(arm) for arm in ['off','on']}
    for arm in ['off','on']:
        if pin(FULL/arm/'build.log')['sha256']!=receipt['arms'][arm]['buildlog_sha256']:raise ValueError('actual build log drift')
        pin(FULL/arm/'command.json')
        for unit in UNITS+['platform/gc_asset_gate.cpp']:
            row=actual[arm][unit];a=row['args']
            if '-matomic-model=soft-gusa' not in a or '-std=gnu++20' not in a:raise ValueError('compiler profile drift')
            gate=[x for x in a if x.startswith('-DRE4DC_GC_ASSET_GATE=')]
            catalog=[x for x in a if x.startswith('-DRE4DC_GC_ASSET_CATALOG_SHA256=')]
            if gate!=(['-DRE4DC_GC_ASSET_GATE=1'] if arm=='on' else []):raise ValueError('actual Gate flag mismatch')
            if arm=='on' and bool(catalog)!=(unit!='model_bridge.cpp'):raise ValueError('GAME/PLATFORM group mismatch')
            if any('MOTION_UNKNOWN' in x for x in a):raise ValueError('historical command contains new knob')
            d=FULL/arm/'out/obj'/(str(Path(unit).with_suffix('.d')));pin(d)
            paths=[]
            for name in deps(d):
                path=(ORIGINAL/PREFIX/name).resolve() if not Path(name).is_absolute() else Path(name)
                paths.append(str(path));pin(path)
                if path.is_relative_to(ORIGINAL):project.add(str(path.relative_to(ORIGINAL)))
                elif path.is_relative_to(FULL/arm/'out/obj'):generated[str(path)]=(arm,str(path.relative_to(FULL/arm/'out/obj')))
            for i,arg in enumerate(a):
                if arg!='-include':continue
                path=Path(a[i+1]);path=path if path.is_absolute() else (ORIGINAL/PREFIX/path).resolve()
                pin(path)
                if path.is_relative_to(ORIGINAL):project.add(str(path.relative_to(ORIGINAL)))
                elif path.is_relative_to(FULL/arm/'out/obj'):generated[str(path)]=(arm,str(path.relative_to(FULL/arm/'out/obj')))
            old_dependencies[arm+':'+unit]={'path':str(d),'sha256':pins[str(d)]['sha256'],'paths':paths,'scope':'Historical -MMD user-header dependencies only; not a fresh or complete SDK-system-header proof.'}
    for unit in UNITS+['platform/gc_asset_gate.cpp']:
        if canonical(actual['off'][unit]['args'],'off')!=canonical(actual['on'][unit]['args'],'on'):raise ValueError('OFF/ON flags differ beyond exact GC knobs '+unit)
    # Fixed source/header supplement for newly enabled code, including an optional
    # Leon pipe whose production flag is zero. No optional knob is invented.
    project.update(RUNTIME_DIFF)
    project.update(PREFIX+'platform/include/'+name for name in ['gc_asset_gate.h','gc_asset_motion_unknown.h','native_actor_leon_pipe.inc'])
    binaries=[SDK/'utils/build_wrappers/kos-c++',SDK/'utils/build_wrappers/kos-cc',TREE/'port/dreamcast/kos-env.sh']
    binaries += [TOOLS/name for name in ['sh-elf-g++','sh-elf-size','sh-elf-nm','sh-elf-objcopy']]
    binaries += [Path('/opt/toolchains/dc/sh-elf/libexec/gcc/sh-elf/15.2.0/cc1plus'),Path('/opt/toolchains/dc/sh-elf/sh-elf/bin/as')]
    providers=[SDK/'lib/dreamcast/libkallisti.a',Path('/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/libgcc.a'),Path('/opt/toolchains/dc/sh-elf/sh-elf/lib/libc.a')]
    # Use existing real full ON ELF as candidate definitions, not a new map/link.
    providers += [FULL/'on/out/re4dc-game.elf']
    for path in binaries+providers:pin(path)
    pin(__file__)
    if args.output:
        out=args.output.resolve()
        if out.exists():raise ValueError('never overwrite prepared exports')
        if not out.is_relative_to(Path('/dev/shm')):raise ValueError('source export must stay in RAM')
        out.mkdir()
    else:out=Path(tempfile.mkdtemp(prefix='gc-motion24-target-prep-',dir='/dev/shm'))
    # Exact git objects only; original worktrees/headers/builds are never modified.
    for label,ref in [('parent',parent),('current',current)]:
        for name in sorted(project):
            exists=subprocess.run(['git','-C',str(TREE),'cat-file','-e',ref+':'+name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
            if not exists:
                if label=='parent' and name in {PREFIX+HELPER,PREFIX+'platform/include/gc_asset_motion_unknown.h'}:continue
                raise ValueError('source dependency missing from exact ref '+name)
            data=git('show',ref+':'+name,binary=True);dest=out/label/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            source_pins[label+':'+name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    for path,(arm,name) in generated.items():
        dest=out/'generated'/arm/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(Path(path).read_bytes())
        if sha(dest)!=pins[path]['sha256']:raise ValueError('generated header copy drift')
    arms=[]
    for unit in UNITS+[HELPER]:
        specs=[('current','off','absent'),('current','off','zero'),('current','on','absent'),('current','on','zero'),('current','on','on')]
        if unit!=HELPER:specs=[('parent','off','absent'),('parent','on','absent')]+specs
        for label,gate,motion in specs:
            template=unit if unit!=HELPER else 'platform/gc_asset_gate.cpp'
            a=actual[gate][template]['args'].copy()
            a=[x for x in a if x not in ['-MMD','-MP','-MD']]
            for option in ['-MF','-MT','-MQ']:
                while option in a:i=a.index(option);del a[i:i+2]
            for old,(arm,name) in generated.items():a=[str(out/'generated'/arm/name) if x==old else x for x in a]
            if motion!='absent':a.append('-DRE4DC_GC_ASSET_MOTION_UNKNOWN='+('1' if motion=='on' else '0'))
            a[a.index('-c')+1]=unit
            tag=label+'-'+Path(unit).stem+'-gate'+('1' if gate=='on' else '0')+'-motion'+motion
            a[a.index('-o')+1]=str(out/'objects'/(tag+'.o'));a.append('-fstack-usage')
            arms.append({'tag':tag,'label':label,'source':parent if label=='parent' else current,'unit':unit,'gate':int(gate=='on'),'motion':motion,'cwd':str(out/label/PREFIX),'argv':a,'raw_command_template':actual[gate][template],
                'group':'GAME' if unit=='model_bridge.cpp' else 'PLATFORM','new_helper_template':unit==HELPER,
                'empty_required':unit==HELPER and motion!='on','changes_to_actual_command':['output/source path for new helper only','generated-header relocation to exact copied bytes','remove dependency side-effect flags; generate full dependencies in allocated run','add -fstack-usage','add only explicit Motion value when requested']})
    if len(arms)!=33 or sum(r['motion']=='on' for r in arms)!=5:raise ValueError('matrix size drift')
    for name,row in pins.items():
        if sha(name)!=row['sha256']:raise ValueError('pinned input changed before export seal '+name)
    size=sum(x.stat().st_size for x in out.rglob('*') if x.is_file())
    if size>CAP:raise ValueError('source exports exceed proposed owned cap')
    plan={'status':'PREPARED_NOT_EXECUTED','head':current,'parent':parent,'runtime':RUNTIME,'test_source':FROZEN_TEST,'export':str(out),'source_export_bytes':size,'changed_files':changed,'runtime_diff':sorted(runtime),'source_pins':source_pins,'input_pins':pins,'historical_dependencies':old_dependencies,'arms':arms,'arm_count':33,'ON_count':5,
        'wrapper_queries':0,'sdk_commands':0,'slot_acquired':False,'execution_environment_required':{'KOS_BASE':str(SDK),'KOS_CC_BASE':'/opt/toolchains/dc/sh-elf','wrapper':str(SDK/'utils/build_wrappers/kos-c++'),'SOURCE_DATE_EPOCH':'1760000000','JOBS':'1'},'allocations_required':['root approval after source CLEAR and prep review','one canonical gc-motion24 lease and one shared SDK slot','jobs1 release priority','256MiB RLIMIT_AS/owned output cap; C>=24GiB throughout','source/commands/all resolved dependencies/provider/tool before-after pins'],
        'future_run_analysis':['fresh compiler -M dependency pass per arm, pin every full system/project/generated dependency before compile; verify afterward','strip-debug object identity: parent/current Gate0absent and currentGate0zero; parent/current Gate1absent and currentGate1zero per existing unit','all four helper OFF variants section/symbol-empty; new helper ON BSS <=32 raw B, RAII/local fields4 each','size -A, nm defined/undefined, object/stripped/SU hashes for every arm','Motion1-vs-parentGate1absent sections and per-function self frames; retain nested-source chain caveats','new undefineds resolved by five selected objects or pinned real SDK/libgcc/libc/fullON ELF candidates; no aliases/stubs/final map claim','stop on any mismatched pin, missing dependency, compiler/provider error, cap/floor violation; preserve failed arm/log before changes'],
        'known_limits':['No command in this tool can invoke SDK/Make/wrapper/version query; git and byte hashing only','No fresh full programme/map/heap/highwater/runtime/guest/coverage or provenance claim','LEON_NATIVE_PIPE actual profile0: optional pipe controls are source/host only, not active target code pricing','Raw/MV/blob/lake/alternate world routes remain partial; production profile MV_SHADOWS1 does not imply Motion coverage','Historical -MMD does not include system headers; allocated compiler -M pass must seal the actual full dependency closure','New helper inherits only the exact generic PLATFORM command, not native_ui/actor overrides','Original full1d63 receipt identity is historical; this matrix compares catalog870789 to Motionaab, no new14-overlay/full-link acceptance']}
    (out/'PREPARATION.json').write_text(json.dumps(plan,indent=2)+'\n')
    (OWN/'PREPARATION.json').write_text(json.dumps(plan,indent=2)+'\n')
    manifest={str(f.relative_to(out)):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.rglob('*') if f.is_file()}
    (OWN/'EXPORT-MANIFEST.json').write_text(json.dumps({'export':str(out),'files':manifest},indent=2)+'\n')
    print(json.dumps({'status':plan['status'],'arm_count':33,'ON_count':5,'export':str(out),'export_bytes':size,'sdk_commands':0,'manifest_sha256':sha(OWN/'EXPORT-MANIFEST.json')},indent=2))

if __name__=='__main__':main()
