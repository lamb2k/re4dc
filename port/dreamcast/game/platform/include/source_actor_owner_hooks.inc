// Included after the source actor ledger block, before Trans().
// All helpers are values; no borrowed ledger/primitive pointers escape.
#if RE4DC_AUX_OBJ_NATIVE
// AUX_OBJ_NATIVE (crowd.mk, lane garr18 2026-10-19; default 0; render only): a narrow native path for allowlisted ObjMgr
// objects that are parts of a character but separate source objects (coordinator 10-19: never in the EmMgr ledger). A
// live ObjMgr work of an allowlisted kind (id, type, part count) gets its own small presentation record for the frame
// (the ledger's sticky choice rule: 0 undecided -> 1 source -> 2 owned native) and then runs the ordinary actor
// transaction (registry plan, every proof, skin lease). The EmMgr ledger, its counts and the reserve are unchanged.
// Rows are data: a later kind is one row. A full table or an unproved object keeps the source path.
namespace {
struct AuxKind { unsigned char id, type, parts; };
constexpr AuxKind kAuxKinds[]={
    {0x16,4,14},  // Garrador core: em10SetParasite cObj16 (BIN227 / TPL228, 14 parts), registry descriptor garr-core-em1b
};
constexpr unsigned kAuxEntries=4;
struct AuxEntry { FrameIdentity frame; ModelIdentity model; unsigned presentation; };
AuxEntry auxEntries[kAuxEntries];
unsigned auxRefused;
bool auxObject(const cModel* m) {
    bool kind=false;
    for(const auto& k:kAuxKinds)if(m->id==k.id && m->type==k.type && m->nParts==k.parts){kind=true;break;}
    if(!kind || !(m->be_flag&1) || !m->pParts)return false;
    // A work whose root matrix is still singular (its first frame, before em10SetParasite places it) is not drawn by
    // either path; it joins once placed, so the plan's inverse proof never declines it to the source path.
    {Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return false;}
    // Membership: a work on ObjMgr's live list (bounded walk; the list holds every live object work).
    unsigned n=0;
    for(const cUnit* u=ObjMgr.pAlive;u && n<512u && sourceActorRam(u);u=u->pNext,++n)
        if(u==static_cast<const cUnit*>(m))return true;
    return false;
}
AuxEntry* auxEntry(const FrameIdentity& frame,const ModelIdentity& model,bool add) {
    AuxEntry* free=nullptr;
    for(auto& e:auxEntries) {
        if(e.frame==frame && e.model==model)return &e;
        if(!free && !(e.frame==frame))free=&e;
    }
    if(!add)return nullptr;
    if(!free){if(auxRefused++<4)re4dc_log("AUX_OBJ table full f=%u\n",frame.frame);return nullptr;}
    *free={frame,model,0};return free;
}
}
#endif
extern "C" int re4dc_actor_transaction_identity(cModel* m,re4dc_source::FrameIdentity* frame,re4dc_source::ModelIdentity* model) {
    if(!sourceActorActive || !sourceActorRenderActive)return 0;
    if(!m || !frame || !model || !sourceActorRam(m) || !sourceActorIdentity(*frame) ||
       !sourceActorLedger.ready(*frame))return -1;
    *model=sourceActorModel(m);
    if(sourceActorLedger.membership(*frame,*model)==Membership::SourceHandled)return 1;
    // A reused actor address cannot become an untracked source fallback after
    // a native first pass. Unrelated ObjMgr/world models are not participants.
#if RE4DC_AUX_OBJ_NATIVE
    if(sourceActorLedger.presentation_address(*frame,model->address))return -1;
    return auxObject(m) && auxEntry(*frame,*model,true)?1:0;  // AUX_OBJ_NATIVE: an allowlisted ObjMgr part
#else
    return sourceActorLedger.presentation_address(*frame,model->address)?-1:0;
#endif
}
extern "C" int re4dc_actor_transaction_choice(cModel* m,unsigned* value) {
    FrameIdentity frame{};ModelIdentity model{};
#if RE4DC_AUX_OBJ_NATIVE
    if(!value || re4dc_actor_transaction_identity(m,&frame,&model)!=1)return 0;
    if(const auto* e=auxEntry(frame,model,false)){*value=e->presentation;return 1;}
    return sourceActorLedger.presentation_choice(frame,model,*value);
#else
    return value && re4dc_actor_transaction_identity(m,&frame,&model)==1 &&
        sourceActorLedger.presentation_choice(frame,model,*value);
#endif
}
extern "C" int re4dc_actor_transaction_choose(cModel* m,unsigned value) {
    FrameIdentity frame{};ModelIdentity model{};
#if RE4DC_AUX_OBJ_NATIVE
    if(re4dc_actor_transaction_identity(m,&frame,&model)!=1)return 0;
    if(auto* e=auxEntry(frame,model,false)) {
        if(!((e->presentation==0 && value==1) || (e->presentation==1 && value==2)))return 0;  // the ledger's rule
        e->presentation=value;return 1;
    }
    return sourceActorLedger.presentation_choose(frame,model,value);
#else
    return re4dc_actor_transaction_identity(m,&frame,&model)==1 &&
        sourceActorLedger.presentation_choose(frame,model,value);
#endif
}
#if RE4DC_NATIVE_MODEL_REGISTRY
extern "C" int re4dc_registry_candidate(const cModel*);
#endif
extern "C" int re4dc_actor_transaction_candidate(cModel* m) {    // Disable the FRONT_NATIVE fast return only for these source-prepared
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
