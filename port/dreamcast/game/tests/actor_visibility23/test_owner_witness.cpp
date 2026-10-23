#include "../../platform/include/actor_visibility23_witness.h"
#include "../../platform/include/actor_visibility23_window.h"
#include <cassert>
#include <limits>
using namespace actor_visibility23::witness;
static Source source(unsigned mode=1,unsigned role=0,unsigned path=0){return {0x1000,0x2000+role*16,0x3000,0x4000,0x5000,1,mode,2,3,12,8,path};}
static Owner owner(unsigned role=0){return {0x1000,0x2000+role*16,0x2b,10,2,30,role,7,0x119,100,200};}
static World world(){World w{};w.storage=w.current_storage=0x6000;w.metadata=w.current_metadata=0x7000;
 w.stage=Placement;w.field=5;w.result=w.owner=w.complete=1;w.epoch=w.stamp=2;w.frame=w.current_frame=200;
 w.scene=w.current_scene=300;w.coverage=w.required=3;w.room=0x119;w.metadata_bytes=1376;w.metadata_version=2;return w;}
static void bounds(State& s){float lo[3]={1,2,3},hi[3]={4,5,6},v[12]{},p[7]{},V[6]{};s.bounds(lo,hi,v,p,V);}
static void query(State& s,unsigned mode=1,unsigned role=0,unsigned path=0,bool hidden=true,bool commit=true){
 auto q=source(mode,role,path);q.workspace=s.last;s.begin(q);s.identify(1,owner(role));bounds(s);s.world(world());
 if(hidden)s.potential();s.revalidate(1,owner(role));s.end(hidden&&mode==2);
 if(hidden&&mode==2&&commit)s.skip(path,q.lod,q.meshlet,q.nv,q.nt);
}
static void close(State& s){for(unsigned i=s.binds+1;i<=600;++i)s.window(2,i,s.mode,i);s.window(3,601,0,600);}
int main(){
 static_assert(unsigned(actor_visibility23::Window::Start)==1&&unsigned(actor_visibility23::Window::Continue)==2&&unsigned(actor_visibility23::Window::Complete)==3&&unsigned(actor_visibility23::Window::Cancel)==4&&unsigned(actor_visibility23::Window::Invalid)==5,"actual event ABI");
 // Real counters distinguish mode1 potential from branch-committed mode2 work.
 {State s;s.window(1,1,1,1);query(s);close(s);assert(s.qualified()&&s.parts[0].potential==1&&s.parts[0].would==12&&s.parts[0].positions==0&&!s.samples[1].query.committed);}
 {State s;s.window(1,1,2,1);query(s,2,0,0);query(s,2,1,1);close(s);assert(s.qualified()&&s.parts[0].skip==1&&s.parts[1].skip==1&&s.parts[0].positions==12&&s.parts[1].triangles==8&&s.samples[1].query.committed&&s.samples[3].query.committed);}
 {State s;s.window(1,1,1,1);query(s,1,0,0,false);close(s);assert(s.qualified()&&s.parts[0].bound==1&&!s.parts[0].potential);}
 // An unrelated owner may really skip, but never becomes a boss count.
 {State s;s.window(1,1,2,1);s.begin(source(2));s.identify(0,{});s.end(true);s.skip(0,2,3,12,8);query(s,2);close(s);assert(s.qualified()&&s.unattributed==1&&s.parts[0].skip==1);}
 // Missing, duplicate or mismatched actual caller commits fail closed.
 for(unsigned failure=0;failure<4;++failure){State s;s.window(1,1,2,1);query(s,2,0,0,true,false);
  if(failure==1)s.skip(1,2,3,12,8);if(failure==2){s.skip(0,2,3,12,8);s.skip(0,2,3,12,8);}if(failure==3)s.begin(source(2));close(s);assert(!s.qualified()&&(s.failures&Pair));assert(s.parts[0].skip<=1);}
 // Real lifetime and role/part identities are checked within and across calls.
 for(unsigned failure=0;failure<8;++failure){State s;s.window(1,1,1,1);query(s);s.begin(source());auto o=owner();
  if(failure==0)++o.serial;if(failure==1)++o.epoch;if(failure==2)++o.life;if(failure==3)o.info+=1;
  if(failure==4)o.role=2;if(failure==5)o.flags=0;if(failure==6)o.room=0x101;
  s.identify(1,o);if(failure==7){++o.serial;s.revalidate(1,o);}s.end(false);close(s);assert(!s.qualified()&&(s.failures&Identity));}
 // No guessed field or receipt can qualify a potential/actual-skip witness.
 for(unsigned failure=0;failure<14;++failure){State s;s.window(1,1,2,1);s.begin(source(2));s.identify(1,owner());bounds(s);auto w=world();
  if(failure==0)w.stage=Receipt;if(failure==1)w.field=0;if(failure==2)w.result=0;if(failure==3)w.active=1;if(failure==4)w.complete=0;
  if(failure==5)w.coverage=0;if(failure==6)++w.current_scene;if(failure==7)++w.current_frame;if(failure==8)++w.current_storage;
  if(failure==9)++w.stamp;if(failure==10)++w.current_fpscr;if(failure==11)++w.current_metadata;if(failure==12)--w.metadata_bytes;if(failure==13)w.metadata_version=0;
  s.world(w);s.potential();s.end(true);s.skip(0,2,3,12,8);close(s);assert(!s.qualified()&&(s.failures&Context));}
 // Bounded arrays preserve the first draw and potential per role, not a log per query.
 {State s;s.window(1,1,2,1);for(unsigned role=0;role<2;++role)for(unsigned i=0;i<40;++i)query(s,2,role,role,i%2);close(s);
  assert(s.qualified());unsigned n=0;for(const auto& sample:s.samples)n+=sample.present;assert(n==4&&s.parts[0].query==40&&s.parts[1].query==40);}
 // Abort/partial, unknown identity, serial wrap, mode/context drift and overflow are unqualified.
 {State s;s.window(1,1,1,1);query(s);s.window(4,2,0,1);assert(s.sealed&&!s.qualified()&&(s.failures&Incomplete));}
 {State s;s.window(1,1,1,1);query(s);s.window(3,2,0,1);assert(!s.qualified());}
 {State s;s.window(1,1,1,1);s.begin(source());s.identify(-1,{});s.end(false);close(s);assert(!s.qualified());}
 {State s;s.window(1,~0U,1,1);query(s);s.window(2,0,1,2);close(s);assert(!s.qualified()&&(s.failures&Sequence));}
 {State s;s.window(1,1,1,1);auto q=source();q.workspace=2;s.begin(q);s.identify(1,owner());s.end(false);close(s);assert(!s.qualified()&&(s.failures&Context));}
 {State s;s.window(1,1,2,1);s.parts[0].positions=~0U;query(s,2);close(s);assert(!s.qualified()&&(s.failures&Overflow)&&s.parts[0].positions==~0U);}
 {State s;s.window(1,1,1,1);s.tokens=~0U;query(s);close(s);assert(!s.qualified()&&(s.failures&Overflow));}
 {State s;s.window(1,1,1,1);query(s);close(s);s.window(1,602,1,1);assert(!s.qualified()&&(s.failures&Sequence));}
 // Mode0/outside-window work and duplicate completion cannot manufacture actual cuts.
 {State s;query(s,2);assert(!s.active&&!s.owner_seen&&!s.parts[0].skip);s.window(1,1,0,1);s.begin(source(0));s.end(false);close(s);assert(!s.qualified()&&!s.parts[0].skip);}
 {State s;s.window(1,1,2,1);query(s,2);close(s);const auto count=s.parts[0].skip;s.skip(0,2,3,12,8);s.window(3,602,0,600);assert(s.qualified()&&s.parts[0].skip==count);}
 return 0;
}
