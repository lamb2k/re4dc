"""Exact c57 read-only observer, inline Motion v2, no trace fallback or write API."""
import ctypes,hashlib,importlib.util,json,os,pathlib,re,struct,time
P=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('adapter',P/'observer-v2.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

def coherent_frames(before,inside,after,pointers_match):return pointers_match and before is not None and before==inside==after

class Observer:
 @staticmethod
 def qa_safe(row):return False # this guest plan never reopens QA or posts the QA chord
 def __init__(self,cap,binding,layout):
  self.cap=pathlib.Path(cap);self.binding=json.loads(pathlib.Path(binding).read_text());self.layout=json.loads(pathlib.Path(layout).read_text());self.handle=None;self.ram=None;self.last=None;self.started=time.monotonic();self.last_log=0;self.last_key=None;self.buffer=None
  if self.binding['source_candidate']!='c57ff60f0f462fdd2c419883b0258963504d756a' or self.binding['disc_program_sha256']!='52190ed293d8e62238bcad40fd351d35a965b253ad5b59cda570d0de34187e45' or self.binding['elf_sha256']!='248dd4aac7c4e22a7a18a0183fc6409401fddf610d98881c90dd9664e342640b':raise ValueError('wrong exact guest fixture')
  if self.layout['elf_sha256']!=self.binding['elf_sha256']:raise ValueError('wrong exact DWARF')
  contract=pathlib.Path(self.binding['source_contract']);self.source=json.loads(contract.read_text())
  if hashlib.sha256(contract.read_bytes()).hexdigest()!=self.binding['source_contract_sha256']:raise ValueError('source contract changed')
  self.adapter=a.Reader(self.buffer_read,self.binding['observer_symbols'],self.layout,self.binding['elf_sha256'],source_contract=self.source,expected_source=self.binding['source_candidate'])
  self.k=ctypes.WinDLL('kernel32',use_last_error=True);self.k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];self.k.OpenProcess.restype=ctypes.c_void_p;self.k.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];self.k.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)];self.k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(ctypes.c_ulonglong)]*4;self.k.CloseHandle.argtypes=[ctypes.c_void_p]
 def buffer_read(self,p,n):
  if self.buffer is None or p<0x8c000000 or p+n>0x8d000000:raise ValueError('snapshot unavailable/outsideRAM')
  return self.buffer[p-0x8c000000:p-0x8c000000+n]
 def live_read(self,p,n):
  if not 0x8c000000<=p<=0x8d000000-n:raise ValueError('live read outside mainRAM')
  data=ctypes.create_string_buffer(n);done=ctypes.c_size_t()
  if not self.k.ReadProcessMemory(self.handle,self.ram+p-0x8c000000,data,n,ctypes.byref(done)) or done.value!=n:raise OSError('incomplete read-only sample')
  return data.raw
 def field(self,p,typ,n,fmt):
  # Legacy runner movement clocks can ask for a fresh scalar, never write it.
  if isinstance(p,str):p=int(p,0)
  a._contract.validate_read(self.layout,typ,n,fmt);values=struct.unpack('<'+fmt,self.live_read(p+self.adapter.off(typ,n),struct.calcsize('<'+fmt)));return values[0] if len(values)==1 else list(values)
 def register(self):
  try:pid=int((self.cap/'flycast.pid').read_text().strip());text=(self.cap/'flycast.log').read_text(errors='replace')
  except (FileNotFoundError,ValueError):return False
  matches=re.findall(r'RAM\(16 MB\) ([0-9A-Fa-f]+)',text)
  if not matches:return False
  h=self.k.OpenProcess(0x1010,False,pid)
  if not h:raise OSError('cannot open owned read-only process')
  try:
   path=ctypes.create_unicode_buffer(32768);size=ctypes.c_ulong(len(path))
   if not self.k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(size)) or pathlib.Path(path.value).resolve()!=(self.cap/'flycast.exe').resolve():raise ValueError('observer executable ownership mismatch')
   times=[ctypes.c_ulonglong() for _ in range(4)]
   if not self.k.GetProcessTimes(h,*[ctypes.byref(v) for v in times]):raise OSError('observer start unavailable')
   self.handle=h;self.start=times[0].value;self.pid=pid;self.ram=int(matches[-1],16);return True
  except BaseException:self.k.CloseHandle(h);raise
 def sample(self):
  if self.handle is None and not self.register():return
  times=[ctypes.c_ulonglong() for _ in range(4)]
  if not self.k.GetProcessTimes(self.handle,*[ctypes.byref(v) for v in times]) or times[0].value!=self.start or times[1].value:raise EOFError('owned observer PID ended/changed')
  row=None
  for attempt in range(4):
   pg=struct.unpack('<I',self.live_read(self.adapter.sy['_pG'],4))[0];pl_before=struct.unpack('<I',self.live_read(self.adapter.sy['_pPL'],4))[0];foff=self.adapter.off('GlobalWork','Frame_cnt');before=struct.unpack('<I',self.live_read(pg+foff,4))[0] if 0x8c000000<=pg<=0x8d000000-self.layout['found']['GlobalWork']['bytes'] else None
   self.buffer=self.live_read(0x8c000000,16*1024**2);row=self.adapter.snapshot();row.update(self.adapter.actor_chain())
   pg_after=struct.unpack('<I',self.live_read(self.adapter.sy['_pG'],4))[0];after=struct.unpack('<I',self.live_read(pg_after+foff,4))[0] if before is not None and pg_after==pg else None
   pl_after=struct.unpack('<I',self.live_read(self.adapter.sy['_pPL'],4))[0];frame=(row.get('global') or {}).get('frame');player=(row.get('player') or {}).get('ptr');row['transport_coherent']=coherent_frames(before,frame,after,pg_after==pg and pl_before==pl_after==player);row['coherent']=row.get('coherent',False) and row['transport_coherent'];row['transport_attempts']=attempt+1;row['non_atomic']=True
   if row['coherent']:break
  row.update(host_s=time.monotonic()-self.started,observed_monotonic=time.monotonic(),pid=self.pid,start_filetime=self.start)
  self.last=row;data=json.dumps(row,allow_nan=False)+'\n';temporary=self.cap/'latest-state.tmp';temporary.write_text(data);os.replace(temporary,self.cap/'latest-state.json')
  g=row.get('global') or {};pl=row.get('player') or {};key=(g.get('player_life'),tuple(g.get('rno',[])),tuple(pl.get('rno',[])),pl.get('dmgType_bits'),tuple((x['ptr'],x['serial'],tuple(x['rno']),x['hp']) for x in row.get('actors',[])))
  if time.monotonic()-self.last_log>=.25 or key!=self.last_key:
   with (self.cap/'read-only-state.jsonl').open('a') as f:f.write(data)
   self.last_log=time.monotonic();self.last_key=key
 def close(self):
  if self.handle:self.k.CloseHandle(self.handle);self.handle=None
