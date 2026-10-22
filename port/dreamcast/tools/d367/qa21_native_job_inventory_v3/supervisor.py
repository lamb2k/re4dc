"""Default-off ONE native inventory supervisor; requires separately allocated literal bytes."""
import argparse,ctypes,hashlib,importlib.util,json,os,pathlib,shutil,subprocess,sys,threading,time
P=pathlib.Path(__file__).parent

def load_cleanup():
    spec=importlib.util.spec_from_file_location('fixture_cleanup',P/'cleanup.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def hard_parent(done,state):
    if done.wait(9.5):return
    # No child -> safe parent-only abort. With a child, NEVER silently drop a
    # retained live process: checked termination/retry until signaled boundary.
    while not done.is_set():
        proc=state.get('proc')
        if proc is None or state.get('finalized'):os._exit(125)
        try:
            state['terminate'](int(proc._handle))
        except BaseException as exc:state['note'](state['errors'],{'operation':'absolute_termination',**state['failure'](exc)})
        try:
            stamp=state['times'](int(proc._handle))
            if state['wait_status'](int(proc._handle))==0 and stamp[1]>=stamp[0]>0 and (state.get('birth') is None or stamp[0]==state['birth']):os._exit(125)
        except BaseException as exc:state['note'](state['errors'],{'operation':'absolute_finalization',**state['failure'](exc)})
        done.wait(.02)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    cleanup=load_cleanup();absolute_done=threading.Event();state={'proc':None,'finalized':False,'errors':[],'note':cleanup.note,'failure':cleanup.failure};absolute_guard=threading.Thread(target=hard_parent,args=(absolute_done,state),daemon=True);absolute_guard.start()
    ap=argparse.ArgumentParser();ap.add_argument('--tools-sha256',required=True);ap.add_argument('--execute-root-allocation',action='store_true');args=ap.parse_args()
    if not args.execute_root_allocation:raise RuntimeError('default-off; root allocation required')
    if sha(P/'manifest.json')!=args.tools_sha256:raise RuntimeError('exact reviewed tools seal required')
    if os.name!='nt':raise RuntimeError('Windows only')
    cfg=json.loads((P/'config.json').read_text());template=(P/'FUTURE_ROOT_ALLOCATION_BYTES.json').read_bytes()
    if pathlib.Path(cfg['allocation']).read_bytes()!=template:raise RuntimeError('exact root allocation bytes required')
    for row in json.loads((P/'manifest.json').read_text())['files']:
        path=pathlib.Path(row['path']) if row['absolute'] else P/row['path']
        if sha(path)!=row['sha256']:raise RuntimeError('source pin changed: '+str(path))
    root=pathlib.Path(cfg['output'])
    if root.resolve()!=root.absolute() or root.exists():raise RuntimeError('fresh canonical fixture output required')
    if shutil.disk_usage('C:/').free<cfg['admission']:raise RuntimeError('fresh admission refused')
    root.mkdir();(root/'KEEP').write_text('Owned one-shot native startup inventory; preserve failures. No image/input/guest.\n')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
    k.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(ctypes.c_ulonglong)]*4
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];k.WaitForSingleObject.restype=ctypes.c_ulong
    def terminate(handle):
        if not k.TerminateProcess(handle,125):raise ctypes.WinError(ctypes.get_last_error())
    def retained_times(handle):
        stamp=[ctypes.c_ulonglong() for _ in range(4)]
        if not k.GetProcessTimes(handle,*[ctypes.byref(x) for x in stamp]):raise ctypes.WinError(ctypes.get_last_error())
        return [x.value for x in stamp]
    state.update(terminate=terminate,times=retained_times,wait_status=lambda h:k.WaitForSingleObject(h,0))
    k.GetCompressedFileSizeW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)];k.GetCompressedFileSizeW.restype=ctypes.c_ulong
    def usage():
        total=4096
        for file in root.rglob('*'):
            if not file.is_file():total+=4096;continue
            high=ctypes.c_ulong();ctypes.set_last_error(0);low=k.GetCompressedFileSizeW(str(file),ctypes.byref(high))
            if low==0xffffffff and ctypes.get_last_error():raise ctypes.WinError(ctypes.get_last_error())
            total+=max(file.stat().st_size,(high.value<<32)|low)
        return total
    proc=None;done=threading.Event();guard=None;result={'qualified':False,'no_flycast':True,'no_input':True,'cleanup_errors':state['errors']};origin=time.monotonic()
    try:
        proc=subprocess.Popen([sys.executable,'-B',str(P/'coordinator.py'),str(root)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        state['proc']=proc
        # Parent owns only coordinator's retained Popen HANDLE. Child owns sole job.
        # Hard thread never writes/enumerates/joins; parent cap <=10s, child <=5s.
        def deadline():
            if done.wait(max(0,4.75-(time.monotonic()-origin))):return
            while not done.is_set():
                try:terminate(int(proc._handle))
                except BaseException as exc:cleanup.note(result['cleanup_errors'],{'operation':'deadline_terminate',**cleanup.failure(exc)})
                done.wait(.02)
        guard=threading.Thread(target=deadline,name='fixture-retained-parent-deadline',daemon=True);guard.start()
        times=[ctypes.c_ulonglong() for _ in range(4)]
        if not k.GetProcessTimes(int(proc._handle),*[ctypes.byref(x) for x in times]):raise ctypes.WinError(ctypes.get_last_error())
        buf=ctypes.create_unicode_buffer(32768);n=ctypes.c_ulong(len(buf))
        if not k.QueryFullProcessImageNameW(int(proc._handle),0,buf,ctypes.byref(n)):raise ctypes.WinError(ctypes.get_last_error())
        if os.path.normcase(os.path.abspath(buf.value))!=os.path.normcase(os.path.abspath(sys.executable)):raise RuntimeError('coordinator retained executable mismatch')
        state['birth']=times[0].value
        result['coordinator']={'pid':proc.pid,'creation_filetime':times[0].value,'path':buf.value}
        while proc.poll() is None:
            if usage()>=4194304:raise RuntimeError('cumulative logical/allocated output cap')
            if shutil.disk_usage('C:/').free<19394461696:raise RuntimeError('runtime floor')
            time.sleep(.02)
        result['exit_code']=proc.wait(timeout=.2)
        child=json.loads((root/'coordinator-result.json').read_text())
        result['qualified']=result['exit_code']==0 and child.get('qualified') is True and child.get('private_job_empty') is True and child.get('hardstop_fired') is False
    except BaseException as exc:result['error']=type(exc).__name__+': '+str(exc)
    finally:
        # Every kill/wait/finalization attempt is independent. Missing proof
        # retains both deadline threads and the exact process HANDLE.
        finalized=cleanup.retained_cleanup(proc,terminate,retained_times,state['wait_status'],state.get('birth'),result['cleanup_errors'])
        while not finalized['signaled_finalized']:
            result['qualified']=False;result['cleanup_hold']=finalized
            try:(root/'supervisor-hold.json').write_text(json.dumps(result,indent=2))
            except BaseException as exc:cleanup.note(result['cleanup_errors'],{'operation':'hold_receipt',**cleanup.failure(exc)})
            time.sleep(.02)
            finalized=cleanup.retained_cleanup(proc,terminate,retained_times,state['wait_status'],state.get('birth'),result['cleanup_errors'])
        state['finalized']=True;result.update(finalized)
        try:
            if proc is not None and finalized.get('actual_seconds',6)>5:raise RuntimeError('child bound failed')
            result['qualified']=result['qualified'] and not result['cleanup_errors']
            result['charged_bytes']=usage();result['free_bytes']=shutil.disk_usage('C:/').free
            if result['charged_bytes']+131072>=4194304 or result['free_bytes']<19394461696:raise RuntimeError('final resource gate')
            result['parent_seconds']=time.monotonic()-origin
            if result['parent_seconds']>10:raise RuntimeError('parent bound failed')
            (root/'supervisor-result.json').write_text(json.dumps(result,indent=2))
            if usage()>=4194304 or shutil.disk_usage('C:/').free<19394461696:raise RuntimeError('postwrite resource gate')
        finally:
            if guard is not None:cleanup.disarm_if_proven(finalized['signaled_finalized'],done,guard,lambda:None)
            absolute_done.set();absolute_guard.join(timeout=.2)
            if absolute_guard.is_alive():raise RuntimeError('absolute guard failed to join; handle retained')
            if proc is not None:proc._handle.Close()
    return 0 if result['qualified'] else 1

if __name__=='__main__':raise SystemExit(main())
