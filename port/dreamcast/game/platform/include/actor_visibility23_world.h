#pragma once
#include <cstdint>
#include <cstring>
#include <actor_visibility23_r119_certificate.h>
namespace actor_visibility23 {
// Private programme-only receipt; all methods are synchronous and single-owner.
// Native frame identity is the actual PVR owner frame, not the source tick.
struct WorldReceipt {
 bool owner=false,active=false,complete=false;
 const void* storage=nullptr;const void* metadata=nullptr;unsigned epoch=0,stamp=0,frame=0,scene=0;
 float words[25]{},near=0,far[2]{};unsigned coverage[2]{};
 void close(){owner=active=complete=false;storage=nullptr;if(epoch!=~0U)++epoch;}
 void bind(const void* p,bool valid){close();storage=p;owner=valid&&epoch!=~0U;}
 void begin(unsigned f,const float* view,const float* P,const float* V){
  if(active){active=complete=false;if(epoch!=~0U)++epoch;return;} // nested pass refuses both receipts
  active=owner;complete=false;frame=f;stamp=epoch;coverage[0]=coverage[1]=0;
  far[0]=far[1]=1.0e30f;near=0;scene=0;
  std::memcpy(words,view,48);std::memcpy(words+12,P,28);std::memcpy(words+19,V,24);
 }
 void end(bool success){complete=active&&success;active=false;}
 void emit(unsigned field,unsigned part,unsigned let,const unsigned char* strips,
           unsigned bytes,const unsigned char* codes,unsigned vertices,unsigned limit,
           unsigned depth_mask,unsigned screen_mask,float n,float f,unsigned current_scene){
  if(!active||stamp!=epoch||(field!=5&&field!=7)||!strips||!codes)return;
  if(!current_scene)return;
  if(scene&&scene!=current_scene){active=complete=false;return;}
  scene=current_scene;
  const unsigned k=field==5?0:1;
  for(const auto& need:r119::needs){
   if(need.field!=field||need.part!=part||need.meshlet!=let||need.strip>=bytes)continue;
   const unsigned count=strips[need.strip];
   if(count<3||count>limit||need.strip+1+count>bytes)continue;
   unsigned all=255,any=0;bool valid=true;
   for(unsigned i=0;i<count;i++){
    const unsigned index=strips[need.strip+1+i];
    if(index>=vertices){valid=false;break;}
    all&=codes[index];any|=codes[index];
   }
   // These are exactly the native fast-walk acceptance predicates. Other
   // strips may clip/cull; they cannot supply any certificate coverage bit.
   if(!valid||(any&depth_mask)||(all&screen_mask))continue;
   coverage[k]|=need.mask;near=n;if(f<far[k])far[k]=f;
  }
 }
 bool ready(unsigned f,const void* current,const float* view,const float* P,const float* V,
            unsigned k,float n,float requested_far,unsigned current_scene)const{
  return current_scene&&scene==current_scene&&k<2&&owner&&complete&&!active&&stamp==epoch&&f==frame&&current==storage&&
   coverage[k]==r119::full[k]&&n==near&&requested_far<=far[k]&&
   !std::memcmp(words,view,48)&&!std::memcmp(words+12,P,28)&&!std::memcmp(words+19,V,24);
 }
};
}
