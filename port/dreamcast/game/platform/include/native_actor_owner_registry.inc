// Included in native_actor_fast.cpp's anonymous namespace after SkinEntry,
// skins, skin_count and skin_frame. Default-off ACTOR_TRANSACTION only.
struct OwnedSkin { Re4dcActorSource source{}; const void* info=nullptr; const float* palette=nullptr; unsigned entries=0,serial=0; };
OwnedSkin owned_skins[kSkins];
unsigned owned_skin_serial;
bool owned_submission;
void owned_skin_clear() {
    // This path is only retirement before the primitive owner frees storage.
    // Do not read any borrowed palette/record while revoking the registry.
    for(unsigned i=0;i<kSkins;++i)if(owned_skins[i].serial){
        if(skins[i].palette==owned_skins[i].palette)skins[i]={};
        owned_skins[i]={};
    }
}
void owned_skin_invalidate_frames(); // definition after the Frame cache

#if defined(RE4DC_MCHECK_LEONGC) && RE4DC_MCHECK_LEONGC && defined(RE4DC_ACTOR_SKIN_DIAG) && RE4DC_ACTOR_SKIN_DIAG
// cx-integrate: D51 (Codex 3b1798a7/8027fcd7) instruments the plain acquisition below; MCHECK_LEONGC has its own
// SKINACQ fail why=1..5 copy (same refusal codes). Use one or the other.
#error "ACTOR_SKIN_DIAG=1 and MCHECK_LEONGC=1 both instrument re4dc_actor_skin_acquire; build one"
#endif
#if defined(RE4DC_MCHECK_LEONGC) && RE4DC_MCHECK_LEONGC
static int skin_acquire_inner(unsigned& why_,unsigned source_frame,const Re4dcActorSkinBinding* in,unsigned n,Re4dcActorSkinLease* out) {
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    if(skin_admission_pending.serial){why_=6;return 0;}
#endif
    if(!out || out->serial || out->count || !in || !n || n>kRe4dcActorRoles || source_frame!=skin_frame || owned_skin_serial==UINT32_MAX){why_=1;return 0;}
    unsigned index[kRe4dcActorRoles],high=skin_count;
    for(unsigned k=0;k<n;++k){
        const auto& b=in[k];
        if(!b.info || !b.palette || !b.entries || b.entries>256 || !b.source.positions || !b.source.normals ||
           b.source.palette_entries!=b.entries || !b.source.position_count || !b.source.normal_count){why_=2;return 0;}
        for(unsigned j=0;j<k;++j)if(in[j].info==b.info){why_=3;return 0;}
        unsigned at=kSkins;
        for(unsigned i=0;i<skin_count;++i)if(skins[i].info==b.info && !skins[i].positions){at=i;break;}
        if(at==kSkins){
            for(unsigned i=0;i<high;++i){
                bool chosen=false;for(unsigned j=0;j<k;++j)chosen|=index[j]==i;
                if(!chosen && !skins[i].info && !owned_skins[i].serial){at=i;break;}
            }
            if(at==kSkins){if(high==kSkins){why_=4;return 0;}at=high++;}
        }
        if(owned_skins[at].serial){why_=5;return 0;}
        index[k]=at;
    }
    // No registry mutation occurred before every slot and source span qualified.
    const unsigned serial=++owned_skin_serial;
    for(unsigned k=0;k<n;++k){
        const unsigned i=index[k];const SkinEntry old=i<skin_count?skins[i]:SkinEntry{};
        out->old[k]={i,old.info,old.positions,old.palette,old.entries,old.materialized};
        skins[i]={in[k].info,nullptr,in[k].palette,in[k].entries,0};
        owned_skins[i]={in[k].source,in[k].info,in[k].palette,in[k].entries,serial};
    }
    skin_count=high;out->frame=source_frame;out->count=n;out->serial=serial;
    owned_skin_invalidate_frames();return 1;
}
extern "C" int re4dc_actor_skin_acquire(unsigned source_frame,const Re4dcActorSkinBinding* in,unsigned n,Re4dcActorSkinLease* out) {
    unsigned why=0;const unsigned frame_before=skin_frame,count_before=skin_count;
    const int rv=skin_acquire_inner(why,source_frame,in,n,out);
    static unsigned logged;
    if(!rv && logged<16){++logged;re4dc_log("SKINACQ fail why=%u frame=%u skin_frame=%u count=%u n=%u\n",why,source_frame,frame_before,count_before,n);}
    return rv;
}
#else
#if RE4DC_ACTOR_SKIN_DIAG
unsigned owned_skin_diag_reports;
void owned_skin_diag(unsigned why,unsigned source_frame,unsigned n,unsigned role,unsigned value,const Re4dcActorSkinBinding* in) {
    if(owned_skin_diag_reports++<32) {
        re4dc_log("SKINACQ why=%u source=%u registry=%u count=%u serial=%u roles=%u role=%u value=%u\n",
            why,source_frame,skin_frame,skin_count,owned_skin_serial,n,role,value);
        if(why==4) {
            unsigned unique=0,eager=0,materialized=0,owned=0;
            for(unsigned i=0;i<skin_count;++i) {
                bool earlier=false;
                for(unsigned j=0;j<i;++j)earlier|=skins[j].info==skins[i].info;
                unique+=!earlier;eager+=skins[i].positions!=nullptr;
                materialized+=skins[i].materialized!=0;owned+=owned_skins[i].serial!=0;
            }
            re4dc_log("SKINACQ_SLOTS unique=%u eager=%u materialized=%u owned=%u\n",unique,eager,materialized,owned);
            for(unsigned k=0;k<n;++k) {
                unsigned matches=0,lazy=0,mat=0,held=0;
                for(unsigned i=0;i<skin_count;++i)if(skins[i].info==in[k].info) {
                    ++matches;lazy+=!skins[i].positions;mat+=skins[i].materialized!=0;held+=owned_skins[i].serial!=0;
                }
                re4dc_log("SKINACQ_ROLE role=%u info=%p entries=%u matches=%u lazy=%u materialized=%u owned=%u\n",
                    k,in[k].info,in[k].entries,matches,lazy,mat,held);
            }
        }
    }
}
#define SKINACQ_REFUSE(why,role,value) do { owned_skin_diag(why,source_frame,n,role,value,in);return 0; } while(0)
#else
#define SKINACQ_REFUSE(why,role,value) return 0
#endif
extern "C" int re4dc_actor_skin_acquire(unsigned source_frame,const Re4dcActorSkinBinding* in,unsigned n,Re4dcActorSkinLease* out) {
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    if(skin_admission_pending.serial)return 0;
#endif
    if(!out || out->serial || out->count || !in || !n || n>kRe4dcActorRoles || source_frame!=skin_frame || owned_skin_serial==UINT32_MAX)SKINACQ_REFUSE(1,0,source_frame!=skin_frame);
    unsigned index[kRe4dcActorRoles],high=skin_count;
    for(unsigned k=0;k<n;++k){
        const auto& b=in[k];
        if(!b.info || !b.palette || !b.entries || b.entries>256 || !b.source.positions || !b.source.normals ||
           b.source.palette_entries!=b.entries || !b.source.position_count || !b.source.normal_count)SKINACQ_REFUSE(2,k,b.entries);
        for(unsigned j=0;j<k;++j)if(in[j].info==b.info)SKINACQ_REFUSE(3,k,j);
        unsigned at=kSkins;
        for(unsigned i=0;i<skin_count;++i)if(skins[i].info==b.info && !skins[i].positions){at=i;break;}
        if(at==kSkins){
            for(unsigned i=0;i<high;++i){
                bool chosen=false;for(unsigned j=0;j<k;++j)chosen|=index[j]==i;
                if(!chosen && !skins[i].info && !owned_skins[i].serial){at=i;break;}
            }
            if(at==kSkins){if(high==kSkins)SKINACQ_REFUSE(4,k,high);at=high++;}
        }
        if(owned_skins[at].serial)SKINACQ_REFUSE(5,k,at);
        index[k]=at;
    }
    // No registry mutation occurred before every slot and source span qualified.
    const unsigned serial=++owned_skin_serial;
    for(unsigned k=0;k<n;++k){
        const unsigned i=index[k];const SkinEntry old=i<skin_count?skins[i]:SkinEntry{};
        out->old[k]={i,old.info,old.positions,old.palette,old.entries,old.materialized};
        skins[i]={in[k].info,nullptr,in[k].palette,in[k].entries,0};
        owned_skins[i]={in[k].source,in[k].info,in[k].palette,in[k].entries,serial};
    }
    skin_count=high;out->frame=source_frame;out->count=n;out->serial=serial;
    owned_skin_invalidate_frames();return 1;
}
#undef SKINACQ_REFUSE
#endif
extern "C" int re4dc_actor_skin_validate(const Re4dcActorSkinLease* lease) {
    if(!lease || !lease->serial || !lease->count || lease->count>kRe4dcActorRoles || lease->frame!=skin_frame)return 0;
    for(unsigned k=0;k<lease->count;++k){
        const unsigned i=lease->old[k].index;
        if(i>=skin_count || owned_skins[i].serial!=lease->serial || !skins[i].info || skins[i].info!=owned_skins[i].info || skins[i].positions ||
           skins[i].materialized || skins[i].palette!=owned_skins[i].palette || skins[i].entries!=owned_skins[i].entries)return 0;
    }
    return 1;
}
extern "C" int re4dc_actor_skin_release(Re4dcActorSkinLease* lease) {
    if(!lease)return 0;
    if(!lease->serial){*lease={};return 1;}
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    if(skin_admission_pending.serial)return 0;
#endif
    if(!re4dc_actor_skin_validate(lease)){
        const unsigned serial=lease->serial;*lease={};
        // Failure still revokes every surviving entry of THIS owner before
        // callers may retire its palettes. Never restore old source records
        // over a newer registration. Frame caches can also borrow the palette.
        for(unsigned i=0;i<kSkins;++i)if(owned_skins[i].serial==serial){
            if(skins[i].palette==owned_skins[i].palette)skins[i]={};
            owned_skins[i]={};
        }
        owned_skin_invalidate_frames();return 0;
    }
    // Validate the complete batch before restoring any original source slot.
    const unsigned n=lease->count;lease->serial=0;lease->count=0;
    for(unsigned k=0;k<n;++k){
        const auto& old=lease->old[k];
        owned_skins[old.index]={};
        skins[old.index]={old.info,old.positions,old.palette,old.entries,old.materialized};
    }
    owned_skin_invalidate_frames();return 1;
}
extern "C" int re4dc_actor_owned_source(const void* info,unsigned source_frame,Re4dcActorSource* out) {
    if(!info || !out || skin_frame!=source_frame)return 0;
    for(unsigned i=0;i<skin_count;++i)if(skins[i].info==info && !skins[i].positions && owned_skins[i].serial){
        if(skins[i].materialized || skins[i].palette!=owned_skins[i].palette || skins[i].entries!=owned_skins[i].entries)return 0;
        *out=owned_skins[i].source;return 1;
    }
    return 0;
}
