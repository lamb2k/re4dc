// Build32: a nominee's captured source palette recipe lives in the existing
// primitive span. A row/valid owner lease is authority before this descriptor
// is dereferenced; the descriptor's epoch is a second, not first, check.
struct SkinRecipe {
    unsigned magic,frame;
    const void* model;
    const void* weight;
    unsigned n_ext,serial,epoch,slot;
};
static constexpr unsigned kSkinRecipeMagic=0x7FA5E2A5u; // distinct from SkinLazyHead
static_assert(sizeof(SkinRecipe)==(sizeof(void*)==4?32u:40u),"skin recipe pointer/layout ABI");
static_assert(sizeof(SkinEntry)==(sizeof(void*)==4?20u:32u),"ordinary skin row ABI");
static_assert(sizeof(Re4dcActorSkinBackup)==(sizeof(void*)==4?24u:40u),"saved skin row ABI");
static constexpr unsigned kSkinRecipeBytes=(sizeof(SkinRecipe)+31u)&~31u;
unsigned skin_recipe_epoch=1;
bool skin_recipe_building;
extern "C" int re4dc_prim_recipe_claim(unsigned,unsigned,unsigned,void**);
extern "C" int re4dc_prim_recipe_release(unsigned);
extern "C" unsigned re4dc_prim_recipe_credit();
extern "C" unsigned re4dc_prim_recipe_frame();
extern "C" void re4dc_prim_recipe_retire_credit();
extern "C" const float* re4dc_skin_recipe_materialize(const void*,const void*,unsigned,unsigned,unsigned);

bool skin_recipe_nominated(const SkinEntry& e) {
    return !e.positions && (e.materialized==kSkinRecipeNominee ||
        e.materialized==kSkinRecipePending || e.materialized==kSkinRecipeReady ||
        e.materialized==kSkinRecipeDone);
}
unsigned skin_recipe_registration_state(const SkinEntry& e) {
    return skin_recipe_nominated(e)?kSkinRecipeReady:0u;
}
bool skin_recipe_readable(const SkinEntry& e) {
    return e.materialized==0 || e.materialized==kSkinRecipeReady ||
        e.materialized==kSkinRecipePending;
}
bool skin_recipe_valid(const SkinEntry&,unsigned);
bool skin_recipe_eligible(const SkinEntry* e) {
    if(!e || !skin_recipe_readable(*e) || !e->palette || !e->entries)return false;
    return e->materialized!=kSkinRecipePending ||
        skin_recipe_valid(*e,unsigned(e-skins));
}
bool skin_recipe_valid(const SkinEntry& e,unsigned slot) {
    // The caller must first prove this is a current ordinary row. In
    // particular, a copied lease.old never calls this helper on its own.
    if(slot>=skin_count || &skins[slot]!=&e || e.materialized!=kSkinRecipePending ||
       e.positions || !e.info || !e.palette || !e.entries ||
       skin_recipe_epoch==~0u || skin_frame==~0u ||
       skin_frame!=re4dc_prim_recipe_frame())return false;
    const auto* d=reinterpret_cast<const SkinRecipe*>(e.palette);
    return d->magic==kSkinRecipeMagic && d->frame==skin_frame &&
        d->slot==slot && d->epoch==skin_recipe_epoch && d->serial &&
        d->serial<=skin_admission_serial && (d->n_ext&0xffffu)==e.entries;
}
bool skin_recipe_drop(SkinEntry& e,unsigned slot) {
    if(e.materialized!=kSkinRecipePending)return true;
    if(!skin_recipe_valid(e,slot))return false;
    const unsigned n=e.entries;
    if(n>(~0u-31u)/48u)return false;
    return re4dc_prim_recipe_release((n*48u+31u)&~31u)!=0;
}
void skin_recipe_frame_retire() {
    // Owner serials were revoked by the caller before this sweep. A hidden
    // lease.old cannot subsequently restore its saved pointer.
    for(unsigned i=0;i<skin_count;++i)
        if(skin_recipe_nominated(skins[i]))skins[i]={};
    re4dc_prim_recipe_retire_credit();
    skin_recipe_building=false;
}
extern "C" void re4dc_actor_skin_recipe_retire() {
    // SetPrimBuffPtr calls this after sourceActorRetire (owner serial revoke)
    // and before changing the primitive cursor, including prim_cnt==0.
    skin_recipe_frame_retire();
    if(skin_recipe_epoch!=~0u)++skin_recipe_epoch;
}
extern "C" int re4dc_actor_skin_recipe_claim(Re4dcActorSkinAdmission* ticket,
                                               const void* model,const void* weight,unsigned n_ext) {
    if(!skin_admission_matches(ticket) || skin_recipe_building)return -1;
    const auto p=skin_admission_pending;
    if(p.frame!=skin_frame || p.positions || p.slot>=skin_count ||
       skins[p.slot].info!=p.info || !skin_recipe_nominated(skins[p.slot]))return 0;
    SkinEntry& e=skins[p.slot];
    if(!model || !weight || !p.entries || p.entries>0xffffu ||
       (n_ext&0xffffu)!=p.entries || (n_ext&~0x1ffffu) ||
       skin_recipe_epoch==~0u || p.entries>(~0u-31u)/48u)return -1;
    unsigned old_credit=0;
    SkinRecipe* d=nullptr;
    if(e.materialized==kSkinRecipePending) {
        if(!skin_recipe_valid(e,p.slot))return -1;
        old_credit=(e.entries*48u+31u)&~31u;
        d=reinterpret_cast<SkinRecipe*>(const_cast<float*>(e.palette));
    }
    const unsigned new_credit=(p.entries*48u+31u)&~31u;
    void* allocation=nullptr;
    if(!re4dc_prim_recipe_claim(d?0u:kSkinRecipeBytes,old_credit,new_credit,&allocation))return -1;
    if(!d) {
        d=static_cast<SkinRecipe*>(allocation);
    }
    *d={kSkinRecipeMagic,p.frame,model,weight,n_ext,p.serial,skin_recipe_epoch,p.slot};
    e={p.info,nullptr,reinterpret_cast<const float*>(d),p.entries,kSkinRecipePending};
    skin_admission_pending={};*ticket={};
    ++stats.skin_registered;
    return 1;
}
bool skin_recipe_materialize(SkinEntry& e) {
    if(e.materialized!=kSkinRecipePending)return skin_recipe_readable(e);
    if(skin_recipe_building || skin_frame==~0u)return false;
    const unsigned slot=unsigned(&e-skins);
    if(!skin_recipe_valid(e,slot))return false;
    const SkinRecipe d=*reinterpret_cast<const SkinRecipe*>(e.palette);
    const unsigned bytes=(e.entries*48u+31u)&~31u;
    skin_recipe_building=true;
    const float* palette=re4dc_skin_recipe_materialize(d.model,d.weight,d.n_ext,d.frame,bytes);
    skin_recipe_building=false;
    if(!palette)return false;
    // The source builder is non-yielding. Reentry into registry writers is
    // rejected while building, so this is still the same current row.
    e.palette=palette;e.materialized=kSkinRecipeReady;
    return true;
}

