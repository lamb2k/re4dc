// Same native records/positions/lighting/clip/packet emitter as actor submission.
// The explicit current-pose snapshot removes skin-registry-slot admission, not
// a material/light/format predicate. It is never interpreted by the GX walker.
extern "C" re4dc::NativeDrawResult re4dc_actor_native_submit_result(const Re4dcModelPart* p,unsigned replay) {
    using re4dc::NativeDrawOutcome;
    NativeContinuationProgress progress;
    if(replay)progress.result.queued=1; // the existing queue already accepted ownership
    const NativePoseSnapshot* snapshot=p?native_pose_of(*p):nullptr;
    if(!snapshot || !uv32::prepare_owned(*p)) {
        native_refused(&progress);
        if(progress.result.outcome==NativeDrawOutcome::PartialAbort)re4dc_model_packet_abort();
        if(p)re4dc_actor_native_pose_release(p);
        re4dc_model_result(1,0,0);return progress.result;
    }
    const float near=p->projection[6]/(p->projection[5]-1.0f),far=p->projection[6]/p->projection[5];
    bool finite=true;
    for(float v:p->modelview)finite=finite && re4dc::render::is_finite(v);
    for(float v:p->projection)finite=finite && re4dc::render::is_finite(v);
    for(float v:p->viewport)finite=finite && re4dc::render::is_finite(v);
    Re4dcModelPacket preflight{};
    if(!finite || !qualifies(*p,true) || !re4dc::render::is_finite(near) || !re4dc::render::is_finite(far) ||
       near<=0 || far<=near || (p->cull!=3 && !re4dc_model_packet_reserve(p,&preflight))) {
        native_refused(&progress);
        if(progress.result.outcome==NativeDrawOutcome::PartialAbort)re4dc_model_packet_abort();
        re4dc_actor_native_pose_release(p);re4dc_model_result(2,0,0);return progress.result;
    }
    if(p->cull==3){re4dc_actor_native_pose_release(p);return {NativeDrawOutcome::Culled};}
    if(!replay) {
        re4dc::NativeDrawResult deferred{NativeDrawOutcome::UnsupportedBeforePublication};
        if(re4dc_model_defer_native_result(p,&deferred)) {
            if(deferred.outcome!=NativeDrawOutcome::Queued)re4dc_actor_native_pose_release(p);
            return deferred;
        }
    }
    Frame f{};f.info=p->info;f.frame=frame_serial;f.mode=kSkin;f.q=pow2(-int(p->shift));
    f.positions=snapshot->input.positions.data;f.position_stride=8;f.position_count=p->position_count;
    f.normals=snapshot->input.normals.data;f.normal_stride=8;f.normal_count=p->normal_count;
    f.small_normals=false;f.nq=pow2(-int(p->normal_shift));f.palette=pose_palette(*snapshot);
    f.palette_entries=snapshot->input.palette_count;f.near_distance=near;f.far_distance=far;
    std::memcpy(f.modelview,p->modelview,sizeof(f.modelview));std::memcpy(f.projection,p->projection,sizeof(f.projection));
    std::memcpy(f.viewport,p->viewport,sizeof(f.viewport));
    float matrix[3][4];screen_rows(*p,matrix);
    for(unsigned c=0;c<4;++c) {
        f.screen[c*4]=matrix[0][c];f.screen[c*4+1]=matrix[1][c];
        f.screen[c*4+2]=f.screen[c*4+3]=matrix[2][c];
    }
    // No skin table is required: pass_positions already completes an AVK miss
    // with position_matrix + positions_asm/positions_c on this exact pose.
    if(!actor_submit_impl(p,&f,&progress))native_refused(&progress);
    if(progress.result.outcome==NativeDrawOutcome::PartialAbort)re4dc_model_packet_abort();
    re4dc_actor_native_pose_release(p);
    return progress.result;
}
