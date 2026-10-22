#!/usr/bin/env python3
"""Whole SH4 event OFF identities and prerequisites for bounded forward receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

import qualify_event_start_rollback_sh4 as small

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
GAME=REPO/'port/dreamcast/game'
BASE='0b58098ee'
KNOB='EVD_FORWARD_RECEIPT'
SYMBOL='RE4DC_'+KNOB


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    start_free=small.space(128)
    args.out.mkdir(parents=True,exist_ok=False)
    baseline=subprocess.check_output(['git','-C',str(REPO),'show',BASE+':src/game/event.cpp'])
    candidate=(REPO/'src/game/event.cpp').read_bytes()
    baseline_make=args.out/'baseline.Makefile'
    baseline_make.write_bytes(subprocess.check_output(['git','-C',str(REPO),'show',BASE+':port/dreamcast/game/Makefile']))
    (args.out/'baseline-event.cpp').write_bytes(baseline)
    (args.out/'candidate-event.cpp').write_bytes(candidate)
    source=args.out/'event.cpp'
    rows=[]
    for cabin in (0,1):
      for txn in (0,1):
        hashes={}
        variants=[('baseline',0,baseline),('disabled',0,candidate)]
        if cabin:variants.append(('enabled',1,candidate))
        for variant,enabled,data in variants:
            out=args.out/f'cabin{cabin}-txn{txn}'/variant
            out.mkdir(parents=True)
            make=['make','--no-print-directory','-f',str(baseline_make if variant=='baseline'else GAME/'Makefile'),
                  f'OBJDIR={out}',f'CABIN_SOURCE={cabin}','ROUTE_CH21=1','ROUTE_CH22=1','ROUTE_OVL=1',
                  'EM10_SHARED=1','WORLD_STAGE_MODULES=0','ROUTE_MOVIES=1','AICA_AUDIO=1','AICA_STREAMS=1',
                  'NATIVE_STATIC=1','D349_RENDERER_STACK=1','PVR_STREAM=1',f'EVD_ADMISSION_TXN={txn}',
                  f'EVD_START_CLEANUP={txn}',f'EVD_ARAM_ALLOC_RETRY={cabin}','EVD_MODULE_VALIDATE_FIRST=1']
            if variant!='baseline':make.append(f'{KNOB}={enabled}')
            small.run([*make,str(out/'cabin-source.h'),str(out/'demo-presentation-knobs.txt')],out/'headers.log')
            dry=small.run([*make,'-n',str(out/'src/game/event.o')],out/'make-command.log')
            commands=[shlex.split(line)for line in dry.splitlines()if line.startswith('kos-c++ ')]
            assert len(commands)==1
            command=commands[0]
            command.append('-fstack-usage')
            command[command.index('../../../src/game/event.cpp')]=str(source)
            assert ('-D'+SYMBOL+'=1'in command)==bool(enabled)
            assert ('-DRE4DC_EVD_ARAM_ALLOC_RETRY=1'in command)==bool(cabin)
            assert '-DRE4DC_EVD_MODULE_VALIDATE_FIRST=1'in command
            if variant=='disabled':
                implicit=[part for part in make if part!=KNOB+'=0']
                assert small.run([*implicit,'-n',str(out/'src/game/event.o')],out/'default-command.log')==dry
            source.write_bytes(data)
            (out/'src/game').mkdir(parents=True)
            (out/'command.json').write_text(json.dumps(command,indent=2)+'\n')
            small.run(command,out/'compile.log')
            obj=out/'src/game/event.o';stripped=out/'event-stripped.o'
            small.run(['sh-elf-objcopy','--strip-debug',obj,stripped],out/'strip.log')
            size=small.run(['sh-elf-size',stripped],out/'size.txt')
            undefined=small.run(['sh-elf-nm','-u',stripped],out/'undefined.txt')
            assert ('re4dc_cabin_source_allocation'in undefined)==bool(enabled)
            stack=(out/'src/game/event.su').read_text()
            names=('EventMgr::SetEvd(','EventMgr::SetEvt(','Event::init(','int EventMgr::EvtReadSub(')
            selected=[line for line in stack.splitlines()if any(name in line for name in names)]
            lambdas=[line for line in stack.splitlines()if 'EvtReadSub'in line and 'lambda'in line]
            assert len(selected)==5
            hashes[variant]=sha(stripped)
            rows.append(dict(cabin_source=cabin,evd_admission_txn=txn,aram_alloc_retry=cabin,module_validate_first=1,
                             forward_receipt=enabled,variant=variant,event_cpp_sha256=hashlib.sha256(data).hexdigest(),
                             stripped_event_o_sha256=hashes[variant],size=size,selected_stack_usage=selected,
                             auxiliary_lambda_stack_usage=lambdas))
        assert hashes['baseline']==hashes['disabled']
    refusals=[]
    for value in ('2','-1','yes'):
        result=subprocess.run(['make','--no-print-directory','-n',KNOB+'='+value],cwd=GAME,text=True,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
        (args.out/f'invalid-{value}.log').write_text(result.stdout)
        assert result.returncode and KNOB+' must be 0 or 1'in result.stdout
        refusals.append(value)
    missing=[]
    cases=(('CABIN_SOURCE',0,0,1),('EVD_ARAM_ALLOC_RETRY',1,0,1),('EVD_MODULE_VALIDATE_FIRST',1,1,0))
    text=candidate.decode()
    begin=text.index('#if defined('+SYMBOL+')')
    end=text.index('\n#endif',text.index('extern "C" int re4dc_cabin_source_allocation',begin))+len('\n#endif')
    contract=text[begin:end]
    contract_path=args.out/'source-contract.inc';contract_path.write_text(contract+'\n')
    for required,cabin,aram,module in cases:
        result=subprocess.run(['make','--no-print-directory','-n',KNOB+'=1',f'CABIN_SOURCE={cabin}',
                               f'EVD_ARAM_ALLOC_RETRY={aram}',f'EVD_MODULE_VALIDATE_FIRST={module}'],cwd=GAME,
                              text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
        (args.out/f'missing-{required}.log').write_text(result.stdout)
        assert result.returncode and KNOB+' requires '+required in result.stdout
        command=['kos-c++','-E','-P','-x','c++','-D'+SYMBOL+'=1',f'-DRE4DC_CABIN_SOURCE={cabin}',
                 f'-DRE4DC_EVD_ARAM_ALLOC_RETRY={aram}',f'-DRE4DC_EVD_MODULE_VALIDATE_FIRST={module}',str(contract_path)]
        result=subprocess.run(command,cwd=GAME,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
        (args.out/f'direct-missing-{required}.log').write_text(result.stdout)
        assert result.returncode and KNOB+' requires '+required in result.stdout
        missing.append(required)
    small.run(['kos-c++','-E','-P','-x','c++','-D'+SYMBOL+'=1','-DRE4DC_CABIN_SOURCE=1',
               '-DRE4DC_EVD_ARAM_ALLOC_RETRY=1','-DRE4DC_EVD_MODULE_VALIDATE_FIRST=1',contract_path],args.out/'valid-contract.txt')
    signature='int EventMgr::EvtReadSub(char* nm, int aram, int em, int* out, int wait, u32 sz)'
    begin=text.index(signature);end=begin+re.search(r'^}',text[begin:],re.M).end()
    policy=args.out/'selected-policy.cpp';policy.write_text(contract+'\n'+text[begin:end]+'\n')
    ppc=[]
    for enabled in (0,1):
        ppc.append(small.run(['kos-c++','-E','-P','-x','c++','-D__PPC__=1','-DRE4DC_CABIN_SOURCE=0',
                             '-DRE4DC_EVD_ARAM_ALLOC_RETRY=0','-DRE4DC_EVD_MODULE_VALIDATE_FIRST=0',
                             f'-D{SYMBOL}={enabled}',policy],args.out/f'ppc-{enabled}.txt'))
    assert ppc[0]==ppc[1]
    output_bytes=sum(p.stat().st_size for p in args.out.rglob('*')if p.is_file())
    assert output_bytes<=20*1024**2,'Small-object output budget exceeded'
    receipt=dict(scope='Actual SH4 event.o only. No linked program, guest, full-stack, whole epoch or hardware acceptance.',
                 baseline_revision=BASE,candidate_event_sha256=hashlib.sha256(candidate).hexdigest(),qualifier_sha256=sha(Path(__file__)),
                 helper_sha256=sha(Path(small.__file__)),baseline_make_sha256=sha(baseline_make),objects=rows,
                 invalid_knobs_rejected=refusals,make_and_direct_prerequisites_rejected=missing,
                 ppc_selected_preprocessed_sha256=hashlib.sha256(ppc[0].encode()).hexdigest(),
                 ppc_limit='Selected source preprocessing, not a PPC object/full game identity.',
                 start_C_free_bytes=start_free,finish_C_free_bytes=small.space(64),start_guard=16*1024**3+128*1024**2,
                 stop_guard=16*1024**3+64*1024**2,output_bytes_before_receipt=output_bytes,output_limit_bytes=20*1024**2)
    (args.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
