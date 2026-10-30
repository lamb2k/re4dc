// Only the already-live shared-table skin lease can retain a prepared table.
// The existing acquire/release/primitive-retirement fences still invalidate
// every Frame. No raw palette pointer alone extends that lifetime.
#if !RE4DC_ACTOR_TRANSACTION || RE4DC_ACTOR_SKIN_OWNER_POOL
#error ACTOR_TABLE_REUSE14 requires the existing shared-table actor transaction
#endif
const OwnedSkin* table14_owner(const void* info) {
    if(skin_frame==~0u)return nullptr;
    for(unsigned i=0;i<skin_count;++i){const auto& o=owned_skins[i];const auto& e=skins[i];
        if(o.serial && o.info==info && e.info==info && !e.positions && !e.materialized &&
           e.palette==o.palette && e.entries==o.entries)return &o;
    }
    return nullptr;
}
bool table14_current(const Frame& f,const Re4dcModelPart& p) {
    // Unretained source frames keep the original single-table hit policy.
    if(f.mode!=kSkin || !f.table_owner14)return true;
    const auto* o=table14_owner(p.info);
    return o && f.table_owner14==o->serial && f.table_source_frame14==skin_frame &&
        f.palette==o->palette && f.palette_entries==o->entries &&
        f.positions==o->source.positions && f.normals==o->source.normals &&
        f.position_count==p.position_count && f.normal_count==p.normal_count &&
        f.position_count==o->source.position_count && f.normal_count==o->source.normal_count &&
        f.small_normals==bool(o->source.small_normals) && f.small_normals==(p.normal_shift==6) &&
        f.q==pow2(-int(p.shift)) && f.nq==pow2(-int(p.normal_shift));
}
void table14_prepare(Frame& f,const Re4dcModelPart& p,unsigned entries) {
    const auto* o=table14_owner(p.info);
    const bool owned=o && o->entries==entries && entries && entries<=256 &&
        f.palette==o->palette && f.positions==o->source.positions && f.normals==o->source.normals;
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
    const unsigned bytes=(entries*65u+31u)&~31u;
#else
    const unsigned bytes=(entries*114u+31u)&~31u;
#endif
    // Retention fits INSIDE the workspace amount already reserved by the
    // ordinary owner. It cannot reduce the existing scratch limit or borrow
    // another region of the primitive buffer. Holes from Frame victim reuse
    // remain charged until the ordinary single-table fallback resets them.
    const unsigned reserved=owned_workspace.maximum();
    const unsigned used=workspace_end<=workspace_bytes?workspace_bytes-workspace_end:~0u;
    bool retain=owned && bytes<=reserved && used<=reserved-bytes &&
        workspace_top<=workspace_end && bytes<=workspace_end-workspace_top;
    for(const auto& old:frames)if(&old!=&f && old.skin_positions &&
        (!owned || old.frame!=frame_serial || old.table_owner14!=o->serial || old.table_source_frame14!=skin_frame))retain=false;
    if(!retain){
        for(auto& old:frames)if(&old!=&f && old.skin_positions){
            old.frame=~0u;old.skin_positions=old.skin_dirs=nullptr;old.skin_ready=old.dirs_ready=nullptr;
        }
        workspace_end=workspace_bytes;
    }
    f.table_owner14=owned?o->serial:0;f.table_source_frame14=skin_frame;
}
