#pragma once
#ifndef RE4DC_PLAN_OWNER_SCOPED
#define RE4DC_PLAN_OWNER_SCOPED 0
#endif
#if RE4DC_PLAN_OWNER_SCOPED
// Registry publication, not pointer equality, identifies source backing. An
// unknown/ambiguous range has no immutable-owner authority (slot == ~0U).
// Wrap uses the existing global reset fence, which revokes every plan and raw
// prepared position/normal/static-light consumer before tokens can repeat.
struct Re4dcDrawOwnerStamp {
    unsigned slot=~0U, incarnation=0;
    bool valid() const { return slot!=~0U && incarnation; }
    bool operator==(const Re4dcDrawOwnerStamp& b) const {
        return slot==b.slot && incarnation==b.incarnation;
    }
};
extern "C" Re4dcDrawOwnerStamp re4dc_model_draw_owner_stamp(const void*,unsigned);
inline Re4dcDrawOwnerStamp re4dc_model_draw_array_owner(const void* p,unsigned count,unsigned stride){
    if(!count || !stride || count>~0U/stride)return {};
    return re4dc_model_draw_owner_stamp(p,count*stride);
}
#endif
