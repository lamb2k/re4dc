"""Actual allocator-excerpt host regression and fail-closed preflight; RAM compile only."""
import hashlib,importlib.util,json,pathlib,struct,subprocess,tempfile
here=pathlib.Path(__file__).parent;proof=json.loads((here/'BACKING-PROOF.json').read_text())
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
v2=module('v2',here/'freeze330-observer-v2.py');v1=module('v1',pathlib.Path(proof['legacy_reader']))
profile=pathlib.Path(proof['profile']).read_bytes();parts=pathlib.Path(proof['parts_source']).read_bytes();legacy=pathlib.Path(proof['legacy_receipt']).read_bytes()
assert v2.authenticate(proof,profile,parts,legacy)=={'ENEMY_DEMAND':1,'OBJECT_DEMAND':1}
assert hashlib.sha256(pathlib.Path(proof['legacy_reader']).read_bytes()).hexdigest()==proof['legacy_reader_sha256']
text=parts.decode()
def excerpt(anchor):
 start=text.index(anchor);left=text.index('{',start);depth=1;i=left+1
 while depth:
  depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i]
cpp='''#include <cassert>\n#include <cstdint>\n#include <cstddef>\nusing u32=std::uint32_t;using u8=unsigned char;\nstruct cParts{};struct cModelInfo{};struct cObj{};struct cEm{};\n#define RE4DC_PARTS_DEMAND 0\n#define RE4DC_MODELINFO_DEMAND 0\n#define RE4DC_OBJECT_DEMAND 1\n#define RE4DC_ENEMY_DEMAND 1\ntemplate<class T> struct cManager {T* pArray;u32 nArray,size;u32 pArrayPush;bool prepareWork(u32,u32);};\n'''
cpp+=excerpt('template<class T> struct alignas(32) Chunk')+';\n'+excerpt('template<class T> struct alignas(32) Pool')+';\n'
start=text.index('template<class T> constexpr bool demand=false;');end=text.index('template<> constexpr bool demand<cEm> = RE4DC_ENEMY_DEMAND;',start)+len('template<> constexpr bool demand<cEm> = RE4DC_ENEMY_DEMAND;');cpp+=text[start:end]+'\n'
cpp+=excerpt('template<class T> bool sparse(')+'\n'+excerpt('template<class T> Pool<T>* pool(')+'\n'
cpp+='template<class T>struct Frozen {u32 n;T**slots;};template<class T>Frozen<T>*frozen(cManager<T>*){return nullptr;}\n'
cpp+=excerpt('template<class T> T* work_at(')+'\n'
cpp+='u32 selected_first,selected_count;template<class T>bool prepare_work(cManager<T>*,u32 f,u32 n){selected_first=f;selected_count=n;return true;}\n'
cpp+=excerpt('template<> bool cManager<cObj>::prepareWork(')+'\n'+excerpt('template<> bool cManager<cEm>::prepareWork(')+'\n'
cpp+='''int main(){
 alignas(32) unsigned char objbuf[sizeof(Pool<cObj>)+10*sizeof(cObj*)]{};
 auto*p=reinterpret_cast<Pool<cObj>*>(objbuf);cManager<cObj>o{reinterpret_cast<cObj*>(p),10,800,0};
 auto*remote=reinterpret_cast<cObj*>(std::uintptr_t(0x8ca00020));p->slots()[6]=remote;
 assert(work_at(&o,6)==remote);assert(work_at(&o,5)==nullptr);assert(work_at(&o,10)==nullptr);
 cManager<cEm>e{nullptr,10,3552,0};assert(o.prepareWork(6,1)&&selected_first==0&&selected_count==8);
 assert(e.prepareWork(6,1)&&selected_first==6&&selected_count==2);
 assert(o.prepareWork(9,1)&&selected_first==8&&selected_count==2);
 assert(!o.prepareWork(10,1)&&!e.prepareWork(0,2));
}\n'''
with tempfile.TemporaryDirectory(prefix='worldemit-sparse-correction-',dir='/dev/shm') as tmp:
 td=pathlib.Path(tmp);(td/'actual-allocator.cpp').write_text(cpp);r=subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',str(td/'actual-allocator.cpp'),'-o',str(td/'control')],capture_output=True,text=True);assert r.returncode==0,r.stderr;subprocess.run([str(td/'control')],check=True)
 print('PASS actual extracted Pool/slots/sparse/work_at and distinct cObj8/cEm2 prepareWork; host pointer ABI adapter only')
 # A source-valid sparse node is outside the false contiguous pArray extent.
 manager=bytearray(56);array=0x8c800000;live=0x8ca00020;struct.pack_into('<III',manager,4,array,8,800);struct.pack_into('<I',manager,20,live)
 try:v1.actor_roster(lambda p,n:(_ for _ in ()).throw(AssertionError('must reject before model read')),manager)
 except v1.Refused as err:assert 'not exact manager slot' in str(err)
 else:raise AssertionError('V1 sparse counterexample did not expose defect')
 print('PASS actual source-valid sparse witness exposes legacy contiguous ownership rejection (observer defect, not game failure)')
 for label,knobs in [('current-both','ENEMY_DEMAND=1\nOBJECT_DEMAND=1\n'),('enemy-only','ENEMY_DEMAND=1\nOBJECT_DEMAND=0\n'),('object-only','ENEMY_DEMAND=0\nOBJECT_DEMAND=1\n'),('unqualified-other-profile','ENEMY_DEMAND=0\nOBJECT_DEMAND=0\n')]:
  try:v2.require_supported_backing(knobs)
  except v2.UnsupportedNativeBacking as err:assert json.loads(str(err))['observer_runtime_supported'] is False
  else:raise AssertionError('guard bypass '+label)
 print('PASS current sparse backing and all unqualified alternative profiles refuse before roster/process access')
 for bad in [b'ENEMY_DEMAND=1\n',profile.replace(b'OBJECT_DEMAND=1',b'OBJECT_DEMAND=0',1),parts+b'\n',legacy+b'\n']:
  try:v2.authenticate(proof,bad if bad.startswith(b'ENEMY_DEMAND=1\n') or bad.startswith(profile[:40]) else profile,bad if bad.startswith(parts[:40]) else parts,bad if bad.startswith(legacy[:40]) else legacy)
  except v2.InvalidBackingProof:pass
  else:raise AssertionError('changed authentication accepted')
 print('PASS malformed/modified profile/source/sealed receipt pins reject')
 out=td/'refusal.json';r=subprocess.run(['python3',str(here/'freeze330-observer-v2.py'),'--proof',str(here/'BACKING-PROOF.json'),'--profile',proof['profile'],'--parts-source',proof['parts_source'],'--legacy-receipt',proof['legacy_receipt'],'--refusal-output',str(out)],capture_output=True,text=True)
 assert r.returncode==3,(r.returncode,r.stderr);report=json.loads(out.read_text());assert report['status']=='UNSUPPORTED_NATIVE_BACKING' and not report['process_opened'] and not report['guest_started'] and not report['strict_pixel_qualified']
 print('PASS real current source/profile CLI returns explicit unsupported3 and never opens/starts a process')
assert hashlib.sha256(pathlib.Path(proof['legacy_receipt']).read_bytes()).hexdigest()==v2.LEGACY_RECEIPT
print('ALL CORRECTION CONTROLS PASS; sealed V1 preserved, no SDK/guest, no sparse-reader or pixel qualification claim')