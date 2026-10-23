// Included once after the R4PV v1 loader, inside native_static's namespace.
// Generated proof certificates are private build inputs; absent means draw all.
extern "C" int re4dc_pvs23_scene(unsigned out[2]);
extern "C" int re4dc_pvs23_opaque_ready(const unsigned*,unsigned);
namespace proof23 {
using re4dc::pvsproof::Panel;using re4dc::pvsproof::Certificate;
#ifdef RE4DC_PVS23_CERTIFICATES
#include RE4DC_PVS23_CERTIFICATES
constexpr unsigned ncertificates=sizeof(certificates)/sizeof(certificates[0]);
#else
const Certificate* const certificates=nullptr;
constexpr unsigned ncertificates=0;
#endif
const Certificate* cert=nullptr;
re4dc::pvsproof::Receipts receipts;
float key[27]{};
unsigned checked_frame=~0U,checked_generation=~0U,checked_fpscr=~0U,commits=0;
bool valid=false;
unsigned fpscr(){
#if defined(__sh__)
    unsigned value;asm volatile("sts fpscr,%0":"=r"(value));return value;
#else
    return ~0U; // host architecture cannot qualify target arithmetic state
#endif
}
bool sources(){
    if(!cert || !valid || !ps2w.storage || checked_generation!=pvs::generation ||
       cert->room!=ps2w.room || !cert->npanels || cert->npanels>re4dc::pvsproof::kMaxPanels)return false;
    unsigned char fields[2U*re4dc::pvsproof::kMaxPanels];
    for(unsigned q=0;q<cert->npanels;++q){fields[2*q]=std::uint8_t(cert->panels[q].field);fields[2*q+1]=std::uint8_t(cert->panels[q].field>>8);}
    return re4dc_ps2_placements_intact(cert->room,fields,cert->npanels)!=0;
}
bool sync(unsigned epoch[2]){
    if(!sources() || !re4dc_pvs23_scene(epoch) || epoch[0]!=checked_frame){receipts.clear();return false;}
    receipts.sync(epoch[0],epoch[1],cert->room,pvs::generation,key);return true;
}
}
extern "C" int re4dc_pvs23_table_guard(unsigned room,const void* file,unsigned bytes,unsigned mesh_crc,unsigned mesh_bytes,unsigned policy_crc){
    using namespace proof23;
    cert=nullptr;valid=false;receipts.clear();checked_frame=checked_generation=~0U;
    if(!file)return 0;
    for(unsigned i=0;i<ncertificates;++i){
        const auto& c=certificates[i];
        if(c.room!=room || c.mesh_crc!=mesh_crc || c.mesh_bytes!=mesh_bytes || c.policy_crc!=policy_crc ||
           c.table_bytes!=bytes || c.table_crc!=ps2_crc32(static_cast<const unsigned char*>(file),bytes) ||
           !c.npanels || c.npanels>re4dc::pvsproof::kMaxPanels || !c.panels)continue;
        const auto& pk=ps2w.package;
        bool okay=pk.lod() && c.max_placement<ps2w.nplacements;
        for(unsigned q=0;q<c.npanels && okay;++q){
            const auto& panel=c.panels[q];
            okay=panel.placement<=c.max_placement && panel.placement<ps2w.nplacements && panel.field<65536U &&
                 panel.part<pk.header().part_count && panel.meshlet<pk.header().meshlet_count;
            if(!okay)break;
            const auto& pl=ps2w.placements[panel.placement];const auto& mesh=pk.meshes()[pl.mesh];
            const auto& part=ps2w.parts[panel.part];
            const auto& lod=pk.part_lods()[panel.part];
            okay=pl.placement==panel.field && panel.part>=mesh.first_part && panel.part<mesh.first_part+mesh.part_count &&
                 panel.cluster>=lod.first_cluster && panel.cluster-lod.first_cluster<lod.cluster_count &&
                 part.pass==0U && !(part.reserved&1U) && (part.cull==0U || part.cull==2U);
            if(!okay)break;
            const auto& cl=pk.clusters()[panel.cluster];
            if(cl.level_count!=1U){okay=false;break;}
            const auto& level=pk.levels()[cl.first_level];
            okay=panel.meshlet>=level.first_meshlet && panel.meshlet<level.first_meshlet+level.meshlet_count;
            for(unsigned corner:panel.corners)okay=okay && corner<pk.meshlets()[panel.meshlet].vertex_count;
        }
        if(okay){cert=&c;return 1;}
    }
    return 0;
}
extern "C" int re4dc_pvs23_frame_guard(unsigned room,const float* view,const float* projection,const float* viewport,float near,float far){
    using namespace proof23;
#if RE4DC_MESH_FASTPATH && RE4DC_MESH_DIRECT && RE4DC_MESH_VP_SCHED==1 && RE4DC_HW_LEAN && \
    RE4DC_SCENERY_CHUNK && !RE4DC_SCENERY_PIECE_STATE && !RE4DC_SCENERY_DEDUP && !RE4DC_SCENERY_CONE && \
    (!defined(RE4DC_CPU_BACKFACE) || !RE4DC_CPU_BACKFACE)
    if(!cert || room!=cert->room || !view || !projection || !viewport){valid=false;receipts.clear();return 0;}
    float current[27];std::memcpy(current,view,48);std::memcpy(current+12,projection,28);std::memcpy(current+19,viewport,24);
    current[25]=near;current[26]=far;
    const unsigned frame=re4dc_ui_frame(),control=fpscr();
    if(checked_frame!=frame || checked_generation!=pvs::generation || checked_fpscr!=control || std::memcmp(key,current,sizeof(key))){
        receipts.clear();std::memcpy(key,current,sizeof(key));checked_frame=frame;checked_generation=pvs::generation;checked_fpscr=control;
        float eye[3];
        valid=pvs::eye_of(view,eye) && re4dc::pvsproof::numeric(*cert,view,projection,viewport,near,far,
                                                            RE4DC_SCREEN_WF,RE4DC_SCREEN_HF,eye,control);
    }
    if(!sources()){receipts.clear();return 0;}
    return 1;
#else
    (void)room;(void)view;(void)projection;(void)viewport;(void)near;(void)far;
    valid=false;receipts.clear();return 0;
#endif
}
extern "C" void re4dc_pvs23_observe(unsigned placement,unsigned part,unsigned meshlet,const void* cache,const std::uint8_t* codes,unsigned count,
                                    const std::uint8_t* strips,unsigned bytes,unsigned cull,unsigned limit,unsigned pending[3]){
    using namespace proof23;
    if(!pending || !cert || !valid || !pvs::cur || re4dc_ps2_pvs_on!=1U)return;
    unsigned matching=0;
    for(unsigned q=0;q<cert->npanels;++q){const auto& p=cert->panels[q];if(p.placement==placement && p.part==part && p.meshlet==meshlet)matching|=1U<<q;}
    if(!matching)return;
    unsigned epoch[2];if(!sync(epoch))return;
    if(pending[0]!=epoch[0] || pending[1]!=epoch[1]){pending[0]=epoch[0];pending[1]=epoch[1];pending[2]=0;}
    for(unsigned q=0;q<cert->npanels;++q)if((matching>>q)&1U)
        if(re4dc::pvsproof::panel_sent(cert->panels[q],static_cast<const pvr_vertex_t*>(cache),codes,count,strips,bytes,cull,limit))pending[2]|=1U<<q;
}
extern "C" void re4dc_pvs23_commit(unsigned placement,unsigned part,const unsigned pending[3],const unsigned* key){
    using namespace proof23;
    unsigned epoch[2];
    if(!pending || !pending[2] || !sync(epoch) || pending[0]!=epoch[0] || pending[1]!=epoch[1] ||
       !re4dc_pvs23_opaque_ready(key,re4dc::vp::kCacheSlots+64U))return;
    unsigned accepted=0;
    for(unsigned q=0;q<cert->npanels;++q)if(((pending[2]>>q)&1U) && cert->panels[q].placement==placement && cert->panels[q].part==part)accepted|=1U<<q;
    receipts.committed|=accepted;if(accepted)++commits;
}
bool pvs::can_cut(unsigned placement){
    using namespace proof23;
    if(!cur || re4dc_ps2_pvs_on!=1U || !cert || placement<=cert->max_placement || placement>=ps2w.nplacements)return false;
    unsigned epoch[2];if(!sync(epoch) || !receipts.complete(cert->npanels))return false;
    const unsigned field=ps2w.placements[placement].placement;
    if(field>=65536U)return false;
    const unsigned char fields[2]={std::uint8_t(field),std::uint8_t(field>>8)};
    return re4dc_ps2_placements_intact(cert->room,fields,1)!=0;
}
extern "C" void re4dc_pvs23_receipt_state(unsigned out[5]){
    if(!out)return;
    out[0]=proof23::receipts.committed;
    out[1]=proof23::cert?(1U<<proof23::cert->npanels)-1U:0;
    out[2]=proof23::commits;out[3]=pvs::pl_skipped;out[4]=pvs::cl_skipped;
}
