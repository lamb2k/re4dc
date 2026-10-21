#!/usr/bin/env python3
"""Characterize actual condition4 allocation refusal and its complete unit deltas."""
import argparse,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
sys.path.insert(0,str(HERE.parent/'cache21-fixes'))
import test_event_admission_txn as transaction
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    fixture=args.out/'fixture'/transaction.FIXTURE_DIR;fixture.mkdir(parents=True)
    loader=fixture/'test_motion_lifetime.py'
    loader.write_bytes(transaction.git('show',transaction.FIXTURE_REF+':'+transaction.FIXTURE_DIR+'/test_motion_lifetime.py'))
    audit=fixture/'motion_consumer_audit.py'
    audit.write_bytes(transaction.git('show',transaction.FIXTURE_REF+':'+transaction.FIXTURE_DIR+'/motion_consumer_audit.py'))
    sys.path.insert(0,str(fixture));spec=importlib.util.spec_from_file_location('aram_h064',loader)
    h064=importlib.util.module_from_spec(spec);spec.loader.exec_module(h064)
    data=(REPO/'src/game/datactrl.cpp').read_bytes();text=data.decode()
    header=(REPO/'include/datactrl.h').read_bytes()
    (args.out/'datactrl.cpp').write_bytes(data);(args.out/'datactrl.h').write_bytes(header)
    methods=[];pins=[]
    for name in ('setCommand','getCommand','getCondition','isUseOk','waitUseOk','setLoadToMram','setMallocInfo','checkMallocRelease','checkCommand','checkCondition','setClear'):
        body,line=h064.fn(text,'cDataUnit::'+name);methods.append(body)
        pins.append(dict(name=name,line=line,sha256=sha(body.encode())))
    declaration=re.search(r'class cDataUnit\s*\{.*?^};',header.decode(),re.M|re.S)[0]
    variants=[]
    for cabin in (0,1):
        out=args.out/f'cabin{cabin}';out.mkdir()
        (out/'aram_actual_unit_decl.inc').write_text(declaration+'\n')
        (out/'aram_actual_unit_methods.inc').write_text('\n'.join(methods)+'\n')
        argv=['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-fpermissive','-fsanitize=undefined','-fno-sanitize-recover=all','-DRE4DC_GAME=1','-DRE4DC_EVENT_FILES=1',f'-DRE4DC_CABIN_SOURCE={cabin}','-I'+str(out),str(HERE/'aram_allocation_refusal_host.cpp'),'-o',str(out/'test')]
        h064.command(argv,out/'compile.txt',30)
        result=h064.command([out/'test'],out/'run.txt',15);print(result,end='')
        variants.append(dict(cabin_source=cabin,output=result))
    receipt=dict(scope='Read-only actual cDataUnit allocation/command/wait/clear characterization. Allocation failure and event-file install/heap/free/native carrier services are boundaries. No runtime repair/generation/reset/target/gameplay occurrence acceptance.',source_head=transaction.git('rev-parse','HEAD').decode().strip(),source_sha256={'src/game/datactrl.cpp':sha(data),'include/datactrl.h':sha(header)},selected_methods=pins,variants=variants,test_sha256={p.name:sha(p.read_bytes())for p in(Path(__file__),HERE/'aram_allocation_refusal_host.cpp')})
    (args.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
