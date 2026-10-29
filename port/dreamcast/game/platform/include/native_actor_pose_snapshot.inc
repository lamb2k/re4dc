// Existing source primitive allocation + existing WorkspaceReservations ticket.
// No palette/snapshot pointer is read before its out-of-band ticket validates.
struct NativePoseSnapshot {
    re4dc_source::ChunkInput input;
    const void* info;
    unsigned asset,source_frame;
};
struct NativeContinuationProgress {
    re4dc::NativeDrawResult result{re4dc::NativeDrawOutcome::UnsupportedBeforePublication};
    bool header=false;
};
void native_refused(NativeContinuationProgress* p) {
    if(p)p->result.outcome=p->header || p->result.published()
        ?re4dc::NativeDrawOutcome::PartialAbort:re4dc::NativeDrawOutcome::Refused;
}
constexpr unsigned pose_header_bytes=(sizeof(NativePoseSnapshot)+31U)&~31U;
static_assert(sizeof(void*)!=4 || sizeof(NativePoseSnapshot)==72,"SH4 exact source/pose descriptor");
static_assert(sizeof(void*)!=4 || ((pose_header_bytes+27U*48U+31U)&~31U)==1408,"current 27-palette portrait allocation");
const float* pose_palette(const NativePoseSnapshot& p) {
    return reinterpret_cast<const float*>(reinterpret_cast<const u8*>(&p)+pose_header_bytes);
}
const NativePoseSnapshot* native_pose_of(const Re4dcModelPart& p) {
    const auto& t=p.native_pose_lease;
    Re4dcActorStreamState stream{};
    if(!p.native_pose || !re4dc_actor_stream_state(&stream) || !re4dc_actor_workspace_validate(&t) ||
       !owned_workspace.bound(t,frame_serial,p.native_pose) || t.bytes<pose_header_bytes+48U)return nullptr;
    const auto* s=static_cast<const NativePoseSnapshot*>(p.native_pose);
    const auto& c=s->input;
    if(!c.palette_count || c.palette_count>256 ||
       ((pose_header_bytes+c.palette_count*48U+31U)&~31U)!=t.bytes || s->info!=p.info ||
       c.positions.data!=p.source_span.positions || c.normals.data!=p.source_span.normals ||
       c.positions.size!=p.source_span.position_bytes || c.normals.size!=p.source_span.normal_bytes ||
       c.uv.data!=p.uv || c.uv.size!=p.source_span.uv_bytes || c.stream.data!=p.stream || c.stream.size!=p.stream_bytes ||
       c.position_count!=p.position_count || c.normal_count!=p.normal_count ||
       p.source_span.owner_serial!=t.serial || p.source_span.owner_frame!=t.epoch ||
       p.source_span.uv_encoding!=Re4dcActorSourceSpan::U16Q15 || (p.flags&0x80000000U))return nullptr;
    re4dc_source::ChunkProof proof{};
    if(re4dc_actor_immutable_chunk_proof(s->asset,c,proof)!=re4dc_source::BlobError::None)return nullptr;
    return s;
}
extern "C" int re4dc_actor_native_pose_acquire(Re4dcModelPart* p,unsigned asset,
    const re4dc_source::ChunkInput* input,const float* palette,unsigned palette_bytes,unsigned source_frame) {
    // First capability is the compiled single-material portrait hair only.
    // Mutable package/LOD geometries need their own lifetime authority.
    if(!p || !input || !palette || p->native_pose || p->native_pose_lease.serial ||
       asset<29U || asset>42U || !input->palette_count || input->palette_count>256 ||
       input->positions.size>UINT32_MAX || input->normals.size>UINT32_MAX || input->uv.size>UINT32_MAX || input->stream.size>UINT32_MAX ||
       palette_bytes!=input->palette_count*48U || !ram(palette,palette_bytes) ||
       (p->flags&0x80000000U) || p->positions || p->normals)return 0;
    re4dc_source::ChunkProof proof{};
    if(re4dc_actor_immutable_chunk_proof(asset,*input,proof)!=re4dc_source::BlobError::None)return 0;
    for(unsigned i=0;i<input->palette_count*12U;++i)if(!re4dc::render::is_finite(palette[i]))return 0;
    const unsigned bytes=(pose_header_bytes+input->palette_count*48U+31U)&~31U;
    Re4dcActorWorkspaceLease lease{};
    if(!re4dc_actor_workspace_acquire(bytes,&lease))return 0;
    void* memory=re4dc_prim_tail(bytes,16U*1024U);
    if(!memory || !owned_workspace.bind(lease,frame_serial,memory,bytes)) {
        re4dc_actor_workspace_release(&lease);return 0;
    }
    // Source Frame_cnt is retained with the actual weighted pose. Authority is
    // the primitive/render-frame allocation epoch, not the optional skin table.
    auto* snapshot=::new(memory) NativePoseSnapshot{*input,p->info,asset,source_frame};
    std::memcpy(const_cast<float*>(pose_palette(*snapshot)),palette,input->palette_count*48U);
    p->native_pose=memory;p->native_pose_lease=lease;
    p->source_span={input->positions.data,input->normals.data,unsigned(input->positions.size),
        unsigned(input->normals.size),unsigned(input->uv.size),Re4dcActorSourceSpan::U16Q15,lease.serial,lease.epoch};
    if(!native_pose_of(*p)){re4dc_actor_workspace_release(&lease);p->native_pose=nullptr;p->native_pose_lease={};return 0;}
    return 1;
}
extern "C" void re4dc_actor_native_pose_release(const Re4dcModelPart* p) {
    if(p){auto lease=p->native_pose_lease;re4dc_actor_workspace_release(&lease);}
}
extern "C" void re4dc_actor_native_pose_retire(){owned_workspace.retire_bound();}
