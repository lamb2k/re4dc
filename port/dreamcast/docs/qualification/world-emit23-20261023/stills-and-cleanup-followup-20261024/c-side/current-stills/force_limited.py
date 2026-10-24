"""Explicit FPS-limited owned-cap config wrapper; no guest on import and no shared config writes."""
import hashlib,json,os,pathlib,re,runpy,subprocess,sys,time
class ConfigRefused(ValueError):pass
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def enforce_text(text):
 if len(re.findall(r'(?mi)^\[config\]\s*$',text))!=1:raise ConfigRefused('exactly one config section required')
 vals=re.findall(r'(?mi)^\s*aica\.LimitFPS\s*=\s*(.*?)\s*$',text)
 if len(vals)>1 or (vals and vals[0].lower() not in ['yes','true','1']):raise ConfigRefused('pre-existing wrong/duplicate LimitFPS refused before guest')
 if not re.search(r'(?mi)^rend\.EmulateFramebuffer\s*=\s*(yes|true|1)\s*$',text):raise ConfigRefused('framebuffer emulation must already be enabled')
 text=re.sub(r'(?mi)^\s*aica\.LimitFPS\s*=.*(?:\n|$)','',text)
 text=re.sub(r'(?mi)^\[config\]\s*$', '[config]\naica.LimitFPS = yes',text,count=1)
 if re.findall(r'(?mi)^aica\.LimitFPS\s*=\s*(.*?)\s*$',text)!=['yes']:raise ConfigRefused('explicit canonical FPS limit missing')
 return text

def prepare_owned_config(cap):
 if os.environ.get('FP_NOLIMIT')!='0' or os.environ.get('RE4DC_EMU')!='console':raise ConfigRefused('explicit FP_NOLIMIT0 + console required before guest')
 cap=pathlib.Path(cap);cfg=cap/'emu.cfg';before=cfg.read_bytes();text=enforce_text(cfg.read_text());cfg.write_text(text)
 if enforce_text(cfg.read_text())!=cfg.read_text():raise ConfigRefused('config is not canonical/idempotent')
 receipt={'scope':'owned cap config only, before exact child spawn','FP_NOLIMIT':os.environ['FP_NOLIMIT'],'RE4DC_EMU':os.environ['RE4DC_EMU'],'aica.LimitFPS':'yes','before_sha256':hashlib.sha256(before).hexdigest(),'actual_config_sha256':sha(cfg),'wrapper_sha256':sha(__file__),'host_monotonic':time.monotonic()}
 with (cap/'limitfps-prelaunch.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
 (cap/'limitfps-prelaunch.cfg').write_bytes(cfg.read_bytes());return receipt

def main():
 harness=pathlib.Path(sys.argv[1]);args=sys.argv[2:];cap=pathlib.Path(args[args.index('--cap')+1]);original=subprocess.Popen
 if original.__name__!='BoundedPopen':raise ConfigRefused('census-bound-run exact55 outer guard required')
 if os.environ.get('FP_NOLIMIT')!='0' or os.environ.get('RE4DC_EMU')!='console':raise ConfigRefused('explicit limited console environment required')
 guest=None
 class LimitedPopen(original):
  def __init__(self,*a,**kw):
   nonlocal guest
   cmd=a[0] if a else kw.get('args',[]);owned=isinstance(cmd,(list,tuple)) and pathlib.Path(str(cmd[0])).name.lower()=='flycast.exe'
   if owned:
    if guest is not None:raise ConfigRefused('second owned guest refused')
    if pathlib.Path(str(cmd[0])).resolve()!=cap.resolve()/'flycast.exe':raise ConfigRefused('foreign capture executable refused')
    prepare_owned_config(cap)
   super().__init__(*a,**kw)
   if owned:guest=self
 subprocess.Popen=LimitedPopen
 try:sys.argv=[str(harness),*args];runpy.run_path(str(harness),run_name='__main__')
 finally:
  if (cap/'limitfps-prelaunch.json').exists():
   text=(cap/'emu.cfg').read_text();record={'guest_started':guest is not None,'pid':guest.pid if guest else None,'actual_config_sha256':sha(cap/'emu.cfg'),'aica.LimitFPS_yes':re.findall(r'(?mi)^aica\.LimitFPS\s*=\s*(.*?)\s*$',text)==['yes'],'config_still_matches_prelaunch':sha(cap/'emu.cfg')==json.loads((cap/'limitfps-prelaunch.json').read_text())['actual_config_sha256']}
   (cap/'limitfps-run-binding.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
