"""Actual owned guest framebuffer PNGs; no desktop/focus action and no guest writes."""
from pathlib import Path
import ctypes,json,re,time,hashlib,shutil,importlib.util
from ctypes import wintypes as W
EXPECTED='52a5d671203e22e9f20728a8fbc3b61e080f7ba44e06891df635248a374dd053'
def capture_checkpoint(cap,label,action,result):
 cap=Path(cap).resolve();meta=json.loads((cap/'run-start.json').read_text());assert meta['elf_sha256']==EXPECTED
 assert shutil.disk_usage(cap).free>=16*1024**3+64*1024**2,'Retained runtime floor for capture'
 owner=json.loads((cap/'owned-process.json').read_text());k=ctypes.WinDLL('kernel32',use_last_error=True)
 k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)];k.GetProcessTimes.argtypes=[W.HANDLE]+[ctypes.POINTER(W.FILETIME)]*4;k.CloseHandle.argtypes=[W.HANDLE]
 h=k.OpenProcess(0x1000,False,owner['pid']);assert h
 def check():
  path=ctypes.create_unicode_buffer(32768);n=W.DWORD(len(path));assert k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(n));assert Path(path.value).resolve()==Path(owner['path']).resolve()==cap/'flycast.exe'
  f=[W.FILETIME()for _ in range(4)];assert k.GetProcessTimes(h,*[ctypes.byref(x)for x in f]);assert (f[0].dwHighDateTime<<32|f[0].dwLowDateTime)==owner['start_filetime'];assert not(f[1].dwHighDateTime or f[1].dwLowDateTime)
 def latest():
  p=cap/'readonly-combat-io.jsonl'
  if not p.exists():return None
  rows=p.read_text().splitlines()
  return json.loads(rows[-1])if rows else None
 try:
  check();before=latest();fb=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'));assert fb,'No framebuffer marker in exact owned run'
  shot=cap/'shots'/('checkpoint-'+re.sub('[^a-zA-Z0-9_-]','_',label));shot.mkdir(parents=True,exist_ok=False)
  for nm in ['emu.cfg','flycast.log','flycast.pid']:shutil.copyfile(cap/nm,shot/nm)
  (shot/'boot.log').write_text(fb[-1]+'\n',encoding='utf-16')
  spec=importlib.util.spec_from_file_location('qa_owned_fb_capture',cap/'capture_ui_vram.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.capture(shot,shot/'frames');check();after=latest()
  pngs=list((shot/'frames').glob('*.png'));assert pngs,'Capture produced no PNG frames'
  context=dict(run_id=cap.name,source='d4a3b31fac3362937a3f21eaa874e07be94fd061',elf_sha256=EXPECTED,disc_sha256=meta['disc_sha256'],room=after.get('room')if after else None,source_frame_interval=[before.get('frame')if before else None,after.get('frame')if after else None],action=action,result=result,before=before,after=after,method='Existing framebuffer capture; asynchronous source-frame interval, no guest freeze/write',pngs=[dict(path=str(p),sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest())for p in pngs])
  (shot/'checkpoint-context.json').write_text(json.dumps(context,indent=2)+'\n');return dict(checkpoint=str(shot),metadata=str(shot/'checkpoint-context.json'),pngs=[str(p)for p in pngs])
 finally:k.CloseHandle(h)
