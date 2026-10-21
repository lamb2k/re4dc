#!/usr/bin/env python3
"""Requalify sealed forward controls with nonreturning target diagnostic semantics."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[4]
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    floor=18*1024**3+128*1024**2;start=shutil.disk_usage('/mnt/c').free;assert start>=floor;a.out.mkdir(parents=True,exist_ok=False)
    source_files=('src/game/event.cpp','src/game/dvd.cpp','src/game/datactrl.cpp','port/dreamcast/game/platform/native_event_file.cpp','port/dreamcast/game/platform/mem.cpp')
    pins={}
    for path in source_files:
        data=(REPO/path).read_bytes();pins[path]=sha(data);out=a.out/'source'/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    sealed={}
    for path in('src/game/event.cpp','src/game/dvd.cpp','src/game/datactrl.cpp','port/dreamcast/game/platform/native_event_file.cpp','port/dreamcast/tools/d367/cache21-callers/cabin_forward_characterization_host.cpp','port/dreamcast/tools/d367/cache21-callers/event_start_rollback_host.cpp','port/dreamcast/tools/d367/cache21-callers/test_cabin_forward_characterization.py'):
        baseline=subprocess.check_output(['git','-C',str(REPO),'show','bf250af8e:'+path]);current=(REPO/path).read_bytes();assert current==baseline,path;sealed[path]=sha(current)
    result=subprocess.run([sys.executable,str(HERE/'test_cabin_forward_characterization.py'),'--forward-pair','--out',str(a.out/'sealed-returning')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45);(a.out/'sealed-returning.log').write_text(result.stdout);assert result.returncode==0,result.stdout
    source=(HERE/'cabin_forward_characterization_host.cpp').read_text();needle='static void re4dc_missing(const char*){++diagnostics;}';assert source.count(needle)==1
    source=source.replace(needle,'static void forward_missing_observer();\nstatic void re4dc_missing(const char*){++diagnostics;forward_missing_observer();}').replace('int main(){','int unexecuted_original_forward_matrix(){')
    generated=a.out/'forward_diagnostic_base.cpp';generated.write_text(source)
    rows=[];variants=[]
    for enabled in(0,1):
        out=a.out/f'guard{enabled}';out.mkdir();fixture=a.out/'sealed-returning'/f'forward{enabled}-cabin1'
        command=['g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-fno-pie','-no-pie','-Wall','-Wextra','-fpermissive','-DRE4DC_GAME=1','-DRE4DC_EVENT_FILES=1','-DRE4DC_CABIN_SOURCE=1','-DRE4DC_EVD_ADMISSION_TXN=1','-DRE4DC_EVD_START_CLEANUP=1','-DRE4DC_EVD_START_ROLLBACK=1','-DRE4DC_EVD_DEBUG_READ_CLEANUP=0','-DRE4DC_EVD_EXEC_FAILURE_CLEANUP=0','-DRE4DC_EVD_ARAM_ALLOC_RETRY=1','-DRE4DC_EVD_READ_RELEASE_REFS=0','-DRE4DC_EVD_READ_ADMISSION_PREFLIGHT=0','-DRE4DC_EVD_MODULE_VALIDATE_FIRST=1',f'-DRE4DC_EVD_FORWARD_RECEIPT={enabled}','-I'+str(a.out),'-I'+str(fixture),'-I'+str(HERE),str(HERE/'forward_diagnostic_host.cpp'),'-o',str(out/'test')]
        assert shutil.disk_usage('/mnt/c').free>=floor
        result=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30);(out/'compile.txt').write_text(result.stdout);assert result.returncode==0,result.stdout
        variants.append(dict(forward_receipt=enabled,command=command))
        for stop in(0,1):
          for refs in(1,2):
           for fresh in(0,1):
            for mode in range(33):
                if fresh and(mode==1 or mode>=28):continue
                result=subprocess.run([str(out/'test'),str(mode),str(fresh),str(refs),str(stop)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
                assert result.returncode in(0,73),result.stdout
                row=json.loads(result.stdout);rows.append(row)
                assert row['mode']==mode and row['guard']==enabled and row['diagnostic_stop']==stop
                fatal_modes=set(range(1,11))|{12,21,25,27}
                if enabled:fatal_modes-=set(range(11,22))
                halt=bool(stop and mode in fatal_modes)
                assert(row['outcome']=='halt')==halt and(result.returncode==73)==halt,row
                assert row['pushes']==1 and not row['pops'] and row['effect_count']==refs-1 and row['effect_final_dispatches']==int(refs==1),row
                if halt:
                    assert row['diagnostics']==1 and row['swapped']==0 and row['result']==-1,row
                    assert row['output']==(0x90000000 if fresh else 0),row
                    assert row['borrow_depth']==int(mode in set(range(4,11))|{25,27}),row
                else:
                    success=not enabled or mode==0 or mode==1 or mode>=28
                    assert row['result']==int(success) and row['swapped']==int(success),row
                    expected=(0x90008000 if mode==12 else 0x90000000)if success else 0
                    assert row['output']==expected and not row['borrow_depth'],row
                if mode==7:
                    assert row['state']==6 and row['role']==1 and row['phase']==2 and row['readers']==1 and row['pending_requests']==1 and row['backing_bytes']==0x11 and row['module_bytes']==0x5a,row
                if mode==11:
                    assert row['generation']==42 and row['post_token']==(0 if enabled else 42),row
    groups=[]
    for enabled in(0,1):
      for stop in(0,1):
        selected=[r for r in rows if r['guard']==enabled and r['diagnostic_stop']==stop]
        group=dict(forward_receipt=enabled,diagnostic_stop=stop,cases=len(selected),halt=sum(r['outcome']=='halt'for r in selected),return_failure=sum(r['result']==0 for r in selected),return_success=sum(r['result']==1 for r in selected));groups.append(group);print(json.dumps(group))
    assert groups==[dict(forward_receipt=0,diagnostic_stop=0,cases=120,halt=0,return_failure=0,return_success=120),dict(forward_receipt=0,diagnostic_stop=1,cases=120,halt=54,return_failure=0,return_success=66),dict(forward_receipt=1,diagnostic_stop=0,cases=120,halt=0,return_failure=104,return_success=16),dict(forward_receipt=1,diagnostic_stop=1,cases=120,halt=46,return_failure=60,return_success=14)]
    (a.out/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
    total=sum(p.stat().st_size for p in a.out.rglob('*')if p.is_file());assert total<=20*1024**2
    receipt=dict(scope='Read-only nonreturning/returning diagnostic qualification of unchanged bf250 forward source/fixtures.480 process-isolated observations plus original120 OFF/120 ON returning controls.',head=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),source_sha256=pins,sealed_bf250_identities=sealed,qualifier_sha256=sha(Path(__file__).read_bytes()),driver_sha256=sha((HERE/'forward_diagnostic_host.cpp').read_bytes()),generated_adapter_sha256=sha(generated.read_bytes()),cases_sha256=sha((a.out/'cases.json').read_bytes()),groups=groups,variants=variants,boundaries=['Target re4dc_missing logs and sleeps forever. Host _Exit73 captures at diagnostic entry and does not unwind automatic borrow scope. It does not execute the crash hook, scheduler sleep loop or real target hardware.','Original bf250 source/tests are byte-identical. Generated clone adds an observer to the declared diagnostic boundary and renames the unused original main; current source bodies and injected mutation controls remain the sealed fixture projections.','Native forward/DMA/provider/allocation/module/effect helper/callback boundaries remain as documented by the original receipt. Mutation callability is adversarial source qualification, not a proven production callback occurrence.','A fatal diagnostic prevents final caller publication/cleanup. Fresh out was already written by the earlier module lookup and remains nonzero at halt. Error returns clear output only when the caller branch is reached.','No full program, linked image, actual hardware ARQ, Flycast, route occurrence or whole archive lifetime acceptance.'],resource_guard=dict(start_C_free_bytes=start,finish_C_free_bytes=shutil.disk_usage('/mnt/c').free,floor_bytes=floor,output_bytes_before_receipt=total,output_limit_bytes=20*1024**2))
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
