#include "actor_visibility23.h"
extern "C" int host_groups(const void* pos,const void* records,unsigned epoch,unsigned vertices,unsigned count,unsigned stride,unsigned words,unsigned* groups){
 actor_visibility23::Key k{pos,pos,records,epoch,count,65535,0,(unsigned short)vertices,(unsigned char)stride,(unsigned char)words};
 return actor_visibility23::acquire(k,groups)!=nullptr;
}
extern "C" int host_bounds(const void* pos,const void* rec,unsigned nv,unsigned count,const float* palette,unsigned entries,float q,const float* mv,const float* view,const float* proj,const float* viewport,float* lo,float* hi){
 actor_visibility23::Key k{pos,pos,rec,1,count,65535,0,(unsigned short)nv,8,3};unsigned n=0;
 const auto* g=actor_visibility23::acquire(k,&n);return g&&actor_visibility23::camera_bounds(g,n,palette,entries,q,mv,view,proj,viewport,1,25000,lo,hi);
}
