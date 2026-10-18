// Included after the source actor ledger block, before Trans().
// All helpers are values; no borrowed ledger/primitive pointers escape.
extern "C" int re4dc_actor_transaction_identity(cModel* m,re4dc_source::FrameIdentity* frame,re4dc_source::ModelIdentity* model) {
    if(!sourceActorActive || !sourceActorRenderActive){
#if defined(RE4DC_MCHECK_LEONGC) && RE4DC_MCHECK_LEONGC
        static unsigned inactive_leon_notes;
        if(m==(cModel*)pPL && inactive_leon_notes<8){
            ++inactive_leon_notes;
            re4dc_log("SOURCE_ACTOR_INACTIVE t=%u room=%02x%02x active=%u render=%u count=%u epoch=%u rno=%u system=%08x status=%08x/%08x display=%08x\n",
                unsigned(pG->Frame_cnt),unsigned(pG->stage_no),unsigned(pG->room_no),
                unsigned(sourceActorActive),unsigned(sourceActorRenderActive),sourceActorCount,sourceActorEpoch,
                unsigned(pG->Rno0),unsigned(pG->System_flg),
                unsigned(pG->Status_flg[1]),unsigned(pG->Status_flg[2]),unsigned(pG->Disp_flg));
        }
#endif
        return 0;
    }
    if(!m || !frame || !model || !sourceActorRam(m) || !sourceActorIdentity(*frame) ||
       !sourceActorLedger.ready(*frame))return -1;
    *model=sourceActorModel(m);
    if(sourceActorLedger.membership(*frame,*model)==Membership::SourceHandled)return 1;
    // A reused actor address cannot become an untracked source fallback after
    // a native first pass. Unrelated ObjMgr/world models are not participants.
    return sourceActorLedger.presentation_address(*frame,model->address)?-1:0;
}
extern "C" int re4dc_actor_transaction_choice(cModel* m,unsigned* value) {
    FrameIdentity frame{};ModelIdentity model{};
    return value && re4dc_actor_transaction_identity(m,&frame,&model)==1 &&
        sourceActorLedger.presentation_choice(frame,model,*value);
}
extern "C" int re4dc_actor_transaction_choose(cModel* m,unsigned value) {
    FrameIdentity frame{};ModelIdentity model{};
    return re4dc_actor_transaction_identity(m,&frame,&model)==1 &&
        sourceActorLedger.presentation_choose(frame,model,value);
}
#if RE4DC_NATIVE_MODEL_REGISTRY
extern "C" int re4dc_registry_candidate(const cModel*);
#endif
extern "C" int re4dc_actor_transaction_candidate(cModel* m) {
    // Disable the FRONT_NATIVE fast return only for these source-prepared
    // reviewed classes. Their ordinary state/postlude runs via commonModelTrans.
#if RE4DC_ACTOR_SKIN_RESERVE
    if(!sourceActorNativeOwner(m))return 0;
#else
#if RE4DC_NATIVE_MODEL_REGISTRY
    // NATIVE_MODEL_REGISTRY: also non-partner models whose id has a validated
    // runtime descriptor of the same part count (coarse_actor_owner_registry.inc,
    // O(1) id mask first). These only nominate; the ledger membership below and the transaction's
    // role / skeleton / material proofs admit, and a declined actor draws the
    // whole source path through commonModelTrans.
#if defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22
    // Cabin Luis only: his exact loaded registry descriptor nominates the
    // prepared partner. Ownership still requires the ledger and every plan proof.
#if defined(RE4DC_NMR_ASHLEY) && RE4DC_NMR_ASHLEY
    // PS2_ASHLEY: the partner Ashley (pSUB id 3) likewise, by her draw-slot descriptor.
    if(!m || !(m==(cModel*)pPL || (m!=(cModel*)pSUB && ((m->id>=0x10 && m->id<=0x20) ||
       re4dc_registry_candidate(m))) || (m==(cModel*)pSUB && (m->id==4 || m->id==3) && re4dc_registry_candidate(m))))return 0;
#else
    if(!m || !(m==(cModel*)pPL || (m!=(cModel*)pSUB && ((m->id>=0x10 && m->id<=0x20) ||
       re4dc_registry_candidate(m))) || (m==(cModel*)pSUB && m->id==4 && re4dc_registry_candidate(m))))return 0;
#endif
#elif defined(RE4DC_NMR_ASHLEY) && RE4DC_NMR_ASHLEY
    // PS2_ASHLEY (native_model_registry.mk): the partner Ashley (pSUB id 3) is nominated only by her exact loaded
    // draw-slot descriptor; ownership still requires the ledger and every plan proof.
    if(!m || !(m==(cModel*)pPL || (m!=(cModel*)pSUB && ((m->id>=0x10 && m->id<=0x20) ||
       re4dc_registry_candidate(m))) || (m==(cModel*)pSUB && m->id==3 && re4dc_registry_candidate(m))))return 0;
#else
    if(!m || !(m==(cModel*)pPL || (m!=(cModel*)pSUB && ((m->id>=0x10 && m->id<=0x20) ||
       re4dc_registry_candidate(m)))))return 0;
#endif
#else
    if(!m || !(m==(cModel*)pPL || (m!=(cModel*)pSUB && m->id>=0x10 && m->id<=0x20)))return 0;
#endif
#endif
    FrameIdentity frame{};ModelIdentity model{};
    return re4dc_actor_transaction_identity(m,&frame,&model)!=0;
}
