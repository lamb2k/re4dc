#!/usr/bin/env python3
"""Independent actual-header/Event source lifecycle tests, strict UBSan/vptr."""
import argparse,hashlib,json,pathlib,re,subprocess,os,time,sys
sys.dont_write_bytecode=True
from audit_archive_borrow_boundaries import body
PIN='f3149dfc7a8e9bbf317eae6d192d9665b9568ce5'
HERE=pathlib.Path(__file__).resolve().parent
def sha(x):return hashlib.sha256(x).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
 def git(*args):return subprocess.check_output(['git','-C',a.repo,*args])
 sources={};pins={};selected=[]
 for name in ['include/cManager.h','include/event.h','include/atari.h','src/game/event.cpp','port/dreamcast/game/game30.mk']:
  raw=git('show',PIN+':'+name);sources[name]=raw.decode();pins[name]=dict(sha256=sha(raw),bytes=len(raw),blob=git('rev-parse',PIN+':'+name).decode().strip())
 def fn(path,sig):
  text=sources[path];match=re.search(re.escape(sig)+r'[^;{]*\{',text);assert match,(path,sig);begin=match.start();opening=match.end()-1;code,line,end=body(text[begin:],sig);value=text[begin:opening+len(code)+2]
  selected.append(dict(path=path,signature=sig,line=text[:begin].count('\n')+1,sha256=sha(value.encode())));return value
 h=sources['include/cManager.h'];needle='void operator delete(void*, unsigned int) {}';assert h.count(needle)==1
 (out/'manager_actual_source.h').write_text(h)
 (out/'manager_actual_host.h').write_text(h.replace(needle,'void operator delete(void*, std::size_t) {}'))
 (out/'types.h').write_text('// Fixed-width scalar aliases supplied before the actual header.\n')
 eh=sources['include/event.h'];decls=[]
 for kind,name in [('struct','DatTblEntry'),('class','DatTbl'),('struct','EvtBinEntry'),('struct','EvtHeader'),('struct','EvtPacket'),('class','Event'),('struct','EvtReadEm'),('class','EventMgr')]:
  pattern=r'^'+kind+' '+name+r'(?:\s*:[^{]+)?\s*\{.*?^};';m=re.search(pattern,eh,re.S|re.M);assert m,(kind,name);decls.append(m[0]);selected.append(dict(path='include/event.h',declaration=name,line=eh[:m.start()].count('\n')+1,sha256=sha(m[0].encode())))
 (out/'event_actual_declarations.inc').write_text('\n'.join(decls)+'\nextern EventMgr EvtMgr;\n')
 methods=[]
 for sig in ['static inline int EvtWorkNo(','Event::Event(u8 t)','Event::~Event()','int Event::init(','EventMgr::EventMgr()','EventMgr::~EventMgr()','int EventMgr::construct(','int EventMgr::DelAll()','int EventMgr::Run()','int EventMgr::IsAliveEvt(','int EventMgr::SetEvt(char* nm, Event** out)','DatTbl::DatTbl()','DatTbl::~DatTbl()']:
  methods.append(fn('src/game/event.cpp',sig))
 methods.append('template<class T>\n'+fn('src/game/event.cpp','void cManager<T>::destroyNow(T* p)'))
 (out/'event_actual_methods.inc').write_text('\n'.join(methods)+'\n')
 check=re.search(r'// Verify the actual Event layout.*?^#endif',sources['src/game/event.cpp'],re.S|re.M)[0].rsplit('#endif',1)[0]
 (out/'event_actual_offset_checks.inc').write_text('#if RE4DC_EVENT_MANAGER_STORAGE_FLAGS\n'+check+'\n#endif\n')
 text=sources['src/game/event.cpp'];sig='for (u32 i = 0; i < nArray && pArray; i++)';begin=text.index(sig);opening=text.index('{',begin);code,_,_=body(text[begin:],sig);loop=text[begin:opening+len(code)+2];assert loop.count('RE4DC_EVENT_IS_ALIVE')==1
 (out/'event_actual_reader_scan.inc').write_text(loop+'\n');selected.append(dict(path='src/game/event.cpp',signature='EvtReadExec actual reader census loop',line=text[:begin].count('\n')+1,sha256=sha(loop.encode())))
 (out/'sat_actual_predicate.inc').write_text(fn('include/atari.h','inline int cSat::isAlive()')+'\n')
 fixture=HERE/'event_storage_lifetime_host.cpp';(out/fixture.name).write_bytes(fixture.read_bytes())
 logs=[];results=[]
 def command(argv,label,expect=0):
  cp=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=50,env={**os.environ,'UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=0'})
  (out/(label+'.log')).write_text(cp.stdout);logs.append(dict(label=label,argv=argv,returncode=cp.returncode,log_sha256=sha(cp.stdout.encode())))
  if expect==0:assert cp.returncode==0,(label,cp.stdout[-6000:])
  else:assert cp.returncode!=0 and ('invalid vptr' in cp.stdout or 'does not point to an object of type' in cp.stdout),(label,cp.returncode,cp.stdout)
  return cp.stdout
 base=['g++','-std=c++17','-O1','-g0','-fsanitize=undefined,vptr','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-fno-pie','-no-pie','-fpermissive','-Wall','-Wextra','-DRE4DC_GAME=1','-DRE4DC_CABIN_SOURCE=0','-DRE4DC_EVD_START_CLEANUP=1','-I'+str(out),str(out/fixture.name)]
 for guard in [0,1]:
  binary=out/('guard'+str(guard));command(base+['-DRE4DC_EVENT_MANAGER_STORAGE_FLAGS='+str(guard),'-o',str(binary)],'compile'+str(guard));results.append(dict(guard=guard,binary_sha256=sha(binary.read_bytes()),bytes=binary.stat().st_size))
 command([str(out/'guard1')],'on-lifecycle')
 controls=['raw-count','create','index','back','immediate','deferred','dead-count','direct-del','direct-alive','reader']
 for case in controls:command([str(out/'guard0'),case],'off-'+case,expect=1)
 receipt=dict(source_commit=PIN,source_objects=pins,selected_actual_fragments=selected,host_adapter=dict(header_delete_size='Only empty sized operator delete argument unsigned int→std::size_t for64-bit host ABI; all policy/manager bodies unchanged',placement='standard host placement new; actual header guard',scalars='u32 fixed32; mapped32-bit source addresses',declarations='Complete actual DatTbl/Event/EventMgr declarations, host pointer layout; native offset independently qualified by main SH4 receipt',boundaries='DatTbl allocation/end and packet frame services, logging, Event run/end callbacks are explicit stubs; SetEvt/init/constructor/destructor/manager/directscan bodies actual',sat='actual cSat::isAlive body over projected fields; no non-Event deletion invoked'),strict_flags=base,variants=results,commands=logs,off_expected_failures=controls,scope='Source/host lifecycle only. No heap reset/ABA/issue52/full programme/guest/hardware closure.')
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');size=sum(p.stat().st_size for p in out.rglob('*') if p.is_file());aggregate=sum(p.stat().st_size for d in out.parent.glob('cache21-event-storage-independent[0-9]*') for p in d.rglob('*') if p.is_file());assert aggregate*2+80000<2*1024*1024,aggregate
 print(json.dumps(dict(result='PASS',output=next((out/'on-lifecycle.log').open()).strip(),off_failures=len(controls),fresh_bytes=size,all_attempts_bytes=aggregate,cap_with_mirror_bytes=aggregate*2+80000)))
if __name__=='__main__':main()
