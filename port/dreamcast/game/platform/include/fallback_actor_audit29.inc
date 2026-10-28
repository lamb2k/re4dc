// Included in native_actor_fast.cpp after Lights and the part-light dispatcher.
// This records source context and the selected path; it does not pick lights.
re4dc::fa29actor::State fa29_actor_rows{};
extern "C" void re4dc_fa29_actor_identity(const Re4dcModelPart*, unsigned*, unsigned*, unsigned*);

re4dc::fa29actor::Key fa29_actor_key(const Re4dcModelPart& p) {
    return {reinterpret_cast<uintptr_t>(p.model),reinterpret_cast<uintptr_t>(p.info),
            reinterpret_cast<uintptr_t>(p.part),p.serial};
}
unsigned fa29_rgba(const unsigned char* c) {
    return (unsigned(c[0])<<24)|(unsigned(c[1])<<16)|(unsigned(c[2])<<8)|unsigned(c[3]);
}
void fa29_actor_note(const Re4dcModelPart& p, const Lights& lights) {
    if (!re4dc::fa29::collecting() || !p.lighting) return;
    const SourceLighting& s=*p.lighting;
    unsigned path=lights.constant?3U:lights.fast?1U:2U;
#if RE4DC_ACTOR_PROBE_LIGHT
    if (!lights.constant && lights.probe) path=0;
#endif
    // The bounded attribution table is for declined probes / exact lighting,
    // not successful probes or trivial unlit constants. Existing DFA totals
    // continue to account for every other submitted path.
    if (path==0 || (!s.enable && path!=2)) return;
    re4dc::fa29actor::Context c{};
    c.material=fa29_rgba(s.material); c.ambient=fa29_rgba(s.ambient);
    std::memcpy(&c.tev_bits,&s.tev_scale,sizeof(c.tev_bits));
    c.controls=(s.enable?1U:0U)|(s.ambient_vertex?2U:0U)|(s.material_vertex?4U:0U)|
        ((s.diffuse&255U)<<8)|((s.attenuation&255U)<<16)|
        (s.normal_matrix[3]==1.0e30f?0x01000000U:0U)|
        (s.normal_matrix[7]==1.0e30f?0x02000000U:0U);
    c.light_mask=s.mask;
    bool fresh=false;
    const unsigned index=re4dc::fa29actor::observe(fa29_actor_rows,fa29_actor_key(p),c,path,&fresh);
    if (fresh) {
        auto& id=fa29_actor_rows.rows[index].id;
        re4dc_fa29_actor_identity(&p,&id.tag,&id.info_index,&id.part_offset);
        id.positions=p.position_count; id.normals=p.normal_count; id.stream_bytes=p.stream_bytes;
        id.source_key=fa29_rgba(p.source_key); id.material_flags=p.material_flags;
    }
}
void fa29_actor_exact_vertices(const Re4dcModelPart& p, unsigned count) {
    if (!re4dc::fa29::collecting()) return;
    re4dc::fa29actor::vertices(fa29_actor_rows,fa29_actor_key(p),count);
}
} // anonymous namespace: export only the diagnostic formatter/lifecycle API
extern "C" void re4dc_fa29_actor_reset() { fa29_actor_rows=re4dc::fa29actor::State{}; }
extern "C" unsigned re4dc_fa29_actor_line_count() { return re4dc::fa29actor::line_count(fa29_actor_rows); }
extern "C" int re4dc_fa29_actor_format_line(unsigned row,char* out,unsigned cap) {
    return re4dc::fa29actor::format_line(fa29_actor_rows,row,out,cap);
}
namespace {
