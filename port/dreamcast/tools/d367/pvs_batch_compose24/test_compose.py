#!/usr/bin/env python3
"""Host-only source-extracted lifecycle controls. No SDK or media access."""
import hashlib,json,os,pathlib,re,subprocess,tempfile,time,unittest
ROOT=pathlib.Path(__file__).resolve().parents[5]
GAME=ROOT/'port/dreamcast/game';PL=GAME/'platform';BASE='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
# Preserve the original b6/fb qualification; separately compare current composed
# source against the reviewed integrated pre-composer (GC+selected-affine) tree.
HISTORICAL_COMPOSE='b6b4fa7a3cf3a5244d28a31eae9a8bf42f18ce45'
INTEGRATED_PRECOMPOSE='e3ed0d2ab2482ade7f5a3615009f59a43ccdcfae'
def text(rel):return (GAME/rel).read_text()
def function(s,anchor):
 a=s.index(anchor);i=s.index('{',a);level=1;j=i+1
 while level:
  level+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[a:j]
def between(s,a,b):return s[s.index(a):s.index(b,s.index(a))]
def cpp_tokens(s):return re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\d+|\S',s)
ONE='PS2_PVS SCENERY_SUBMIT_BATCH SCENERY_CHUNK SCENERY_SELECT_ONLY SCENERY_REPLAY_LEAN TA_DIRECT MESH_DIRECT PS2_WORLD_MESH PS2_WORLD_HDR_CACHE PS2_STRIP_GROUPS MESH_FASTPATH MESH_VP_SCHED HW_LEAN PVR_STREAM D349_RENDERER_STACK PS2_WORLD_SOURCE_OWNER PS2_WORLD_SOURCE_TEX_PREP'.split()
ZERO='WORLD_SCRATCH TA_GUARD PS2_WORLD_TRANSITION_OWNER PS2_WORLD_R11F_OWNER SCENERY_PIECE_STATE SCENERY_DEDUP SCENERY_CONE CPU_BACKFACE TA_MATERIAL_DIAG WORLD_HOLE_DIAG PS2_WORLD_PREFLIGHT_DIAG GC_ASSET_GATE GC_ASSET_MOTION_UNKNOWN'.split()
class Controls(unittest.TestCase):
 def build(self,src,expected=True):
  with tempfile.TemporaryDirectory(prefix='pvsbc-host-',dir='/dev/shm') as t:
   p=pathlib.Path(t);(p/'unit.cpp').write_text(src)
   c=subprocess.run(['g++','-std=c++17','-O0',str(p/'unit.cpp'),'-o',str(p/'run')],capture_output=True,text=True)
   self.assertEqual(c.returncode,0,c.stderr)
   r=subprocess.run([str(p/'run')],capture_output=True,text=True)
   self.assertEqual(r.returncode==0,expected,r.stderr)
   if not expected:
    self.assertEqual(r.returncode,-6,r.stderr)
    self.assertIn('Assertion',r.stderr)
 def test_make_prerequisites_and_original_guard(self):
  with tempfile.TemporaryDirectory(prefix='pvsbc-make-',dir='/dev/shm') as t:
   p=pathlib.Path(t)/'Makefile';p.write_text('OBJDIR=obj\ninclude '+str(GAME/'scenery19.mk')+'\n.PHONY: all\nall:;@:\n')
   def call(over):
    d={**dict.fromkeys(ONE,'1'),**dict.fromkeys(ZERO,'0'),'PS2_PVS_DEFAULT':'0','PS2_PVS_BATCH_COMPOSE':'1'};d.update(over)
    return subprocess.run(['make','-s','-f',str(p),'all',*[k+'='+v for k,v in d.items()]],capture_output=True,text=True)
   self.assertEqual(call({}).returncode,0)
   for k in ONE:
    for v in ['0','2','']:
     with self.subTest(k=k,v=v):self.assertNotEqual(call({k:v}).returncode,0)
   for k in ZERO:
    with self.subTest(k=k):self.assertNotEqual(call({k:'1'}).returncode,0)
   for d in [{'PS2_PVS_BATCH_COMPOSE':'0'},{'PS2_PVS_BATCH_COMPOSE':'2'},{'PS2_PVS_BATCH_COMPOSE':''},{'PS2_PVS_DEFAULT':'1'},{'PS2_INTERIOR_CULL':'2'}]:self.assertNotEqual(call(d).returncode,0)
   self.assertEqual(call({'PS2_PVS_BATCH_COMPOSE':'0','PS2_PVS':'0'}).returncode,0)
 def test_source_guards(self):
  for rel in ['platform/native_static.cpp','platform/native_ui.cpp']:
   s=between(text(rel),'// PVS_BATCH_COMPOSITION_GUARD\n','// PVS_BATCH_COMPOSITION_GUARD_END')
   def compile(over):
    d={**dict.fromkeys(ONE,'1'),**dict.fromkeys(ZERO,'0'),'PS2_PVS_DEFAULT':'0','PS2_PVS_BATCH_COMPOSE':'1'};d.update(over)
    return subprocess.run(['g++','-x','c++','-E','-P',*[('-DRE4DC_'+k+'='+v) for k,v in d.items()],'-'],input=s,capture_output=True,text=True)
   self.assertEqual(compile({}).returncode,0,rel)
   must=ONE if rel.endswith('native_static.cpp') else [x for x in ONE if x in ['PS2_PVS','SCENERY_SUBMIT_BATCH','TA_DIRECT','PS2_WORLD_HDR_CACHE','PVR_STREAM','D349_RENDERER_STACK','PS2_WORLD_SOURCE_OWNER','PS2_WORLD_SOURCE_TEX_PREP']]
   for k in must+ZERO+['PS2_PVS_DEFAULT','PS2_PVS_BATCH_COMPOSE','PS2_INTERIOR_CULL']:
    for v in (['0','2'] if k in must else (['1','2'] if k in ZERO else ['2'])):
     with self.subTest(rel=rel,k=k,v=v):self.assertNotEqual(compile({k:v}).returncode,0)
 def test_full_file_off_preprocess(self):
  for before,after,label in [(BASE,HISTORICAL_COMPOSE,'historical-b6-vs-fb'),(INTEGRATED_PRECOMPOSE,None,'current-vs-integrated-precomposer')]:
   for rel in ['platform/native_static.cpp','platform/native_ui.cpp','platform/include/native_ui_source_world.inc']:
    old=subprocess.check_output(['git','-C',str(ROOT),'show',before+':port/dreamcast/game/'+rel],text=True)
    for pvs,batch in [(0,0),(0,1),(1,0)]:
     flags=['-DRE4DC_GC_ASSET_GATE=0','-DRE4DC_GC_ASSET_MOTION_UNKNOWN=0','-DRE4DC_PS2_PVS_BATCH_COMPOSE=0','-DRE4DC_PS2_PVS='+str(pvs),'-DRE4DC_SCENERY_SUBMIT_BATCH='+str(batch),'-DRE4DC_TA_DIRECT=1','-DRE4DC_PS2_WORLD_HDR_CACHE=1','-DRE4DC_PS2_WORLD_SOURCE_OWNER=1','-DRE4DC_PS2_WORLD_SOURCE_TEX_PREP=1','-DRE4DC_SCENERY_CHUNK=1','-DRE4DC_NATIVE_MESH=1','-DRE4DC_MESH_FASTPATH=1','-DRE4DC_MESH_DIRECT=1','-DRE4DC_PS2_WORLD_MESH=1','-DRE4DC_MESH_LOD=1','-DRE4DC_PS2_WORLD_LEAN=1','-DRE4DC_MESH_PRIME_LAZY=1','-DRE4DC_MESH_VP_SCHED=1','-DRE4DC_MESH_STRIP_LEAN=1','-DRE4DC_HW_LEAN=1','-DRE4DC_MESH_DEPTH_CULL=1','-D__sh__=1','-DRE4DC_PVR_STREAM=1','-DRE4DC_D349_RENDERER_STACK=1']
     streams=[]
     for s in [old,subprocess.check_output(['git','-C',str(ROOT),'show',after+':port/dreamcast/game/'+rel],text=True) if after else text(rel)]:
      s=re.sub(r'^#include .*\n','',s,flags=re.M)
      r=subprocess.run(['g++','-x','c++','-E','-P',*flags,'-'],input=s,capture_output=True,text=True)
      self.assertEqual(r.returncode,0,r.stderr);streams.append(cpp_tokens(r.stdout))
     self.assertEqual(*streams,(label,rel,pvs,batch))
 def fixture(self,snapshot=0,baseline=False,source_ref=None):
  ref=source_ref or (BASE if baseline else None)
  read=(lambda rel:subprocess.check_output(['git','-C',str(ROOT),'show',ref+':port/dreamcast/game/'+rel],text=True)) if ref else text
  ui=read('platform/native_ui.cpp');st=read('platform/native_static.cpp');sw=read('platform/include/native_ui_source_world.inc')
  acquire=between(sw,'Key sourceWorldPreparedKey{};','#endif\n#if (defined(RE4DC_PS2_WORLD_SOURCE_TEX_MIP)')
  # Last endif is the outer SOURCE_TEX_PREP, not part of the extracted fixture.
  acquire=acquire.rsplit('\n#endif',1)[0] if acquire.rstrip().endswith('#endif') else acquire
  ending=between(ui,'// WORLD_SUBMIT_END_IMPLEMENTATION\n','// WORLD_SUBMIT_END_IMPLEMENTATION_END')
  full=between(ui,'// WORLD_SUBMIT_BEGIN_IMPLEMENTATION\n','// WORLD_SUBMIT_BEGIN_IMPLEMENTATION_END')
  starts=[m.start() for m in re.finditer(r'#if RE4DC_SCENERY_SUBMIT_BATCH\n\s+auto\* sq=batch',full)]
  self.assertEqual(len(starts),2)
  tails=[full[a:full.index('return 1;',a)+len('return 1;')] for a in starts]
  failure=function(full,'struct FailedBegin')+';'
  # Pick the second image declaration: the first belongs to optional diagnostic comparison.
  coldstart=full.index('    const Re4dcUiImage image{&key,nullptr,k[2],k[3],5,0,0};',full.index('return 1;'))
  cold=full[coldstart:full.index('    Entry* handle=load(image,false,&key);',coldstart)+len('    Entry* handle=load(image,false,&key);')]
  after_load=full[full.index('    Entry* handle=load(image,false,&key);',coldstart)+len('    Entry* handle=load(image,false,&key);'):full.index('    const auto& t=handle->package.textures()[0];',coldstart)]
  prepare=between(sw,'void sourceWorldTexturePrepare() {','    // Also call prepare with an unusable frame to retire any previous ticket.')+'}\n'
  # Use the complete actual flush, with only external renderer methods mocked.
  flush=function(st,'auto chunk_flush=[&]()->int')
  finish=function(st,'void pvs_finish(bool success)')
  restart=function(st,'void chunk_restart()')
  # Project the real disabled GC branch; do not mock a GC handle/provider.
  # fb254 had no GC instrumentation: preserve that historical fixture unchanged.
  disabled_model_macros=''
  if '#define RE4DC_GCA_MODEL_ACCEPT' in ui:
   disabled=between(ui,'#else\n#define RE4DC_GCA_TEXTURE(...) ((void)0)','#endif\n#if defined(RE4DC_FX_PS2_PACK)')
   disabled_model_macros='\n'.join(re.findall(r'^#define RE4DC_GCA_MODEL_(?:ACCEPT\(\)|TEXTURE\(\.\.\.\)) \(\(void\)0\)$',disabled,re.M))+'\n'
   self.assertEqual(len(disabled_model_macros.splitlines()),2)
  else:self.assertIn(ref,[BASE,HISTORICAL_COMPOSE],'Current GC0 source macro branch missing')
  return disabled_model_macros+r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
