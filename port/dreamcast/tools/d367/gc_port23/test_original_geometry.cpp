#include "gc_asset_actor_original.h"
#include <cassert>
#include <cstring>
#ifdef RE4DC_GC_ASSET_TEST
#include "gc_asset_members.h"
extern "C" void re4dc_log(const char*,...){}
#endif
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
 assert(original_color_bytes(stream,32,0x80000000U)==12);
 assert(!original_color_bytes(stream,32,0));
 // FE3 reader's constant/variable ci and all LOD prefix extents are bounded.
 alignas(32) unsigned char fe[128]{};fe[0]=0xfe;fe[1]=3;fe[2]=1;fe[4]=1;fe[8]=10;fe[10]=16;
 put(fe+32,3U|(3U<<8));for(unsigned i=0;i<3;++i)fe[40+i*8+6]=i;
 fe[64]=0;fe[65]=1;fe[66]=0x82;assert(original_color_bytes(fe,sizeof fe,0)==12);
 for(unsigned n=0;n<67;++n)assert(!original_color_bytes(fe,n,0));
 fe[3]=1;fe[12]=20;fe[84]=22;fe[86]=24;put(fe+88,2U|(3U<<8));fe[96]=0;fe[97]=1;fe[98]=0x81;
 assert(original_color_bytes(fe,sizeof fe,0)==12);
 fe[88]=4;assert(!original_color_bytes(fe,sizeof fe,0));fe[88]=2;
 fe[98]=0x82;assert(!original_color_bytes(fe,sizeof fe,0));fe[98]=0x81;
 fe[8]=9;assert(!original_color_bytes(fe,sizeof fe,0));fe[8]=10;
 fe[2]=0;fe[6]=2;assert(original_color_bytes(fe,sizeof fe,0)==12);
 fe[1]=4;assert(!original_color_bytes(fe,sizeof fe,0));
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
#ifdef RE4DC_GC_ASSET_TEST
 // Use the actual bounded archive/member implementation; no identity comes
 // from this parser alone. Capture happens once before relocation/FE writes.
 put(file,1);put(file+16,64);std::memcpy(file+20,"BIN",3);
 alignas(32) unsigned char metadata[32768]{};
 assert(member_original_storage_bytes()<=sizeof metadata);assert(member_original_storage(metadata,member_original_storage_bytes()));
 int owner;install(nullptr,0);begin(0x111,1,Required);ModelMember member;
 assert(member_adopt(&owner,file,sizeof file,true));assert(member_capture(d));assert(member_lookup(d,&member));
 const unsigned serial=member.serial;assert(member_original_source(serial,in));
 {MemberDerivationScope change(stream,32);assert(change.ticket==serial);assert(!member_original_source(serial,in));stream[0]=0xfe;change.complete();}
 assert(member_original_source(serial,in)); // same immutable source after a recognized complete representation write
 in.uv=file+900;assert(!member_original_source(serial,in));in.uv=d+192;
 {MemberDerivationScope failed(stream,32);assert(failed.ticket==serial);}
 assert(!member_original_source(serial,in));member_retire(&owner);stream[0]=0x90;
 assert(member_adopt(&owner,file,sizeof file,true));assert(member_capture(d));assert(member_lookup(d,&member));
 assert(member.serial!=serial && member_original_source(member.serial,in));assert(!member_original_source(serial,in));
 {MemberDerivationScope first(stream,32);MemberDerivationScope nested(stream,4);assert(!nested.ticket);first.complete();}
 assert(!member_original_source(member.serial,in));member_retire(&owner);
 for(unsigned k=0;k<150;++k){
  assert(member_adopt(&owner,file,sizeof file,true));assert(member_capture(d));assert(member_lookup(d,&member));
  assert(member_original_source(member.serial,in));member_retire(&owner);assert(!member_original_source(member.serial,in));
 }
 end(1);
#endif
}
