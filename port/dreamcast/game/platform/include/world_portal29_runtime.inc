// Included after ps2w, dynamic/AREA/gate state and PVS proof services.
// Portal geometry is static; permission to use it is current-image evidence.
namespace wp29 {
re4dc::portal29::Receipts receipts;
re4dc::pvsproof::Certificate numeric_cert{};
unsigned validated_generation=~0U,view_frame=~0U,scene=~0U;
unsigned admitted=0,declined=0,commits=0,source_declines=0,scene_declines=0,waits=0;
bool valid=false,candidate=false;
float view_key[27]{};

bool sources(){
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
    return valid && re4dc_pvs23_scene(epoch) && epoch[0]==view_frame && epoch[1]==scene &&
           pc::wp29_generation==receipts.generation && std::memcmp(ps2w.view,view_key,48)==0 &&
           std::memcmp(ps2w.projection,view_key+12,28)==0 && std::memcmp(ps2w.viewport,view_key+19,24)==0;
}
bool witness(unsigned placement,unsigned part){
    if(!pc::wp29_witnesses)return false;
    for(unsigned q=0;q<pc::wp29_count;++q){const auto& w=pc::wp29_witnesses[q];
        if(w.placement==placement && w.part==part)return true;}
    return false;
}
void finish(unsigned placement,unsigned part,bool success,const unsigned* key){
    if(!success || !same_scene() || !sources() || !re4dc_pvs23_opaque_ready(key,re4dc::vp::kCacheSlots+64U))return;
    for(unsigned q=0;q<pc::wp29_count;++q){const auto& w=pc::wp29_witnesses[q];
        if(w.placement==placement && w.part==part){receipts.commit(q);++commits;}}
}
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
