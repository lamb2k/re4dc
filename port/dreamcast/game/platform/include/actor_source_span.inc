// Included inside uv32 in the production actor TU. The transaction publishes
// these spans only after immutable_chunk_proof and skin acquisition. No source
// mutation/conversion is allowed during that lease; replacement/re-LOD first
// revokes the lease. The never-reused skin serial is the borrow incarnation.
struct SpanKey {
    Re4dcActorSourceSpan span{};
    const void* info=nullptr;
    const u8* uv=nullptr;
    const u8* stream=nullptr;
    unsigned stream_bytes=0,positions=0,normals=0,flags=0;
};
struct SpanEntry { SpanKey key{};unsigned certificate=0; };
constexpr unsigned kSpanEntries=16;
SpanEntry span_entries[kSpanEntries];
static_assert(sizeof(void*)!=4 || sizeof(Re4dcActorSourceSpan)==32,"SH4 source span metadata");
static_assert(sizeof(void*)!=4 || sizeof(span_entries)==1024,"SH4 bounded span memo");
unsigned span_next,span_preparations,span_hits,span_records;

bool same_span_key(const SpanKey& a,const SpanKey& b) {
    const auto& x=a.span;const auto& y=b.span;
    return x.positions==y.positions && x.normals==y.normals &&
        x.position_bytes==y.position_bytes && x.normal_bytes==y.normal_bytes && x.uv_bytes==y.uv_bytes &&
        x.uv_encoding==y.uv_encoding && x.owner_serial==y.owner_serial && x.owner_frame==y.owner_frame &&
        a.info==b.info && a.uv==b.uv && a.stream==b.stream && a.stream_bytes==b.stream_bytes &&
        a.positions==b.positions && a.normals==b.normals && a.flags==b.flags;
}
bool span_owner_current(const Re4dcModelPart& p) {
    const auto& a=p.source_span;
    if(!a.owner_serial || a.owner_frame!=skin_frame)return false;
    const Re4dcActorSource* source=nullptr;
#if RE4DC_ACTOR_SKIN_OWNER_POOL
    for(unsigned i=0;i<owned_skin_high;++i) {
        const auto& e=owned_skins[i];
        if(e.serial==a.owner_serial && e.skin.info==p.info && !e.skin.materialized && owned_skin_source_valid(e)) {
            source=&e.source;break;
        }
    }
#else
    for(unsigned i=0;i<skin_count;++i) {
        const auto& e=owned_skins[i];const auto& s=skins[i];
        if(e.serial==a.owner_serial && e.info==p.info && s.info==e.info && !s.positions && !s.materialized &&
           s.palette==e.palette && s.entries==e.entries) {source=&e.source;break;}
    }
#endif
    return source && source->positions==a.positions && source->normals==a.normals && !source->small_normals &&
        source->position_count==p.position_count && source->normal_count==p.normal_count;
}
bool prepare_owned(const Re4dcModelPart& p,unsigned* certificate=nullptr) {
    using namespace re4dc::format32;
    const auto& a=p.source_span;
    // Owner validation precedes every source read, including a memo hit.
    if(!span_owner_current(p) || p.positions || p.normals || p.position_stride!=6 || p.normal_stride!=6 || p.normal_shift!=14 ||
       !p.stream || p.stream_bytes<sizeof(BlobHeader) || p.stream_bytes>1024*1024 ||
       (reinterpret_cast<std::uintptr_t>(p.stream)&3U) || !p.uv ||
       (reinterpret_cast<std::uintptr_t>(p.uv)&1U) ||
       (reinterpret_cast<std::uintptr_t>(a.positions)&1U) || (reinterpret_cast<std::uintptr_t>(a.normals)&1U) ||
       (a.uv_encoding!=Re4dcActorSourceSpan::U16Q15 && a.uv_encoding!=Re4dcActorSourceSpan::S16Q8) ||
       ((p.flags&0x80000000U)!=0)!=(a.uv_encoding==Re4dcActorSourceSpan::S16Q8) ||
       !p.position_count || p.position_count>65535 || !p.normal_count || p.normal_count>65535 ||
       a.position_bytes/8U<p.position_count || a.normal_bytes/8U<p.normal_count || !a.uv_bytes || (a.uv_bytes&3U) ||
       !ram(a.positions,a.position_bytes) || !ram(a.normals,a.normal_bytes) || !ram(p.uv,a.uv_bytes) ||
       !ram(p.stream,p.stream_bytes))return false;
    const SpanKey key{a,p.info,p.uv,p.stream,p.stream_bytes,p.position_count,p.normal_count,p.flags&0x80000000U};
    for(const auto& e:span_entries)if(same_span_key(e.key,key)) {
        ++span_hits;if(certificate)*certificate=e.certificate;return true;
    }
    ++span_preparations;
    const auto& b=*reinterpret_cast<const BlobHeader*>(p.stream);
    // Mutable bake/pending-LOD records and vertex-colour arrays need their
    // own authority. Do not turn this lease into permission to modify them.
    if(b.magic!=kMagic || b.version!=kVersion || (b.flags&(kHasCi|kHasBake|kLodPending)) ||
       !b.meshlets || b.levels>kMaxLevels || !re4dc::render::is_finite(b.radius) || b.radius<0)return false;
    for(float f:b.center)if(!re4dc::render::is_finite(f))return false;
    const unsigned rec=unsigned(b.rec4)*4U,idx=unsigned(b.idx4)*4U;
    if(rec<sizeof(BlobHeader) || b.meshlets>(rec-sizeof(BlobHeader))/sizeof(MeshletInfo) ||
       idx<rec || idx>p.stream_bytes)return false;
    const unsigned stride=3U,records=(idx-rec)/(stride*2U);
    const auto* table=reinterpret_cast<const MeshletInfo*>(p.stream+sizeof(BlobHeader));
    const auto* data=reinterpret_cast<const u16*>(p.stream+rec);
    const LevelInfo* levels=nullptr;
    if(b.levels) {
        const unsigned at=unsigned(b.lod4)*4U;
        if(at<idx || at>p.stream_bytes || b.levels>(p.stream_bytes-at)/sizeof(LevelInfo))return false;
        levels=reinterpret_cast<const LevelInfo*>(p.stream+at);
        for(unsigned l=0;l<b.levels;++l) {
            const unsigned at=unsigned(levels[l].table4)*4U,lists=unsigned(levels[l].lists4)*4U;
            if(at<idx || at>p.stream_bytes || b.meshlets>(p.stream_bytes-at)/sizeof(MeshletLevel) ||
               lists<idx || lists>p.stream_bytes || !re4dc::render::is_finite(levels[l].error) || levels[l].error<0)return false;
        }
    }
    auto list_valid=[&](Counts n,unsigned lists,unsigned at) {
        const unsigned nv=n.vertices(),ni=n.indices();
        if(!nv && !ni && !n.triangles())return true;
        if(!nv || nv>kMaxVertices || !ni || ni>kMaxIndices || lists>p.stream_bytes ||
           at>p.stream_bytes-lists || ni>p.stream_bytes-lists-at)return false;
        unsigned length=0,triangles=0;
        for(unsigned j=0;j<ni;++j) {
            const unsigned v=p.stream[lists+at+j];
            if((v&127U)>=nv || ++length>kMaxStrip)return false;
            if(v&128U) {if(length<3)return false;triangles+=length-2;length=0;}
        }
        return !length && triangles==n.triangles();
    };
    const unsigned code=uv_excess_bits(b),exponent=uv_certificate_exponent(code);
    unsigned checked_code=code;
    for(unsigned m=0;m<b.meshlets;++m) {
        const auto& t=table[m];const unsigned count=t.n.vertices(),first=t.first;
        if(!count || count>kMaxVertices || first>records || count>records-first || !list_valid(t.n,idx,t.index))return false;
        for(unsigned v=0;v<count;++v) {
            const auto* r=data+(first+v)*stride;++span_records;
            if(r[0]>=p.position_count || r[1]>=p.normal_count || unsigned(r[2])>=a.uv_bytes/4U)return false;
        }
        // All stored LODs are checked now, including levels not selected by
        // this camera. Every transformed LOD record must be a level-zero prefix.
        for(unsigned l=0;l<b.levels;++l) {
            const auto& t1=reinterpret_cast<const MeshletLevel*>(p.stream+unsigned(levels[l].table4)*4U)[m];
            if(t1.n.vertices()>count || !list_valid(t1.n,unsigned(levels[l].lists4)*4U,t1.index))return false;
        }
        if(exponent && !uv_record_range(exponent,data+first*stride,stride,count,p.uv,
            a.uv_encoding==Re4dcActorSourceSpan::S16Q8,counters.scanned_records,a.uv_bytes))checked_code=kUvSourceDeclined;
    }
    span_entries[span_next++%kSpanEntries]={key,checked_code};
    if(certificate)*certificate=checked_code;
    return true;
}
