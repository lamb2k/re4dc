#!/usr/bin/env python3
"""Whole SH4 event/native-event-file OFF identities and bounded epoch-query objects."""
import argparse,hashlib,json,re,shlex,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4];GAME=REPO/'port/dreamcast/game'
sys.path.insert(0,str(HERE))
import qualify_event_start_rollback_sh4 as small
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--baseline-ref',default='06f598ba5');args=parser.parse_args()
    start=small.space(128);args.out.mkdir(parents=True,exist_ok=False)
    def git(path):return subprocess.check_output(['git','-C',str(REPO),'show',args.baseline_ref+':'+path])
    paths={'event':'src/game/event.cpp','native':'port/dreamcast/game/platform/native_event_file.cpp'}
    source={key:{'baseline':git(path),'candidate':(REPO/path).read_bytes()}for key,path in paths.items()}
    baseline_make=args.out/'baseline.Makefile';baseline_make.write_bytes(git('port/dreamcast/game/Makefile'))
    header='port/dreamcast/game/platform/include/native_cabin.h'
    (args.out/'baseline-native_cabin.h').write_bytes(git(header));(args.out/'candidate-native_cabin.h').write_bytes((REPO/header).read_bytes())
    rows=[]
    for cabin in (0,1):
        hashes={}
        variants=[('baseline',0),('disabled',0)]+([('enabled',1)]if cabin else[])
        for variant,enabled in variants:
            out=args.out/f'cabin{cabin}'/variant;out.mkdir(parents=True)
            make=['make','--no-print-directory','-f',str(baseline_make if variant=='baseline' else GAME/'Makefile'),f'OBJDIR={out}',f'CABIN_SOURCE={cabin}',
                  'ROUTE_CH21=1','ROUTE_CH22=1','ROUTE_OVL=1','EM10_SHARED=1','WORLD_STAGE_MODULES=0','ROUTE_MOVIES=1','AICA_AUDIO=1','AICA_STREAMS=1','NATIVE_STATIC=1','D349_RENDERER_STACK=1','PVR_STREAM=1']
            if variant!='baseline':make.append(f'EVD_ARAM_ALLOC_RETRY={enabled}')
            small.run([*make,str(out/'cabin-source.h'),str(out/'demo-presentation-knobs.txt')],out/'headers.log')
            targets={'event':out/'src/game/event.o','native':out/'platform/native_event_file.o'}
            dry=small.run([*make,'-n',*map(str,targets.values())],out/'make-command.log')
            commands=[shlex.split(line)for line in dry.splitlines()if line.startswith('kos-c++ ')]
            assert len(commands)==2
            if variant=='disabled':
                implicit=[arg for arg in make if arg!='EVD_ARAM_ALLOC_RETRY=0']
                assert small.run([*implicit,'-n',*map(str,targets.values())],out/'default-command.log')==dry
            for key,path in paths.items():
                command=next(cmd for cmd in commands if str(targets[key])in cmd)
                assert ('-DRE4DC_EVD_ARAM_ALLOC_RETRY=1'in command)==bool(enabled)
                text=source[key]['baseline'if variant=='baseline'else'candidate']
                local=out/(key+'.cpp');local.write_bytes(text)
                source_arg=next(arg for arg in command if arg.endswith('src/game/event.cpp')or arg.endswith('platform/native_event_file.cpp'))
                command[command.index(source_arg)]=str(local)
                command+=['-fstack-usage','-iquote',str(GAME/'platform')]
                targets[key].parent.mkdir(parents=True,exist_ok=True)
                (out/(key+'-command.json')).write_text(json.dumps(command,indent=2)+'\n')
                small.run(command,out/(key+'-compile.log'))
                stripped=out/(key+'-stripped.o');small.run(['sh-elf-objcopy','--strip-debug',targets[key],stripped],out/(key+'-strip.log'))
                size=small.run(['sh-elf-size',stripped],out/(key+'-size.txt'))
                names=small.run(['sh-elf-nm','-C',stripped],out/(key+'-nm.txt'))
                assert ('re4dc_cabin_carrier_preload_epoch'in names)==bool(enabled)
                su=targets[key].with_suffix('.su').read_text()
                selected=[line for line in su.splitlines()if 'EventMgr::EvtReadSub('in line or 're4dc_cabin_carrier_preload_epoch('in line]
                objsha=sha(stripped.read_bytes());hashes[(variant,key)]=objsha
                rows.append(dict(cabin_source=cabin,variant=variant,enabled=enabled,object=key,source_sha256=sha(text),stripped_object_sha256=objsha,size=size,selected_stack_usage=selected))
        for key in paths:assert hashes[('baseline',key)]==hashes[('disabled',key)]
    invalid=[]
    for value in ('2','-1','yes'):
        cp=subprocess.run(['make','--no-print-directory','-n','EVD_ARAM_ALLOC_RETRY='+value],cwd=GAME,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
        (args.out/('invalid-'+value+'.log')).write_text(cp.stdout)
        assert cp.returncode and 'EVD_ARAM_ALLOC_RETRY must be 0 or 1'in cp.stdout;invalid.append(value)
    for value in (None,'0'):
        cmd=['make','--no-print-directory','-n','EVD_ARAM_ALLOC_RETRY=1']+(['CABIN_SOURCE='+value]if value is not None else[])
        cp=subprocess.run(cmd,cwd=GAME,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
        (args.out/('missing-cabin-'+str(value)+'.log')).write_text(cp.stdout)
        assert cp.returncode and 'EVD_ARAM_ALLOC_RETRY requires CABIN_SOURCE=1'in cp.stdout
    direct=[]
    for key in paths:
        text=source[key]['candidate'].decode()
        block=re.search(r'#if defined\(RE4DC_EVD_ARAM_ALLOC_RETRY\).*?^#endif\n#endif',text,re.M|re.S)[0]
        contract=args.out/(key+'-contract.cpp');contract.write_text(block+'\n')
        cp=subprocess.run(['kos-c++','-E','-P','-x','c++','-DRE4DC_EVD_ARAM_ALLOC_RETRY=1',str(contract)],cwd=GAME,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
        (args.out/(key+'-direct-missing-cabin.log')).write_text(cp.stdout)
        assert cp.returncode and 'EVD_ARAM_ALLOC_RETRY requires CABIN_SOURCE'in cp.stdout;direct.append(key)
    text=source['event']['candidate'].decode();begin=text.index('int EventMgr::EvtReadSub(');end=begin+re.search(r'^}',text[begin:],re.M).end()
    policy=args.out/'selected-ppc-policy.cpp';policy.write_text(text[begin:end]+'\n')
    ppc=[small.run(['kos-c++','-E','-P','-x','c++','-D__PPC__=1','-DRE4DC_CABIN_SOURCE=0',f'-DRE4DC_EVD_ARAM_ALLOC_RETRY={flag}',policy],args.out/f'ppc{flag}.txt')for flag in(0,1)]
    assert ppc[0]==ppc[1]
    receipt=dict(scope='Whole actual SH4 event.o/native_event_file.o only; no linked program/overlay/guest/hardware/whole-reset acceptance.',baseline_revision=args.baseline_ref,
        source_sha256={path:sha(source[key]['candidate'])for key,path in paths.items()},header_sha256=sha((REPO/header).read_bytes()),qualifier_sha256=sha(Path(__file__).read_bytes()),
        start_C_free_bytes=start,finish_C_free_bytes=small.space(64),start_guard=16*small.GIB+128*small.MIB,stop_guard=16*small.GIB+64*small.MIB,
        invalid_values_rejected=invalid,direct_source_missing_cabin_rejected=direct,ppc_selected_preprocessed_sha256=sha(ppc[0].encode()),objects=rows)
    (args.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
