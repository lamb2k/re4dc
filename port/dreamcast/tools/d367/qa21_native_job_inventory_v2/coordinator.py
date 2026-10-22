"""Startup-only helper. No stdin release; no image/input/Flycast calls."""
import ctypes,importlib.util,json,os,pathlib,sys,threading,time
P=pathlib.Path(__file__).parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    root=pathlib.Path(sys.argv[1]);cfg=json.loads((P/'config.json').read_text())
    if os.name!='nt' or root!=pathlib.Path(cfg['output']):raise RuntimeError('wrong fixture platform/output')
    backend=load('frozen_backend',P/'frozen-windows-backend.py').WindowsBackend(root,root,root,'',None)
    api=load('frozen_api',P/'frozen-native-reference-api.py').WindowsApi()
    cleanup=load('cleanup',P/'cleanup.py');inventory=load('inventory',P/'inventory.py');done=threading.Event();fired=threading.Event();job=backend.create_private_job();inner=None
    result={'qualified':False,'purpose':'startup inventory only; no game qualification','cleanup_errors':[],'snapshots':[]}
    # Pure captured-job hardstop: no filesystem/path/IPC calls on this thread.
    def guard():
        if not done.wait(3.5):
            fired.set()
            while not done.is_set():
                try:backend.checked(backend.k.TerminateJobObject(job,125))
                except BaseException as exc:cleanup.note(result['cleanup_errors'],{'operation':'guardian_job_stop',**inventory.error(exc)})
                proc=backend.inner
                if proc is not None:
                    try:backend.checked(backend.k.TerminateProcess(int(proc._handle),125))
                    except BaseException as exc:cleanup.note(result['cleanup_errors'],{'operation':'guardian_inner_stop',**inventory.error(exc)})
                done.wait(.02)
    timer=threading.Thread(target=guard,name='fixture-private-job-hardstop',daemon=True);timer.start()
    def publish(row):
        data=json.dumps(row,indent=2).encode()
        if len(data)>131072:raise RuntimeError('inventory record cap')
        (root/'inventory.json').write_bytes(data)
    def inspect(pid):
        h=backend.checked(backend.k.OpenProcess(0x101000,False,pid));item={'pid':pid};errors=[]
        try:
            # Field queries are independent: a path failure does not erase birth.
            try:item['retained_times']=backend.times(h)
            except Exception as exc:errors.append({'field':'retained_times',**inventory.error(exc)})
            try:item['identity']=backend.info(pid,h)
            except Exception as exc:errors.append({'field':'path_birth',**inventory.error(exc)})
            try:item['native']=api.process(h,job,backend.inner_identity if pid==backend.inner_identity['pid'] else item.get('identity'),require_live=True)
            except Exception as exc:errors.append({'field':'native_exact_membership',**inventory.error(exc)})
            if errors:item['query_error']=errors
            return item
        finally:api.close(h)
    try:
        result['spawn_started_monotonic']=time.monotonic()
        inner=backend.spawn_waiting(cfg['inner_argv'],job)
        result['expected_inner']=backend.inner_identity
        result['startup_seconds']=time.monotonic()-result['spawn_started_monotonic']
        (root/'startup.json').write_text(json.dumps(result,indent=2))
        # Membership mismatch is NEVER waived. First refusal ends this single fixture.
        for delay in [0,.02,.1]:
            if delay:time.sleep(delay)
            result['snapshots'].append(inventory.capture(api,job,backend.inner_identity,inspect,publish))
        result['qualified']=True
    except BaseException as exc:result['error']=inventory.error(exc)
    finally:
        # Independent actions; errors cannot skip wait/telemetry/job-empty checks.
        pinned=getattr(backend,'inner_identity',None)
        state=cleanup.job_cleanup(backend,job,inner,pinned,result['cleanup_errors'])
        while not state['safe_to_disarm']:
            result['cleanup_hold']=state
            try:(root/'cleanup-hold.json').write_text(json.dumps(result,indent=2))
            except BaseException as exc:cleanup.note(result['cleanup_errors'],{'operation':'hold_receipt',**inventory.error(exc)})
            # Guardian remains live and owns handles until BOTH proofs succeed.
            time.sleep(.02)
            state=cleanup.job_cleanup(backend,job,inner,pinned,result['cleanup_errors'])
        result.update(state)
        cleanup.disarm_if_proven(state['safe_to_disarm'],done,timer,lambda:backend.close_owned_handles(job,inner,None))
        result['hardstop_fired']=fired.is_set()
        result['qualified']=result['qualified'] and not result['cleanup_errors'] and not fired.is_set()
        (root/'coordinator-result.json').write_text(json.dumps(result,indent=2))
    return 0 if result['qualified'] else 1

if __name__=='__main__':raise SystemExit(main())
