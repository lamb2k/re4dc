// Included inside the transaction's unnamed namespace, default-off G1 only.
// No palette, skin, workspace or texture lease is retained in this context.
extern "C" unsigned re4dc_fog_enabled();
struct ActorFadeContext {
    cModelInfo* info[kRe4dcActorRoles]{};
    unsigned flags[kRe4dcActorRoles]{},role[kRe4dcActorRoles]{};
    float mv[kRe4dcActorRoles][12]{},projection[7]{},viewport[6]{};
    re4dc::render::SourceLighting lit{};
    unsigned count=0,alpha=255,fog=0,factor[2]{},hash=0;
#if RE4DC_NMR_DYING
    unsigned own_lit=0;  // the record lit itself (r.lit); 0: the drain keeps the plan's constant / probe record
#endif
};
struct ActorFadePending {
    ActorFadePending* next=nullptr;
    Re4dcActorFadeTicket ticket{};
    const void* parts_owner=nullptr;
    unsigned binding_revision=0;
    re4dc_fade::State state=re4dc_fade::State::Pending;
    Re4dcActorPlan plan{};
    ActorFadeContext context{};
};
static_assert(sizeof(ActorFadePending)<=sizeof(ActorOwnedRecord),"G1 pending storage does not exceed the original owner header");
ActorFadePending* actor_fade_head;
unsigned actor_fade_sequence,actor_fade_pending;