#include <cstdarg>
#include <string>
#define RE4DC_PS2_PVS_BATCH_COMPOSE 1
#define RE4DC_GC_ASSET_GATE 0
#define RE4DC_GC_ASSET_MOTION_UNKNOWN 0
#define RE4DC_PS2_WORLD_SOURCE_TEX_PREP 1
#define RE4DC_SCENERY_SUBMIT_BATCH 1
#define RE4DC_SCENERY_REPLAY_LEAN 1
#define RE4DC_PS2_PVS 1
#define RE4DC_TA_DIRECT 1
#define RE4DC_WHD(x) ((void)0)
#define RE4DC_SCENERY_UV_SNAPSHOT '''+str(snapshot)+r'''
struct Key {unsigned crc,fnv;bool operator==(const Key& o)const{return crc==o.crc && fnv==o.fnv;}};
struct Re4dcWorldSubmitBatch {std::uint32_t* sq=nullptr;};
bool direct_open=false,sq_live=false,load_fail=false,frame_ready=true,stream_aborted=false;unsigned frame=7,unlocks=0,locks=0,logs=0,loads=0,missing=0,model_texture_rejects=0;
struct Log {unsigned frame,crc,fnv;std::string what;};std::vector<Log> log_rows;
void re4dc_log(const char* f,...){assert(!sq_live && !direct_open);++logs;va_list ap;va_start(ap,f);unsigned x=va_arg(ap,unsigned),y=va_arg(ap,unsigned);unsigned z=std::strstr(f,"ACQUIRE")?va_arg(ap,unsigned):0;va_end(ap);log_rows.push_back({x,y,z,f});}
void* sq_lock(void*){assert(!sq_live);sq_live=true;++locks;static std::uint32_t words[128]{};return words;}
void sq_unlock(){assert(sq_live);sq_live=false;++unlocks;}
void sq_flush(void*){assert(sq_live);}
void re4dc_missing(const char*){assert(!sq_live && !direct_open);++missing;}
constexpr void* PVR_TA_INPUT=nullptr;
'''+acquire+r'''
unsigned direct_parts=0,direct_slots=0,frame_pvr_calls=0,frame_pvr_bytes=0,stream_model_bytes=0,stream_peak_bytes=0,model_used=0,model_pending=8;
'''+ending+r'''
struct Entry {unsigned frame;};Entry entry{};Entry* model_handle=&entry;
struct Re4dcUiImage {const Key* key;void* data;unsigned w,h,a,b,c;};
Entry* load(const Re4dcUiImage&,bool,const Key*){assert(!sq_live && !direct_open);++loads;return load_fail?nullptr:&entry;}
std::uint32_t model_packets[128]{};constexpr unsigned kModelPacketBytes=4096;
struct Re4dcModelDirect {std::uint32_t* sq;void* scratch;unsigned scratch_capacity;float u_scale,v_scale;};
'''+failure+r'''
int fail(Re4dcWorldSubmitBatch* batch){FailedBegin failed_begin{batch};return 0;}
int hot(Re4dcWorldSubmitBatch* batch,const Key& key){FailedBegin failed_begin{batch};Re4dcModelDirect result{},*out=&result;
'''+tails[0]+r'''
}
int cold(Re4dcWorldSubmitBatch* batch,const Key& key){FailedBegin failed_begin{batch};unsigned k[6]={key.crc,key.fnv,8,8,0,0};
'''+cold+after_load+r'''
(void)handle;Re4dcModelDirect result{},*out=&result;
'''+tails[1]+r'''
}
'''+prepare+r'''
namespace re4dc {namespace room {struct MeshPart {float uv_bias[2]{},uv_scale[2]{};};}}
struct Part {unsigned cull=9;float uv_offset[2]{30,40};};
struct Package {re4dc::room::MeshPart data[3]{};const re4dc::room::MeshPart* parts()const{return data;}};
struct Pick {unsigned result=1,pending=0;};
std::vector<float> sent_uv;unsigned commits=0,aborts=0;bool cold_next=false;
void re4dc_pvs23_commit(unsigned,unsigned,const unsigned*,const unsigned*){assert(!sq_live && !direct_open);++commits;}
int re4dc_model_packet_streaming(){return 1;}
void re4dc_model_packet_abort(){assert(!sq_live && !direct_open);++aborts;}
struct EmitterData {Part& part;float mv[12];float near,far;};
struct MeshDraw {
 Part& p;Re4dcWorldSubmitBatch* submit_batch=nullptr;bool direct=false,lean_part=false,streaming=false,bound=false,submitted=false;
 unsigned sg_groups=0,alpha=0,part_index=0,slots=0,used=0,input=0,output=0,primed=99,pvs_placement=0,pvs_pending[3]{0,0,0};
 void *sg=nullptr,*cache=(void*)1;float mvq[12]{};const unsigned* ps2=nullptr;
 MeshDraw(EmitterData e,const Package&,const re4dc::room::MeshPart&,void*,void*):p(e.part){}
 void set_clip(){}
'''+restart+r'''
 int chunk_emit(const Pick* picks,unsigned n){assert(!cache && !primed && !bound && !submitted);if(!n)return 1;const auto& x=*picks;
  if(!x.result)return 0;sent_uv.push_back(p.uv_offset[0]);sent_uv.push_back(p.uv_offset[1]);Key key{1,2};
  if(cold_next)cold(submit_batch,key);else hot(submit_batch,key);slots=3;pvs_pending[2]=x.pending;return int(x.result);
 }
 void end_direct(){if(direct_open)re4dc_ps2_world_direct_end_batch(slots,submit_batch);}
'''+finish+r'''
};
void queued(unsigned result,unsigned pending,unsigned contexts=2,bool empty_first=false){
 Part part;Package cpkg;float near=1,far=100;
 struct ChunkPart {unsigned cull,index,placement,first,count;float uv_offset[2],mvq[12];unsigned key[6];};
 ChunkPart cctx[2]{};cctx[0].cull=1;cctx[1].cull=2;cctx[0].uv_offset[0]=1;cctx[0].uv_offset[1]=2;cctx[1].uv_offset[0]=3;cctx[1].uv_offset[1]=4;cctx[1].first=1;cctx[0].count=cctx[1].count=1;
 if(empty_first)cctx[0].count=0;Pick cpk[2]={{1,0},{result,pending}};unsigned nctx=contexts,npk=contexts;
 struct {void *lut=nullptr,*gather=nullptr,*sg=nullptr;unsigned sg_groups=0;} ps2w;
 struct {unsigned native=0,aborts=0,fallback=0;} c;
'''+flush+r''';
 unsigned before=commits;const unsigned uv_begin=sent_uv.size();int status=chunk_flush();assert(!sq_live && !direct_open && !sourceWorldDiagnosticSqHeld);assert(part.cull==9);assert(part.uv_offset[0]==30 && part.uv_offset[1]==40);if(!contexts){assert(status==1 && commits==before);return;}
 #if RE4DC_SCENERY_UV_SNAPSHOT
 if(!empty_first){assert(sent_uv[uv_begin]==1 && sent_uv[uv_begin+1]==2);}if(result && contexts==2){unsigned i=uv_begin+(empty_first?0:2);assert(sent_uv[i]==3 && sent_uv[i+1]==4);}
#else
 if(!empty_first){assert(sent_uv[uv_begin]==30 && sent_uv[uv_begin+1]==40);}if(result && contexts==2){unsigned i=uv_begin+(empty_first?0:2);assert(sent_uv[i]==30 && sent_uv[i+1]==40);}
#endif
 if(int(result)<0){assert(status==-1 && commits==before && aborts);}
 else {assert(status==1);assert(commits==before+(pending && result && contexts==2));}
}
int main(){
 sourceWorldPreparedKey={1,2};sourceWorldPreparedFrame=frame;Re4dcWorldSubmitBatch b;
 hot(&b,{9,2});assert(!logs && !sourceWorldAcquired);re4dc_ps2_world_direct_end_batch(3,&b);assert(sq_live && sourceWorldDiagnosticSqHeld);re4dc_ps2_world_batch_close(&b);
 hot(&b,{1,2});assert(sourceWorldAcquired==1 && sourceWorldAcquireDiagnostic.pending && !logs);re4dc_ps2_world_direct_end_batch(3,&b);assert(sq_live && !direct_open);
 sourceWorldTexturePrepare();assert(sourceWorldPreparedFrame==7 && sourceWorldAcquired==1 && !logs); // unsupported held reentry preserves live owner; no new ticket
 re4dc_ps2_world_batch_close(&b);assert(logs==1 && log_rows.back().frame==7 && log_rows.back().crc==1 && log_rows.back().fnv==2);
 hot(&b,{1,2});re4dc_ps2_world_direct_end_batch(3,&b);re4dc_ps2_world_batch_close(&b);assert(logs==1);
 sourceWorldTexturePrepare();assert(logs==2 && sourceWorldPreparedFrame==0 && sourceWorldAcquired==0); // acquire before USED
 frame=9;sourceWorldPreparedFrame=9;sourceWorldPreparedKey={1,2};cold(nullptr,{1,2});assert(loads==1 && sourceWorldAcquired==1);re4dc_model_direct_end(3);assert(!sq_live && logs==3);sourceWorldTexturePrepare();
 // A captured OLD key/frame is independent of later live globals.
 frame=10;sourceWorldPreparedFrame=10;hot(&b,{1,2});re4dc_ps2_world_direct_end_batch(3,&b);frame=11;sourceWorldPreparedKey={8,9};re4dc_ps2_world_batch_close(&b);assert(log_rows.back().frame==10 && log_rows.back().crc==1 && log_rows.back().fnv==2);
 sourceWorldTexturePrepare();assert(!sourceWorldAcquired);
 // Actual FailedBegin destructor cannot close a nested live part, but closes
 // an idle prior prefix on failure. Overflow closes before its diagnostic.
 unsigned old_unlocks=unlocks;hot(&b,{9,2});fail(&b);assert(sq_live && unlocks==old_unlocks);
 re4dc_ps2_world_direct_end_batch(3,&b);fail(&b);assert(!sq_live && unlocks==old_unlocks+1);
 hot(&b,{9,2});re4dc_ps2_world_direct_end_batch(32768,&b);assert(!sq_live && missing==1);
 hot(&b,{9,2});re4dc_ps2_world_direct_end_batch(3,&b);load_fail=true;
 assert(!cold(&b,{1,2}) && !sq_live && !b.sq && model_texture_rejects==1);load_fail=false;
 queued(1,3,0);queued(1,3,1);queued(1,3,2,true);queued(1,3);queued(0,0);queued(unsigned(-1),3);cold_next=true;queued(1,3);
 assert(!sq_live && !direct_open);assert(sizeof(SourceWorldAcquireDiagnostic)==16);return 0;
}
'''
 def test_host_off_object_identity_and_state(self):
  with tempfile.TemporaryDirectory(prefix='pvsbc-identity-',dir='/dev/shm') as t:
   p=pathlib.Path(t);objects=[]
   for before,after in [(BASE,HISTORICAL_COMPOSE),(INTEGRATED_PRECOMPOSE,None)]:
    objects=[]
    for index,ref in enumerate([before,after]):
     prefix=self.fixture(source_ref=ref).split('struct Entry {')[0]
     prefix=prefix.replace('#define RE4DC_PS2_PVS_BATCH_COMPOSE 1','#define RE4DC_PS2_PVS_BATCH_COMPOSE 0')
     f=p/'unit.cpp';obj=p/('old.o' if index==0 else 'new.o');f.write_text(prefix)
     r=subprocess.run(['g++','-std=c++17','-O2','-g0','-c',str(f),'-o',str(obj)],capture_output=True,text=True)
     self.assertEqual(r.returncode,0,r.stderr)
     subprocess.run(['objcopy','--strip-all',str(obj)],check=True);objects.append(obj.read_bytes())
    self.assertEqual(*objects,(before,after))
   # Source-owned resident state:16-byte event plus1-byte held bool on host.
   f.write_text(self.fixture().split('struct Entry {')[0]);obj=p/'on.o'
   subprocess.run(['g++','-std=c++17','-O2','-c',str(f),'-o',str(obj)],check=True)
   symbols=subprocess.check_output(['nm','-S','--defined-only',str(obj)],text=True)
   for name,size in [('sourceWorldAcquireDiagnostic',16),('sourceWorldDiagnosticSqHeld',1)]:
    rows=[x for x in symbols.splitlines() if x.split()[-1]==name];self.assertEqual(len(rows),1);self.assertEqual(int(rows[0].split()[1],16),size)
 def test_actual_hot_cold_queue_snapshot0_and1(self):
  for s in [0,1]:
   with self.subTest(snapshot=s):self.build(self.fixture(s))
 def test_receipt_only_dispatch_and_mutant(self):
  s=text('platform/native_static.cpp');a=s.index('#if RE4DC_PS2_PVS_BATCH_COMPOSE\n        // Qualification mode ONLY:');b=s.index('\n#endif',a)+len('\n#endif');dispatch=s[a:b]
  prefix='#include <cassert>\n#include <cstdint>\n#define RE4DC_PS2_PVS_BATCH_COMPOSE 1\nnamespace pvs {unsigned calls=0;std::uint8_t token=1;const std::uint8_t* cur=&token;bool can_cut(unsigned){++calls;return true;}}\nint main(){unsigned i=0;\n'
  src=prefix+dispatch+'\nassert(!pvs_cur && !pvs::calls && pvs::cur==&pvs::token);}'
  self.build(src);self.build(src.replace('pvs_cur=nullptr','pvs_cur=pvs::can_cut(i)?pvs::cur:nullptr'),False)
 def test_semantic_mutants(self):
  src=self.fixture(1)
  mutants=[('lost_source_close','result<=0 || e.pvs_pending[2]','result<=0'),('hot_log','sourceWorldAcquireDiagnostic={key,frame,true};','sourceWorldAcquireDiagnostic={key,frame,true}; re4dc_log("ACQUIRE",frame,key.crc,key.fnv);'),('logical_only_flush','if(direct_open || sourceWorldDiagnosticSqHeld)return false;','if(direct_open)return false;'),('old_frame','const unsigned old_frame=d.frame;','const unsigned old_frame=frame;'),('lost_uv_restore','value[0]=saved[0];value[1]=saved[1];','/* dropped pending UV restoration */'),('prepare_flush','if(!sourceWorldTextureFlushAcquired())return;','/* lost flush/refusal */'),('old_key','const Key key=d.key;','const Key key=sourceWorldPreparedKey;'),('duplicate_event','d.pending=false;','/* pending retained */'),('lost_hold_tracking','sourceWorldDiagnosticSqHeld=true;','sourceWorldDiagnosticSqHeld=false;')]
  for name,a,b in mutants:
   with self.subTest(name=name):
    self.assertIn(a,src);self.build(src.replace(a,b),False)
if __name__=='__main__':
 os.environ['PYTHONDONTWRITEBYTECODE']='1';unittest.main()
