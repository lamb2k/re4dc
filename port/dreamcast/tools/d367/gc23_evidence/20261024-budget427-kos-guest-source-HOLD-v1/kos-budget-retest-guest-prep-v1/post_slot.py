"""Actual root3/global16 admission BEFORE WindowsPython; never acquires locks."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time,types
HERE=Path(__file__).resolve().parent
def main():
 assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
 m=sys.modules['guest_common']
 a=argparse.ArgumentParser();a.add_argument('--case',type=int,required=True);v=a.parse_args();k=m.context();g,gpath,seal=m.authorize(k);c=m.case(v.case,k)
 assert v.case in g['case_order'];nonce=os.environ.get('GC_BUDGET_RETEST_ADMISSION_NONCE');assert nonce and len(nonce)==32
 assert os.environ.get('TRACE_SLOTS')=='16' and os.environ.get('RE4DC_EMU')=='console' and os.environ.get('FP_NOLIMIT')=='1' and os.environ.get('RE4DC_MAX_FLYCASTS')=='16'
 locks=m.kernel_locks();m.check_fresh(c);m.check_inputs(g,k);m.metadata_guard(g,k);k.baseline_check(links_changed=True);m.check_poststage(g,k,c['arm']);resources=m.capacity(k,k.ADMIT);assert not m.release_active(),'Release priority'
 ps=Path('/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe');m.verify(ps,m.read(HERE/'INPUT-PINS.json')['powershell'])
 command="@{C_free=(Get-PSDrive -Name C).Free;flycast_count=@(Get-Process -Name 'flycast*' -ErrorAction SilentlyContinue).Count}|ConvertTo-Json -Compress"
 state=json.loads(subprocess.check_output([str(ps),'-NoProfile','-NonInteractive','-Command',command],text=True,timeout=8))
 assert type(state['C_free']) is int and state['C_free']>=k.ADMIT and type(state['flycast_count']) is int and state['flycast_count']<16
 m.check_fresh(c);assert not m.release_active();m.capacity(k,k.ADMIT);m.kernel_locks()
 c={**c,'index':v.case}
 # Replace only the independently pinned Pillow entry with our pre-Popen
 # source/config/owned-process witness; it invokes that exact Pillow loader.
 argv=m.windows_command(c,gpath,seal)
 m.publish_admission(HERE/'attempts'/(c['name']+'-ADMISSION.json'),dict(phase='AUTHENTICATED_BEFORE_WINDOWS_PYTHON',case=v.case,pid=os.getpid(),pgid=os.getpgrp(),nonce=nonce,grant_sha256=m.sha(gpath),guest_kit_sha256=seal,prepared_monotonic=time.monotonic(),locks=locks,resources=resources,Windows=state,argv=argv,cap_absent=True,cache_absent=True,helpers_verified=True,poststage=g['poststage'],before_WindowsPython=True))
 os.execve(argv[0],argv,os.environ)
if __name__=='__main__':main()
