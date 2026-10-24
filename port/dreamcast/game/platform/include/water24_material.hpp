#pragma once
// Default-off r100 PS2 TexBlend target replacement contract. No allocation,
// capture, image conversion, submission or provenance authority lives here.
#include <cstdint>
namespace re4dc { namespace water24 {
constexpr unsigned kRoom=0x100,kWidth=64,kHeight=64,kTargetBytes=8192;
constexpr unsigned kMeshBytes=1537920,kMeshCrc=0xfb35ea9cU;
constexpr unsigned kPolicyCrc=0x25d5daafU,kIdsPolicyCrc=0x14118acdU;
enum class Format : unsigned { None=0, Argb4444Linear=1 };
enum class Timing : unsigned { None=0, PreviousNativeFrame=1 };
enum class Why : unsigned {
    Ready=0, Room, Geometry, SourceObject, Owner, Generation, Target,
    Dimensions, Format, Timing, Fence, SourceReceipt, Retired
};
struct Geometry {
    const void* owner=nullptr;
    const void* proof=nullptr; // actual immutable R4IM/R4PW proof, never the target's proof
    unsigned generation=0,room_generation=0,bytes=0,mesh_crc=0,policy_crc=0,ids_policy_crc=0;
};
struct Request {
    Geometry geometry{};
    const void* source_object=nullptr;
    unsigned room=0,native_frame=0,source_serial=0,source_id=~0U;
    unsigned placement=~0U,mesh=~0U,part=~0U;
};
struct Target {
    const void* owner=nullptr;
    const void* texture=nullptr;
    const void* contributor_receipt=nullptr;
    const void* source_target=nullptr;
    unsigned room=0,room_generation=0,geometry_generation=0,generation=0,slot=~0U;
    unsigned capture_frame=0,render_frame=0,fence=0;
    unsigned receipt_serial=0,width=0,height=0,bytes=0;
    Format format=Format::None;
    Timing timing=Timing::None;
};
// This snapshot comes independently from the one live PVR RTT owner. Copying
// arbitrary caller fields into it does not establish source provenance/fences.
struct CaptureContext {
    Geometry geometry{};
    const void* contributor_receipt=nullptr;
    const void* source_target=nullptr;
    unsigned room=0,receipt_serial=0,slot=~0U;
};
struct Authority {
    Target live{};
    bool room_live=false,geometry_live=false,object_live=false;
    bool contributors_ps2=false,fence_complete=false,immutable=false;
};
struct Material {
    Request request{};
    Target target{};
    // Actual PS2 TexBlend wildcard247 replaces the TEXHeader. Preserve the
    // existing authored normalized UV; no GC screen/refraction UV is invented.
    float u_scale=1.f,v_scale=1.f;
    unsigned source_alpha=240;
};
inline bool candidate(unsigned room,unsigned placement,unsigned mesh,unsigned part){
    return room==kRoom && placement<2 && mesh==placement && part==placement;
}
inline Why request_valid(const Request& r){
    if(r.room!=kRoom)return Why::Room;
    const Geometry& g=r.geometry;
    if(!g.owner || !g.proof || !g.generation || !g.room_generation || g.bytes!=kMeshBytes || g.mesh_crc!=kMeshCrc ||
       g.policy_crc!=kPolicyCrc || g.ids_policy_crc!=kIdsPolicyCrc)return Why::Geometry;
    if(!r.source_object || !r.source_serial || r.source_id>1 ||
       !candidate(r.room,r.placement,r.mesh,r.part) || r.source_id!=r.placement)return Why::SourceObject;
    return Why::Ready;
}
inline Why validate(const Material& m,const Authority& a){
    const Why request=request_valid(m.request);if(request!=Why::Ready)return request;
    const Target& t=m.target;const Target& c=a.live;
    if(!a.room_live || !a.geometry_live || !a.object_live)return Why::Retired;
    if(t.room!=m.request.room || c.room!=t.room)return Why::Room;
    if(!t.owner || !t.texture || !t.source_target || t.source_target!=c.source_target || t.owner!=c.owner || t.texture!=c.texture)return Why::Owner;
    if(!t.generation || t.room_generation!=m.request.geometry.room_generation || t.room_generation!=c.room_generation || t.generation!=c.generation || t.geometry_generation!=m.request.geometry.generation ||
       t.geometry_generation!=c.geometry_generation)return Why::Generation;
    if(t.slot>=8 || t.slot!=c.slot)return Why::Target;
    if(t.width!=kWidth || t.height!=kHeight || t.bytes!=kTargetBytes ||
       t.width!=c.width || t.height!=c.height || t.bytes!=c.bytes)return Why::Dimensions;
    if(t.format!=Format::Argb4444Linear || t.format!=c.format)return Why::Format;
    // The existing PVR owner renders prior-frame effect packets before this
    // frame's scene. This explicit one-frame delay is not same-frame PS2 timing.
    if(t.timing!=Timing::PreviousNativeFrame || t.timing!=c.timing ||
       t.capture_frame+1U!=m.request.native_frame || t.render_frame!=m.request.native_frame ||
       t.capture_frame!=c.capture_frame || t.render_frame!=c.render_frame)return Why::Timing;
    if(!t.fence || t.fence!=c.fence || !a.fence_complete || !a.immutable)return Why::Fence;
    if(!t.contributor_receipt || !t.receipt_serial || t.contributor_receipt!=c.contributor_receipt ||
       t.receipt_serial!=c.receipt_serial || !a.contributors_ps2)return Why::SourceReceipt;
    if(m.u_scale!=1.f || m.v_scale!=1.f || m.source_alpha!=240)return Why::Target;
    return Why::Ready;
}
} }
// Root native_ui/PVR owner supplies these functions. acquire() may mark an
// existing source target wanted but must not allocate a duplicate owner. enter
// and leave bracket one synchronous authored-surface draw outside held SQ.
extern "C" {
int re4dc_water24_acquire(const re4dc::water24::Request*,re4dc::water24::Material*);
int re4dc_water24_enter(const re4dc::water24::Material*);
void re4dc_water24_leave(const re4dc::water24::Material*);
const re4dc::water24::Material* re4dc_water24_current();
int re4dc_water24_current_valid(const re4dc::water24::Material*);
// Root/native_ui authority: current selected PS2 geometry and an independently
// verified contributor-plan receipt, plus accepted resolved texture membership.
int re4dc_water24_capture_context(unsigned slot,re4dc::water24::CaptureContext*);
int re4dc_water24_geometry(re4dc::water24::Geometry*);
int re4dc_water24_source_current(const re4dc::water24::Request*);
unsigned re4dc_water24_room_generation();
int re4dc_water24_capture_contributor(const void* resolved_entry,const re4dc::water24::CaptureContext*);
int re4dc_water24_capture_fence_ok();
// Implemented by the existing PVR RTT owner; does not allocate or alter want.
int re4dc_water24_rtt_target(unsigned slot,const re4dc::water24::Request*,re4dc::water24::Target*);
int re4dc_water24_rtt_current(const re4dc::water24::Target*);
}
