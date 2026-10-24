"""Windows exact child, fixed300s including termination grace; direct pinned source."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time,threading,types,re
HERE=Path(__file__).resolve().parent
def load(name):
 pins=json.loads((HERE/'SOURCE-SEAL.json').read_text())['members'];p=HERE/(name+'.py');b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==pins[p.name]['sha256'];m=types.ModuleType(name);m.__file__=str(p);sys.modules[name]=m;exec(compile(b,str(p),'exec',dont_inherit=True),m.__dict__);return m
def main():
 assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
 a=argparse.ArgumentParser();a.add_argument('--grant',required=True,type=Path);a.add_argument('--grant-sha',required=True);a.add_argument('--seal',required=True);a.add_argument('--arm',required=True,choices=['off','on']);a.add_argument('--cleanup',action='store_true');v=a.parse_args()
 assert hashlib.sha256((HERE/'SOURCE-SEAL.json').read_bytes()).hexdigest()==v.seal
 c=load('core');c.own_seal(v.seal);assert c.sha(v.grant)==v.grant_sha;g=c.read(v.grant);c.grant(g)
 owner=load('owned_process');cap=Path(c.win(c.FINAL/('h2-'+v.arm)));pin=c.read(HERE/'INPUTS.json');expected=pin['helpers']['console']['identity']
 if v.cleanup:
  if (cap/'OWNED-GUEST.json').exists():
   ident=c.read(cap/'OWNED-GUEST.json');assert Path(ident['path']).resolve()==(cap/'flycast.exe').resolve() and ident['sha256']==expected['sha256'];c.fresh(cap/'OWNED-CLEANUP.json',owner.terminate(ident))
  return
 assert sys.pycache_prefix and not Path(sys.pycache_prefix).exists() and not cap.exists()
 assert os.environ.get('RE4DC_EMU')=='console' and os.environ.get('FP_NOLIMIT')=='1' and os.environ.get('RE4DC_MAX_FLYCASTS')=='16'
 pillow=Path(pin['pillow_launcher']['windows_path']);c.verify(pillow,pin['pillow_launcher']['identity']);m=c.module('h2_pillow',pillow,pin['pillow_launcher']['identity']['sha256']);m.install(pillow.with_name('PILLOW-PINS.json'))
 argv=c.route(g,v.arm);harness=Path(argv[0]);c.verify(harness,pin['helpers']['harness']['identity'])
 for n in ['warp','pad']:c.verify(c.win(pin['fixtures'][n]['path']),pin['fixtures'][n]['identity'])
 original=subprocess.Popen;guest=None;timer=None;state=dict(deadline_seconds=c.LIMIT,timer_seconds=c.TIMER,deadline_fired=False,guest_exited=False,harness_sha256=c.sha(harness),expected_executable_sha256=expected['sha256'])
 class OwnedPopen(original):
  def __init__(self,*args,**kwargs):
   nonlocal guest,timer
   cmd=args[0] if args else kwargs.get('args',[]);is_guest=isinstance(cmd,(list,tuple)) and Path(str(cmd[0])).name.lower()=='flycast.exe'
   if is_guest:
    assert guest is None and list(cmd)==[str(cap/'flycast.exe'),'disc.gdi'] and Path(kwargs.get('cwd','')).resolve()==cap.resolve();c.verify(cmd[0],expected)
    text=(cap/'emu.cfg').read_text();assert re.findall(r'^aica\.LimitFPS\s*=\s*(\S+)\s*$',text,re.M)==['no'] and re.findall(r'^rend\.vsync\s*=\s*(\S+)\s*$',text,re.M)==['no']
    c.fresh(cap/'PRE-POPEN.json',dict(arm=v.arm,config=c.row(cap/'emu.cfg'),LimitFPS='no',console=True,before_guest=True,argv=cmd))
   before_create=time.monotonic()
   super().__init__(*args,**kwargs)
   if is_guest:
    guest=self;state.update(pid=self.pid,guest_started_monotonic=before_create)
    try:
     ident=owner.identity(int(self._handle),self.pid);assert ident['sha256']==expected['sha256'] and Path(ident['path']).resolve()==(cap/'flycast.exe').resolve();c.fresh(cap/'OWNED-GUEST.json',ident)
     def stop():
      if self.poll() is None:state['deadline_fired']=True;self.terminate()
     timer=threading.Timer(max(0,c.TIMER-(time.monotonic()-state['guest_started_monotonic'])),stop);timer.daemon=True;timer.start()
    except BaseException:self.terminate();self.wait(timeout=3);raise
 subprocess.Popen=OwnedPopen
 try:
  sys.argv=argv;scope={'__file__':str(harness),'__name__':'__main__'};exec(compile(harness.read_bytes(),str(harness),'exec',dont_inherit=True),scope)
 finally:
  subprocess.Popen=original
  if timer:timer.cancel()
  if guest:
   if guest.poll() is None:guest.terminate()
   guest.wait(timeout=max(.01,c.LIMIT-(time.monotonic()-state['guest_started_monotonic'])))
   state.update(guest_exited=True,guest_observed_elapsed_s=time.monotonic()-state['guest_started_monotonic'],guest_rc=guest.poll())
  if cap.exists():c.fresh(cap/'bounded-launch.json',state)
if __name__=='__main__':main()