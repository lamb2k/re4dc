// Compiles the actual candidate readers. Source owners and GPU/cache services
// are synthetic; this test makes no residency or rendered-pixel claim.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdarg>
#include <cstdlib>
#include <new>
#include <cstring>
#include <array>
#include <algorithm>
#include <vector>
#include <cmath>
#include <sys/mman.h>
#include "re4dc_platform.h"
#include "other_profile.h"
#define RE4DC_PS2_WORLD_SOURCE_OWNER 1
#define RE4DC_PS2_WORLD_SOURCE_TEX_PREP 1
#define RE4DC_PRIMITIVE_BUFFERS 2
using u32=std::uint32_t;using u8=unsigned char;using u16=unsigned short;using f32=float;
using Mtx=float[3][4];
template<class T> struct cManager;
struct Vec { float x=0,y=0,z=0; };
struct Camera {struct {Vec pos{};} param;Mtx v_mat{};};
struct Scissor {u32 x=0,y=0,width=640,height=448;bool operator==(const Scissor& b)const{return x==b.x&&y==b.y&&width==b.width&&height==b.height;}}scissor,native_scissor;
Camera native_camera;
struct cLightInfo {Vec Size{1,1,1},Offset{};unsigned PartsNo=1;};
struct ModelDataHead { unsigned char partsNo=0,parentNo=255,x2=0,x3=0;Vec center{}; };
struct ModelData { unsigned nParts=1,shapeOfs=0;ModelDataHead* pHead=nullptr; };
struct cModelInfo { unsigned be_flag=9;float invisible_factor=1;unsigned char color[4]{255,255,255,255};cModelInfo* pList=nullptr;ModelData* pData=nullptr; };
class cModel;
struct cParts { unsigned be_flag=1;cParts* pList=nullptr;cModel* pParent=nullptr;Vec pos{},ang{},scale{1,1,1}; };
class cModel { public:unsigned serial=1,kindid=2,be_flag=7,nParts=1,ot_type=4,z_mode=0;float invisible_factor=1,invisible_factor2=1;Vec pos{},ang{},scale{1,1,1},world{};Mtx mat{};cLightInfo LightInfo;void* pParts=nullptr;cModelInfo* pModelInfo=nullptr;cParts* pList=nullptr;static cManager<cModelInfo>* mm;static cManager<cParts>* pm;cModel* getPartsPtr(int){return this;}void drawAllBoundingBox(cModelInfo*){} };
class cObj:public cModel { public:int blk=-1; };
class cEm:public cModel {};
struct SmdWork { Vec pos{},rot{},scale{1,1,1};unsigned char binNo=0,tplNo=0,motNo=255,id=0;unsigned char pad[28]{};unsigned flags=0; };
static_assert(sizeof(SmdWork)==72);
struct cSmd { unsigned char Version=64,Flag=0;unsigned short nModel=90;unsigned BinTblOfs=0,TplTblOfs=0,MotTblOfs=0;SmdWork work[90]; };
struct Global { unsigned Rno0=3,stage_no=2,room_no=0,System_flg=0x400,Status_flg[4]{},Debug_flg[4]{},Frame_cnt=300;unsigned long prim_cnt=0;unsigned nPrim=65536,vtx_buf_no=0;Camera Cam{}; } global,*pG=&global;
#define G_ROOM_ID ((pG->stage_no<<8)|pG->room_no)
cSmd* pSmd=nullptr;cObj** scrTbl=nullptr;int nScrWork=90;
unsigned room_generation=10,frame=200,re4dc_alive_gen[4]{1,2,3,4};bool room_live=true,movie=false,subscreen=false;
int re4dc_coarse_image=0,re4dc_pace_skipping=0;unsigned log_count,aborts,camera_calls,draw_calls;
unsigned memory_sub=0,memory_table=0,memory_bytes=0;unsigned long memory_address=0;
extern "C" void re4dc_log(const char* format,...){++log_count;
 if(std::strstr(format,"PS2SOURCE_MEMORY")){va_list ap;va_start(ap,format);(void)va_arg(ap,unsigned);
  memory_sub=va_arg(ap,unsigned);memory_table=va_arg(ap,unsigned);memory_address=va_arg(ap,unsigned long);memory_bytes=va_arg(ap,unsigned);va_end(ap);}}
