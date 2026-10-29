// ACTOR_SKIN_OWNER_POOL: included in native_actor_fast.cpp's namespace after
// SkinEntry. Ordinary skin entries are never replaced by an owned transaction.
// Records live in this bounded table; the public leases remain copied values.
struct OwnedEntry { SkinEntry skin{}; Re4dcActorSource source{}; unsigned serial=0; };
constexpr unsigned kOwnedSkins=re4dc_actor::WorkspaceReservations::MaxOwners*kRe4dcActorRoles;
static_assert(sizeof(void*)!=4 || sizeof(OwnedEntry)==48,"SH-4 owned skin entry");
OwnedEntry owned_skins[kOwnedSkins];
unsigned owned_skin_high;
unsigned owned_skin_serial;
bool owned_submission;
void owned_skin_invalidate_frames();

bool owned_skin_source_valid(const OwnedEntry& e) {
    return e.skin.info && !e.skin.positions && e.skin.palette && e.skin.entries && e.skin.entries<=256 &&
        e.source.positions && e.source.normals && e.source.position_count && e.source.normal_count &&
        e.source.palette_entries==e.skin.entries;
}
SkinEntry* find_owned_skin(const void* info) {
    if(!info)return nullptr;
    for(unsigned i=0;i<owned_skin_high;++i)
        if(owned_skins[i].serial && owned_skins[i].skin.info==info)return &owned_skins[i].skin;
    return nullptr;
}
void owned_skin_clear() {
    // Retirement never reads borrowed palettes, source arrays or old leases.
    for(unsigned i=0;i<owned_skin_high;++i)owned_skins[i]={};
    owned_skin_high=0;
}
extern "C" int re4dc_actor_skin_acquire(unsigned source_frame,const Re4dcActorSkinBinding* in,unsigned n,Re4dcActorSkinLease* out) {
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    if(skin_admission_pending.serial)return 0;
#endif
    if(!out || out->serial || out->count || !in || !n || n>kRe4dcActorRoles ||
       source_frame!=skin_frame || owned_skin_serial==UINT32_MAX)return 0;
    unsigned index[kRe4dcActorRoles],high=owned_skin_high;
    for(unsigned k=0;k<n;++k){
        const auto& b=in[k];
        if(!b.info || !b.palette || !b.entries || b.entries>256 || !b.source.positions || !b.source.normals ||
           b.source.palette_entries!=b.entries || !b.source.position_count || !b.source.normal_count)return 0;
        for(unsigned j=0;j<k;++j)if(in[j].info==b.info)return 0;
        if(find_owned_skin(b.info))return 0;
        unsigned at=kOwnedSkins;
        for(unsigned i=0;i<high;++i){
            bool chosen=false;for(unsigned j=0;j<k;++j)chosen|=index[j]==i;
            if(!chosen && !owned_skins[i].serial){at=i;break;}
        }
        if(at==kOwnedSkins){if(high==kOwnedSkins)return 0;at=high++;}
        index[k]=at;
    }
    // No mutation, allocation or callback precedes complete batch admission.
    const unsigned serial=++owned_skin_serial;
    for(unsigned k=0;k<n;++k){
        const unsigned i=index[k];const auto& b=in[k];
        owned_skins[i]={{b.info,nullptr,b.palette,b.entries,0},b.source,serial};
        // With an isolated table these value fields certify the published
        // entry; there is no ordinary slot to back up or later restore.
        out->old[k]={i,b.info,nullptr,b.palette,b.entries,0};
    }
    owned_skin_high=high;out->frame=source_frame;out->count=n;out->serial=serial;
    owned_skin_invalidate_frames();return 1;
}
extern "C" int re4dc_actor_skin_validate(const Re4dcActorSkinLease* lease) {
    if(!lease || !lease->serial || !lease->count || lease->count>kRe4dcActorRoles || lease->frame!=skin_frame)return 0;
    for(unsigned k=0;k<lease->count;++k){
        const auto& expected=lease->old[k];const unsigned i=expected.index;
        if(i>=owned_skin_high)return 0;
        for(unsigned j=0;j<k;++j)if(lease->old[j].index==i)return 0;
        const auto& e=owned_skins[i];const auto& s=e.skin;
        if(e.serial!=lease->serial || !owned_skin_source_valid(e) || s.materialized || expected.positions || expected.materialized ||
           s.info!=expected.info || s.palette!=expected.palette || s.entries!=expected.entries)return 0;
    }
    // A truncated or duplicated copied handle cannot acknowledge a partial
    // release while unmentioned entries still borrow the owner's palette.
    unsigned found=0;
    for(unsigned i=0;i<owned_skin_high;++i)found+=owned_skins[i].serial==lease->serial;
    return found==lease->count;
}
extern "C" int re4dc_actor_skin_release(Re4dcActorSkinLease* lease) {
    if(!lease)return 0;
    if(!lease->serial){*lease={};return 1;}
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    if(skin_admission_pending.serial)return 0;
#endif
    const unsigned serial=lease->serial;
    const int okay=re4dc_actor_skin_validate(lease);
    if(okay){lease->serial=0;lease->count=0;}else *lease={};
    // Success and hostile/stale-handle failure both revoke every surviving
    // entry of THIS serial before a caller can retire its palette. Other
    // owners and all ordinary registrations are untouched.
    for(unsigned i=0;i<owned_skin_high;++i)if(owned_skins[i].serial==serial)owned_skins[i]={};
    while(owned_skin_high && !owned_skins[owned_skin_high-1].serial)--owned_skin_high;
    owned_skin_invalidate_frames();return okay;
}
extern "C" int re4dc_actor_owned_source(const void* info,unsigned source_frame,Re4dcActorSource* out) {
    if(!info || !out || skin_frame!=source_frame)return 0;
    for(unsigned i=0;i<owned_skin_high;++i){
        const auto& e=owned_skins[i];
        if(e.serial && e.skin.info==info){
            if(e.skin.materialized || !owned_skin_source_valid(e))return 0;
            *out=e.source;return 1;
        }
    }
    return 0;
}
bool owned_skin_from_lease(const Re4dcActorSkinLease* lease,const void* info,const SkinEntry*& skin,Re4dcActorSource& source) {
    if(!re4dc_actor_skin_validate(lease))return false;
    for(unsigned k=0;k<lease->count;++k){
        const auto& e=owned_skins[lease->old[k].index];
        if(e.skin.info==info){skin=&e.skin;source=e.source;return true;}
    }
    return false;
}
