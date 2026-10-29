// Included after ps2w, dynamic/AREA/gate state and PVS proof services.
// Portal geometry is static; permission to use it is current-image evidence.
namespace wp29 {
re4dc::portal29::Receipts receipts;
re4dc::pvsproof::Certificate numeric_cert{};
unsigned validated_generation=~0U,view_frame=~0U,scene=~0U;
unsigned admitted=0,declined=0,commits=0,source_declines=0,scene_declines=0,waits=0;
bool valid=false,candidate=false;
float view_key[27]{};

#if RE4DC_WORLD_PORTAL_COMPLETION
unsigned completion_serial=0;
const void* completion_storage=nullptr;
const void* completion_parts=nullptr;
const void* completion_placements=nullptr;
unsigned completion_generation=~0U,completion_room=~0U,completion_count=0;
unsigned completion_keys[re4dc::portal29::kMaxWitnesses][6]{};
bool material_matches(unsigned part,const unsigned* key){
    if(!key || !ps2w.parts || part>=ps2w.package.header().part_count)return false;
    const auto& m=ps2w.parts[part];
    return key[0]==m.crc && key[1]==m.fnv && key[2]==m.width && key[3]==m.height &&
           key[4]==m.pass && key[5]==m.cull;
}
bool completion_sources_current(){
    if(completion_count>re4dc::portal29::kMaxWitnesses || !completion_storage || completion_storage!=ps2w.storage || completion_parts!=ps2w.parts ||
       completion_placements!=ps2w.placements || completion_generation!=pc::wp29_generation ||
       completion_room!=ps2w.room || completion_count!=pc::wp29_count || !pc::wp29_witnesses)return false;
    for(unsigned q=0;q<completion_count;++q)
        if(!material_matches(pc::wp29_witnesses[q].part,completion_keys[q]))return false;
    return true;
}
void completion_begin(){
    // Existing receipt bits may cross opaque->later passes only for exactly
    // the same source/material state. A same-address reload gets a new cell epoch.
    if(!completion_sources_current())receipts.clear();
    // Zero is permanently exhausted. No frame/room/movie reset restores it.
    static bool exhausted=false;
    if(completion_serial==~0U)exhausted=true;
    if(!exhausted)++completion_serial;else completion_serial=0;
    completion_storage=ps2w.storage;completion_parts=ps2w.parts;completion_placements=ps2w.placements;
    completion_generation=pc::wp29_generation;completion_room=ps2w.room;completion_count=pc::wp29_count;
    for(unsigned q=0;q<completion_count;++q){
        const auto& m=ps2w.parts[pc::wp29_witnesses[q].part];auto* key=completion_keys[q];
        key[0]=m.crc;key[1]=m.fnv;key[2]=m.width;key[3]=m.height;key[4]=m.pass;key[5]=m.cull;
    }
}
#endif

bool sources(){
#if RE4DC_WORLD_PORTAL_COMPLETION
    if(pc::wp29_count>re4dc::portal29::kMaxWitnesses)return false;
#endif
    if(!pc::data.block || !pc::wp29_witnesses || !pc::wp29_count || !ps2w.storage ||
       !ps2w.parts || !ps2w.package.lod() || !dyn::ids || dyn::nids!=ps2w.nplacements ||
       pc::kPcRoom!=ps2w.room)return false;
    const auto& pk=ps2w.package;
    for(unsigned q=0;q<pc::wp29_count;++q){
        const auto& w=pc::wp29_witnesses[q];
        if(w.placement>=ps2w.nplacements || w.part>=pk.header().part_count)return false;
        const auto& pl=ps2w.placements[w.placement];const auto& m=pk.meshes()[pl.mesh];
        const auto& part=ps2w.parts[w.part];
        if(w.part<m.first_part || w.part-m.first_part>=m.part_count || part.pass!=0U ||
           part.reserved || (part.cull!=0U && part.cull!=2U) || pl.placement>=dyn::nids)return false;
        const unsigned id=dyn::ids[pl.placement];
        // Builder excludes source-owned/dynamic occluders. Keep this explicit:
        // a currently-resting moving wall is still not an immutable witness.
        if(id<dyn::kIds && dyn::slot_of[id]!=dyn::kNone)return false;
        const unsigned char field[2]={std::uint8_t(pl.placement),std::uint8_t(pl.placement>>8)};
        if(!re4dc_ps2_placements_intact(ps2w.room,field,1U))return false;
    }
    return true;
}
bool numeric_bounds(){
    numeric_cert={};numeric_cert.margin_mm=64U;
    const auto& pk=ps2w.package;
    for(unsigned i=0;i<ps2w.nplacements;++i){
        const auto& pl=ps2w.placements[i];const auto& m=pk.meshes()[pl.mesh];
        double b[3];
        for(unsigned a=0;a<3;++a){
            if(!std::isfinite(m.origin[a]) || !std::isfinite(m.step[a]))return false;
            b[a]=std::fabs(double(m.origin[a]))+65535.0*std::fabs(double(m.step[a]));
        }
        for(unsigned r=0;r<3;++r){
            double magnitude=0;
            for(unsigned a=0;a<3;++a){
                if(!std::isfinite(pl.affine[4*r+a]))return false;
                magnitude+=std::fabs(double(pl.affine[4*r+a]))*b[a];
            }
            if(!std::isfinite(pl.affine[4*r+3]))return false;
            magnitude+=std::fabs(double(pl.affine[4*r+3]));
            if(!(magnitude<=1000000.0))return false;
            if(magnitude>numeric_cert.world_abs[r])numeric_cert.world_abs[r]=magnitude;
        }
    }
    for(double& n:numeric_cert.world_abs)if(n<1.0)n=1.0;
    return true;
}
void begin(unsigned pass,const float* P,float near,float far){
    pc::st.active=false;candidate=false;valid=false;
    unsigned epoch[2];
    if(!pc::data.block || !re4dc_pvs23_scene(epoch) || epoch[0]!=re4dc_ui_frame()){
        receipts.clear();++scene_declines;return;
    }
    if(validated_generation!=pc::wp29_generation){
        receipts.clear();validated_generation=pc::wp29_generation;
        if(!numeric_bounds()){validated_generation=~0U;++declined;return;}
    }
    float key[27];std::memcpy(key,ps2w.view,48);std::memcpy(key+12,P,28);
    std::memcpy(key+19,ps2w.viewport,24);key[25]=near;key[26]=far;
    if(!pass)receipts.clear();
    receipts.sync(epoch[0],epoch[1],pc::wp29_generation,key);
    std::memcpy(view_key,key,sizeof(key));view_frame=epoch[0];scene=epoch[1];
#if RE4DC_SCENERY_CONE || RE4DC_SCENERY_PIECE_STATE || RE4DC_SCENERY_DEDUP || \
    (defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE)
    // These paths may deliberately remove/replace source geometry or use an
    // unproved transform policy. They retain ordinary drawing with this cell.
    ++declined;return;
#else
    if(!sources()){++source_declines;return;}
#if RE4DC_WORLD_PORTAL_COMPLETION
    completion_begin();
    receipts.sync(epoch[0],epoch[1],pc::wp29_generation,key);
    if(!completion_serial){++declined;return;}
#endif
    // Always rebuild from this pass's actual camera. Never borrow Trans actor
    // state or a previous frame's eye; current source receipts are separate.
    pc::setup(ps2w.view,P,near);
    const bool geometric=pc::st.active;pc::st.active=false;
    if(!geometric || !re4dc::pvsproof::numeric(numeric_cert,ps2w.view,P,ps2w.viewport,near,far,
         RE4DC_SCREEN_WF,RE4DC_SCREEN_HF,pc::st.eye,proof23::fpscr())){++declined;return;}
    valid=candidate=true;++admitted;
#endif
}
bool same_scene(){
    unsigned epoch[2];
#if RE4DC_WORLD_PORTAL_COMPLETION
    const bool current=valid && re4dc_pvs23_scene(epoch) && epoch[0]==view_frame && epoch[1]==scene &&
           pc::wp29_generation==receipts.generation && std::memcmp(ps2w.view,view_key,48)==0 &&
           std::memcmp(ps2w.projection,view_key+12,28)==0 && std::memcmp(ps2w.viewport,view_key+19,24)==0 &&
           completion_sources_current();
    if(!current){valid=false;receipts.clear();}
    return current;
#else
    return valid && re4dc_pvs23_scene(epoch) && epoch[0]==view_frame && epoch[1]==scene &&
           pc::wp29_generation==receipts.generation && std::memcmp(ps2w.view,view_key,48)==0 &&
           std::memcmp(ps2w.projection,view_key+12,28)==0 && std::memcmp(ps2w.viewport,view_key+19,24)==0;
#endif
}
bool witness(unsigned placement,unsigned part){
    if(!pc::wp29_witnesses)return false;
#if RE4DC_WORLD_PREPARED09
    return re4dc::portal29::witness_index(pc::wp29_witnesses,pc::wp29_count,placement,part)!=re4dc::portal29::kMaxWitnesses;
#else
    for(unsigned q=0;q<pc::wp29_count;++q){const auto& w=pc::wp29_witnesses[q];
        if(w.placement==placement && w.part==part)return true;}
    return false;
#endif
}
#if RE4DC_WORLD_PORTAL_COMPLETION
re4dc::portal29::Ticket capture(unsigned placement,unsigned part,const unsigned* key){
    if(!completion_serial || !same_scene() || !material_matches(part,key))return {};
#if RE4DC_WORLD_PREPARED09
    const unsigned q=re4dc::portal29::witness_index(pc::wp29_witnesses,pc::wp29_count,placement,part);
    if(q!=re4dc::portal29::kMaxWitnesses)return {completion_serial,q,placement,part};
#else
    for(unsigned q=0;q<pc::wp29_count;++q){const auto& w=pc::wp29_witnesses[q];
        if(w.placement==placement && w.part==part)return {completion_serial,q,placement,part};}

#endif
    return {};
}
void finish(const re4dc::portal29::Ticket& ticket,const re4dc::portal29::Completion& completion,const unsigned* key){
    if(!completion.witnessed() || !ticket.serial || ticket.serial!=completion_serial || !same_scene() ||
       !sources() || ticket.witness>=pc::wp29_count)return;
    const auto& w=pc::wp29_witnesses[ticket.witness];
    if(w.placement!=ticket.placement || w.part!=ticket.part || !material_matches(w.part,key) || std::memcmp(completion_keys[ticket.witness],key,6U*sizeof(unsigned)) ||
       !re4dc_pvs23_opaque_ready(key,re4dc::vp::kCacheSlots+64U))return;
    receipts.commit(ticket.witness);++commits;
}
#else
void finish(unsigned placement,unsigned part,bool success,const unsigned* key){
    if(!success || !same_scene() || !sources() || !re4dc_pvs23_opaque_ready(key,re4dc::vp::kCacheSlots+64U))return;
    for(unsigned q=0;q<pc::wp29_count;++q){const auto& w=pc::wp29_witnesses[q];
        if(w.placement==placement && w.part==part){receipts.commit(q);++commits;}}
}
#endif
// Called before each placement's portal test, outside any queued SQ ownership.
// A failed source part, gate change, package/movie generation or scene change
// removes culling immediately. No target order or source draw is rearranged.
void activate(){
    pc::st.active=false;
    if(!candidate || !same_scene() || !receipts.complete(pc::wp29_count)){++waits;return;}
    if(!sources()){receipts.clear();valid=false;++source_declines;return;}
    pc::st.active=true;
}
} // namespace wp29