extern "C" int re4dc_actor_skin_finish_owner(Re4dcActorSkinLease* lease) {
    // Validation precedes any saved descriptor read. Primitive retirement
    // revoked serials before address reuse, including a same-Frame_cnt reset.
    if(skin_recipe_building || !re4dc_actor_skin_validate(lease) ||
       lease->frame!=re4dc_prim_recipe_frame())return 0;
    unsigned total=0;
    for(unsigned k=0;k<lease->count;++k) {
        const auto& old=lease->old[k];
        if(old.materialized!=kSkinRecipePending)continue;
        if(old.index>=skin_count || old.positions || !old.info || !old.palette ||
           old.info!=skins[old.index].info || !old.entries ||
           old.entries>(~0u-31u)/48u)return 0;
        const auto* d=reinterpret_cast<const SkinRecipe*>(old.palette);
        if(d->magic!=kSkinRecipeMagic || d->frame!=lease->frame ||
           d->slot!=old.index || d->epoch!=skin_recipe_epoch ||
           !d->serial || d->serial>skin_admission_serial ||
           (d->n_ext&0xffffu)!=old.entries)return 0;
        const unsigned bytes=(old.entries*48u+31u)&~31u;
        if(total>~0u-bytes)return 0;
        total+=bytes;
    }
    if(total>re4dc_prim_recipe_credit())return 0;
    for(unsigned k=0;k<lease->count;++k) {
        auto& old=lease->old[k];
        if(old.materialized!=kSkinRecipePending)continue;
        const unsigned bytes=(old.entries*48u+31u)&~31u;
        if(!re4dc_prim_recipe_release(bytes))return 0;
        const unsigned index=old.index;
        old={index,nullptr,nullptr,nullptr,0,0};
    }
    return 1;
}
