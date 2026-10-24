"""Pinned source/config before guest Popen; existing Pillow/exact55 child unchanged."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,types
if not __debug__:raise RuntimeError('Optimized Python refused')
HERE=Path(__file__).resolve().parent
def row(p):return dict(size=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def fresh(p,j):
 with Path(p).open('x') as f:json.dump(j,f,indent=1);f.write('\n')
def config_guard(text):
 assert re.findall(r'^aica\.LimitFPS\s*=\s*(\S+)\s*$',text,re.M)==['no'],'Actual explicit unthrottled config required'
 assert re.findall(r'^rend\.vsync\s*=\s*(\S+)\s*$',text,re.M)==['no']
def module(name,p,pin):
 raw=Path(p).read_bytes();assert len(raw)==pin['size'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
 m=types.ModuleType(name);m.__file__=str(p);sys.modules[name]=m;exec(compile(raw,str(p),'exec',dont_inherit=True),m.__dict__);return m
def record_owned(process,path,expected,owner,write):
 # This runs before BoundedPopen installs its timer. Any witness/write fault
 # must terminate this exact just-created object so no unwitnessed guest leaks.
 try:
  ident=owner.identity(int(process._handle),process.pid);assert Path(ident['path']).resolve()==Path(path).resolve() and ident['sha256']==expected['sha256'];write(ident)
 except BaseException:process.terminate();process.wait(timeout=3);raise
def main():
 assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
 ap=argparse.ArgumentParser();ap.add_argument('--case',type=int,required=True);ap.add_argument('--tools',required=True);ap.add_argument('--grant',type=Path,required=True);ap.add_argument('--grant-sha256',required=True);ap.add_argument('--cleanup',action='store_true');ap.add_argument('payload',nargs=argparse.REMAINDER);a=ap.parse_args()
 assert row(HERE/'TOOLCHAIN-SEAL.json')['sha256']==a.tools
 pins=read(HERE/'TOOLCHAIN-SEAL.json')['members']
 for n,pin in pins.items():assert row(HERE/n)==pin
 assert row(a.grant)['sha256']==a.grant_sha256;grant=read(a.grant);assert grant['approved'] and grant['kit_sha256']==a.tools and grant['case_order'] in [[0,1],[2,3],[0,1,2,3]] and a.case in grant['case_order'] and grant['H2'] is False
 plan=read(HERE/'PLAN.json');assert type(a.case) is int and 0<=a.case<4;c=plan['cases'][a.case]
 cap=Path(c['argv'][c['argv'].index('--cap')+1]);expected=read(HERE/'INPUT-PINS.json')['helpers']['console']['identity'];owner=module('owned_win_process',HERE/'owned_process.py',pins['owned_process.py'])
 if a.cleanup:
  target=cap/'OWNED-GUEST.json'
  if not target.exists():return
  ident=read(target);assert Path(ident['path']).resolve()==(cap/'flycast.exe').resolve() and ident['sha256']==expected['sha256'];fresh(cap/'OWNED-CLEANUP.json',owner.terminate(ident));return
 assert sys.pycache_prefix and Path(sys.pycache_prefix).is_absolute() and not Path(sys.pycache_prefix).exists() and not cap.exists()
 assert os.environ.get('RE4DC_EMU')=='console' and os.environ.get('FP_NOLIMIT')=='1' and os.environ.get('RE4DC_MAX_FLYCASTS')=='16'
 payload=a.payload[1:] if a.payload and a.payload[0]=='--' else a.payload
 assert payload==c['argv'][10:],'Only exact pinned Pillow/bound/harness args'
 original=subprocess.Popen;guest=None
 class CheckedPopen(original):
  def __init__(self,*args,**kwargs):
   nonlocal guest
   cmd=args[0] if args else kwargs.get('args',[]);exe=cmd[0] if isinstance(cmd,(list,tuple)) else cmd;is_guest=Path(str(exe)).name.lower()=='flycast.exe'
   if is_guest:
    assert guest is None and Path(str(exe)).resolve()==(cap/'flycast.exe').resolve();assert row(exe)==expected
    assert isinstance(cmd,(list,tuple)) and list(cmd)==[str(cap/'flycast.exe'),'disc.gdi'] and Path(kwargs.get('cwd',Path.cwd())).resolve()==cap.resolve()
    text=(cap/'emu.cfg').read_text();config_guard(text)
    fresh(cap/'PRE-POPEN.json',dict(case=a.case,config=row(cap/'emu.cfg'),explicit_aica_LimitFPS='no',vsync='no',exact_executable=row(exe),before_guest=True))
   super().__init__(*args,**kwargs)
   if is_guest:
    guest=self
    record_owned(self,cap/'flycast.exe',expected,owner,lambda ident:fresh(cap/'OWNED-GUEST.json',ident))
 subprocess.Popen=CheckedPopen
 try:
  pillow=Path(payload[0]);pin=read(HERE/'INPUT-PINS.json')['pillow_launcher'];assert pillow.resolve()==Path(pin['windows_path']).resolve() and row(pillow)==pin['identity']
  sys.argv=payload;m={'__file__':str(pillow),'__name__':'__main__'};exec(compile(pillow.read_bytes(),str(pillow),'exec',dont_inherit=True),m)
  from PIL import Image
  images=[];pairs={}
  for p in sorted((cap/'shots').rglob('fb*.png')):
   assert p.name in ['fb0.png','fb1.png'] and p.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
   with Image.open(p) as image:assert image.format=='PNG' and image.size==(640,480);image.verify()
   with Image.open(p) as image:image.load();assert image.size==(640,480)
   images.append(dict(path=p.relative_to(cap).as_posix(),identity=row(p),size=[640,480]));pairs.setdefault(str(p.parent),set()).add(p.name)
  assert images and any(v=={'fb0.png','fb1.png'} for v in pairs.values()),'Actual decoded paired PNG stills required'
  fresh(cap/'PNG-READBACK.json',dict(status='ACTUAL_PNG_DECODE_READBACK_PASS',images=images,visual_acceptance=False,memory_acceptance=False))
 finally:subprocess.Popen=original
if __name__=='__main__':main()
