// ACTOR_R300_FULL_SOURCE only. Included inside the source-actor namespace.
// The ordinary full-source traversal keeps ownership of preparation and order.
// This scope records its existing callback; it never invokes/replays one.
// Status2/04000000 means a pending SubScreenOpen request, before its fade/swap.
// roomListsSwapped() still excludes the actual sub-screen memory window. MapMgr
// codec models are not participants; only this ordinary EmMgr traversal is.
bool sourceActorFullEligible(int coarse,int swapped) {
    return !coarse && !swapped && !re4dc_pace_drop_models && !RE4DC_PACE_CHECK && pPL &&
        pG->Rno0==3 && pG->stage_no==3 && pG->room_no==0 &&
        ((pG->System_flg&0x400u) || (pG->Status_flg[2]&0x04000000u)) &&
        !(pG->System_flg&0x100000u);
}
void sourceActorFullDecline(unsigned reason) {
    sourceActorFailure(reason);
    sourceActorRetire();
}
struct SourceActorFullPreparation {
    cModel* model;
    re4dc_source::PreparationTicket ticket{};
    bool claimed=false;
    explicit SourceActorFullPreparation(cModel* m):model(m) {
        if(!sourceActorFullPass)return;
        FrameIdentity now{};
        if(!sourceActorActive || !sourceActorRam(m) || !sourceActorIdentity(now) ||
           !sourceActorLedger.claim(now,ticket) || !(ticket.model==sourceActorModel(m))) {
            sourceActorFullDecline(23);return;
        }
        claimed=true;
    }
    ~SourceActorFullPreparation() {
        if(!claimed || !sourceActorFullPass)return;
        FrameIdentity after{};
        if(!sourceActorIdentity(after) ||
           !sourceActorLedger.complete(after,ticket,sourceActorModel(model)))sourceActorFullDecline(24);
    }
};
bool sourceActorFullReady() {
    FrameIdentity now{};
    return sourceActorFullPass && sourceActorActive && sourceActorIdentity(now) && sourceActorLedger.ready(now);
}
void sourceActorFullFinish() {
    if(sourceActorFullPass && !sourceActorFullReady())sourceActorFullDecline(25);
}
