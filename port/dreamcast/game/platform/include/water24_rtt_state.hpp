#pragma once
#include "water24_material.hpp"
namespace re4dc { namespace water24 {
struct Serial {
    unsigned value=0;bool exhausted=false;
    unsigned next(){if(exhausted || value==~0U){exhausted=true;return 0;}return ++value;}
};
inline bool same_context(const CaptureContext& a,const CaptureContext& b){
    return a.room==kRoom && a.room==b.room && a.geometry.owner &&
           a.geometry.owner==b.geometry.owner && a.geometry.proof && a.geometry.proof==b.geometry.proof &&
           a.geometry.generation && a.geometry.generation==b.geometry.generation &&
           a.geometry.room_generation && a.geometry.room_generation==b.geometry.room_generation &&
           a.geometry.bytes==kMeshBytes && a.geometry.bytes==b.geometry.bytes &&
           a.geometry.mesh_crc==kMeshCrc && a.geometry.mesh_crc==b.geometry.mesh_crc &&
           a.geometry.policy_crc==kPolicyCrc && a.geometry.policy_crc==b.geometry.policy_crc &&
           a.geometry.ids_policy_crc==kIdsPolicyCrc && a.geometry.ids_policy_crc==b.geometry.ids_policy_crc &&
           a.slot<8 && a.slot==b.slot && a.source_target && a.source_target==b.source_target &&
           a.contributor_receipt && a.contributor_receipt==b.contributor_receipt &&
           a.receipt_serial && a.receipt_serial==b.receipt_serial;
}
struct RttStamp {
    unsigned epoch=0,capture_frame=0,contributors=0;
    CaptureContext capture{},rendered_context{};
    bool sources_ok=false,closed=false;
    Target rendered{};
    void invalidate(){epoch=0;sources_ok=false;closed=false;rendered=Target{};rendered_context=CaptureContext{};}
    void begin(const CaptureContext& c,unsigned frame){
        capture=c;capture_frame=frame;contributors=0;closed=false;
        sources_ok=same_context(c,c);
    }
    void contributor(bool accepted){sources_ok=sources_ok && accepted;++contributors;}
    void close(const CaptureContext& current){
        sources_ok=sources_ok && same_context(capture,current);closed=true;
    }
    bool publish(const CaptureContext& current,unsigned frame,unsigned slot,
                 const void* owner,const void* texture,unsigned w,unsigned h,unsigned fence,bool fence_ok){
        // Clear first: a failed render never lends a previous image's receipt.
        rendered=Target{};rendered_context=CaptureContext{};
        if(!epoch || !owner || !texture || slot>=8 || w!=kWidth || h!=kHeight ||
           !closed || !sources_ok || !contributors || slot!=capture.slot || capture_frame+1U!=frame || !fence || !fence_ok ||
           !same_context(capture,current))return false;
        rendered_context=capture;rendered.owner=owner;rendered.source_target=capture.source_target;rendered.texture=texture;rendered.contributor_receipt=capture.contributor_receipt;
        rendered.room=capture.room;rendered.room_generation=capture.geometry.room_generation;rendered.geometry_generation=capture.geometry.generation;
        rendered.generation=epoch;rendered.slot=slot;rendered.capture_frame=capture_frame;
        rendered.render_frame=frame;rendered.fence=fence;rendered.receipt_serial=capture.receipt_serial;
        rendered.width=w;rendered.height=h;rendered.bytes=kTargetBytes;
        rendered.format=Format::Argb4444Linear;rendered.timing=Timing::PreviousNativeFrame;
        return true;
    }
    bool current(const Target& t,const CaptureContext& c,unsigned frame,const void* owner,
                 const void* texture,unsigned w,unsigned h,bool fence_ok)const{
        return epoch && rendered.generation==epoch && t.generation==epoch &&
            t.source_target && t.source_target==c.source_target && t.source_target==rendered.source_target &&
            t.owner==owner && t.owner==rendered.owner && t.texture==texture && t.texture==rendered.texture &&
            t.room==kRoom && t.room==c.room && t.room_generation==c.geometry.room_generation && t.room_generation==rendered.room_generation && t.geometry_generation==c.geometry.generation &&
            t.geometry_generation==rendered.geometry_generation && t.slot==rendered.slot &&
            t.capture_frame==rendered.capture_frame && t.capture_frame+1U==frame &&
            t.render_frame==frame && t.render_frame==rendered.render_frame &&
            t.width==w && t.height==h && w==kWidth && h==kHeight && t.bytes==kTargetBytes &&
            t.format==Format::Argb4444Linear && t.timing==Timing::PreviousNativeFrame &&
            t.fence && t.fence==rendered.fence && fence_ok &&
            t.contributor_receipt && t.contributor_receipt==c.contributor_receipt &&
            t.contributor_receipt==rendered.contributor_receipt && t.receipt_serial &&
            t.receipt_serial==c.receipt_serial && t.receipt_serial==rendered.receipt_serial &&
            same_context(rendered_context,c);
    }
};
} }
