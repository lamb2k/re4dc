"""Pure host integrity/cap controls plus exact mode1 source with mock allocators."""
from pathlib import Path
import copy, fcntl, hashlib, json, os, py_compile, resource, signal, struct, subprocess, tempfile, time, unittest
import graph,prepare,run
HERE=Path(__file__).resolve().parent

def synthetic_elf(override=None,clobber=None):
 routes=dict(graph.ROUTES)
 routes.update({'___wrap_'+name:'_'+name for name in graph.WRAPS})
 if override:routes.update(override)
 names=sorted(set(routes)|set(routes.values()))
 addresses={n:0x8c010000+16*i for i,n in enumerate(names)};code=bytearray()
 for name in names:
  if name in routes:
   if name==clobber:body=struct.pack('<HHHHIHH',0xd001,0x6013,0x402b,0x0009,addresses[routes[name]],0x0009,0x0009)
   else:body=struct.pack('<HHHHIHH',0xd001,0x402b,0x0009,0x0009,addresses[routes[name]],0x0009,0x0009)
  else:body=struct.pack('<HH',0x000b,0x0009)+bytes(12)
  code.extend(body)
 strings=bytearray(b'\0');symbols=bytearray(16)
 for name in names:
  index=len(strings);strings.extend(name.encode()+b'\0');symbols.extend(struct.pack('<IIIBBH',index,addresses[name],16,0x12,0,1))
 textoff=256;symoff=textoff+len(code);stroff=symoff+len(symbols);shoff=(stroff+len(strings)+3)&~3
 out=bytearray(shoff+4*40);out[textoff:textoff+len(code)]=code;out[symoff:symoff+len(symbols)]=symbols;out[stroff:stroff+len(strings)]=strings
 header=struct.pack('<16sHHIIIIIHHHHHH',b'\x7fELF\x01\x01\x01'+bytes(9),2,42,1,addresses[names[0]],0,shoff,0,52,0,0,40,4,0);out[:52]=header
 sections=[(0,0,0,0,0,0,0,0,0,0),(0,1,6,0x8c010000,textoff,len(code),0,0,4,0),
           (0,2,0,0,symoff,len(symbols),3,1,4,16),(0,3,0,0,stroff,len(strings),0,0,1,0)]
 for i,section in enumerate(sections):struct.pack_into('<IIIIIIIIII',out,shoff+i*40,*section)
 return bytes(out)

def synthetic_mode1_log(plan):
 lines=(prepare.QA/'off/build.log').read_text().splitlines()
 link=next(x for x in lines if 'bash tools/link.sh ' in x)+' '+' '.join('-Wl,--wrap='+x for x in graph.WRAPS)
 source=[next(x for x in lines if ' -c '+unit+' ' in x).replace(' -c ',' -DRE4DC_KOS_CENSUS=1 -c ',1)
         for unit in ['platform/kos_census.cpp','ui_bridge.cpp']]
 overlays=[x for x in lines if 'gen_overlay: .ovl_' in x]
 return '\n'.join([link,*source,*overlays])