extern "C" int re4dc_room4_state(unsigned* g,unsigned* c,unsigned* b,unsigned* s,unsigned* r){*g=room_generation;*c=*b=*s=*r=0;return room_live;}
extern "C" int re4dc_ui_movie_texture(){return movie;}
extern "C" int re4dc_ss_ui_order(){return subscreen;}
extern "C" unsigned re4dc_ui_frame(){return frame;}
extern "C" void re4dc_model_packet_abort(){++aborts;}
#include "source_world_allocator.inc"
template<class T> struct cManager {T* pArray=nullptr;unsigned nArray=0,size=sizeof(T),pArrayPush=0;bool suspended=false;};
template<class T> constexpr bool demand=true;
template<class T> struct Frozen {unsigned n=0;T** slots=nullptr;};
template<class T> Frozen<T>* frozen(cManager<T>* m){static Frozen<T> f;return m->suspended?&f:nullptr;}
#include "source_world_actual_pools.inc"
cManager<cObj> ObjMgr;cManager<cEm> EmMgr;cManager<cModelInfo> ModInfoMgr;cManager<cParts> PartsMgr;
cManager<cModelInfo>* cModel::mm=&ModInfoMgr;cManager<cParts>* cModel::pm=&PartsMgr;
#include "source_world_pools.inc"
template<class T> T* make_pool(cManager<T>& manager,unsigned count) {
 auto* p=new(host_alloc(sizeof(Pool<T>)+count*sizeof(T*)))Pool<T>{};
 auto* c=new(host_alloc(sizeof(Chunk<T>)+count*sizeof(T)))Chunk<T>{};
 p->capacity=count;p->heap=4;p->handle=Heap[4].handle;p->chunks=c;c->count=count;c->bytes=sizeof(Chunk<T>)+count*sizeof(T);
 manager={reinterpret_cast<T*>(p),count,sizeof(T),0,false};
 for(unsigned i=0;i<count;++i){new(c->parts()+i)T{};p->slots()[i]=c->parts()+i;}return c->parts();
}
std::array<cObj,90>* objects_storage;std::array<cModelInfo,90>* infos_storage;std::array<cParts,90>* parts_storage;
alignas(32) unsigned char archive[30000]{};bool archive_live=true;
extern "C" int re4dc_model_owned_source(const void* p,unsigned bytes){const auto a=reinterpret_cast<std::uintptr_t>(p),b=reinterpret_cast<std::uintptr_t>(archive);return archive_live&&a>=b&&a-b<=sizeof(archive)&&bytes<=sizeof(archive)-(a-b);}
#include "ps2_source_world.h"
#include "source_world_scroll.inc"
struct PartMeta { unsigned crc=0,fnv=0,width=0,height=0,pass=0,cull=0,texture=0,reserved=0; };
struct MeshHeader {unsigned version=3,bytes=510048,crc=3459209119U,mesh_count=63,part_count=152;};
struct WorldPackage {MeshHeader h{};const MeshHeader& header()const{return h;}};
struct Counts {unsigned native=1,fallback=0,aborts=0;};
PartMeta world_parts[152];unsigned sourceWorldPackageGeneration=2,sourceWorldSidecarCrc=4040448078U;
struct Ps2World {void* storage=archive;PartMeta* parts=world_parts;void* placements=archive;void* lut=archive;void* gather=archive;unsigned room=0x200,want=0x200,nplacements=90;WorldPackage package{};Counts count[3]{};}ps2w;
namespace dyn { const unsigned char* ids=archive;unsigned nids=90; }
extern "C" int re4dc_coarse_source_camera(float* v,float* p,float* port){++camera_calls;std::memcpy(v,pG->Cam.v_mat,sizeof(Mtx));std::fill_n(p,7,1.f);std::fill_n(port,6,1.f);return 1;}
extern "C" void re4dc_ps2_mesh_camera(const float* view,const float*,const float*){std::memcpy(native_camera.v_mat,view,sizeof(Mtx));native_scissor=scissor;}
extern "C" int re4dc_ps2_world_source_draw(){++draw_calls;return 1;}
#include "native_source_world.inc"
void ModelRender(cModel*);
// Real enum values are extracted from include/trans_ot.h by the host runner.
#include "source_world_actual_ot.inc"
OtWork g_OtWork[OT_MAX]{};OtData* nodes=nullptr;
struct Gx {unsigned char* prim=nullptr;} gx;
using GxWork=Gx;
#define GXWORK() (&::gx)
#include "source_world_frame.inc"
struct Key {unsigned crc=0,fnv=0;bool operator==(const Key& b)const{return crc==b.crc&&fnv==b.fnv;}};
// Match the public Texture descriptor fields read by the production predicate.
// Synthetic services still do not validate/upload actual GPU payloads.
namespace re4dc::texture {
constexpr unsigned kArgb4444=2,kAlpha=1,kBinaryAlpha=2,kMipmap=4;
constexpr unsigned kPayloadLinear=0,kPayloadTwiddled=1,kPayloadVq=2;
}
struct Tex {unsigned width=256,height=256,format=2,data_size=131072,flags=0,payload=1,reserved_0=0;};
struct TexHeader {unsigned texture_count=1;};
struct TexturePackage {bool uploaded=true;unsigned bytes=131072;void* vram=archive;Tex t{};TexHeader h{};bool upload_complete()const{return uploaded;}unsigned vram_bytes()const{return bytes;}void* pvr_texture(unsigned)const{return vram;}const TexHeader& header()const{return h;}const Tex* textures()const{return &t;}};
struct Entry {bool valid=true;Key key{};unsigned frame=0;TexturePackage package{};}cache_entry;
bool frame_ready=true,stream_scene=false,stream_retire=false,stream_aborted=false,direct_open=false;unsigned vram_claims=0,loads=0,load_case=0,texfails=0;bool loaded_pin=false;
#include "native_ui.h"
Entry* load(const Re4dcUiImage& image,bool pin,const Key* key){++loads;loaded_pin=pin;assert(image.format==5&&image.width==256&&image.height==256);cache_entry.key=*key;cache_entry.frame=frame;
 if(load_case==1)return nullptr;if(load_case==2)++sourceWorldPackageGeneration;if(load_case==3)++room_generation;if(load_case==4)++global.Frame_cnt;return &cache_entry;}
