"""Guarded fresh-output fp master variant. PREPARATION ONLY until root grant.
Reuses official fp_iso and exact official geniso/redirect semantics. No SDK,
shared cache, pruning, existing output deletion or source asset mutation.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,tempfile,time,signal
import common as c
import process_group as pg
HERE=Path(__file__).resolve().parent
WINPY='/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def row(p):return dict(size=Path(p).stat().st_size,sha256=sha(p))
def read(p):return json.loads(Path(p).read_text())
def fresh(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def absolute_fresh(p,root):
 p=Path(p);root=Path(root)
 if not p.is_absolute() or p!=p.resolve() or root!=root.resolve() or not p.is_relative_to(root) or p==root or p.exists():raise ValueError('Nonfresh or escaped owned output '+str(p))
 return p

def safe_key(key):
 p=Path(key)
 if not isinstance(key,str) or p.is_absolute() or '..' in p.parts or str(p)!=key or not key or chr(0) in key:raise ValueError('Escaped/noncanonical source manifest member '+str(key))
 return key

def exact_manifest(original,actual,allowed,expected):
 for key in set(original)|set(actual)|set(expected)|set(allowed):safe_key(key)
 if actual!=expected:raise ValueError('Programme/assets readback differs from exact expected manifest')
 differences={k for k in set(original)|set(actual) if original.get(k)!=actual.get(k)}
 if differences!=set(allowed):raise ValueError('Not exactly15 programme and3 fixture differences')
 return sorted(differences)

def floor(required):
 windows=int(subprocess.check_output([WINPY,'-I','-S','-B','-c',"import shutil;print(shutil.disk_usage('C:\\\\').free)"],text=True).strip());wsl=shutil.disk_usage('/mnt/c').free
 value=dict(windows_free=windows,wsl_free=wsl,lower_free=min(windows,wsl),required=required)
 if value['lower_free']<required:raise ValueError('Capacity floor '+str(value))
 return value

def owned_bytes(roots):
 seen=set();total=0
 for root in roots:
  if root.is_symlink():raise ValueError('Owned root symlink refused')
  if not root.exists():continue
  for p in root.rglob('*'):
   if p.is_symlink():raise ValueError('Owned symlink refused')
   if not p.is_file():continue
   s=p.stat();k=(s.st_dev,s.st_ino)
   if k not in seen:seen.add(k);total+=s.st_size
 return total

def host_argv(argv):
 if not argv or str(argv[0]) not in ('/usr/bin/genisoimage','/usr/bin/python3.12'):raise ValueError('Unpinned PATH host tool refused')
 return [str(x) for x in argv]

def main(arm):
 def stopped(sig,frame):raise RuntimeError('Owned stage interruption '+str(sig))
 for sig in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]:signal.signal(sig,stopped)
 plan=c.verify_kit('stage')
 qa={'source':c.SOURCE,'arms':{a:{'files':plan['programmes'][a],'raw_sha256':plan['programmes'][a]['program.bin']['sha256']} for a in ['off','on']}}
 c.verify_inputs(plan)
 finalroot=Path(plan['base_paths'][arm]).parent;workroot=Path(plan['work_paths'][arm]).parent
 base=absolute_fresh(plan['base_paths'][arm],finalroot);work=absolute_fresh(plan['work_paths'][arm],workroot)
 assert str(finalroot)=='/mnt/c/Flycast-Evidence/re4-dreamcast/rain-diag24-20261024/_qa-media-8ce-recovery-v4'
 assert str(workroot)=='/root/probe/rain-diag24-qa-media-recovery-v4'
 cap=plan['capacity'];admission=floor(cap['C_admission_bytes'])
 assert owned_bytes([finalroot,workroot])<cap['owned_cap_bytes']
 for name,pin in plan['official_tools'].items():assert row(HERE/name)==pin
 assert row('/usr/bin/genisoimage')==plan['genisoimage']
 assert row('/usr/bin/python3.12')==plan['host_python']
 assert not c.release_active(),'Release priority'
 assert plan['OFF_reuse']['enabled'] is False,'Recovery must build both arms fresh'
 original=read(HERE/'CURRENT-CANDIDATE-MANIFEST.json');expected=read(HERE/(arm.upper()+'-EXPECTED-MANIFEST.json'));allowed=set(plan['allowed_differences']);fixture=Path(plan['assets']['read_only_fixture'])
 for key,pin in original.items():
  safe_key(key)
  if key in allowed:continue
  path=fixture/key;assert path.is_file() and not path.is_symlink() and row(path)==pin,key
 programme=Path(plan['programme_roots'][arm])
 for name,pin in qa['arms'][arm]['files'].items():
  if name not in ('program.bin','re4dc-game.elf') and not name.endswith('.ovl'):raise ValueError('Unexpected QA programme file')
  path=programme/name if name=='program.bin' else programme/name
  assert row(path)==dict(size=pin['size'],sha256=pin['sha256'])
 finalroot.mkdir(parents=True,exist_ok=True);workroot.mkdir(parents=True,exist_ok=True);base.mkdir();work.mkdir();(work/'tmp').mkdir();cdroot=work/'cdroot';cdroot.mkdir()
 fresh(base/'ADMISSION.json',admission)
 # Only unchanged assets are linked. Programme/fixtures are created separately,
 # so no write can reach an original hardlink inode.
 for key,pin in original.items():
  safe_key(key)
  if key in allowed:continue
  assert not Path(key).is_absolute() and '..' not in Path(key).parts
  dest=cdroot/key;dest.parent.mkdir(parents=True,exist_ok=True);os.link(fixture/key,dest)
 def copy_new(src,dest):
  dest.parent.mkdir(parents=True,exist_ok=True)
  with Path(src).open('rb') as inp,dest.open('xb') as out:shutil.copyfileobj(inp,out,1<<20)
 copy_new(programme/'program.bin',cdroot/'1ST_READ.BIN')
 for name in qa['arms'][arm]['files']:
  if name.endswith('.ovl'):copy_new(programme/name,cdroot/'dc'/name)
 for name in ('warp','padscript','w11'):
  with (cdroot/'dc'/(name+'.txt')).open('xb') as f:f.write(bytes(8192))
 got={str(p.relative_to(cdroot)):row(p) for p in cdroot.rglob('*') if p.is_file()};exact_manifest(original,got,allowed,expected)
 assert owned_bytes([finalroot,workroot])<cap['owned_cap_bytes'];floor(cap['C_floor_bytes'])
 iso=c.load_source('official_fp_iso',HERE/'official_fp_iso.py',plan['official_tools']['official_fp_iso.py'])
 env={'PATH':'/usr/bin:/bin','HOME':'/root','LANG':'C','LC_ALL':'C','PRUNE_AUTO':'0','RE4DC_STAGE_EXT4':'0','TMPDIR':str(work/'tmp')}
 commands=[]
 def run(argv,label):
  commands.append(host_argv(argv));fresh(base/(label+'-COMMAND.json'),commands[-1])
  previous_subreaper=pg.enable_subreaper();child=None;containment=None
  try:
   with (base/(label+'.log')).open('x') as log:
    child=subprocess.Popen(commands[-1],env=env,cwd=work,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);started=time.monotonic()
    while child.poll() is None:
     time.sleep(0.5)
     if c.release_active():raise ValueError('Release priority')
     if owned_bytes([finalroot,workroot])>cap['owned_cap_bytes'] or time.monotonic()-started>180:raise ValueError('Owned cap/180s host command deadline; preserve outputs')
     floor(cap['C_floor_bytes'])
    if child.returncode:raise ValueError('Host command failed '+label+' rc='+str(child.returncode))
  finally:
   if child:
    try:
     containment=pg.cleanup(child,previous_subreaper)
     fresh(base/(label+'-CONTAINMENT.json'),containment)
    except BaseException as e:
     fresh(base/(label+'-CONTAINMENT-FAILED.json'),{'contained':False,'error':repr(e),'pgid':child.pid})
     raise
   else:
    # No child was created; restore this process-local setting.
    if not previous_subreaper:
     libc=pg.ctypes.CDLL(None,use_errno=True)
     if libc.prctl(36,0,0,0,0)!=0:raise OSError(pg.ctypes.get_errno(),'Restore subreaper')
  if owned_bytes([finalroot,workroot])>cap['owned_cap_bytes']:raise ValueError('Owned media cap exceeded; preserve partial outputs')
  floor(cap['C_floor_bytes'])
 run(['/usr/bin/genisoimage','-quiet','-C','0,45000','-G',HERE/'SOURCE-IP.BIN','-r','-J','-l','-input-charset','iso8859-1','-V','RE4DCROOM','-o',base/'track03.iso',cdroot],'track03')
 # Streaming readback uses the actual official ISO reader with bounded chunks.
 prep=c.load_source('media_readback',HERE/'media_readback.py')
 actual,extents,ip=prep.stream_manifest(base/'track03.iso',iso);diff=exact_manifest(original,actual,allowed,expected);assert ip==(HERE/'SOURCE-IP.BIN').read_bytes()
 fresh(base/'base-manifest.json',actual);fresh(base/'BASE-DIFF.json',dict(exact_allowed=diff,main_and14_from_QA=True,all_assets_exact=True))
 for name,lba in [('warp',400),('padscript',420),('w11',440)]:run(['/usr/bin/python3.12','-I','-S','-B',HERE/'official_fp_iso.py','redirect',base/'track03.iso','/dc/'+name+'.txt',str(lba),'8192'],'redirect-'+name)
 low=work/'t1root';low.mkdir();(low/'README.TXT').write_bytes(b'RE4DC GD-ROM image. The game is in the high-density area (track 3).\r\n')
 run(['/usr/bin/genisoimage','-quiet','-G',HERE/'SOURCE-IP.BIN','-V','RE4DCLD','-input-charset','iso8859-1','-o',base/'track01-template.iso',low],'track01')
 with (base/'track01-template.iso').open('r+b') as f:
  assert f.seek(0,2)<400*2048;f.truncate(606*2048)
 with (base/'track02.raw').open('xb') as f:f.write(bytes(302*2352))
 fresh(base/'base.json',dict(kind='QA twin from already verified raw programme; no SDK conversion',tree=str(cdroot),elf=str(programme/'re4dc-game.elf'),warp_lba=400,pad_lba=420,w11_lba=440,fixture_bytes=8192,gdi='3\n1 0 4 2048 track01.iso 0\n2 756 0 2352 track02.raw 0\n3 45000 4 2048 track03.iso 0\n'))
 # Independently verify final directory extents in BOTH trees and all final file
 # bytes, reading the redirected fixtures from their real track1 slots.
 tr=iso.Track(base/'track03.iso',45000);lowtrack=iso.Track(base/'track01-template.iso',0);roots=iso.volume_roots(tr);redirects={};post={}
 try:
  for root,joliet in [(roots[0],False),(roots[1],True)]:
   assert root is not None
   for name,e,n,isdir,dlba,off in iso.walk(tr,root,joliet):
    if name.lower() in ('/dc/warp.txt','/dc/padscript.txt','/dc/w11.txt'):
     wanted={'/dc/warp.txt':400,'/dc/padscript.txt':420,'/dc/w11.txt':440}[name.lower()];assert (e,n)==(wanted,8192);redirects[(joliet,name.lower())]=[e,n]
  assert len(redirects)==6
  for name,e,n in iso.files(tr):
   key=name.lstrip('/');h=hashlib.sha256();remain=n;lba=e;reader=lowtrack if e<45000 else tr
   while remain:
    count=min(remain,1<<20);blob=reader.read_bytes(lba,count);h.update(blob);remain-=count;lba+=count//2048
   post[key]=dict(size=n,sha256=h.hexdigest())
 finally:tr.f.close();lowtrack.f.close()
 exact_manifest(original,post,allowed,expected);fresh(base/'FINAL-READBACK-MANIFEST.json',post)
 (base/'track03.sha256').write_text(sha(base/'track03.iso')+'\n');fresh(base/'COMPLETE.json',dict(status='STAGED_READBACK_PASS_GUEST_PENDING',arm=arm,source=qa['source'],programme=qa['arms'][arm]['raw_sha256'],plan_sha256=sha(HERE/'PLAN.json'),tracks={n:row(base/n) for n in ['track03.iso','track01-template.iso','track02.raw']},assets_exact=True,all14_exact=True,redirect_records=6,track03=row(base/'track03.iso'),sourceIP=plan['sourceIP'],owned_bytes=owned_bytes([finalroot,workroot]),floor=floor(cap['C_floor_bytes']),WORK_preserved=str(work),no_cleanup=True))
 print(str(base/'COMPLETE.json'))
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--arm',choices=['off','on'],required=True);a=ap.parse_args();main(a.arm)
