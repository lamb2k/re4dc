"""Backface stock runner child: sole semantic hook is the existing capture call."""
import ast,copy,ctypes as C,hashlib,importlib.util,json,os,pathlib,re,sys,time
P=pathlib.Path(__file__).parent
API=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367\qa22_nontrace_detached_run_v1\reference-hooks\native_reference_api.py')
API_SHA='466d5cfb558b57dc03d08050012573a5e783dfe21c69990aa4fd4fdf6f35d255'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def capture_call(n):return isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='mod' and n.func.attr=='capture'
def instrument(source):
 original=ast.parse(source);calls=[n for n in ast.walk(original) if capture_call(n)]
 if len(calls)!=1 or len(calls[0].args)!=2 or calls[0].keywords:raise ValueError('unique unchanged stock capture call required')
 tree=copy.deepcopy(original)
 class Patch(ast.NodeTransformer):
  def visit_Call(self,node):
   if capture_call(node):return ast.copy_location(ast.Call(func=ast.Name(id='_backface_capture_hook',ctx=ast.Load()),args=[node.func,*node.args],keywords=[]),node)
   return self.generic_visit(node)
 tree=Patch().visit(tree);ast.fix_missing_locations(tree)
 restored=copy.deepcopy(tree)
 class Restore(ast.NodeTransformer):
  def visit_Call(self,node):
   if isinstance(node.func,ast.Name) and node.func.id=='_backface_capture_hook':return ast.copy_location(ast.Call(func=node.args[0],args=node.args[1:],keywords=[]),node)
   return self.generic_visit(node)
 restored=Restore().visit(restored)
 if ast.dump(restored,include_attributes=False)!=ast.dump(original,include_attributes=False):raise ValueError('non-capture AST changed')
 return tree