class Host(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.plan=prepare.read(HERE/'PREPARATION.json')
  cls.small={k:cls.plan[k] for k in ['source','arm_order','object_reuse','budget','root','commands','proposal_tokens','final_caller_values','environment']}
 def rejects(self,change):
  p=copy.deepcopy(self.small);change(p)
  with self.assertRaises((AssertionError,KeyError)):prepare.semantic(p)
 def test_exact_pair(self):self.assertTrue(prepare.semantic(self.small))
 def test_mode2(self):self.rejects(lambda p:p['commands']['on'].append('KOS_CENSUS=2'))
 def test_held_squeeze(self):self.rejects(lambda p:p['commands']['on'].append('KOS_SQUEEZE_BYTES=49152'))
 def test_token_order(self):self.rejects(lambda p:p['commands']['on'].reverse())
 def test_wrong_source(self):self.rejects(lambda p:p.update(source='8ce5'))
 def test_object_reuse(self):self.rejects(lambda p:p.update(object_reuse=True))
 def test_wrong_root(self):self.rejects(lambda p:p.update(root='/root/work/lanes/gc-motion24'))
 def test_deadline(self):self.rejects(lambda p:p['budget'].update(per_arm_seconds=601))
 def test_jobs(self):self.rejects(lambda p:p['budget'].update(jobs=4))
 def test_slots(self):self.rejects(lambda p:p['budget'].update(shared_slots=2))
 def test_floor(self):self.rejects(lambda p:p['budget'].update(C_floor_bytes=20*1024**3))
 def test_integrity_byte_flip(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d)/'input';p.write_bytes(b'a');pins={str(p):prepare.row(p)};p.write_bytes(b'b')
   with self.assertRaises(AssertionError):prepare.verify(pins)
 def test_cap_C(self):
  b=self.plan['budget']
  with self.assertRaises(AssertionError):run.check_capacity(b,b['C_floor_bytes']-1,8*1024**3,0)
 def test_cap_RAM(self):
  b=self.plan['budget']
  with self.assertRaises(AssertionError):run.check_capacity(b,30*1024**3,b['RAM_floor_bytes']-1,0)
 def test_cap_owned(self):
  b=self.plan['budget']
  with self.assertRaises(AssertionError):run.check_capacity(b,30*1024**3,8*1024**3,b['owned_bytes_cap']+1)
 def test_actual_dead_option(self):
  root=Path(self.plan['root']);argv=self.plan['commands']['off']+['KOS_CENSUS_MISSPELLED=1']
  result=prepare.actual_preflight(root/'off/source',argv)
  self.assertEqual(result['returncode'],1);self.assertIn('KOS_CENSUS_MISSPELLED',result['stderr'])
 def test_allocation_refused(self):
  env={'PATH':'/usr/bin:/bin','HOME':'/root'}
  r=subprocess.run(['bash',str(HERE/'run.sh')],env=env,capture_output=True,text=True,timeout=5)
  self.assertEqual(r.returncode,2);self.assertIn('ROOT_CENSUS_SOURCE_GRANT_REQUIRED',r.stdout)
 def test_inherited_compiler_refused(self):
  env={'PATH':'/usr/bin:/bin','HOME':'/root','GC_KOS_CENSUS_SOURCE':prepare.SOURCE,'GC_KOS_CENSUS_PLAN':'fake','GC_KOS_CENSUS_TOOLS':'fake','CFLAGS':'-DUNREVIEWED'}
  r=subprocess.run(['/bin/bash',str(HERE/'run.sh')],env=env,capture_output=True,text=True,timeout=5)
  self.assertEqual(r.returncode,2);self.assertIn('INHERITED_INJECTION_REFUSED:CFLAGS',r.stdout)
 def test_actual_flock_not_path_or_env(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d)/'owned-host-lock'
   with p.open('w') as stream:
    with self.assertRaises(AssertionError):run.assert_fd_lock(stream.fileno(),p)
    fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);run.assert_fd_lock(stream.fileno(),p)
    fcntl.flock(stream,fcntl.LOCK_UN)
    with self.assertRaises(AssertionError):run.assert_fd_lock(stream.fileno(),p)
 def test_environment_slot_is_insufficient(self):
  with self.assertRaises((AssertionError,OSError)):run.actual_locks()
 def test_release_matcher(self):
  self.assertTrue(run.release_cmd(['/bin/bash','/root/rr-cycle.sh']))
  self.assertTrue(run.release_cmd(['/usr/bin/python3','-B','/root/rr-jobs.py']))
  self.assertFalse(run.release_cmd(['/usr/bin/python3','-c','rr-cycle.sh']))
  self.assertFalse(run.release_cmd(['/bin/bash','/root/unrelated.sh']))
 def test_preexisting_cache_isolated(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d);module=root/'cache_control.py';module.write_text('value=1\n');stamp=module.stat()
   cached=Path(py_compile.compile(str(module),doraise=True));before=cached.read_bytes()
   module.write_text('value=2\n');os.utime(module,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
   code='import sys;sys.path.insert(0,'+repr(str(root))+');import cache_control;print(cache_control.value)'
   value=subprocess.check_output(['/usr/bin/python3','-B','-E','-X','pycache_prefix='+str(root/'isolated'),'-c',code],text=True)
   self.assertEqual(value.strip(),'2');self.assertEqual(cached.read_bytes(),before)
 def owned_stop_control(self,which):
  with tempfile.TemporaryDirectory(prefix='kos-census-stop-host-',dir='/dev/shm') as d:
   root=Path(d);pidfile=root/'pid'
   childcode='from pathlib import Path;import os,time;Path('+repr(str(pidfile))+').write_text(str(os.getpid()));time.sleep(30)'
   code='import sys,time,signal;sys.path.insert(0,'+repr(str(HERE))+');import run;'+''.join('signal.signal('+str(int(s))+',run.signal_stop);' for s in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT])
   code+='start=time.monotonic();f=open('+repr(str(root/'child.log'))+',"w");'
   if which in ['floor','release']:code+='monitor=lambda: (_ for _ in ()).throw(run.OwnedStop("'+which+' control")) if time.monotonic()-start>0.2 else None;'
   else:code+='monitor=lambda:None;'
   code+='run.owned_child(["/usr/bin/python3","-c",'+repr(childcode)+'],f,start+'+('0.2' if which=='deadline' else '10')+',monitor)'
   helper=subprocess.Popen(['/usr/bin/python3','-B','-E','-X','pycache_prefix='+str(root/'cache'),'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   until=time.monotonic()+3
   while not pidfile.exists() and helper.poll() is None and time.monotonic()<until:time.sleep(0.02)
   self.assertTrue(pidfile.exists());childpid=int(pidfile.read_text())
   if which in ['TERM','HUP']:os.kill(helper.pid,signal.SIGTERM if which=='TERM' else signal.SIGHUP)
   stdout,stderr=helper.communicate(timeout=6)
   self.assertNotEqual(helper.returncode,0);self.assertIn(b'OwnedStop',stderr)
   self.assertFalse(Path('/proc/'+str(childpid)).exists(),'Owned child survived cancellation')
 def test_SIGTERM_owned_cleanup(self):self.owned_stop_control('TERM')
 def test_SIGHUP_owned_cleanup(self):self.owned_stop_control('HUP')
 def test_analysis_floor_owned_cleanup(self):self.owned_stop_control('floor')
 def test_analysis_deadline_owned_cleanup(self):self.owned_stop_control('deadline')
 def test_release_priority_owned_cleanup(self):self.owned_stop_control('release')
 def test_synthetic_routes(self):
  elf=graph.ELF(synthetic_elf())
  for source,target in graph.ROUTES:self.assertTrue(elf.tail_route(source,target))
  for name in graph.WRAPS:self.assertTrue(elf.tail_route('___wrap_'+name,'_'+name))
 def test_mode1_graph(self):self.assertEqual(graph.link_graph(synthetic_mode1_log(self.plan),'off',self.plan['baseline_wraps']['off'])['raw_object_count'],449)
 def test_extra_aligned_wrap_rejected(self):
  with self.assertRaises(AssertionError):graph.link_graph(synthetic_mode1_log(self.plan)+'\n', 'off',self.plan['baseline_wraps']['off']+['aligned_alloc'])
  text=synthetic_mode1_log(self.plan).replace('-Wl,--wrap=malloc','-Wl,--wrap=aligned_alloc',1)
  with self.assertRaises(AssertionError):graph.link_graph(text,'off')
 def test_missing_wrap_rejected(self):
  text=synthetic_mode1_log(self.plan).replace('-Wl,--wrap=malloc','',1)
  with self.assertRaises(AssertionError):graph.link_graph(text,'off')
 def test_extra_object_rejected(self):
  text=synthetic_mode1_log(self.plan).replace('bash tools/link.sh ','bash tools/link.sh /outside/reused.o ',1)
  with self.assertRaises(AssertionError):graph.link_graph(text,'off')
 def test_overlay_order_rejected(self):
  text=synthetic_mode1_log(self.plan).replace('gen_overlay: .ovl_pl0f','gen_overlay: .ovl_wrong',1)
  with self.assertRaises(AssertionError):graph.link_graph(text,'off')
 def test_mode2_compile_rejected(self):
  text=synthetic_mode1_log(self.plan).replace('-DRE4DC_KOS_CENSUS=1','-DRE4DC_KOS_CENSUS=2',1)
  with self.assertRaises(AssertionError):graph.link_graph(text,'off')
 def test_unwrapped_malloc_route_rejected(self):
  elf=graph.ELF(synthetic_elf({'__malloc_r':'_malloc'}))
  with self.assertRaises(AssertionError):elf.tail_route('__malloc_r','___wrap_malloc')
 def test_register_clobber_rejected(self):
  elf=graph.ELF(synthetic_elf(clobber='__malloc_r'))
  with self.assertRaises(AssertionError):elf.tail_route('__malloc_r','___wrap_malloc')
 def test_wrong_machine_rejected(self):
  b=bytearray(synthetic_elf());struct.pack_into('<H',b,18,3)
  with self.assertRaises(AssertionError):graph.ELF(bytes(b))
 def test_real_mode1_source_accounting(self):
  source=prepare.git(prepare.TREE,'show',prepare.SOURCE+':port/dreamcast/game/platform/kos_census.cpp')
  self.assertEqual(hashlib.sha256(source).hexdigest(),'beb692fa9725b788cfce647897ae6dad632421dc0916b2a6d08315e1702427eb')
  with tempfile.TemporaryDirectory(prefix='kos-census-mode1-host-',dir='/dev/shm') as d:
   root=Path(d)
   for name,body in [('arch/irq.h','int irq_disable(); void irq_restore(int);'),('kos/irq.h',''),('kos/thread.h','')]:
    p=root/'include'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
   unit=root/'unit.cpp';unit.write_bytes(source+b'\n'+CPP.encode())
   command=['/usr/bin/g++','-std=c++17','-O1','-DRE4DC_KOS_CENSUS=1','-I'+str(root/'include'),str(unit),'-o',str(root/'test')]
   r=subprocess.run(command,capture_output=True,text=True,timeout=45);self.assertEqual(r.returncode,0,r.stderr)
   result=subprocess.run([str(root/'test')],capture_output=True,text=True,timeout=5)
   self.assertEqual(result.returncode,0,result.stderr);self.assertIn('ACTUAL_MODE1_ACCOUNTING_CONTROLS_PASS',result.stdout)
   names=subprocess.check_output(['/usr/bin/nm',str(root/'test')],text=True)
   self.assertNotIn('re4dc_kos_threads_report',names);self.assertNotIn('re4dc_kos_census_window',names)
   self.host_receipt={'exact_source_sha256':hashlib.sha256(source).hexdigest(),'host_compiler_sha256':prepare.sha('/usr/bin/g++'),
    'host_only':True,'SDK':False,'scope':'Unmodified census body with three mock include headers and fake allocators; no game/target execution.',
    'stdout':result.stdout,'mode2_thread_and_peak_symbols_absent':True}
   receipt=HERE/'ACTUAL-SOURCE-HOST-CONTROLS.json'
   if receipt.exists():self.assertEqual(json.loads(receipt.read_text()),self.host_receipt)
   else:
    with receipt.open('x') as stream:stream.write(json.dumps(self.host_receipt,indent=2)+'\n')

CPP=r'''
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <climits>
static std::uintptr_t next_ptr=0x10000;
static bool fail_realloc=false;
static unsigned last_a=0,last_n=0,free_null=0,logged_overflow=0;
int irq_disable(){return 0;} void irq_restore(int){}
extern "C" void* __real_malloc(std::size_t){next_ptr+=32;return reinterpret_cast<void*>(next_ptr);}
extern "C" void* __real_calloc(std::size_t a,std::size_t b){return __real_malloc(a*b);}
extern "C" void* __real_memalign(std::size_t a,std::size_t n){last_a=a;last_n=n;if(!a || (a&(a-1)))return nullptr;next_ptr=(next_ptr+a)&~(a-1);return reinterpret_cast<void*>(next_ptr);}
extern "C" void* __real_aligned_alloc(std::size_t a,std::size_t n){return __real_memalign(a,n);}
extern "C" void* __real_realloc(void*,std::size_t n){if(fail_realloc||!n)return nullptr;return __real_malloc(n);}
extern "C" void __real_free(void* p){if(!p)++free_null;}
extern "C" void* __real__Znwj(std::size_t n){return __wrap_malloc(n);}
extern "C" void* __real__Znaj(std::size_t n){return __wrap_malloc(n);}
extern "C" void re4dc_kos_heap_state(unsigned*,unsigned*,unsigned*){}
extern "C" void re4dc_log(const char* format,...){
 if(!std::strstr(format,"callers="))return;
 va_list ap;va_start(ap,format);(void)va_arg(ap,const char*);
 for(int i=0;i<6;++i){unsigned value=va_arg(ap,unsigned);if(i==5)logged_overflow=value;}
 va_end(ap);
}
void reset(){std::memset(live,0,sizeof(live));lost=count=cur=0;fail_realloc=false;logged_overflow=0;}
int main(){
 reset();void* p=__wrap_malloc(64);assert(count==1&&cur==64);
 add(p,96,reinterpret_cast<void*>(1234));assert(count==1&&cur==96); // duplicate pointer replaces
 __wrap_free(p);assert(count==0&&cur==0);
 reset();p=__wrap__Znwj(80);assert(count==1&&cur==80); // inner wrapped malloc, outer new only reattributes
 __wrap_free(p);p=__wrap__Znaj(24);assert(count==1&&cur==24);__wrap_free(p);
 reset();p=__wrap_malloc(40);fail_realloc=true;assert(!__wrap_realloc(p,90));assert(count==1&&cur==40);
 fail_realloc=false;void* q=__wrap_realloc(p,90);assert(q&&q!=p&&count==1&&cur==90);
 assert(!__wrap_realloc(q,0));assert(count==0&&cur==0);
 __wrap_free(nullptr);assert(count==0&&cur==0&&free_null==1);
 reset();p=__wrap_memalign(32,127);assert(last_a==32&&last_n==127&&reinterpret_cast<std::uintptr_t>(p)%32==0&&count==1&&cur==127);
 assert(!__wrap_memalign(3,32));assert(count==1&&cur==127);__wrap_free(p);
 reset();p=__wrap_calloc(3,7);assert(count==1&&cur==21);__wrap_free(p);
 reset();for(unsigned i=0;i<4097;++i)add(reinterpret_cast<void*>(0x10000+i*32),1,reinterpret_cast<void*>(1234));
 assert(count==4096&&cur==4096&&lost==1); // coverage must be UNKNOWN on lost entries
 reset();for(unsigned i=0;i<257;++i)add(reinterpret_cast<void*>(0x10000+i*32),1,reinterpret_cast<void*>(0x20000+i*2));
 re4dc_kos_census_log("host",0x100);assert(logged_overflow==1); // caller-row truncation is explicit
 reset();add(reinterpret_cast<void*>(0x10000),UINT_MAX,reinterpret_cast<void*>(1));add(reinterpret_cast<void*>(0x10020),1,reinterpret_cast<void*>(2));
 assert(cur==0&&count==2); // arithmetic limit exposed, not called complete coverage
 std::puts("ACTUAL_MODE1_ACCOUNTING_CONTROLS_PASS: duplicate/new/realloc/free-null/alignment/calloc/table-loss/row-overflow/32bit-limit");
}
'''

if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
 unittest.main(verbosity=2)
