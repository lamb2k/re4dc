// SKIN_ADMISSION32: one provisional source palette ticket. Admission observes
// the ordinary registry's exact replacement/free-slot rules without changing
// it; the ticket blocks competing writers while re4dc_prim_tail + memcpy run.
// A failed allocation cancels only this ticket. No allocator rewind is legal.
bool skin_admission_matches(const Re4dcActorSkinAdmission* t) {
    const auto& p=skin_admission_pending;
    return t && t->serial && t->serial==p.serial && t->frame==p.frame &&
        t->slot==p.slot && t->entries==p.entries && t->info==p.info &&
        t->positions==p.positions && t->provisional==p.provisional;
}
extern "C" int re4dc_actor_skin_admit(unsigned frame,const void* info,const void* positions,
                                      unsigned entries,Re4dcActorSkinAdmission* out) {
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if(skin_recipe_building)return 0;
#endif
    if(!out || out->serial || !info || !entries || skin_admission_pending.serial ||
       skin_admission_serial==~0U)return 0;
    const bool current=frame==skin_frame;
    unsigned slot=kSkins;
    bool replace=false;
    if(current) {
#if RE4DC_ACTOR_TRANSACTION
#if RE4DC_ACTOR_SKIN_OWNER_POOL
        if(find_owned_skin(info))return 0;
#else
        for(unsigned i=0;i<skin_count;++i)if(owned_skins[i].serial && owned_skins[i].info==info)return 0;
#endif
#endif
        if(!positions) {
            SkinEntry* e=
#if RE4DC_ACTOR_SKIN_OWNER_POOL
                find_ordinary_skin(info,nullptr);
#else
                find_skin(info,nullptr);
#endif
            if(e) {
                slot=unsigned(e-skins);
#if RE4DC_ACTOR_TRANSACTION && !RE4DC_ACTOR_SKIN_OWNER_POOL
                if(owned_skins[slot].serial)return 0;
#endif
                replace=true;
            }
        }
        if(!replace) {
            for(unsigned i=0;i<skin_count;++i)if(!skins[i].info
#if RE4DC_ACTOR_TRANSACTION && !RE4DC_ACTOR_SKIN_OWNER_POOL
                && !owned_skins[i].serial
#endif
            ){slot=i;break;}
            if(slot==kSkins){if(skin_count==kSkins)return 0;slot=skin_count;}
        }
    } else {
        // Do not retire the preceding frame or its owner leases on an OOM.
        // The source register's frame switch occurs only at publication.
        slot=0;
    }
    const unsigned serial=++skin_admission_serial;
    skin_admission_pending={serial,frame,slot,entries,info,positions,!replace};
    *out=skin_admission_pending;
    return 1;
}
extern "C" void re4dc_actor_skin_cancel(Re4dcActorSkinAdmission* ticket) {
    if(!skin_admission_matches(ticket))return;
    skin_admission_pending={};
    *ticket={};
}
extern "C" void re4dc_actor_skin_retire_pending() {
    // SetPrimBuffPtr retires backing storage before another frame can borrow
    // its address. A copied ticket cannot publish into that new incarnation.
    skin_admission_pending={};
}
extern "C" int re4dc_actor_skin_commit(Re4dcActorSkinAdmission* ticket,const float* palette) {
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if(skin_recipe_building)return 0;
#endif
    if(!skin_admission_matches(ticket) || !palette)return 0;
    const Re4dcActorSkinAdmission p=skin_admission_pending;
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    unsigned state=0;
    if(p.frame==skin_frame && p.slot<skin_count && !p.positions) {
        SkinEntry& old=skins[p.slot];
        state=skin_recipe_registration_state(old);
        if(!skin_recipe_drop(old,p.slot))return 0;
    }
#endif
    skin_admission_pending={};
    *ticket={};
    if(p.frame!=skin_frame) {
#if RE4DC_ACTOR_TRANSACTION
        owned_skin_clear();owned_skin_invalidate_frames();
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
        skin_recipe_frame_retire();
#endif
        skin_frame=p.frame;skin_count=0;
    }
    // The ticket excluded every competing register/reserve/acquire and the
    // source allocator path does not yield. This selected slot remains free
    // or is precisely the prior lazy entry we are replacing.
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    skins[p.slot]={p.info,p.positions,palette,p.entries,state};
#else
    skins[p.slot]={p.info,p.positions,palette,p.entries,0};
#endif
    if(p.slot>=skin_count)skin_count=p.slot+1;
    ++stats.skin_registered;
    return 1;
}
