// PVR_RTT (pvr_rtt.mk; lane castlerender19 2026-10-19, user decision 10-19 "Verdugo ice option (a), exact"; render
// only, default 0): render-to-texture on the PVR for the source's TexRenderMng targets (game/TexRender.cpp). The GC
// draws a target's effects (esp Tool_flg 0x10000, the target's OT slot) into the EFB at twice the texture size and
// copies it at half size (GXCopyTex, RGBA8, texture id 0xF8 + slot). Here:
// - capture: between RenderTexRenderMgr and CopyTexRenderMgr (the slot's OT bracket) every effect sprite that
//   re4dc_effect_sprite gets is mapped from the 640x480 sprite basis (esp_sub.cpp projects through the target's
//   viewport) into the target's texels and kept as a finished TR sprite packet (screen: depth always, no fog);
// - render: before the next frame's scene, a target a model asked for in the last 2 frames (re4dc_rtt_want) is drawn
//   by one KOS render-to-texture scene (pvr_scene_begin_rtt, w x h, ARGB4444 write: the copy keeps the EFB alpha)
//   into its own VRAM texture, the background cleared to 0 (GX copy clear). One frame later than the GC: the GC
//   copies inside the same frame's OT, the PVR renders a scene at a time.
// - use: re4dc_rtt_texture gives the model path the texture (native_ui packet_begin under re4dc_rtt_override).
// Room start (TexRenderMgrRoomInit) frees the textures. Nothing changes while no model asks for a target.
namespace {
namespace rtt {
constexpr unsigned kSlots=8,kMaxSprites=96;
struct Target { pvr_ptr_t tex; unsigned w,h,want_frame,rendered,frames; };
Target targets[kSlots];
unsigned char packets[kMaxSprites][kSpritePacket] __attribute__((aligned(32)));
unsigned char packet_slot[kMaxSprites];
unsigned packet_count,pending_count,pending_mask;
int capture_slot=-1;
float cap_kx,cap_ky,cap_ox;
unsigned captured,dropped,renders,log_frame,seen_mask,peak;
int override_slot=-1;
bool wanted(int slot){return targets[slot].want_frame && frame-targets[slot].want_frame<=2U;}
unsigned pow2(unsigned v){unsigned p=8;while(p<v)p<<=1;return p;}
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
#define RE4DC_RTTOUT03_RETURN(state,legacy,sent,queued) return {re4dc::NativeDrawOutcome::state,sent,queued}
re4dc::NativeDrawResult capture_result03(const Re4dcEffectSprite* s){
    if(!s)RE4DC_RTTOUT03_RETURN(UnsupportedBeforePublication,0,0,0);
#else
#define RE4DC_RTTOUT03_RETURN(state,legacy,sent,queued) return legacy
int capture(const Re4dcEffectSprite* s){
#endif
    Target& t=targets[capture_slot];
    if(!t.tex){
        if(t.w<8 || t.w>256 || t.h<8 || t.h>256 || pow2(t.w)!=t.w || pow2(t.h)!=t.h){++dropped;RE4DC_RTTOUT03_RETURN(UnsupportedBeforePublication,0,0,0);}
        t.tex=pvr_mem_malloc(t.w*t.h*2);
        if(!t.tex){++dropped;RE4DC_RTTOUT03_RETURN(Refused,0,0,0);}
        std::memset(t.tex,0,t.w*t.h*2);
        re4dc_log("PVR_RTT target slot=%d %ux%u vram=%08x bytes=%u\n",capture_slot,t.w,t.h,unsigned(uintptr_t(t.tex)),t.w*t.h*2);
    }
    if((s->color>>24)==0)RE4DC_RTTOUT03_RETURN(PolicySkip,0,0,0);
    if(packet_count>=kMaxSprites){++dropped;RE4DC_RTTOUT03_RETURN(Refused,0,0,0);}
    Re4dcEffectSprite m=*s;
    for(unsigned i=0;i<4;++i){
        if(!std::isfinite(m.x[i]) || !std::isfinite(m.y[i])){++dropped;RE4DC_RTTOUT03_RETURN(UnsupportedBeforePublication,0,0,0);}
        m.x[i]=m.x[i]*cap_kx-cap_ox;m.y[i]=m.y[i]*cap_ky;
    }
    m.screen=1;
#if RE4DC_UI_HANDLES
    Entry* e=resolve(m.image,nullptr,true);
#else
    Entry* e=load(m.image);
#endif
    if(!e){++dropped;RE4DC_RTTOUT03_RETURN(Refused,0,0,0);}
    fx_packet(m,e,packets[packet_count]);
    packet_slot[packet_count++]=(unsigned char)capture_slot;if(packet_count>peak)peak=packet_count;
    ++captured;
    // Copied capture ownership is queued even if this frame later aborts.
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    if(stream_aborted)RE4DC_RTTOUT03_RETURN(PartialAbort,1,0,1);
#endif
    RE4DC_RTTOUT03_RETURN(Queued,1,0,1);
}
#undef RE4DC_RTTOUT03_RETURN
#if defined(RE4DC_PVR_RTT_STATS) && RE4DC_PVR_RTT_STATS
// PVR_RTT_STATS (test builds): every rendered target shown as a 128 x 128 screen sprite at the top left (slot s at
// x = 16 + 136 s), through the effect sprite queue, so a still shows the texture the PVR rendered.
void debug_overlay(){
    if(!frame_ready || stream_aborted || draining_parts)return;
    for(unsigned s=0;s<kSlots;++s){
        const Target& t=targets[s];
        if(!t.tex || !t.rendered || !wanted(int(s)))continue;
        alignas(32) unsigned char packet[kSpritePacket];
        pvr_sprite_cxt_t c;pvr_sprite_cxt_txr(&c,PVR_LIST_TR_POLY,PVR_TXRFMT_ARGB4444|PVR_TXRFMT_NONTWIDDLED,t.w,t.h,t.tex,PVR_FILTER_NONE);
        c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_ALWAYS;c.depth.write=PVR_DEPTHWRITE_DISABLE;
        c.blend.src=PVR_BLEND_ONE;c.blend.dst=PVR_BLEND_ZERO;c.txr.env=PVR_TXRENV_REPLACE;
        auto* h=reinterpret_cast<pvr_poly_hdr_t*>(packet);pvr_sprite_compile(h,&c);h->argb=0xffffffffU;h->oargb=0;
        auto* b=reinterpret_cast<pvr_sprite_txr_t*>(packet+sizeof(pvr_poly_hdr_t));
        const float x0=16.0f+136.0f*float(s),y0=72.0f,x1=x0+128.0f,y1=y0+128.0f;
        b->flags=PVR_CMD_VERTEX_EOL;
        b->ax=x0;b->ay=y1;b->az=1.0f;b->bx=x0;b->by=y0;b->bz=1.0f;b->cx=x1;b->cy=y0;b->cz=1.0f;b->dx=x1;b->dy=y1;b->dummy=0;
        b->auv=PVR_PACK_16BIT_UV(0.0f,1.0f);b->buv=PVR_PACK_16BIT_UV(0.0f,0.0f);b->cuv=PVR_PACK_16BIT_UV(1.0f,0.0f);
        const unsigned required=kSpriteNode+kSpritePacket;
        if(required+8192>deferred_top)return;
        deferred_top-=required;
        auto* node=new(frame_storage+deferred_top) DeferredPart{};node->lighting=kSpriteTag;node->changed[0]=1;
        std::memcpy(frame_storage+deferred_top+kSpriteNode,packet,kSpritePacket);
        if(deferred_last)deferred_last->next=node;else deferred_first=node;
        deferred_last=node;++deferred_count;
    }
}
#endif
}  // namespace rtt
}  // namespace
extern "C" void re4dc_rtt_capture_begin(int slot,unsigned tw,unsigned th,unsigned efb_w,unsigned efb_h,unsigned ofs){
    if(slot<0 || slot>=int(rtt::kSlots) || !efb_w || !efb_h)return;
    rtt::Target& t=rtt::targets[slot];
    if(t.tex && (t.w!=tw || t.h!=th)){pvr_mem_free(t.tex);t.tex=nullptr;t.rendered=0;}
    if(!(rtt::seen_mask&(1U<<slot))){rtt::seen_mask|=1U<<slot;re4dc_log("PVR_RTT slot %d first pass %ux%u efb %ux%u ofs %u\n",slot,tw,th,efb_w,efb_h,ofs);}
    t.w=tw;t.h=th;
    // texel = (EFB pixel - copy x) / 2; EFB pixel = sprite x * efb_w / 640 (y: efb_h / 480).
    rtt::cap_kx=float(efb_w)/640.0f*0.5f;rtt::cap_ky=float(efb_h)/480.0f*0.5f;rtt::cap_ox=float(ofs)*0.5f;
    // This frame's capture replaces the slot's previous one.
    unsigned k=0;
    for(unsigned i=0;i<rtt::packet_count;++i)if(rtt::packet_slot[i]!=slot){
        if(k!=i){std::memcpy(rtt::packets[k],rtt::packets[i],kSpritePacket);rtt::packet_slot[k]=rtt::packet_slot[i];}
        ++k;
    }
    rtt::packet_count=k;
    rtt::capture_slot=slot;
}
extern "C" void re4dc_rtt_capture_end(){
#if defined(RE4DC_PVR_RTT_STATS) && RE4DC_PVR_RTT_STATS
    if(rtt::capture_slot>=0)rtt::debug_overlay();
#endif
    rtt::capture_slot=-1;
}
extern "C" int re4dc_rtt_capturing(){return rtt::capture_slot>=0;}
// The esp target slot of a Core_flg (esp.cpp EspTrans: 8 -> 0, 0x10 -> 1 ... 0x200 -> 6) wanted in the last 2 frames.
extern "C" int re4dc_rtt_core_wanted(unsigned core){
    int slot=-1;
    if(core&8)slot=0;else for(int b=4;b<=9;++b)if(core&(1U<<b)){slot=b-3;break;}
    return slot>=0 && frame-rtt::targets[slot].want_frame<=2U && rtt::targets[slot].want_frame;
}
extern "C" void re4dc_rtt_want(int slot){if(slot>=0 && slot<int(rtt::kSlots))rtt::targets[slot].want_frame=frame;}
extern "C" int re4dc_rtt_ready(int slot){
    return slot>=0 && slot<int(rtt::kSlots) && rtt::targets[slot].tex && rtt::targets[slot].rendered;
}
extern "C" void re4dc_rtt_override(int slot){rtt::override_slot=slot;}
extern "C" void* re4dc_rtt_override_texture(unsigned* w,unsigned* h){
    if(rtt::override_slot<0)return nullptr;
    const auto& t=rtt::targets[rtt::override_slot];
    if(!t.tex)return nullptr;
    *w=t.w;*h=t.h;return t.tex;
}
extern "C" void re4dc_rtt_room_reset(){
    for(auto& t:rtt::targets){if(t.tex)pvr_mem_free(t.tex);t=rtt::Target{};}
    rtt::packet_count=0;rtt::capture_slot=-1;rtt::override_slot=-1;
}
// Before the frame's scene (native stream open): the wanted targets' render-to-texture scenes. The previous scene has
// rendered first (present_fence): the pixel format register is shared with it.
extern "C" void re4dc_rtt_render_pending(){
    unsigned mask=0;
    for(unsigned s=0;s<rtt::kSlots;++s){
        const auto& t=rtt::targets[s];
        if(t.tex && frame-t.want_frame<=2U)
            for(unsigned i=0;i<rtt::packet_count;++i)if(rtt::packet_slot[i]==s){mask|=1U<<s;break;}
    }
    if(frame-rtt::log_frame>=300U && (mask || rtt::captured)){
        rtt::log_frame=frame;
        re4dc_log("PVR_RTT frame=%u mask=%02x packets=%u captured=%u dropped=%u renders=%u peak=%u\n",frame,mask,rtt::packet_count,
                  rtt::captured,rtt::dropped,rtt::renders,rtt::peak);
    }
    if(!mask)return;
    const std::uint64_t rtt_t0=timer_us_gettime64();(void)rtt_t0;
    present_fence();
    const std::uint32_t fb=PVR_GET(PVR_FB_CFG_2);
    const std::uint32_t bg=pvr_state.bg_color;
    for(unsigned s=0;s<rtt::kSlots;++s)if(mask&(1U<<s)){
        auto& t=rtt::targets[s];
        PVR_SET(PVR_FB_CFG_2,(fb&~7U)|2U);   // ARGB4444 pixel write
        pvr_state.bg_color=0;
        if(pvr_scene_begin_rtt(t.tex,t.w,t.h,t.w)<0)break;
        if(pvr_list_begin(PVR_LIST_TR_POLY)<0){pvr_scene_finish();break;}
        for(unsigned i=0;i<rtt::packet_count;++i)if(rtt::packet_slot[i]==s)pvr_prim(rtt::packets[i],kSpritePacket);
        pvr_list_finish();pvr_scene_finish();
        pvr_wait_render_done();
        t.rendered=1;++t.frames;++rtt::renders;
#if defined(RE4DC_PVR_RTT_STATS) && RE4DC_PVR_RTT_STATS
        if((t.frames&63)==1){   // PVR_RTT_STATS (test builds): the rendered texels (ARGB4444) read back
            const volatile std::uint16_t* px=static_cast<const volatile std::uint16_t*>(t.tex);
            unsigned sa=0,sr=0,sg=0,sb=0,cover=0;
            for(unsigned i=0;i<t.w*t.h;++i){const unsigned v=px[i];const unsigned a4=v>>12;sa+=a4;sr+=(v>>8)&15;sg+=(v>>4)&15;sb+=v&15;cover+=a4!=0;}
            const unsigned n=t.w*t.h;
            for(unsigned i=0;i<rtt::packet_count;++i)if(rtt::packet_slot[i]==s){
                const auto* b=reinterpret_cast<const pvr_sprite_txr_t*>(rtt::packets[i]+sizeof(pvr_poly_hdr_t));
                const auto* h=reinterpret_cast<const pvr_poly_hdr_t*>(rtt::packets[i]);
                re4dc_log("PVR_RTT sprite a=%d,%d b=%d,%d c=%d,%d d=%d,%d argb=%08x cmd=%08x\n",int(b->ax),int(b->ay),int(b->bx),int(b->by),
                          int(b->cx),int(b->cy),int(b->dx),int(b->dy),unsigned(h->argb),unsigned(h->cmd));
                break;
            }
            re4dc_log("PVR_RTT texels slot=%u frame=%u cover=%u/%u mean a=%u r=%u g=%u b=%u (x17/255) us=%u\n",s,frame,cover,n,sa/n,sr/n,sg/n,sb/n,
                      unsigned(timer_us_gettime64()-rtt_t0));
        }
#endif
    }
    pvr_state.bg_color=bg;
    PVR_SET(PVR_FB_CFG_2,fb);
}