bool actor_fade_eligible_g1(cModel* m,const Re4dcActorPlan& p) {
#if RE4DC_NMR_DYING && !defined(RE4DC_AGDF_G1)
    // NATIVE_MODEL_REGISTRY_DYING without ACTOR_GANADO_DEATH_FADE: the reviewed id13 candidate stays off.
    (void)m;(void)p;return false;
#else
    // hp belongs to the actual recovered cEm. Do not read it for other types.
    if(!m || m->kindid!=0 || m->id!=0x13)return false;
    return re4dc_fade::state_allows(*m,p.appearance,static_cast<cEm*>(m)->hp);
#endif
}
bool actor_fade_eligible(cModel* m,const Re4dcActorPlan& p) {
#if RE4DC_NMR_DYING
    // NATIVE_MODEL_REGISTRY_DYING (native_model_registry.mk): a Ganado-class enemy (em10.cpp family, ids 0x10..0x20,
    // one source pass) planned by the PS2 Ganado cast or a registry descriptor, while its whole-model fade runs (death:
    // invisible_factor -0.1 per frame; the source skips the model at 0, trans.cpp), keeps its native plan: the G1 ticket
    // draws it at its source FIFO position in the TR list with the source's alpha. Before, actor_semantics declined it
    // and its last frames drew GC (CAST-GC).
    if(m && m->kindid==0 && m->id>=0x10 && m->id<=0x20 && !m->ot_type &&
       m->invisible_factor>0.0f && m->invisible_factor<1.0f && m->invisible_factor2==1.0f && m->alpha_omit==255)return true;
#endif
    return actor_fade_eligible_g1(m,p);
}
unsigned actor_fade_hash(const ActorFadeContext& c) {
    unsigned hash=2166136261u;
    auto bytes=[&](const void* p,unsigned n){const auto* b=static_cast<const unsigned char*>(p);while(n--)hash=(hash^*b++)*16777619u;};
    bytes(&c.count,sizeof(c.count));bytes(&c.alpha,sizeof(c.alpha));bytes(&c.fog,sizeof(c.fog));bytes(c.factor,sizeof(c.factor));
    for(unsigned i=0;i<c.count;++i){bytes(c.mv[i],sizeof(c.mv[i]));bytes(&c.flags[i],sizeof(c.flags[i]));bytes(&c.role[i],sizeof(c.role[i]));}
    bytes(c.projection,sizeof(c.projection));bytes(c.viewport,sizeof(c.viewport));
    for(const auto& l:c.lit.lights){bytes(l.position,sizeof(l.position));bytes(l.direction,sizeof(l.direction));bytes(l.a,sizeof(l.a));bytes(l.k,sizeof(l.k));bytes(l.color,sizeof(l.color));}
    bytes(c.lit.normal_matrix,sizeof(c.lit.normal_matrix));bytes(c.lit.ambient,sizeof(c.lit.ambient));bytes(c.lit.material,sizeof(c.lit.material));
    const unsigned ctl[]={c.lit.mask,c.lit.enable,c.lit.ambient_vertex,c.lit.material_vertex,c.lit.diffuse,c.lit.attenuation};
    bytes(ctl,sizeof(ctl));bytes(&c.lit.tev_scale,sizeof(c.lit.tev_scale));return hash;
}
ActorFadeContext actor_fade_capture(cModel* m,const ActorOwnedRecord& r) {
    ActorFadeContext c{};c.count=r.count;c.alpha=r.base.alpha_state;c.fog=r.base.source_key[2];c.lit=r.lit;
    c.factor[0]=re4dc_fade::bits(m->invisible_factor);c.factor[1]=re4dc_fade::bits(m->invisible_factor2);
#if RE4DC_NMR_DYING
    c.own_lit=r.base.lighting==&r.lit;
#endif
    std::memcpy(c.projection,r.base.projection,sizeof(c.projection));std::memcpy(c.viewport,r.base.viewport,sizeof(c.viewport));
    for(unsigned i=0;i<r.count;++i){c.info[i]=r.part[i].info;c.flags[i]=r.part[i].flags;c.role[i]=r.part[i].role;std::memcpy(c.mv[i],r.part[i].mv,sizeof(c.mv[i]));}
    c.hash=actor_fade_hash(c);return c;
}
ActorFadePending* actor_fade_find(const ModelIdentity& model) {
    for(auto* p=actor_fade_head;p;p=p->next)if(p->ticket.model==model)return p;
    return nullptr;
}
bool actor_fade_current(const Re4dcActorFadeTicket& ticket,unsigned expected_choice) {
    // This guard is deliberately first: retirement clears live before storage
    // reuse and no retained pointer may be traversed after a changed identity.
    if(!actor_owned_live || !(actor_owned_frame==ticket.frame))return false;
    auto* m=reinterpret_cast<cModel*>(ticket.model.address);
    FrameIdentity frame{};ModelIdentity model{};unsigned choice=0;
    return re4dc_actor_transaction_identity(m,&frame,&model)==1 && frame==ticket.frame && model==ticket.model &&
        re4dc_actor_transaction_choice(m,&choice) && choice==expected_choice;
}
void actor_fade_note(const char* phase,const Re4dcActorFadeTicket& t,const ActorFadeContext* c,unsigned why=0) {
    // One complete bounded line per transition; no shared AVD128 truncation.
    re4dc_log("AFD %s t=%u m=%p s=%u q=%u ep=%u a=%u f=%08x/%08x ctx=%08x why=%u\n",phase,t.frame.frame,
        reinterpret_cast<void*>(t.model.address),t.model.serial,t.sequence,t.queue_epoch,c?c->alpha:0,
        c?c->factor[0]:0,c?c->factor[1]:0,c?c->hash:0,why);
}
#if RE4DC_ACTOR_TRANSACTION_DIAG
void actor_fade_words(const Re4dcActorFadeTicket& t,const char* field,unsigned index,const void* data,unsigned bytes) {
    const auto* p=static_cast<const unsigned char*>(data);
    for(unsigned at=0;at<bytes;at+=16) {
        unsigned words[4]{};const unsigned n=bytes-at<16?bytes-at:16;std::memcpy(words,p+at,n);
        re4dc_log("AFD_CTX t=%u s=%u q=%u field=%s i=%u at=%u n=%u w=%08x/%08x/%08x/%08x\n",
            t.frame.frame,t.model.serial,t.sequence,field,index,at,n,words[0],words[1],words[2],words[3]);
    }
}
void actor_fade_snapshot(const Re4dcActorFadeTicket& t,const ActorFadeContext& c) {
    for(unsigned i=0;i<c.count;++i) {
        re4dc_log("AFD_ROLE t=%u s=%u q=%u i=%u role=%u info=%p flags=%08x\n",t.frame.frame,t.model.serial,t.sequence,i,c.role[i],c.info[i],c.flags[i]);
        actor_fade_words(t,"mv",i,c.mv[i],sizeof(c.mv[i]));
    }
    actor_fade_words(t,"projection",0,c.projection,sizeof(c.projection));
    actor_fade_words(t,"viewport",0,c.viewport,sizeof(c.viewport));
    for(unsigned i=0;i<8;++i)actor_fade_words(t,"light",i,&c.lit.lights[i],sizeof(c.lit.lights[i]));
    actor_fade_words(t,"normal",0,c.lit.normal_matrix,sizeof(c.lit.normal_matrix));
    actor_fade_words(t,"ambient",0,c.lit.ambient,sizeof(c.lit.ambient));
    actor_fade_words(t,"material",0,c.lit.material,sizeof(c.lit.material));
    const unsigned control[]={c.count,c.alpha,c.fog,c.factor[0],c.factor[1],c.lit.mask,c.lit.enable,
        c.lit.ambient_vertex,c.lit.material_vertex,c.lit.diffuse,c.lit.attenuation,re4dc_fade::bits(c.lit.tev_scale),c.hash};
    actor_fade_words(t,"control",0,control,sizeof(control));
}
#endif
void actor_fade_retire() {
    // Do not walk headers whose primitive storage may already be revoked.
    const unsigned lost=actor_fade_pending;actor_fade_head=nullptr;actor_fade_pending=0;
    if(lost){re4dc_log("AFD retire lost=%u\n",lost);actor_fail();}
}