#define RE4DC_TEXCHK_FAIL(key,why) (++texfails)
#include "native_ui_source_world.inc"
// Instrumented external geometry/GX services around exact production bodies.
struct GeoSphere {Vec pos;float r;};struct GeoHexahedron{};
void* CameraViewFrustumPtr(Camera*){static GeoHexahedron h;return &h;}
bool collision_sphere_hexahedron(GeoSphere*,GeoHexahedron*){return true;}
void CameraGetLookVecInverse(Camera*,Vec* out){*out={0,0,1};}
float PSVECDotProduct(Vec* a,Vec* b){return a->x*b->x+a->y*b->y+a->z*b->z;}
void PSMTXMultVecSR(Mtx,Vec* a,Vec* out){*out=*a;}
void PSVECAdd(Vec* a,Vec* b,Vec* out){*out={a->x+b->x,a->y+b->y,a->z+b->z};}
bool isBit(unsigned a,unsigned b){return (a&b)!=0;}
#define SQRTF(x) std::sqrt(x)
#define ENCV_TRANS_NOTE(m,n) ((void)0)
#define OT_MARK(w,f) ((void)0)
#define RE4_MEM_LO 1U
#define RE4_MEM_HI 0xffffffffU
#define PTR_INVALID(p) (reinterpret_cast<std::uintptr_t>(p)<RE4_MEM_LO)
void U32Set(u32& value,u32 next){value=next;}
int g_NowExecOtType=OT_MAX;float OT_MUL=.05f;
unsigned screen_prepares,light_prepares,callback_postludes,source_geometry,shader_resets,draw_syncs,mixed_callbacks;
std::vector<int> callback_tables;
std::vector<Scissor> callback_scissors;std::vector<Camera> callback_cameras;
int commonScreenMat(cModel*){++screen_prepares;return 1;}
void lightSetEm(cModel*){++light_prepares;}void lightSetObj(cModel*){++light_prepares;}
void GXSetAlphaCompare(int,int,int,int,int){}
void GXSetZMode(int,int,int){}
void CameraCurrentProjection(){}
void GXSetNumChans(int){}
void GXSetChanCtrl(int,int,int,int,int,int,int){}
struct GXColor {u8 r,g,b,a;};
void GXSetChanAmbColor(int,GXColor){}void GXSetChanMatColor(int,GXColor){}
void LightSetModel(cModel*){}
void GXSetAlphaUpdate(int){}void GXSetDstAlpha(int,int){}
void shaderReset(){++shader_resets;}
void* g_prev_tpl_addr=nullptr;void* g_prev_add_tpl_addr=nullptr;
void GXSetCurrentGXThread(){}
struct {void setFog(){}} LightMgr;
void SetDrawTmpBufType(int){}void bio4_AddBgColor(){}void drawGround(int){}void ClearZbuf(){}
Camera itemCamera{};
void GXSetFog(int,float,float,float,float,GXColor){}
#define FRef(x) 1.f
int Filter09GetbUse(){return 0;}void Filter09Render(int){}
void GXSetDrawSync(int){++draw_syncs;}void Render_DrawSyncCallback(u16){}void GXSetDrawSyncCallback(void(*)(u16)){}
struct {float x=0,y=0,width=640,height=448;}Screen;
void GXSetScissor(u32 x,u32 y,u32 w,u32 h){scissor={x,y,w,h};}
void ClearOt();void clearOtWork(OtWork*);void CrearOtMirrorWork(){}
#include "source_world_actual_registration.inc"
#define objects (*objects_storage)
#define infos (*infos_storage)
#define source_parts (*parts_storage)
unsigned checks=0;void check_at(bool ok,unsigned line){++checks;if(!ok){std::fprintf(stderr,"check %u at line %u failed\n",checks,line);std::abort();}}
#define check(v) check_at((v),__LINE__)
struct GuardPage {
 void* p=mmap(nullptr,4096,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 GuardPage(){assert(p!=MAP_FAILED);}~GuardPage(){munmap(p,4096);}
};
void NonModelCallback(void*){++mixed_callbacks;}
void reset(unsigned n=3){
 global=Global{};pG=&global;room_generation=10;frame=200;room_live=archive_live=true;movie=subscreen=false;re4dc_coarse_image=re4dc_pace_skipping=0;
 screen_prepares=light_prepares=callback_postludes=source_geometry=shader_resets=draw_syncs=mixed_callbacks=0;
 callback_tables.clear();callback_scissors.clear();callback_cameras.clear();scissor=Scissor{};native_scissor=Scissor{};native_camera=Camera{};
 allocator_reset();
 assert(MemReplaceHeap(0,1)&&MemSetCurrentHeap(1));InitOt();
 assert(MemReplaceHeap(1,2)&&MemSetCurrentHeap(2));host_alloc(96);
 assert(MemReplaceHeap(2,3)&&MemSetCurrentHeap(3));host_alloc(96);
 assert(MemReplaceHeap(3,4)&&MemSetCurrentHeap(4));
 objects_storage=reinterpret_cast<std::array<cObj,90>*>(make_pool(ObjMgr,90));
 infos_storage=reinterpret_cast<std::array<cModelInfo,90>*>(make_pool(ModInfoMgr,90));
 parts_storage=reinterpret_cast<std::array<cParts,90>*>(make_pool(PartsMgr,90));make_pool(EmMgr,4);
 cModel::mm=&ModInfoMgr;cModel::pm=&PartsMgr;
 scrTbl=static_cast<cObj**>(host_alloc(90*sizeof(cObj*)));std::fill_n(scrTbl,90,nullptr);
 global.prim_cnt=reinterpret_cast<unsigned long>(host_alloc(global.nPrim*RE4DC_PRIMITIVE_BUFFERS));gx.prim=reinterpret_cast<unsigned char*>(global.prim_cnt);sourceWorldPrimGeneration=1;
 re4dc_alive_gen[0]=1;re4dc_alive_gen[2]=3;sourceWorldPackageGeneration=2;sourceWorldSidecarCrc=4040448078U;ps2w=Ps2World{};dyn::ids=archive;dyn::nids=90;
 sourceWorldFailures=sourceWorldReports=0;memory_sub=memory_table=memory_bytes=0;memory_address=0;
 sourceWorldImageFrame=~0U;sourceWorldImageGeneration=0;sourceWorldImageResult=0;sourceWorldFrame=SourceWorldFrame{};sourceWorldRenderActive=false;
 aborts=camera_calls=draw_calls=loads=load_case=texfails=0;loaded_pin=false;frame_ready=true;stream_scene=stream_retire=stream_aborted=direct_open=false;vram_claims=0;
 sourceWorldPreparedFrame=sourceWorldAcquired=0;cache_entry=Entry{};
 std::memset(archive,0,sizeof(archive));pSmd=new(archive)cSmd{};pSmd->BinTblOfs=(sizeof(cSmd)+31)&~31U;
 auto* offsets=reinterpret_cast<unsigned*>(archive+pSmd->BinTblOfs);unsigned off=(pSmd->BinTblOfs+90*4+31)&~31U;
 nScrWork=90;sourceWorldScrollClear();
 for(unsigned i=0;i<90;++i){
  auto& w=pSmd->work[i];w.binNo=i;w.id=i;offsets[i]=off-pSmd->BinTblOfs;
  auto* d=new(archive+off)ModelData{};off+=32;d->pHead=new(archive+off)ModelDataHead{};off+=32;
  objects[i]=cObj{};infos[i]=cModelInfo{};source_parts[i]=cParts{};
  objects[i].serial=100+i;objects[i].pModelInfo=&infos[i];objects[i].pList=&source_parts[i];infos[i].pData=d;source_parts[i].pParent=&objects[i];scrTbl[i]=&objects[i];sourceWorldScrollBind(i,&objects[i]);
 }
 if(n)for(auto& ot:g_OtWork)ot={};nodes=static_cast<OtData*>(host_alloc(100*sizeof(OtData)));for(unsigned i=0;i<100;++i)new(nodes+i)OtData{};
 for(unsigned i=0;i<n;++i){nodes[i]={&objects[i%90],reinterpret_cast<void(*)(void*)>(ModelRender),i?&nodes[i-1]:nullptr};}
 if(n)g_OtWork[0x0b]={nodes,n};world_parts[13]={0xfa6fe38cU,0x1a02365fU,256,256,2,0,17,0};
}
int main(){
 // Real ModelTrans -> AddOt* -> accepted reader -> real Render/ExecOt -> real
 // ModelRender postludes. Raw0x10 has exactly source id06, as in staged r200.
 for(unsigned mixed=0;mixed<2;++mixed){reset(0);unsigned generation=0;
  check(Heap[1].handle==-1&&Heap[4].handle!=4);
  for(unsigned table=0;table<OT_MAX;++table){const auto& ot=g_OtWork[table];
   check(!sourceWorldAllocated(ot.list,ot.max*sizeof(OtData),true));
   check(re4dc_source_world_ot_retained(ot.list,ot.max*sizeof(OtData)));}
  global.System_flg=0x0c40;global.Cam.v_mat[0][0]=1;global.Cam.v_mat[1][1]=2;global.Cam.v_mat[2][2]=3;itemCamera.v_mat[0][0]=99;
  for(unsigned i=0;i<21;++i){auto& m=objects[i];m.ot_type=i==6?5:i<7?4:i<14?0:1;m.pos.z=pSmd->work[i].pos.z=100;ModelTrans(&m);}
  GuardPage ignored;AddOtDirect(0x10,ignored.p,reinterpret_cast<void(*)()>(NonModelCallback),0,0,nullptr,0);
  if(mixed){auto* enemy=work_at(&EmMgr,0);enemy->kindid=0;enemy->ot_type=0;enemy->pos.z=100;enemy->pModelInfo=&infos[50];ModelTrans(enemy);}
  check(screen_prepares==21+mixed&&light_prepares==21+mixed);
  check(re4dc_source_world_prepare(frame,&generation)&&sourceWorldFrame.count==21);
  unsigned after=0;for(auto* p=&g_OtWork[OT_TYPE_AFTER_RENDER].list[g_OtWork[OT_TYPE_AFTER_RENDER].max-1];p;p=p->next)
   if(p->data&&p->func==reinterpret_cast<void(*)(void*)>(ModelRender)){++after;check(p->data==&objects[6]);}
  check(after==1);sourceWorldTexturePrepare();check(sourceWorldFrame.ready&&loads==1);
  Render();
  check(draw_calls==1&&camera_calls==1&&aborts==0&&source_geometry==mixed);
  check(callback_postludes==21+mixed&&shader_resets==21+mixed&&mixed_callbacks==1&&draw_syncs==1);
  check(!sourceWorldRenderActive&&g_NowExecOtType==OT_MAX);
  check(std::count(callback_tables.begin(),callback_tables.end(),OT_TYPE_AFTER_RENDER)==1);
  check(std::is_sorted(callback_tables.begin(),callback_tables.end()));
  for(unsigned i=0;i<callback_tables.size();++i){check(callback_scissors[i]==native_scissor);check(std::memcmp(callback_cameras[i].v_mat,native_camera.v_mat,sizeof(Mtx))==0);}
  check(native_scissor.y==56&&native_scissor.height==337&&scissor.y==0&&scissor.height==448);
  check(global.Cam.v_mat[0][0]==1&&!(global.Status_flg[3]&0x10000000));
 }
 // Real source retirement changes the OT epoch even while heap4 objects
 // and identical bucket bytes remain; pre-draw fallback and post-draw abort.
 for(unsigned started=0;started<2;++started){reset(0);
  for(unsigned i=0;i<21;++i){auto& m=objects[i];m.ot_type=i==6?5:i<7?4:i<14?0:1;m.pos.z=pSmd->work[i].pos.z=100;ModelTrans(&m);}
  sourceWorldTexturePrepare();check(sourceWorldFrame.ready&&sourceWorldFrame.count==21);
  {SourceWorldRenderScope scope;if(started)check(sourceWorldDraw(&objects[0])==1);
   check(MemDestroyHeap(1)==0);check(!re4dc_source_world_current(frame,2));
   check(sourceWorldDraw(&objects[1])==(started?-1:0));}
  check(draw_calls==started&&aborts==started);
 }
 // Rebuild the exact same source addresses: all older synthetic room/model
 // generations intentionally recur, but the allocator publication epoch must not.
 for(unsigned started=0;started<2;++started){reset(0);
  for(unsigned i=0;i<21;++i){auto& m=objects[i];m.ot_type=i==6?5:i<7?4:i<14?0:1;m.pos.z=pSmd->work[i].pos.z=100;ModelTrans(&m);}
  sourceWorldTexturePrepare();if(started){SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[0])==1);}
  const auto old_frame=sourceWorldFrame;const auto old_object=&objects[0];const auto old_bucket=g_OtWork[0x0b].list;
  reset(0);for(unsigned i=0;i<21;++i){auto& m=objects[i];m.ot_type=i==6?5:i<7?4:i<14?0:1;m.pos.z=pSmd->work[i].pos.z=100;ModelTrans(&m);}
  check(&objects[0]==old_object&&g_OtWork[0x0b].list==old_bucket&&re4dc_source_world_ot_epoch()!=old_frame.ot_epoch);
  sourceWorldFrame=old_frame;check(!re4dc_source_world_current(frame,2));
  {SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[1])==(started?-1:0));}
  check(!draw_calls&&aborts==started);
 }
 // Safe diagnostics distinguish each allocator/extent/traversal refusal.
 {GuardPage guard;for(unsigned sub=1;sub<=7;++sub){reset();unsigned g=0;
  switch(sub){case 1:global.nPrim=0;break;case 2:global.prim_cnt=reinterpret_cast<unsigned long>(guard.p);break;
   case 3:gx.prim=reinterpret_cast<unsigned char*>(global.prim_cnt+global.nPrim+1);break;
   case 4:g_OtWork[0x0b].max=4097;break;case 5:g_OtWork[0x0b].list=static_cast<OtData*>(guard.p);break;
   case 6:nodes[1].next=static_cast<OtData*>(guard.p);break;case 7:nodes[1].data=nullptr;nodes[1].next=&nodes[1];break;}
  check(!re4dc_source_world_prepare(frame,&g)&&memory_sub==sub);check(!draw_calls&&!aborts);
  if(sub>=4)check(memory_table==0x0b);else check(memory_table==~0U);
 }
 reset();sourceWorldTexturePrepare();check(MemDestroyHeap(1)==0);check(!sourceWorldWalk(false)&&memory_sub==8);}
 reset();unsigned work=999,gen=0;check(re4dc_scroll_source_member(&objects[0],100,&work)&&work==0);
 reset();sourceWorldTexturePrepare();const auto prim_before=global.prim_cnt;const auto buffer_before=global.vtx_buf_no;
 SetPrimBuffPtr();SetPrimBuffPtr();check(global.prim_cnt==prim_before&&global.vtx_buf_no==buffer_before);
 check(!re4dc_source_world_current(frame,2));{SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[0])==0);}check(aborts==0);
 reset();sourceWorldTexturePrepare();{SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[0])==1);
 SetPrimBuffPtr();SetPrimBuffPtr();check(sourceWorldDraw(&objects[1])==-1);}check(aborts==1);
 reset();
 for(unsigned i=0;i<90;++i){check(re4dc_scroll_source_member(&objects[i],100+i,&work)&&work==i);}
 reset();sourceWorldTexturePrepare();check(loads==1&&loaded_pin&&sourceWorldPreparedFrame==frame);check(re4dc_source_world_current(frame,2));
 check(!sourceWorldCandidate(&objects[0]));{SourceWorldRenderScope scope;check(sourceWorldCandidate(&objects[0]));check(sourceWorldDraw(&objects[2])==1);check(sourceWorldDraw(&objects[1])==1);}check(draw_calls==1&&camera_calls==1&&!sourceWorldRenderActive);
 sourceWorldTextureAcquired(cache_entry.key);check(sourceWorldAcquired==1);check(re4dc_ps2_source_passes_complete());ps2w.count[2].fallback=1;re4dc_source_world_flush_result(frame,re4dc_ps2_source_passes_complete());check(aborts==1&&!sourceWorldFrame.active);
 // The actual event-transition mask still executes Render's source OTs.
 reset();global.System_flg=0x0c40;sourceWorldTexturePrepare();
 check(loads==1&&sourceWorldFrame.ready);{SourceWorldRenderScope scope;
 check(sourceWorldDraw(&objects[2])==1);check(sourceWorldDraw(&objects[1])==1);}
 check(draw_calls==1&&aborts==0&&global.System_flg==0x0c40);
 // The event bit alone never bypasses movie, source-OT or render exclusions.
 for(unsigned mutation=0;mutation<8;++mutation){reset();global.System_flg=0x0c40;
 switch(mutation){case 0:movie=true;break;case 1:subscreen=true;break;
 case 2:global.System_flg&=~0x400;break;case 3:re4dc_coarse_image=1;break;
 case 4:re4dc_pace_skipping=1;break;case 5:global.System_flg|=0x100000;break;
 case 6:global.Status_flg[1]=0x100;break;case 7:global.Status_flg[2]=0x04000000;break;}
 sourceWorldTexturePrepare();check(loads==0&&!sourceWorldFrame.ready);}
 // Each real ModelTrans target is accepted, descriptive aliases are not.
 for(unsigned table:{0x0bU,0x0dU,0x10U,0x11U}){reset();g_OtWork[0x0b]={};g_OtWork[table]={nodes,3};
 sourceWorldTexturePrepare();check(sourceWorldFrame.count==3&&sourceWorldFrame.ready);
 {SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==1);}check(draw_calls==1&&aborts==0);}
 for(unsigned table:{unsigned(OT_TYPE_SCROLL),unsigned(OT_TYPE_MODEL)}){reset();g_OtWork[0x0b]={};g_OtWork[table]={nodes,3};
 sourceWorldTexturePrepare();check(!sourceWorldFrame.active&&loads==0);}
 // A member published twice across real tables is not silently drawn twice.
 reset();g_OtWork[0x0d]={nodes,3};sourceWorldTexturePrepare();check(!sourceWorldFrame.active&&loads==0);
 // Publication serial, current source owner and room generation fail before a stale info dereference.
 reset();objects[0].serial++;objects[0].pModelInfo=reinterpret_cast<cModelInfo*>(mmap(nullptr,4096,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0));check(!re4dc_scroll_source_member(&objects[0],101,&work));munmap(objects[0].pModelInfo,4096);
 reset();archive_live=false;check(!re4dc_scroll_source_member(&objects[0],100,&work));reset();room_generation++;check(!re4dc_scroll_source_member(&objects[0],100,&work));
 reset();scrTbl[1]=scrTbl[0];check(!re4dc_scroll_source_member(&objects[0],100,&work));reset();sourceWorldScrollClear();check(!re4dc_scroll_source_member(&objects[0],100,&work));
 // Protected pages are passed into the production reader. None is readable,
 // including the complete cModel payload (the old test protected only info).
 {GuardPage guard;
  for(unsigned mutation=0;mutation<11;++mutation){reset();switch(mutation){
   case 0:g_OtWork[0x0b].list=static_cast<OtData*>(guard.p);break;
   case 1:nodes[1].next=static_cast<OtData*>(guard.p);break;
   case 2:nodes[1].data=guard.p;break;
   case 3:nodes[1].data=guard.p;scrTbl[1]=static_cast<cObj*>(guard.p);break;
   case 4:objects[1].pModelInfo=static_cast<cModelInfo*>(guard.p);break;
   case 5:objects[1].pList=static_cast<cParts*>(guard.p);break;
   case 6:scrTbl=static_cast<cObj**>(guard.p);break;
   case 7:ObjMgr.pArray=static_cast<cObj*>(guard.p);break;
   case 8:ModInfoMgr.pArray=static_cast<cModelInfo*>(guard.p);break;
   case 9:PartsMgr.pArray=static_cast<cParts*>(guard.p);break;
   case 10:pool(&ObjMgr)->chunks=static_cast<Chunk<cObj>*>(guard.p);break;}
   check(!re4dc_source_world_prepare(frame,&gen));check(draw_calls==0&&aborts==0);
  }
  reset();nodes[1].data=guard.p;nodes[1].func=NonModelCallback;
  check(re4dc_source_world_prepare(frame,&gen)&&sourceWorldFrame.count==2);
  reset();auto* enemy=work_at(&EmMgr,0);enemy->kindid=0;nodes[1].data=enemy;
  check(re4dc_source_world_prepare(frame,&gen)&&sourceWorldFrame.count==2);
  reset();sourceWorldTexturePrepare();objects[1].pModelInfo=static_cast<cModelInfo*>(guard.p);
  {SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==0);}check(draw_calls==0&&aborts==0);
  reset();sourceWorldTexturePrepare();{SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==1);
   objects[1].pModelInfo=static_cast<cModelInfo*>(guard.p);check(sourceWorldDraw(&objects[1])==-1);
   check(!sourceWorldCandidate(static_cast<cModel*>(guard.p)));}check(aborts==1);
  reset();sourceWorldTexturePrepare();{SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==1);
   ++objects[1].serial;objects[1].pModelInfo=static_cast<cModelInfo*>(guard.p);
   check(sourceWorldDraw(&objects[1])==-1);}check(aborts==1);
 }
 // Exact current slot publication is required, including reused addresses,
 // withdrawn chunks, frozen managers, offsets within a valid allocated cell.
 for(unsigned mutation=0;mutation<12;++mutation){reset();switch(mutation){
  case 0:pool(&ObjMgr)->slots()[1]=nullptr;break;
  case 1:pool(&ModInfoMgr)->slots()[1]=nullptr;break;
  case 2:pool(&PartsMgr)->slots()[1]=nullptr;break;
  case 3:ObjMgr.suspended=true;break;
  case 4:ObjMgr.pArrayPush=1;break;
  case 5:pool(&ObjMgr)->handle++;break;
  case 6:pool(&ObjMgr)->capacity--;break;
  case 7:nodes[1].data=reinterpret_cast<unsigned char*>(&objects[1])+4;break;
  case 8:objects[1].pModelInfo=reinterpret_cast<cModelInfo*>(reinterpret_cast<unsigned char*>(&infos[1])+4);break;
  case 9:objects[1].pList=reinterpret_cast<cParts*>(reinterpret_cast<unsigned char*>(&source_parts[1])+4);break;
  case 10:objects[1].serial++;break;
  case 11:Heap[4].status=1;break;}
  check(!re4dc_source_world_prepare(frame,&gen));check(draw_calls==0&&aborts==0);
 }
 // An old slot value is insufficient when its owning allocation is withdrawn.
 for(unsigned type=0;type<3;++type){reset();const void* chunk=type==0?static_cast<void*>(pool(&ObjMgr)->chunks):
   type==1?static_cast<void*>(pool(&ModInfoMgr)->chunks):static_cast<void*>(pool(&PartsMgr)->chunks);
  auto* cell=reinterpret_cast<const OSHeapCell*>(chunk)-1;
  for(auto** link=&heap_descriptors[Heap[4].handle].allocated;*link;link=&(*link)->next)if(*link==cell){*link=(*link)->next;break;}
  check(!re4dc_source_world_prepare(frame,&gen));check(!draw_calls&&!aborts);
 }
 // A real OtPrim must be fully below the captured allocation cursor. Allocated
 // but unused capacity, the previous buffer and misaligned addresses all fail.
 for(unsigned mutation=0;mutation<6;++mutation){reset();
  auto* primitive=new(reinterpret_cast<void*>(global.prim_cnt))OtPrim{};
  primitive->ot={&objects[3],reinterpret_cast<void(*)(void*)>(ModelRender),nodes,2};
  nodes[1].next=&primitive->ot;gx.prim+=64;
  switch(mutation){case 0:break;case 1:gx.prim-=64;break;
   case 2:nodes[1].next=reinterpret_cast<OtData*>(global.prim_cnt+32);break;
   case 3:nodes[1].next=reinterpret_cast<OtData*>(global.prim_cnt+global.nPrim);break;
   case 4:nodes[1].next=reinterpret_cast<OtData*>(global.prim_cnt+1);break;
   case 5:nodes[1].next=&nodes[1];break;}
  check(bool(re4dc_source_world_prepare(frame,&gen))==(mutation==0));
 }
 for(unsigned mutation=0;mutation<22;++mutation){reset();auto& m=objects[0];auto& info=infos[0];auto& p=source_parts[0];auto& w=pSmd->work[0];auto* d=info.pData;
  switch(mutation){case 0:m.blk=0;break;case 1:m.kindid=1;break;case 2:m.be_flag=0;break;case 3:m.invisible_factor=.5f;break;case 4:m.ang.x=.1f;break;case 5:m.pos.y=1;break;case 6:m.scale.z=2;break;case 7:w.flags=16;break;case 8:w.motNo=0;break;case 9:info.pList=&infos[1];break;case 10:info.pData=infos[1].pData;break;case 11:info.be_flag=11;break;case 12:info.invisible_factor=.5f;break;case 13:info.color[3]=128;break;case 14:d->nParts=2;break;case 15:d->shapeOfs=4;break;case 16:p.pParent=&objects[1];break;case 17:p.ang.x=.87266463f;break;case 18:p.pos.x=1;break;case 19:p.scale.y=2;break;case 20:p.pList=&source_parts[1];break;case 21:p.be_flag=0;break;}
  check(!re4dc_scroll_source_member(&m,100,&work));check(bool(re4dc_source_world_prepare(frame,&gen))==(mutation==1));
 }
 // Being inside the current allocation does not make a chunk header aligned.
 for(unsigned type=0;type<3;++type){reset();
  if(type==0)pool(&ObjMgr)->chunks=reinterpret_cast<Chunk<cObj>*>(reinterpret_cast<unsigned char*>(pool(&ObjMgr)->chunks)+1);
  else if(type==1)pool(&ModInfoMgr)->chunks=reinterpret_cast<Chunk<cModelInfo>*>(reinterpret_cast<unsigned char*>(pool(&ModInfoMgr)->chunks)+1);
  else pool(&PartsMgr)->chunks=reinterpret_cast<Chunk<cParts>*>(reinterpret_cast<unsigned char*>(pool(&PartsMgr)->chunks)+1);
  check(!re4dc_source_world_prepare(frame,&gen));check(!draw_calls&&!aborts);
 }
 // Context exclusions and exact source/package/primitive epochs.
 for(unsigned mutation=0;mutation<10;++mutation){reset();switch(mutation){case 0:movie=true;break;case 1:subscreen=true;break;case 2:global.System_flg=0;break;case 3:global.room_no=1;break;case 4:global.Rno0=2;break;case 5:re4dc_pace_skipping=1;break;case 6:re4dc_coarse_image=1;break;case 7:global.System_flg|=0x100000;break;case 8:global.Status_flg[2]=0x04000000;break;case 9:global.Status_flg[1]=0x100;break;}check(!re4dc_source_world_prepare(frame,&gen));check(loads==0);}
 for(unsigned mutation=0;mutation<9;++mutation){reset();sourceWorldTexturePrepare();switch(mutation){case 0:++room_generation;break;case 1:++sourceWorldPackageGeneration;break;case 2:++re4dc_alive_gen[2];break;case 3:++re4dc_alive_gen[0];break;case 4:++global.Frame_cnt;break;case 5:++global.prim_cnt;break;case 6:++global.nPrim;break;case 7:++global.vtx_buf_no;break;case 8:++sourceWorldPrimGeneration;break;}check(!re4dc_source_world_current(frame,2));}
 reset();nodes[0].data=nodes[1].data;check(!re4dc_source_world_prepare(frame,&gen));reset(91);check(!re4dc_source_world_prepare(frame,&gen));reset(0);check(!re4dc_source_world_prepare(frame,&gen));
 reset();sourceWorldTexturePrepare();nodes[0].data=&objects[4];{SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==0);}check(draw_calls==0);
 reset();sourceWorldTexturePrepare();source_parts[0].ang.x=.8f;{SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==0);}check(draw_calls==0);
 reset();sourceWorldTexturePrepare();ps2w.count[0].fallback=1;{SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==-1);}check(aborts==1&&draw_calls==1);
 // No mixed GC fallback after a native header: changed epochs/poses abort the scene once.
 for(unsigned mutation=0;mutation<9;++mutation){reset();sourceWorldTexturePrepare();{
  SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==1);
  switch(mutation){case 0:++room_generation;break;case 1:++sourceWorldPackageGeneration;break;case 2:++re4dc_alive_gen[2];break;case 3:++re4dc_alive_gen[0];break;case 4:++global.Frame_cnt;break;case 5:++global.prim_cnt;break;case 6:++global.nPrim;break;case 7:++global.vtx_buf_no;break;case 8:++sourceWorldPrimGeneration;break;}
  check(sourceWorldDraw(&objects[1])==-1);check(sourceWorldDraw(&objects[0])==-1);
 }check(aborts==1&&draw_calls==1&&sourceWorldFrame.failed);}
 reset();sourceWorldTexturePrepare();{SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==1);source_parts[0].ang.x=.8f;}check(aborts==1&&sourceWorldFrame.failed);
 reset();sourceWorldTexturePrepare();{SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==1);objects[0].invisible_factor=0;}check(aborts==1&&sourceWorldFrame.failed);
 for(unsigned mutation=0;mutation<11;++mutation){reset();switch(mutation){case 0:ps2w.storage=nullptr;break;case 1:sourceWorldPackageGeneration=~0U;break;case 2:sourceWorldSidecarCrc++;break;case 3:ps2w.package.h.crc++;break;case 4:ps2w.package.h.bytes++;break;case 5:ps2w.parts=nullptr;break;case 6:ps2w.nplacements++;break;case 7:dyn::ids=nullptr;break;case 8:dyn::nids--;break;case 9:ps2w.room++;break;case 10:ps2w.want++;break;}check(!re4dc_ps2_source_package(&gen));}
 for(unsigned mutation=0;mutation<7;++mutation){reset();auto& q=world_parts[13];switch(mutation){case 0:q.crc++;break;case 1:q.fnv++;break;case 2:q.width=128;break;case 3:q.pass=1;break;case 4:q.texture=18;break;case 5:q.height=128;break;case 6:q.reserved=1;break;}Re4dcSourceWorldTexture out{};check(!re4dc_ps2_source_texture(2,&out));sourceWorldTexturePrepare();check(loads==0&&!sourceWorldFrame.ready);}
 for(unsigned mutation=0;mutation<6;++mutation){reset();switch(mutation){case 0:frame_ready=false;break;case 1:stream_scene=true;break;case 2:stream_retire=true;break;case 3:stream_aborted=true;break;case 4:direct_open=true;break;case 5:vram_claims=1;break;}sourceWorldTexturePrepare();check(loads==0&&!sourceWorldFrame.active);}
 for(unsigned mutation=1;mutation<=4;++mutation){reset();load_case=mutation;sourceWorldTexturePrepare();check(loads==1&&!sourceWorldFrame.ready&&!sourceWorldPreparedFrame);}
 for(unsigned mutation=0;mutation<8;++mutation){reset();switch(mutation){case 0:cache_entry.valid=false;break;case 1:cache_entry.package.uploaded=false;break;case 2:cache_entry.package.bytes=10240;break;case 3:cache_entry.package.vram=nullptr;break;case 4:cache_entry.package.h.texture_count=2;break;case 5:cache_entry.package.t.width=128;break;case 6:cache_entry.package.t.height=128;break;case 7:cache_entry.package.bytes=65536;break;}sourceWorldTexturePrepare();check(loads==1&&!sourceWorldFrame.ready);}
 reset();const auto before=objects;const auto before_infos=infos;const auto before_parts=source_parts;const auto before_global=global;
 std::array<unsigned char,sizeof(archive)> before_archive;std::memcpy(before_archive.data(),archive,sizeof(archive));
 sourceWorldTexturePrepare();{SourceWorldRenderScope scope;check(sourceWorldDraw(&objects[2])==1);}
 for(unsigned i=0;i<90;++i){check(std::memcmp(&before[i],&objects[i],sizeof(cObj))==0);}
 check(std::memcmp(before_infos.data(),infos.data(),sizeof(infos))==0);
 check(std::memcmp(before_parts.data(),source_parts.data(),sizeof(source_parts))==0);
 check(std::memcmp(&before_global,&global,sizeof(global))==0);
 check(std::memcmp(before_archive.data(),archive,sizeof(archive))==0);
 check(aborts==0);
 // Representation regression: execute the actual preparation/readiness path.
 // Keep existing legacy formats/layouts and reject inconsistent metadata even
 // when one byte count happens to match the historical size allowlist.
 for(unsigned format=0;format<3;++format)for(unsigned payload=0;payload<2;++payload){
  reset();cache_entry.package.t.format=format;cache_entry.package.t.payload=payload;
  sourceWorldTexturePrepare();check(sourceWorldFrame.ready&&loads==1&&texfails==0);
 }
 for(unsigned format=0;format<3;++format)for(unsigned mip=0;mip<2;++mip){
  reset();auto& t=cache_entry.package.t;t.format=format;t.payload=2;t.flags=mip?4u:0u;
  cache_entry.package.bytes=t.data_size=mip?23894u:18432u;
  sourceWorldTexturePrepare();
#if defined(RE4DC_PS2_WORLD_SOURCE_TEX_VQ) && RE4DC_PS2_WORLD_SOURCE_TEX_VQ
#if RE4DC_CAST_MIPMAP
  const bool expected=true;
#else
  const bool expected=mip==0;
#endif
#else
  const bool expected=false;
#endif
  check(sourceWorldFrame.ready==expected);
  check(texfails==(expected?0u:1u));
 }
 for(unsigned mutation=0;mutation<16;++mutation){
  reset();auto& t=cache_entry.package.t;t.payload=2;t.flags=4;
  cache_entry.package.bytes=t.data_size=23894;
  switch(mutation){
   case 0:--cache_entry.package.bytes;break; // truncated/partial upload bytes
   case 1:--t.data_size;break;              // truncated descriptor
   case 2:t.flags=0;break;                 // mip-sized but base-only layout
   case 3:t.payload=1;break;               // VQ-sized but twiddled layout
   case 4:t.format=3;break;                // indexed/non-16-bit representation
   case 5:t.flags|=1u<<30;break;           // dropped top level
   case 6:t.reserved_0=1;break;
   case 7:t.width=128;break;
   case 8:t.height=128;break;
   case 9:cache_entry.package.uploaded=false;break;
   case 10:cache_entry.package.h.texture_count=2;break;
   case 11:cache_entry.package.vram=nullptr;break;
   case 12:--cache_entry.package.bytes;--t.data_size;break;
   case 13:++cache_entry.package.bytes;++t.data_size;break;
   case 14:cache_entry.package.bytes=t.data_size=18432;break;
   case 15:t.flags=0;t.payload=0;cache_entry.package.bytes=t.data_size=18432;break;
  }
  sourceWorldTexturePrepare();check(!sourceWorldFrame.ready&&texfails==1);
 }
 for(unsigned mutation=0;mutation<5;++mutation){
  reset();auto& t=cache_entry.package.t;
  switch(mutation){case 0:t.data_size=18432;break;case 1:t.payload=9;break;
   case 2:t.format=5;break;case 3:t.flags=4;break;case 4:t.flags=8;break;}
  sourceWorldTexturePrepare();check(!sourceWorldFrame.ready&&texfails==1);
 }
 std::printf("source world actual readers: %u checks PASS (synthetic source/cache/GPU services)\n",checks);
}
