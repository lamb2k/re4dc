#pragma once
// Fixed private-QA diagnostics. Addresses are copied numeric identities only;
// no retained pointer is dereferenced after the synchronous query.
#include <cstdint>
#include <cstring>
namespace actor_visibility23 { namespace witness {
enum Failure : unsigned { Incomplete=1,Overflow=2,Pair=4,Identity=8,Sequence=16,Context=32 };
enum Stage : unsigned { NotCalled,Scene,Cell,Receipt,Metadata,Placement };
struct Owner {
 std::uintptr_t owner=0,info=0;unsigned id=0,serial=0,epoch=0,life=0,role=0,flags=0,room=0,game=0,ui=0;
};
struct Source {
 std::uintptr_t owner=0,info=0,positions=0,blob=0,records=0;
 unsigned workspace=0,mode=0,lod=0,meshlet=0,nv=0,nt=0,path=0;
};
struct World {
 std::uintptr_t storage=0,metadata=0,current_storage=0,current_metadata=0;
 unsigned stage=NotCalled,field=0,result=0,owner=0,active=0,complete=0,epoch=0,stamp=0,
  frame=0,current_frame=0,scene=0,current_scene=0,fpscr=0,current_fpscr=0,
  coverage=0,required=0,room=0,metadata_bytes=0,metadata_version=0;
 float near=0,far=0,current_near=0,current_far=0;
};
struct Query {
 Source source{};Owner owner{};World world{};
 float box[6]{},words[25]{};unsigned token=0;bool live=false,tracked=false,bounded=false,potential=false,committed=false;
};
struct Counts {unsigned query=0,bound=0,potential=0,would=0,skip=0,positions=0,triangles=0;};
struct Sample {Query query{};bool present=false;};
struct State {
 bool active=false,sealed=false,complete=false,owner_seen=false,await_skip=false,ignore_skip=false;
 unsigned mode=0,binds=0,last=0,failures=0,unattributed=0,tokens=0;
 Owner owner{};std::uintptr_t infos[2]{};Counts parts[2]{};Sample samples[4]{};Query pending{};
 void add(unsigned& value,unsigned n){if(n>~0U-value){value=~0U;failures|=Overflow;}else value+=n;}
 void window(unsigned event,unsigned serial,unsigned selected,unsigned count){
  // Window::Event values are checked by host controls against the actual header.
  if(event==1){if(active||sealed){failures|=Sequence;return;}active=true;mode=selected;binds=1;last=serial;if(count!=1||selected>2)failures|=Sequence;return;}
  if(!active)return;
  if(pending.live||await_skip||ignore_skip)failures|=Pair;
  if(event==2){if(serial<=last||count!=binds+1U||selected!=mode)failures|=Sequence;last=serial;add(binds,1);return;}
  if(event==3||event==4||event==5){
   if(serial<=last)failures|=Sequence;
   complete=event==3&&binds==600&&count==600;
   if(!complete)failures|=Incomplete;
   for(const auto& sample:samples)if(sample.present&&sample.query.potential&&mode==2&&!sample.query.committed)failures|=Pair;
   active=false;sealed=true;
  }
 }
 bool qualified()const{return sealed&&complete&&owner_seen&&mode>0&&!failures;}
 void begin(const Source& source){
  if(!active)return;
  if(pending.live||await_skip||ignore_skip)failures|=Pair;
  pending={};pending.live=true;pending.source=source;
  if(tokens==~0U)failures|=Overflow;else++tokens;
  pending.token=tokens;
  if(source.workspace!=last||source.mode!=mode||source.path>1||!source.nv||!source.nt)failures|=Context;
 }
 void identify(int status,const Owner& value){
  if(!pending.live)return;
  if(status==0){add(unattributed,1);return;}
  if(status!=1||value.id!=0x2b||!value.owner||!value.info||!value.epoch||!value.life||value.role>1||
     !(value.flags&1U)||(value.flags&0x4000U)||value.room!=0x119||
     value.owner!=pending.source.owner||value.info!=pending.source.info){failures|=Identity;return;}
  if(owner_seen&&(value.owner!=owner.owner||value.serial!=owner.serial||value.epoch!=owner.epoch||value.life!=owner.life))failures|=Identity;
  if(infos[value.role]&&infos[value.role]!=value.info)failures|=Identity;
  infos[value.role]=value.info;
  if(!owner_seen){owner=value;owner_seen=true;}
  pending.owner=value;pending.tracked=true;
 }
 static bool finite(float value){unsigned bits;std::memcpy(&bits,&value,4);return(bits&0x7f800000U)!=0x7f800000U;}
 void bounds(const float* lo,const float* hi,const float* view,const float* P,const float* V){
  if(!pending.live||!pending.tracked)return;
  for(unsigned i=0;i<3;++i)if(!finite(lo[i])||!finite(hi[i])||lo[i]>hi[i]){failures|=Context;return;}
  std::memcpy(pending.box,lo,12);std::memcpy(pending.box+3,hi,12);
  std::memcpy(pending.words,view,48);std::memcpy(pending.words+12,P,28);std::memcpy(pending.words+19,V,24);
  for(float value:pending.words)if(!finite(value)){failures|=Context;return;}
  pending.bounded=true;
 }
 void world(const World& value){if(pending.live&&pending.tracked)pending.world=value;}
 void revalidate(int status,const Owner& value){
  if(!pending.live||!pending.tracked)return;
  const auto& old=pending.owner;
  if(status!=1||value.owner!=old.owner||value.info!=old.info||value.id!=old.id||value.serial!=old.serial||
     value.epoch!=old.epoch||value.life!=old.life||value.role!=old.role||value.flags!=old.flags||value.room!=old.room)failures|=Identity;
  if(value.game!=old.game||value.ui!=old.ui)failures|=Context;
 }
 void potential(){
  if(!pending.live||!pending.tracked)return;
  pending.potential=true;const auto& w=pending.world;
  if(!pending.bounded||w.stage!=Placement||w.result!=1||!w.owner||w.active||!w.complete||
     (w.field!=5&&w.field!=7)||!w.required||w.coverage!=w.required||!w.current_scene||
     w.scene!=w.current_scene||w.frame!=w.current_frame||w.storage!=w.current_storage||
     !w.storage||!w.epoch||w.epoch!=w.stamp||w.fpscr!=w.current_fpscr||w.room!=0x119||!w.metadata||w.metadata!=w.current_metadata||
     w.metadata_bytes!=1376||w.metadata_version!=2||pending.owner.ui!=w.current_frame)failures|=Context;
 }
 void end(bool result){
  if(!pending.live)return;
  if(!pending.tracked){ignore_skip=result;pending={};return;}
  auto& c=parts[pending.owner.role];add(c.query,1);
  if(pending.bounded)add(c.bound,1);
  if(pending.potential){add(c.potential,1);add(c.would,pending.source.nv);}
  if(result!=(pending.potential&&mode==2))failures|=Pair;
  const unsigned index=pending.owner.role*2U+unsigned(pending.potential);
  if(pending.bounded&&!samples[index].present){samples[index].present=true;samples[index].query=pending;}
  pending.live=false;await_skip=result;
  if(!result)pending={};
 }
 void skip(unsigned path,unsigned lod,unsigned meshlet,unsigned nv,unsigned nt){
  if(!active)return;
  if(ignore_skip){ignore_skip=false;return;}
  if(!await_skip||!pending.tracked||pending.live||mode!=2||!pending.potential||
     path!=pending.source.path||lod!=pending.source.lod||meshlet!=pending.source.meshlet||nv!=pending.source.nv||nt!=pending.source.nt){failures|=Pair;return;}
  auto& c=parts[pending.owner.role];add(c.skip,1);add(c.positions,nv);add(c.triangles,nt);
  for(auto& sample:samples)if(sample.present&&sample.query.token==pending.token)sample.query.committed=true;
  await_skip=false;pending={};
 }
};
static_assert(sizeof(float)==4&&sizeof(unsigned)==4,"witness requires native32 words");
static_assert(sizeof(State)<=4096,"fixed diagnostic state cap");
} }
extern "C" {
int re4dc_actor_visibility23_witness_owner(const void*,const void*,unsigned,actor_visibility23::witness::Owner*);
void re4dc_actor_visibility23_witness_begin(const actor_visibility23::witness::Source*);
void re4dc_actor_visibility23_witness_identity(int,const actor_visibility23::witness::Owner*);
void re4dc_actor_visibility23_witness_bounds(const float*,const float*,const float*,const float*,const float*);
void re4dc_actor_visibility23_witness_world(const actor_visibility23::witness::World*);
void re4dc_actor_visibility23_witness_potential();
void re4dc_actor_visibility23_witness_end(int);
void re4dc_actor_visibility23_witness_skip(unsigned,unsigned,unsigned,unsigned,unsigned);
}
