#include "gc_asset_actor_original.h"
#include <cassert>
#include <cstring>
using namespace re4dc_gcasset;
void put(unsigned char* p,unsigned v){std::memcpy(p,&v,4);}
int main(){
 alignas(32) unsigned char file[1024]{};auto* d=file+64;
 put(d,80);put(d+12,160);put(d+16,192);put(d+20,208);put(d+24,(1U<<16)|(1U<<8)|2);
 put(d+28,256);put(d+32,0x80000000U);put(d+40,0);put(d+44,400);put(d+48,96);put(d+52,128);
 put(d+56,(3U<<16)|3);put(d+60,0x20030818U);put(d+256+24,32);
 auto* stream=d+288;stream[0]=0x90;stream[2]=3;
 for(unsigned i=0;i<3;++i){auto* v=stream+3+i*8;v[1]=i;v[3]=i;v[5]=i;v[7]=i;}
 put(d+400,1);put(d+404,8);put(d+408,1);d[412]=1;
 OriginalModelProof proof;assert(original_parse(proof,17,file,sizeof file,d));
 assert(proof.uv_bytes==12 && proof.color_bytes==12 && proof.weights && proof.shape_bytes==20);
 OriginalModelInput in;in.data=d;in.head=d+80;in.colors=d+160;in.uv=d+192;in.weights=d+208;in.parts=d+256;
 in.positions=d+96;in.normals=d+128;in.part=d+256;in.stream=stream;in.stream_bytes=32;
 in.flags=0x80000000U;in.counts=(3U<<16)|3;in.joints=(1U<<16)|(1U<<8)|2;in.shape=400;
 in.uses_colors=in.uses_weights=in.uses_shape=true;assert(original_select(proof,in));
 // Every independently consumed constituent rejects external replacement,
 // including another in-allocation address that is not its captured section.
 const void** fields[]={&in.head,&in.colors,&in.uv,&in.weights,&in.parts,&in.positions,&in.normals,&in.part,&in.stream};
 for(auto field:fields){const void* saved=*field;*field=file+900;assert(!original_select(proof,in));*field=saved;}
 ++in.stream_bytes;assert(!original_select(proof,in));--in.stream_bytes;
 ++in.counts;assert(!original_select(proof,in));--in.counts;
 ++in.shape;assert(!original_select(proof,in));--in.shape;
 // The exact original GX stream was validated before any FE representation
 // write. A derived FE byte layout remains the same original constituent;
 // permission to perform that mutation is supplied by the owner wrapper.
 stream[0]=0xfe;assert(original_select(proof,in));
 OriginalModelProof bad;assert(!original_parse(bad,18,file,sizeof file,d));stream[0]=0x90;
 assert(!original_parse(bad,0,file,sizeof file,d));assert(!original_parse(bad,18,file,64,d));
 put(d+16,960);assert(!original_parse(bad,18,file,sizeof file,d));put(d+16,192);
 stream[10]=255;assert(!original_parse(bad,18,file,sizeof file,d));stream[10]=0;
 put(d+256+24,1024);assert(!original_parse(bad,18,file,sizeof file,d));put(d+256+24,32);
 put(d+12,960);assert(original_parse(bad,18,file,sizeof file,d));assert(!bad.color_bytes);assert(!original_select(bad,in));put(d+12,160);
 put(d+20,960);assert(original_parse(bad,18,file,sizeof file,d));assert(!bad.weights);assert(!original_select(bad,in));put(d+20,208);
 put(d+408,0xffffffffU);assert(original_parse(bad,18,file,sizeof file,d));assert(!bad.shape_bytes);assert(!original_select(bad,in));put(d+408,1);
 put(d+404,0xfffffff0U);assert(original_parse(bad,18,file,sizeof file,d));assert(!bad.shape_bytes);put(d+404,8);
 d[412]=3;assert(original_parse(bad,18,file,sizeof file,d));assert(!bad.shape_bytes);d[412]=1;
 assert(original_parse(proof,19,file,sizeof file,d));assert(original_select(proof,in));
 proof.serial=0;assert(!original_select(proof,in));
}
