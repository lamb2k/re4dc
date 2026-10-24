"""Owned STAT census launcher: unchanged fp_run.py plus exact-child 55s cap."""
import hashlib,json,os,pathlib,runpy,subprocess,sys,threading,time
harness=pathlib.Path(sys.argv[1]);args=sys.argv[2:]
cap=pathlib.Path(args[args.index('--cap')+1]);orig=subprocess.Popen
state={'harness':str(harness),'harness_sha256':hashlib.sha256(harness.read_bytes()).hexdigest(),'deadline_seconds':55,'deadline_fired':False}
assert os.environ.get('RE4DC_EMU')=='console','console environment required'
expected=pathlib.Path(os.environ.get('RE4DC_CONSOLE_EXE',r'C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe')).resolve()
expected_sha=hashlib.sha256(expected.read_bytes()).hexdigest()
state.update(expected_executable=str(expected),expected_executable_sha256=expected_sha)
timer=None;guest=None
class BoundedPopen(orig):
    def __init__(self,*a,**kw):
        global timer,guest
        cmd=a[0] if a else kw.get('args',[])
        exe=cmd[0] if isinstance(cmd,(list,tuple)) else cmd
        is_guest=pathlib.Path(str(exe)).name.lower()=='flycast.exe'
        if is_guest:
            actual=pathlib.Path(str(exe)).resolve()
            if actual!=cap.resolve()/'flycast.exe':raise RuntimeError('guest outside exact capture path refused')
            if hashlib.sha256(actual.read_bytes()).hexdigest()!=expected_sha:raise RuntimeError('guest executable SHA mismatch')
            if guest is not None:raise RuntimeError('second guest refused')
        super().__init__(*a,**kw)
        if is_guest:
            if guest is not None:raise RuntimeError('second guest refused')
            guest=self;state.update(pid=self.pid,guest_started_monotonic=time.monotonic())
            def stop_exact_child():
                if self.poll() is None:
                    state['deadline_fired']=True
                    self.terminate()
            timer=threading.Timer(55,stop_exact_child);timer.daemon=True;timer.start()
subprocess.Popen=BoundedPopen
try:
    sys.argv=[str(harness),*args]
    runpy.run_path(str(harness),run_name='__main__')
finally:
    if timer:timer.cancel()
    if guest:
        if guest.poll() is None:guest.terminate();guest.wait(timeout=3)
        state.update(guest_exited=True,guest_observed_elapsed_s=round(time.monotonic()-state['guest_started_monotonic'],3),guest_rc=guest.poll())
    cap.mkdir(parents=True,exist_ok=True)
    (cap/'bounded-launch.json').write_text(json.dumps(state,indent=2)+'\n')