class CaptureHook:
 def __init__(self,profile,clock=time.monotonic,proof=None,schedule=None):self.p=profile;self.clock=clock;self.proof=proof;self.schedule=schedule;self.pin=None;self.h=None;self.api=None;self.freeze_seen=None;self.events=[]
 def identity(self):
  if self.proof:return self.proof()
  if self.api is None:
   if sha(API)!=API_SHA:raise ValueError('native identity API changed')
   s=importlib.util.spec_from_file_location('capture_known_native',API);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);self.api=m.WindowsApi();self.api.k.OpenProcess.argtypes=[C.c_uint32,C.c_int,C.c_uint32];self.api.k.OpenProcess.restype=C.c_void_p
  cap=pathlib.Path(self.p['capture']);pid=int((cap/'flycast.pid').read_text())
  if self.h is None:
   if sha(cap/'flycast.exe')!=self.p['console_sha256']:raise ValueError('copied console identity differs')
   self.h=self.api.checked(self.api.k.OpenProcess(0x101010,False,pid));self.pin=self.api.process(self.h,None,require_live=True)
   if self.pin['path']!=str(cap/'flycast.exe').lower().replace('/','\\'):raise ValueError('copied owned guest executable path differs')
  if pid!=self.pin['pid']:raise ValueError('guest PID publication changed')
  row=self.api.process(self.h,None,self.pin,require_live=True);members=self.api.job_pids(None)
  if len(members)>8 or pid not in members or os.getpid() not in members:raise ValueError('guest/current stock child missing from exact current private job inventory')
  return {**{k:row[k] for k in ('pid','start_filetime','path')},'private_job_members':members}
 def __call__(self,original,evidence,output):
  text=(pathlib.Path(self.p['capture'])/'run-output.txt').read_text(errors='replace');marker='warp: frozen at tick '+str(self.p['freeze_tick'])
  if not re.search('^'+re.escape(marker)+'$',text,re.M):return [] # No moving frame or tick3300 stand-in.
  # Stock sets stop_at immediately before its capture block. Reading that
  # caller local is metadata only: AST still replaces just the capture call.
  stop_at=self.schedule() if self.schedule else sys._getframe(1).f_locals.get('stop_at')
  if type(stop_at) not in (int,float):raise ValueError('stock stop deadline not established before capture')
  observed=stop_at-8
  if self.freeze_seen is None:self.freeze_seen=observed
  if self.freeze_seen!=observed:raise ValueError('stock stop observation changed')
  if len(self.events)>=4:raise ValueError('four capture call cap')
  before=self.identity();start=self.clock()
  if not 0<=start-observed<=8:raise ValueError('capture began outside exact stock stop grace')
  event={'freeze_observed_monotonic':self.freeze_seen,'stock_stop_deadline_monotonic':stop_at,'stock_grace_seconds':8,'capture_start_monotonic':start,'identity_before':before,'path':str(output)}
  try:
   boot=(pathlib.Path(evidence)/'boot.log').read_text(encoding='utf-16')
   pointers=re.findall(r'fb=([0-9a-f]+),([0-9a-f]+)',boot)
   if not pointers:raise ValueError('exact stock framebuffer pointers missing')
   expected=[]
   for value in pointers[-1]:
    delta=int(value,16)-0xa5000000
    if delta<0 or delta>=16*1024**2 or delta%8:raise ValueError('invalid pinned KOS framebuffer pointer')
    expected.append(delta//2)
   result=original(evidence,output) # Exact standard capture: one8MiB VRAM read/RGB565 decode.
   end=self.clock();after=self.identity();event.update(capture_end_monotonic=end,identity_after=after)
   if result!=expected:raise ValueError('stock return differs from exact source offsets')
   if {k:after[k] for k in ('pid','start_filetime','path')}!={k:before[k] for k in ('pid','start_filetime','path')} or end-start<0 or end-self.freeze_seen>26:raise ValueError('capture identity/deadline window failed')
   event.update(framebuffer_source_pointers=pointers[-1],framebuffer_source_offsets=result,
                framebuffer_selection='unknown; accept only if both buffers in both arms are mutually identical',
                images={name:sha(pathlib.Path(output)/name) for name in ('fb0.png','fb1.png')})
   event['qualified']=True;return result
  except BaseException as error:event.update(qualified=False,error=repr(error));raise
  finally:
   self.events.append(event);path=pathlib.Path(self.p['capture'])/'capture-events.jsonl'
   with path.open('x' if len(self.events)==1 else 'a') as f:f.write(json.dumps(event,sort_keys=True)+'\n')
 def close(self):
  if self.h:
   while True:
    row=self.api.process(self.h,None,self.pin)
    if row['phase']=='exited' and row['wait_status']==0:break
    time.sleep(.01) # Outer guardian remains armed; no false finalized result.
   self.api.close(self.h);self.h=None

def main():
 profile_path=pathlib.Path(sys.argv[1]);profile=json.loads(profile_path.read_text());stock=pathlib.Path(profile['stock_runner'])
 if profile['fixture_name'] not in ('f1','close-ganado') or profile['arm'] not in ('C','ASM'):raise ValueError('wrong fixed pair')
 if sha(stock)!=profile['stock_sha256']:raise ValueError('stock source changed')
 if profile['environment']!={k:v for k,v in os.environ.items() if k.startswith(('RE4DC_','FP_NOLIMIT'))}:raise ValueError('inherited environment changed')
 source=stock.read_text();tree=instrument(source);hook=CaptureHook(profile);sys.argv=[str(stock),*profile['stock_argv']]
 try:
  exec(compile(tree,str(stock),'exec'),{'__name__':'__main__','__file__':str(stock),'_backface_capture_hook':hook})
  result=json.loads((pathlib.Path(profile['capture'])/'run-result.json').read_text())
  if result.get('status')!='RUN_COMPLETE' or result.get('stopped')!='goal' or result.get('errors') or not hook.events or not all(x['qualified'] for x in hook.events):raise RuntimeError('stock run/capture qualification failed')
 finally:hook.close()
if __name__=='__main__':main()
