#!/usr/bin/env python3
"""Qualify outer start rollback with actual init/manager/carrier bodies."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
sys.path.insert(0,str(HERE.parent/'cache21-fixes'))
import test_event_admission_txn as transaction


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    for own in(Path(__file__),HERE/'event_rollback_init_host.cpp'):
        (args.out/own.name).write_bytes(own.read_bytes())
    fixture=args.out/'h064-fixture'/transaction.FIXTURE_DIR;fixture.mkdir(parents=True)
    pins={}
    for name in transaction.FIXTURE_FILES:
        data=transaction.git('show',f'{transaction.FIXTURE_REF}:{transaction.FIXTURE_DIR}/{name}')
        (fixture/name).write_bytes(data);pins[name]=sha(data)
    sys.path.insert(0,str(fixture));spec=importlib.util.spec_from_file_location('h064_init_fixture',fixture/'test_motion_lifetime.py')
    h064=importlib.util.module_from_spec(spec);spec.loader.exec_module(h064)
    paths=('src/game/event.cpp','src/game/datactrl.cpp','include/event.h','include/datactrl.h','include/cManager.h','include/types.h',
           'src/game/file.cpp','src/game/file_app.cpp','include/file.h','port/dreamcast/game/platform/misc.cpp',
           'port/dreamcast/game/platform/native_event_file.cpp','port/dreamcast/game/platform/native_cabin.cpp')
    source={};selected=[]
    for name in paths:
        data=(REPO/name).read_bytes();source[name]=data.decode();pins[name]=sha(data)
        target=args.out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    # Pin the actual existing/fresh read distinction; transport execution in
    # this fixture still starts with an explicitly pre-existing ReadTbl owner.
    for name in('EventMgr::EvtReadSub','EventMgr::SetRead','EventMgr::GetRead'):
        actual,line=h064.fn(source['src/game/event.cpp'],name)
        selected.append(dict(path='src/game/event.cpp',name=name,line=line,sha256=sha(actual.encode()),execution='Inspected/pinned, not executed; GetRead has the documented pointer-width ABI adapter.'))

    def body(path,name,signature=None):
        text=source[path]
        if signature:
            begin=text.index(signature);masked=h064.fn.__globals__['mask'](text)
            opening=masked.index('{',begin)
            if name in('deleteList','addListFront') or name.startswith('PC') or path.endswith(('native_cabin.cpp','native_event_file.cpp')):
                depth=1;end=opening+1
                while depth:
                    depth+=(masked[end]=='{')-(masked[end]=='}');end+=1
            else:
                # H064's reviewed column-zero boundary handles mutually
                # exclusive preprocessor arms with duplicate opening braces.
                end=opening+re.search(r'^}',masked[opening:],re.M).end()
            result,line=h064.fn(text[begin:end],name);line+=text.count('\n',0,begin)
        else:result,line=h064.fn(text,name)
        selected.append(dict(path=path,name=name,signature=signature,line=line,sha256=sha(result.encode())))
        return result

    event=[body('src/game/event.cpp','EvtWorkNo')]
    event += [body('src/game/event.cpp',name)for name in transaction.METHODS]
    event += [body('src/game/event.cpp','EventMgr::SetEvt',signature)for signature in('int EventMgr::SetEvt(void* data, u32* key)','int EventMgr::SetEvt(char* nm, Event** out)')]
    event += [body('src/game/event.cpp',name)for name in ('EventMgr::construct','EventMgr::DelEvt','EventMgr::EvtReadExec','EventMgr::EvtFree','EventMgr::DelRead','EventMgr::IsAliveEvt','EventMgr::GetFunc','EventMgr::SetFunc','EventMgr::GetBin','Event::Event','Event::~Event','Event::init','Event::ExeEndEvt','Event::ExeFunc','Event::CalMaxCut','Event::CalMaxFrame','Event::CalMaxTotalFrame','DatTbl::DatTbl','DatTbl::~DatTbl','DatTbl::GetNumDat','DatTbl::GetDatWkNo','DatTbl::DelDatWkNo')]
    cast='EvtMgr.SetEvt((void*) addr, (u32*) &evt)';assert sum(method.count(cast)for method in event)==1
    event=[method.replace(cast,'EvtMgr.SetEvt((void*) (u32) addr, (u32*) &evt)')for method in event]
    # A named wrapper injects a packet mutation only AFTER the unchanged actual
    # total-frame method returns, to distinguish the final check from immutable
    # input failures. Only that definition binding is renamed, not its policy.
    total='int Event::CalMaxTotalFrame(int* outCut, int* outTotal)'
    assert sum(method.count(total)for method in event)==1
    event=[method.replace(total,'int Event::actual_CalMaxTotalFrame(int* outCut, int* outTotal)')for method in event]
    manager=['template <class T>\n'+body('include/cManager.h','cManager<T>::create','T* cManager<T>::create(int id)'),
             'template <class T>\n'+body('include/cManager.h','cManager<T>::countActiveWork'),
             'template <class T>\n'+body('include/cManager.h','cManager<T>::destroy'),
             'template <class T>\n'+body('src/game/event.cpp','cManager<T>::destroyNow')]
    inline=[body('include/cManager.h',name,signature)for name,signature in(('deleteList','int deleteList(T* p)'),('addListFront','void addListFront(T* p)'))]
    unit=[body('src/game/datactrl.cpp','cDataUnit::'+name)for name in('setCommand','getCommand','getCondition','isLoadOk','waitLoadOk','checkCommand','setClear','checkMallocRelease')]
    native_files=[body('port/dreamcast/game/platform/misc.cpp',name,'int '+name+'(')for name in('PCopen','PCcreat','PCclose','PCread','PClseek')]
    native_files += [body('src/game/file.cpp',name)for name in('file_open','file_close','file_read','file_seek')]
    native_files += [body('src/game/file_app.cpp',name)for name in('HDReadDebugAlloc','hdRead_malloc')]
    def fragment(path,pattern):
        match=re.search(pattern,source[path],re.M|re.S);assert match,pattern
        text=match[0];selected.append(dict(path=path,declaration=pattern,line=source[path].count('\n',0,match.start())+1,sha256=sha(text.encode())))
        return text
    contract=fragment('src/game/event.cpp',r'#if defined\(RE4DC_EVD_START_CLEANUP\).*?^#endif\n#endif')
    carrier_path='port/dreamcast/game/platform/native_event_file.cpp'
    cabin_path='port/dreamcast/game/platform/native_cabin.cpp'
    cabin_methods=[fragment(carrier_path,r'enum CarrierState \{[^}]+};'),
                   fragment(carrier_path,r'struct CabinCarrier \{.*?^};'),
                   fragment(carrier_path,r'^CabinCarrier carriers\[3\]\{\};'),
                   fragment(carrier_path,r'^bool carrier_fault;'),
                   fragment(carrier_path,r'^const char\* carrier_names\[3\]=[^\n]+'),
                   fragment(cabin_path,r'struct CabinSource \{.*?^} cabin;')]
    cabin_methods += [body(carrier_path,name,signature)for name,signature in(
        ('carrier_index','int carrier_index('),('carrier_number','unsigned carrier_number('),
        ('carrier_current','bool carrier_current('),('carrier_mram_current','bool carrier_mram_current('),
        ('re4dc_cabin_carrier_reserved','extern "C" unsigned re4dc_cabin_carrier_reserved('),
        ('re4dc_cabin_carrier_event','extern "C" int re4dc_cabin_carrier_event('),
        ('re4dc_cabin_carrier_event_deleted','extern "C" void re4dc_cabin_carrier_event_deleted('))]
    cabin_methods += [body(cabin_path,name,signature)for name,signature in(
        ('cabin_key','const char* cabin_key('),('cabin_failure','void cabin_failure('),
        ('close_audio','bool close_audio('),('re4dc_cabin_event_bound','extern "C" void re4dc_cabin_event_bound('),
        ('re4dc_cabin_event_deleted','extern "C" void re4dc_cabin_event_deleted('))]
    constructor=h064.fn((fixture/'motion_event_admission_host.cpp').read_text(),'event_at')[0]
    decl=lambda path,kind,name:re.search(kind+' '+name+r'\s*\{.*?^};',source[path],re.S|re.M)[0]
    variants=[];lifetime_controls=[]
    for rollback,cabin,handoff in((0,0,0),(1,0,0),(0,1,0),(1,1,0),(0,1,1),(1,1,1)):
        txn=cleanup=1
        out=args.out/f'rollback{rollback}-cabin{cabin}-handoff{handoff}';out.mkdir()
        types=[decl('include/event.h','struct',name)for name in('DatTblEntry','EvtHeader','EvtBinEntry','EvtPacket','EvtReadEm')]
        (out/'init_actual_types.inc').write_text('\n'.join(types)+'\n')
        (out/'init_actual_dattbl_decl.inc').write_text(decl('include/event.h','class','DatTbl')+'\n')
        (out/'init_actual_dataunit_decl.inc').write_text(decl('include/datactrl.h','class','cDataUnit')+'\n')
        (out/'init_actual_event_methods.inc').write_text('using EvtFunc=void(*)(Event*,int);\n'+'\n'.join(event)+'\n')
        (out/'init_actual_manager_inline.inc').write_text('\n'.join(inline)+'\n')
        (out/'init_actual_manager_methods.inc').write_text('\n'.join(manager)+'\n')
        (out/'init_actual_dataunit_methods.inc').write_text('\n'.join(unit)+'\n')
        modes=re.findall(r'^#define FILE_OPEN_\w+\s+\d+.*$',source['include/file.h'],re.M)
        assert len(modes)==3
        (out/'init_actual_file_modes.inc').write_text('\n'.join(modes)+'\n')
        (out/'init_actual_native_file_methods.inc').write_text('\n'.join(native_files)+'\n')
        (out/'init_actual_compile_contract.inc').write_text(contract+'\n')
        (out/'init_actual_cabin_methods.inc').write_text('\n'.join(cabin_methods)+'\n')
        (out/'init_h064_header_constructor.inc').write_text(constructor+'\n')
        argv=['g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-fno-pie','-no-pie','-Wall','-Wextra','-fpermissive','-DRE4DC_GAME=1',f'-DRE4DC_CABIN_SOURCE={cabin}',f'-DRE4DC_CABIN_COMPLETE_HANDOFF={handoff}',f'-DRE4DC_EVD_ADMISSION_TXN={txn}',f'-DRE4DC_EVD_START_CLEANUP={cleanup}',f'-DRE4DC_EVD_START_ROLLBACK={rollback}','-I'+str(out),str(HERE/'event_rollback_init_host.cpp'),'-o',str(out/'test')]
        if cabin==0 and (txn==0 or cleanup==1):
            h064.command(argv,out/'strict-compile.txt',30)
            command=[str(out/'test')];cp=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
            (out/'strict-run.command.json').write_text(json.dumps(command)+'\n');(out/'strict-run.txt').write_text(cp.stdout)
            assert cp.returncode!=0 and 'init_actual_manager_methods.inc' in cp.stdout and 'invalid vptr' in cp.stdout
            lifetime_controls.append(dict(evd_admission_txn=txn,start_cleanup=cleanup,returncode=cp.returncode,output=cp.stdout,source_boundary='Actual cManager::destroy writes p->be_flag after delete in the source no-free pool; this strict UBSan vptr diagnostic remains open, not called fixed.'))
        # Keep the source pool's existing post-destructor slot write intact.
        # Exclude only that vptr lifetime check to observe later state changes;
        # the strict diagnostic above is independently retained and reported.
        argv.insert(5,'-fno-sanitize=vptr')
        h064.command(argv,out/'compile.txt',30);result=h064.command([out/'test'],out/'run.txt',20);print(result,end='')
        variants.append(dict(evd_admission_txn=txn,start_cleanup=cleanup,start_rollback=rollback,cabin_source=cabin,cabin_complete_handoff=handoff,output=result))
    receipt=dict(scope='Actual source failed-start outer rollback with init/end/delete/manager/data-unit/carrier/cabin callbacks; UBSan state suite excludes vptr and retains strict lifetime diagnostics. Synthetic inputs, projected ABI, external services. No target/gameplay occurrence/whole read/reset ownership proof.',
        source_head=transaction.git('rev-parse','HEAD').decode().strip(),fixture_revision=transaction.FIXTURE_REF,source_sha256=pins,selected_methods=selected,variants=variants,strict_vptr_lifetime_controls=lifetime_controls,
        prior_fixture_revision='5d10f51e6f68f1c2ee5bca429f9e94d041115574',
        prior_fixture_sha256={name:sha(transaction.git('show','5d10f51e6f68f1c2ee5bca429f9e94d041115574:port/dreamcast/tools/d367/cache21-fixes/'+name))for name in('event_init_failure_host.cpp','test_event_init_failure.py')},
        host_boundaries=['Model table allocation/final free, backing-page free, player/partner/camera/light/effect/messages/sound/scenario services are explicit recorded boundaries.','GetRead native32 pointer-local and EvtReadExec signed int->pointer conversions use the prior explicit host64 ABI adapters.','PFuncTbl is pointer-width in the host projection; cUnit pool delete size uses host size_t; target layouts are not claimed.','Final-check case renames only the actual CalMaxTotalFrame definition binding and mutates the packet after its successful return. This is an injected immutable-input violation, not a normal source failure or target occurrence.','Carrier unit/allocation/module observers and audio/movie services are explicit boundaries; actual carrier admission/exact-event unbind and cabin callbacks execute. Unselected clear/free/reverse paths abort if reached.','ON tests call registered-name SetEvt directly: EvtReadExec would wait for the preserved prior live name, whose completion this fixture does not simulate. Outer read/scenario policy is not repaired or accepted here.'],
        test_sha256={p.name:sha(p.read_bytes())for p in(Path(__file__),HERE/'event_rollback_init_host.cpp')})
    (args.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
