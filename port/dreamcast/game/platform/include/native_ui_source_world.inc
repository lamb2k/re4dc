// Ordinary fenced cache loading and the ordinary current-frame pin. No scene,
// queue, actor lease, preload priority or persistent residency policy changes.
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
extern "C" void re4dc_source_world_diag_begin(unsigned);
extern "C" int re4dc_source_world_diag_active(unsigned);
extern "C" void re4dc_source_world_diag_report(unsigned,const char*);
extern "C" void re4dc_vram_pages_census(unsigned*);
extern "C" unsigned re4dc_vram_pages_snapshot(unsigned*,unsigned*,unsigned,unsigned*,unsigned*);
#endif
namespace {
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
// Four largest free gaps, each with the exact adjacent allocated blocks. Pure
// metadata: no VRAM reads, borrowed source dereferences, allocations or probes.
struct SourceWorldDiagGap { unsigned begin=0,bytes=0;int left=-1,right=-1; };
bool sourceWorldDiagGaps(const unsigned* off,const unsigned* len,unsigned n,unsigned pool,
                        unsigned allocated,SourceWorldDiagGap (&gaps)[4],unsigned& free) {
    if(n>512 || n!=allocated)return false;
    unsigned cursor=0;free=0;
    for(unsigned i=0;i<=n;++i){
        const unsigned end=i<n?off[i]:pool;
        if(end<cursor || end>pool || (i<n && (!len[i] || len[i]>pool-end)))return false;
        SourceWorldDiagGap gap{cursor,end-cursor,i?int(i-1):-1,i<n?int(i):-1};
        free+=gap.bytes;
        for(auto& g:gaps)if(gap.bytes>g.bytes || (gap.bytes && gap.bytes==g.bytes && gap.begin<g.begin)){const auto old=g;g=gap;gap=old;}
        if(i<n)cursor=end+len[i];
    }
    return true;
}
int sourceWorldDiagEntry(unsigned address) {
    int owner=-1;
    for(unsigned i=0;i<kTextureCount;++i){
        const auto& e=entries[i];
        if(!e.valid || e.package.header().texture_count!=1 || !e.package.pvr_texture(0))continue;
        if(std::uintptr_t(e.package.pvr_texture(0))==address){if(owner!=-1)return -2;owner=int(i);}
    }
    return owner;
}
void sourceWorldDiagBlock(const char* where,unsigned gap,const char* side,int block,
                          unsigned base,const unsigned* off,const unsigned* len) {
    if(block<0)return;
    const int index=sourceWorldDiagEntry(base+off[block]);
    const Entry* e=index>=0?&entries[index]:nullptr;
    re4dc_log("PS2PF neighbor f=%u where=%s gap=%u side=%s off=%x bytes=%u entry=%d key=%08x-%08x framepin=%u pinned=%u age=%u\n",
        frame,where,gap,side,off[block],len[block],index,e?e->key.crc:0U,e?e->key.fnv:0U,
        e?unsigned(e->frame==frame):0U,e?unsigned(RE4DC_ENTRY_PINNED(*e)):0U,e?frame-e->frame:0U);
}
void sourceWorldDiagSnapshot(const char* where) {
    if(!re4dc_source_world_diag_active(frame))return;
    constexpr unsigned kCap=512;
    static unsigned off[kCap],len[kCap];
    unsigned base=0,pool=0,c[13]={},resident=0,pinned=0,pinned_bytes=0;
    const unsigned n=re4dc_vram_pages_snapshot(off,len,kCap,&base,&pool);
    re4dc_vram_pages_census(c);
    for(const auto& e:entries)if(e.valid){++resident;if(RE4DC_ENTRY_PINNED(e)){++pinned;pinned_bytes+=e.package.vram_bytes();}}
    const unsigned flags=unsigned(frame_ready)|unsigned(stream_scene)<<1|unsigned(stream_retire)<<2|
        unsigned(stream_aborted)<<3|unsigned(direct_open)<<4;
    re4dc_log("PS2PF vram f=%u where=%s flags=%x claims=%u resident=%u pinned=%u/%u used=%u alloc=%u/%u free=%u largest=%u extents=%u failures=%u base=%08x pool=%u\n",
        frame,where,flags,vram_claims,resident,pinned,pinned_bytes,used,c[0],c[1],c[3],c[4],c[2],c[10],base,pool);
    SourceWorldDiagGap gaps[4]{};unsigned free=0;
    const bool valid=base && pool<=~0U-base && sourceWorldDiagGaps(off,len,n,pool,c[0],gaps,free) && free==c[3];
    if(!valid){re4dc_log("PS2PF map-invalid f=%u where=%s copied=%u alloc=%u derived_free=%u\n",frame,where,n,c[0],free);return;}
    for(unsigned i=0;i<4;++i)if(gaps[i].bytes){
        const auto& g=gaps[i];const unsigned address=base+g.begin;
        const unsigned padding=(2048U-(address&2047U))&2047U;
        re4dc_log("PS2PF gap f=%u where=%s rank=%u off=%x bytes=%u aligned=%u\n",
            frame,where,i,g.begin,g.bytes,g.bytes>padding?g.bytes-padding:0U);
        sourceWorldDiagBlock(where,i,"left",g.left,base,off,len);
        sourceWorldDiagBlock(where,i,"right",g.right,base,off,len);
    }
    int target=-1;
    for(unsigned i=0;i<kTextureCount;++i)if(entries[i].valid && entries[i].key.crc==0xfa6fe38cU && entries[i].key.fnv==0x1a02365fU){target=int(i);break;}
    const Entry* e=target>=0?&entries[target]:nullptr;
    re4dc_log("PS2PF target f=%u where=%s entry=%d bytes=%u address=%08x complete=%u framepin=%u pinned=%u\n",
        frame,where,target,e?unsigned(e->package.vram_bytes()):0U,e?unsigned(std::uintptr_t(e->package.pvr_texture(0))):0U,
        e?unsigned(e->package.upload_complete()):0U,e?unsigned(e->frame==frame):0U,e?unsigned(RE4DC_ENTRY_PINNED(*e)):0U);
}
void sourceWorldDiagBind(const Key& key) {
    static unsigned last=0;static bool seen=false;
    if(key.crc!=0xfa6fe38cU || key.fnv!=0x1a02365fU || !re4dc_source_world_diag_active(frame) || (seen && last==frame))return;
    seen=true;last=frame;sourceWorldDiagSnapshot("fa6-bind");
    re4dc_source_world_diag_report(frame,"fa6-bind");
}
#endif
#if RE4DC_PS2_WORLD_SOURCE_TEX_PREP
Key sourceWorldPreparedKey{};unsigned sourceWorldPreparedFrame,sourceWorldAcquired;
#if RE4DC_PS2_PVS_BATCH_COMPOSE
// One source preparation ticket, one captured diagnostic. No ring/heap or
// alternate Acquired value: live bookkeeping remains exactly 0 or 1.
struct SourceWorldAcquireDiagnostic { Key key{};unsigned frame=0;bool pending=false; } sourceWorldAcquireDiagnostic;
bool sourceWorldDiagnosticSqHeld=false;
bool sourceWorldTextureFlushAcquired() {
    // direct_open alone is insufficient: a logical end can retain batch SQ.
    if(direct_open || sourceWorldDiagnosticSqHeld)return false;
    auto& d=sourceWorldAcquireDiagnostic;
    if(d.pending){
        const Key key=d.key;const unsigned old_frame=d.frame;d.pending=false;
        re4dc_log("PS2SOURCE_TEX_ACQUIRE f=%u key=%08x-%08x\n",old_frame,key.crc,key.fnv);
    }
    return true;
}
#endif
void sourceWorldTextureAcquired(const Key& key) {
    if(frame!=sourceWorldPreparedFrame || !(key==sourceWorldPreparedKey) || sourceWorldAcquired)return;
#if RE4DC_PS2_PVS_BATCH_COMPOSE
    // A second preparation cannot overwrite an undelivered old event. Normal
    // prepare flushes before replacing its ticket; unsupported reentry refuses.
    if(sourceWorldAcquireDiagnostic.pending)return;
#endif
    sourceWorldAcquired=1;
#if RE4DC_PS2_PVS_BATCH_COMPOSE
    sourceWorldAcquireDiagnostic={key,frame,true};
#else
    re4dc_log("PS2SOURCE_TEX_ACQUIRE f=%u key=%08x-%08x\n",frame,key.crc,key.fnv);
#endif
}
#endif
#if (defined(RE4DC_PS2_WORLD_SOURCE_TEX_MIP) && RE4DC_PS2_WORLD_SOURCE_TEX_MIP) || defined(RE4DC_CAST_MIPMAP) // host fixture (mipmap23 test)
#define RE4DC_SOURCE_TEX_MIP_PREP 1
// Source-world identity and ownership are checked by the caller. Match its
// resident representation, not just the pre-mip source byte count. Package
// validation has no exported layout-size helper: keep its bounded full-codebook
// VQ index sum here rather than widening the texture loader's shared API.
bool sourceWorldTextureBytesOk(const Entry& entry,const Re4dcSourceWorldTexture& pick) {
    namespace tx=re4dc::texture;
    const auto& package=entry.package;
    const auto& t=package.textures()[0];
    if(t.width!=pick.width || t.height!=pick.height ||
       t.width<8U || t.width>1024U || t.height<8U || t.height>1024U ||
       (t.width&(t.width-1U)) || (t.height&(t.height-1U)) ||
       t.format>tx::kArgb4444 || t.reserved_0 ||
       (t.flags&~(tx::kAlpha|tx::kBinaryAlpha|tx::kMipmap)))return false;
    const std::uint64_t pixels=std::uint64_t(t.width)*t.height;
    std::uint64_t expected=pick.bytes;
    if(t.flags&tx::kMipmap) {
#if defined(RE4DC_PS2_WORLD_SOURCE_TEX_VQ) && RE4DC_PS2_WORLD_SOURCE_TEX_VQ && ((defined(RE4DC_CAST_MIPMAP) && RE4DC_CAST_MIPMAP) || (defined(RE4DC_PS2_WORLD_SOURCE_TEX_MIP) && RE4DC_PS2_WORLD_SOURCE_TEX_MIP))
        if(t.payload!=tx::kPayloadVq || t.width!=t.height)return false;
        // Package::validate: one 1x1 index, then one index for each 2x2
        // block at every level through the base, after the 2048-byte book.
        std::uint64_t indices=1U;
        for(unsigned side=2U;side<=t.width;side<<=1U)
            indices+=std::uint64_t(side/2U)*(side/2U);
        expected=2048U+indices;
#else
        return false;
#endif
    } else if(t.payload==tx::kPayloadVq) {
#if defined(RE4DC_PS2_WORLD_SOURCE_TEX_VQ) && RE4DC_PS2_WORLD_SOURCE_TEX_VQ
        expected=2048U+pixels/4U;
#else
        return false;
#endif
    } else if((t.payload!=tx::kPayloadLinear && t.payload!=tx::kPayloadTwiddled) ||
              expected!=pixels*2U)return false;
    return t.data_size==expected && package.vram_bytes()==expected;
}
#define RE4DC_SOURCE_TEX_OK(e,p) sourceWorldTextureBytesOk((e),(p))
#else
// Knob off (PS2_WORLD_SOURCE_TEX_MIP=0): the Test 22 size check, unchanged.
#if defined(RE4DC_PS2_WORLD_SOURCE_TEX_VQ) && RE4DC_PS2_WORLD_SOURCE_TEX_VQ
#define RE4DC_SOURCE_TEX_BYTES_OK(v,p) ((v)==(p).bytes || (v)==2048U+(p).width*(p).height/4U)
#else
#define RE4DC_SOURCE_TEX_BYTES_OK(v,p) ((v)==(p).bytes)
#endif
#define RE4DC_SOURCE_TEX_OK(e,p) RE4DC_SOURCE_TEX_BYTES_OK((e).package.vram_bytes(),(p))
#endif
#if RE4DC_PS2_WORLD_TRANSITION_PIN
void sourceWorldTransitionPin() {
    if(!frame_ready || stream_scene || stream_retire || stream_aborted || direct_open || vram_claims)return;
    unsigned generation=0;
    if(!re4dc_ps2_source_package(&generation) || !re4dc_source_world_transition(frame,generation))return;
    Re4dcSourceWorldTexture pick{};
    if(!re4dc_ps2_source_texture(generation,&pick) || pick.generation!=generation)return;
    const Key key{pick.crc,pick.fnv};Entry* selected=nullptr;
    // Own cache slots only. Missing, duplicate or incomplete residency never
    // loads a file, acquires VRAM, releases an upload or keeps a borrowed pointer.
    for(auto& e:entries)if(e.valid && e.key==key){if(selected)return;selected=&e;}
    if(!selected || !selected->package.upload_complete() ||
       selected->package.header().texture_count!=1 || !selected->package.pvr_texture(0) ||
       !RE4DC_SOURCE_TEX_OK(*selected,pick) ||
       selected->package.textures()[0].width!=pick.width || selected->package.textures()[0].height!=pick.height)return;
    unsigned current=0;
    if(!re4dc_ps2_source_package(&current) || current!=generation || !re4dc_source_world_transition(frame,current))return;
    // Same pin as an ordinary cache hit, expiring at the next native frame.
    selected->frame=frame;
    static unsigned reports=0;
    if(reports++<16 || !(frame%120))re4dc_log("PS2TRANSITION_PIN f=%u gen=%u key=%08x-%08x bytes=%u\n",frame,generation,key.crc,key.fnv,pick.bytes);
}
#endif
void sourceWorldTexturePrepare() {
#if RE4DC_PS2_PVS_BATCH_COMPOSE
    // Sole normal caller is frame begin, after the previous synchronous draw
    // and SubmitScope have retired. Preserve the live ticket on unsupported
    // reentry; this is NOT a new source-admission or manager-revocation API.
    if(!sourceWorldTextureFlushAcquired())return;
#endif
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
    re4dc_source_world_diag_begin(frame);sourceWorldDiagSnapshot("preflight");
#endif
#if RE4DC_PS2_WORLD_SOURCE_TEX_PREP
    if(sourceWorldPreparedFrame)re4dc_log("PS2SOURCE_TEX_USED f=%u acquired=%u\n",sourceWorldPreparedFrame,sourceWorldAcquired);
    sourceWorldPreparedFrame=0;sourceWorldAcquired=0;
#endif
    // Also call prepare with an unusable frame to retire any previous ticket.
    unsigned generation=0;
    const int admitted=re4dc_source_world_prepare(frame,&generation);
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
    re4dc_source_world_diag_report(frame,"preflight-result");
#endif
    if(!admitted){
#if RE4DC_PS2_WORLD_TRANSITION_PIN
        sourceWorldTransitionPin();
#endif
        return;
    }
    if(!frame_ready || stream_scene || stream_retire || stream_aborted || direct_open || vram_claims){
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
        if(re4dc_source_world_diag_active(frame))re4dc_log("PS2PF ui-decline f=%u reason=frame-state\n",frame);
#endif
        re4dc_source_world_prepared(frame,generation,0);return;
    }
#if RE4DC_PS2_WORLD_SOURCE_TEX_PREP
    Re4dcSourceWorldTexture pick{};
    if(!re4dc_ps2_source_texture(generation,&pick)){
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
        if(re4dc_source_world_diag_active(frame))re4dc_log("PS2PF ui-decline f=%u reason=texture-descriptor\n",frame);
#endif
        re4dc_source_world_prepared(frame,generation,0);return;
    }
    const Key key{pick.crc,pick.fnv};
    const Re4dcUiImage image{&key,nullptr,pick.width,pick.height,5,0,0};
    Entry* entry=load(image,true,&key);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    // Preparation may yield before any callback is withheld. Reprove its
    // source/package owners before the returned cache entry is inspected.
    if(!re4dc_source_world_preflight_current(frame,generation)){
        re4dc_source_world_prepared(frame,generation,0);return;
    }
#endif
    unsigned current=0;
    const bool valid=re4dc_ps2_source_package(&current) && current==generation &&
        entry && entry->valid && entry->key==key && entry->frame==frame &&
        entry->package.upload_complete() && entry->package.header().texture_count==1 &&
        entry->package.pvr_texture(0) && RE4DC_SOURCE_TEX_OK(*entry,pick) &&
        entry->package.textures()[0].width==pick.width && entry->package.textures()[0].height==pick.height;
    re4dc_source_world_prepared(frame,generation,valid);
    const bool ready=valid && re4dc_source_world_current(frame,generation);
    if(ready){sourceWorldPreparedFrame=frame;sourceWorldPreparedKey=key;}
    re4dc_log("PS2SOURCE_TEX_PREP f=%u gen=%u key=%08x-%08x ready=%u bytes=%u scene=%u\n",
        frame,generation,key.crc,key.fnv,unsigned(ready),ready?unsigned(entry->package.vram_bytes()):0U,unsigned(stream_scene));
    if(!ready && entry)RE4DC_TEXCHK_FAIL(key,"source-world-prep-descriptor");
#endif
}
}
