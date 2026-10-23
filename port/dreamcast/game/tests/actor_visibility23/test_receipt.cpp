#include "actor_visibility23_world.h"
#include <cassert>
using actor_visibility23::WorldReceipt;
static float view[12]={1,0,0,0,0,1,0,0,0,0,1,0};
static float P[7]={0,1,0,1,0,-.001,-1},V[6]={0,0,640,480,0,1};
static int owner;
static void emit(WorldReceipt& w,unsigned field,unsigned fault=0){
 for(const auto& need:actor_visibility23::r119::needs){
  if(need.field!=field)continue;
  unsigned char strips[256]{},codes[3]{};
  strips[need.strip]=3;strips[need.strip+1]=0;strips[need.strip+2]=1;strips[need.strip+3]=2;
  if(fault==1)codes[0]=1; // depth crossing: different clip path
  if(fault==2)codes[0]=codes[1]=codes[2]=4; // screen-all cull
  if(fault==3)strips[need.strip+2]=3; // bad source index
  w.emit(field,need.part+(fault==4),need.meshlet,strips,need.strip+4,codes,3,
      fault==5?2:255,3,60,50,25000,42);
 }
}
int main(){
 WorldReceipt w;w.begin(1,view,P,V);emit(w,5);w.end(true);
 assert(!w.ready(1,&owner,view,P,V,0,50,25000,42));
 w.bind(&owner,true);w.begin(2,view,P,V);emit(w,5);
 assert(!w.ready(2,&owner,view,P,V,0,50,25000,42)); // in flight
 w.end(true);assert(w.ready(2,&owner,view,P,V,0,50,25000,42));
 assert(!w.ready(3,&owner,view,P,V,0,50,25000,42)); // prior frame
 assert(!w.ready(2,nullptr,view,P,V,0,50,25000,42));
 assert(!w.ready(2,&owner,view,P,V,1,50,25000,42)); // unrelated cottage
 float changed[12];__builtin_memcpy(changed,view,sizeof(view));changed[3]=1;
 assert(!w.ready(2,&owner,changed,P,V,0,50,25000,42));
 assert(!w.ready(2,&owner,view,P,V,0,51,25000,42));
 assert(!w.ready(2,&owner,view,P,V,0,50,25001,42));
 for(unsigned fault=1;fault<=5;fault++){
  w.begin(4+fault,view,P,V);emit(w,5,fault);w.end(true);
  assert(!w.ready(4+fault,&owner,view,P,V,0,50,25000,42));
 }
 w.begin(20,view,P,V);emit(w,5);w.end(false);
 assert(!w.ready(20,&owner,view,P,V,0,50,25000,42)); // later bind/pass abort
 w.begin(21,view,P,V);emit(w,7);w.end(true);
 assert(w.ready(21,&owner,view,P,V,1,50,25000,42));
 assert(!w.ready(21,&owner,view,P,V,1,50,25000,0)); // closed scene
 assert(!w.ready(21,&owner,view,P,V,1,50,25000,43)); // movie discard/reopen
 w.begin(22,view,P,V);emit(w,5);w.begin(22,view,P,V);w.end(true);
 assert(!w.ready(22,&owner,view,P,V,0,50,25000,42)); // nested pass revokes
 w.close();assert(!w.ready(21,&owner,view,P,V,1,50,25000,42));
}
