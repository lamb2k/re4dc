#include "water24_rtt_state.hpp"
#include <cstdio>
using namespace re4dc::water24;
unsigned checks;
#define CHECK(x) do{++checks;if(!(x)){std::printf("failed line %u\n",__LINE__);return 1;}}while(0)
int main(){
 int geom=0,proof=0,obj=0,texture=0,owner=0,receipt=0;
 Request r{};r.room=kRoom;r.native_frame=11;r.source_object=&obj;r.source_serial=1;r.source_id=0;r.placement=r.mesh=r.part=0;
 r.geometry.owner=&geom;r.geometry.proof=&proof;r.geometry.generation=3;r.geometry.room_generation=7;
 r.geometry.bytes=kMeshBytes;r.geometry.mesh_crc=kMeshCrc;r.geometry.policy_crc=kPolicyCrc;r.geometry.ids_policy_crc=kIdsPolicyCrc;
 CaptureContext c{};c.room=kRoom;c.geometry=r.geometry;c.contributor_receipt=&receipt;c.receipt_serial=19;c.source_target=&obj;c.slot=0;
 Serial epochs{},fences{};RttStamp s{};s.epoch=epochs.next();s.begin(c,10);s.contributor(true);s.close(c);
 CHECK(s.publish(c,11,0,&owner,&texture,64,64,fences.next(),true));
 Material m{};m.request=r;m.target=s.rendered;Authority a{};a.live=m.target;a.room_live=a.geometry_live=a.object_live=true;a.contributors_ps2=a.fence_complete=a.immutable=true;
 CHECK(validate(m,a)==Why::Ready);CHECK(s.current(m.target,c,11,&owner,&texture,64,64,true));
 #define BAD(field,value,reason) {Material bad=m;bad.field=value;CHECK(validate(bad,a)==Why::reason);}
 BAD(request.room,0x107,Room);BAD(request.geometry.owner,nullptr,Geometry);BAD(request.geometry.proof,nullptr,Geometry);
 BAD(request.geometry.generation,0,Geometry);BAD(request.geometry.room_generation,0,Geometry);BAD(request.geometry.mesh_crc,1,Geometry);BAD(request.geometry.policy_crc,1,Geometry);BAD(request.geometry.ids_policy_crc,1,Geometry);
 BAD(request.source_object,nullptr,SourceObject);BAD(request.source_serial,0,SourceObject);BAD(request.source_id,1,SourceObject);BAD(request.part,3,SourceObject);
 BAD(target.owner,nullptr,Owner);BAD(target.texture,nullptr,Owner);BAD(target.source_target,nullptr,Owner);BAD(target.generation,4,Generation);BAD(target.room_generation,8,Generation);BAD(target.geometry_generation,4,Generation);
 BAD(target.slot,8,Target);BAD(target.width,32,Dimensions);BAD(target.height,128,Dimensions);BAD(target.bytes,16384,Dimensions);BAD(target.format,Format::None,Format);
 BAD(target.timing,Timing::None,Timing);BAD(target.capture_frame,9,Timing);BAD(target.render_frame,10,Timing);BAD(target.fence,0,Fence);BAD(target.fence,9,Fence);
 BAD(target.contributor_receipt,nullptr,SourceReceipt);BAD(target.receipt_serial,0,SourceReceipt);BAD(u_scale,2.f,Target);BAD(source_alpha,255,Target);
 {Authority bad=a;bad.fence_complete=false;CHECK(validate(m,bad)==Why::Fence);bad=a;bad.immutable=false;CHECK(validate(m,bad)==Why::Fence);bad=a;bad.contributors_ps2=false;CHECK(validate(m,bad)==Why::SourceReceipt);bad=a;bad.object_live=false;CHECK(validate(m,bad)==Why::Retired);}
 // Future capture of the SAME target must not overwrite its current rendered receipt.
 s.begin(c,11);s.contributor(true);s.close(c);CHECK(s.current(m.target,c,11,&owner,&texture,64,64,true));
 // A rewritten/retired target, source generation, room or proof cannot borrow it.
 CHECK(!s.current(m.target,c,12,&owner,&texture,64,64,true));CHECK(!s.current(m.target,c,11,&owner,&texture,64,64,false));
 {CaptureContext bad=c;bad.geometry.generation++;CHECK(!s.current(m.target,bad,11,&owner,&texture,64,64,true));bad=c;bad.geometry.proof=&texture;CHECK(!s.current(m.target,bad,11,&owner,&texture,64,64,true));bad=c;bad.geometry.room_generation++;CHECK(!s.current(m.target,bad,11,&owner,&texture,64,64,true));}
 s.invalidate();CHECK(!s.current(m.target,c,11,&owner,&texture,64,64,true));s.epoch=epochs.next();CHECK(s.epoch!=m.target.generation);
 s.begin(c,10);s.contributor(false);s.close(c);CHECK(!s.publish(c,11,0,&owner,&texture,64,64,fences.next(),true));CHECK(!s.rendered.texture);
 s.begin(c,10);s.contributor(true);CHECK(!s.publish(c,11,0,&owner,&texture,64,64,fences.next(),true));
 s.begin(c,10);s.contributor(true);s.close(c);CHECK(!s.publish(c,12,0,&owner,&texture,64,64,fences.next(),true));
 s.begin(c,10);s.contributor(true);s.close(c);CHECK(!s.publish(c,11,0,&owner,&texture,64,64,fences.next(),false));
 s.begin(c,10);s.close(c);CHECK(!s.publish(c,11,0,&owner,&texture,64,64,fences.next(),true));
 Serial wrap{};wrap.value=~0U-1U;CHECK(wrap.next()==~0U);CHECK(wrap.next()==0 && wrap.exhausted);CHECK(wrap.next()==0);
 // Defined u32 frame wrap permits exactly N-1, but epoch/fence serials never wrap.
 s.epoch=epochs.next();s.begin(c,~0U);s.contributor(true);s.close(c);CHECK(s.publish(c,0,0,&owner,&texture,64,64,fences.next(),true));
 std::printf("{\"controls\":%u,\"host_stamp_bytes\":%zu,\"host_material_bytes\":%zu}\n",checks,sizeof(RttStamp),sizeof(Material));
}
