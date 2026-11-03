// Shared body: existing primitive/policy paths, only return attribution changes.
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
#define RE4DC_SPRITE03_RETURN(state,legacy,sent,queued) return {re4dc::NativeDrawOutcome::state,sent,queued}
#define RE4DC_SPRITE03_DIRECT() return {stream_aborted?re4dc::NativeDrawOutcome::PartialAbort:re4dc::NativeDrawOutcome::Submitted,1,0}
    if(!s)RE4DC_SPRITE03_RETURN(UnsupportedBeforePublication,0,0,0);
#if defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12
    const unsigned frame12=frame,epoch12=handle_reset;
#endif
#else
#define RE4DC_SPRITE03_RETURN(state,legacy,sent,queued) return legacy
#define RE4DC_SPRITE03_DIRECT() return 1
#endif

#if RE4DC_TA_MATERIAL_DIAG
    tamat::Scope source_scope(4);
#endif
    if(!frame_ready || stream_aborted || draining_parts)RE4DC_SPRITE03_RETURN(Refused,0,0,0);
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    // PVR_RTT: inside a target's bracket a sprite belongs to the target (pvr_rtt.inc), never to the screen: a target no
    // model shows (e.g. the r221 128x128 slot 0) drops its sprites, as the GC copies them only into its buffer.
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    if(rtt::capture_slot>=0){
        if(!rtt::wanted(rtt::capture_slot))RE4DC_SPRITE03_RETURN(PolicySkip,0,0,0);
        return rtt::capture_result03(s);
    }
#else
    if(rtt::capture_slot>=0)return rtt::wanted(rtt::capture_slot)?rtt::capture(s):0;
#endif
#endif
#if defined(RE4DC_FX_CUT_LOG) && RE4DC_FX_CUT_LOG
    {   // FX_CUT_LOG (test only): fx_count still holds the previous effect frame's queued sprites here.
        static unsigned lf=~0U,nf,drawn,opens0;
        if(lf!=frame){
            if(lf!=~0U){drawn+=fx_count;++nf;}
            lf=frame;
            if(nf==120){
                unsigned cuts=0,skips=0,refused=0,rskip=0;
#if defined(RE4DC_FX_PS2_NONE_CUT) && RE4DC_FX_PS2_NONE_CUT
                cuts=fxnone_cuts;
#if defined(RE4DC_FX_EARLY_CUT) && RE4DC_FX_EARLY_CUT
                skips=fxearly_skips;refused=fxearly_refused;
#endif
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
                rskip=fx_resident_skips;
#endif
                re4dc_log("fx cut log: frame=%u frames=%u drawn=%u none_cuts=%u early_skips=%u early_refused=%u opens=%u missing=%u resident_only=%u\n",
                          frame,nf,drawn,cuts,skips,refused,load_opens-opens0,fx_missing,rskip);
                nf=0;drawn=0;opens0=load_opens;
            }
        }
    }
#endif
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
    fxCoreBeginFxFrame();
#else
    if(fx_frame!=frame){fx_frame=frame;fx_count=0;
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
        fx_new_loads=0;
#endif
    }
#endif
    if((s->color>>24)==0){++fx_culled;RE4DC_SPRITE03_RETURN(PolicySkip,0,0,0);}
#if RE4DC_RES_MODES
    Re4dcEffectSprite scaled;      // esp_sub.cpp projects to 640x480: the current render size (no copy at 640x480)
    if(re4dc_ui_sy!=1.0f || re4dc_ui_sx!=1.0f){scaled=*s;for(unsigned i=0;i<4;++i){scaled.x[i]*=re4dc_ui_sx;scaled.y[i]*=re4dc_ui_sy;}s=&scaled;}
#endif
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
    {   // ESP_SPRITE_FAST: std::isfinite on the bits (UI_QUAD_LEAN's test): an all-ones exponent carries into bit
        // 31 of (bits & 0x7f800000) + 0x00800000; no __unordsf2 call per coordinate.
        typedef std::uint32_t fx_word __attribute__((may_alias));
        const fx_word* xw=reinterpret_cast<const fx_word*>(s->x);
        const fx_word* yw=reinterpret_cast<const fx_word*>(s->y);
        const fx_word* zw=reinterpret_cast<const fx_word*>(s->z);
        std::uint32_t top=0;
        for(unsigned i=0;i<4;++i)
            top|=((xw[i]&0x7f800000U)+0x00800000U)|((yw[i]&0x7f800000U)+0x00800000U)|((zw[i]&0x7f800000U)+0x00800000U);
        if(top&0x80000000U){++fx_culled;RE4DC_SPRITE03_RETURN(UnsupportedBeforePublication,0,0,0);}
    }
#else
    for(unsigned i=0;i<4;++i)if(!std::isfinite(s->x[i]) || !std::isfinite(s->y[i]) || !std::isfinite(s->z[i])){++fx_culled;RE4DC_SPRITE03_RETURN(UnsupportedBeforePublication,0,0,0);}
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    {   // EFFECT_ROOM: spend the cap and the queue only on sprites that can change a pixel. Off screen:
        // all four corners past one edge of the 640x480 frame. Beyond the fog: every corner deeper than
        // the fogged View far, where the fog table is at 100% (the sprite is the fog colour there).
        float x0=s->x[0],x1=s->x[0],y0=s->y[0],y1=s->y[0],zmax=s->z[0];
        for(unsigned i=1;i<4;++i){
            x0=std::min(x0,s->x[i]);x1=std::max(x1,s->x[i]);y0=std::min(y0,s->y[i]);y1=std::max(y1,s->y[i]);
            zmax=std::max(zmax,s->z[i]);
        }
        if(x1<0.0f || x0>RE4DC_SCREEN_WF || y1<0.0f || y0>RE4DC_SCREEN_HF){++fx_culled;RE4DC_SPRITE03_RETURN(Culled,0,0,0);}
        const float fog_far=(!s->screen && re4dc_fog_gate_far)?re4dc_fog_gate_far():0.0f;
        if(fog_far>0.0f && zmax*fog_far<1.0f){++fx_culled;RE4DC_SPRITE03_RETURN(Culled,0,0,0);}
    }
#endif
    if(fx_count>=RE4DC_EFFECT_SPRITE_MAX){++fx_capped;RE4DC_SPRITE03_RETURN(Refused,0,0,0);}
#if defined(RE4DC_FX_PS2_NONE_CUT) && RE4DC_FX_PS2_NONE_CUT && defined(RE4DC_FX_EARLY_CUT) && RE4DC_FX_EARLY_CUT
    if(fxearly_known_cut(s->image)){++fxearly_skips;++fxnone_cuts;RE4DC_SPRITE03_RETURN(PolicySkip,0,0,0);}   // FX_EARLY_CUT: no resolve
    fxearly_armed=true;fxearly_hit=false;
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    fx_resident_only=frame-fx_evict_frame<=1 || fx_new_loads>=kFxNewLoads;
#if defined(RE4DC_FX_TEX_POOL) && RE4DC_FX_TEX_POOL
    if(!fx_pool_full && fx_new_loads<kFxNewLoads)fx_resident_only=false;   // FX_TEX_POOL: fill the pool first
#endif
    const unsigned opens=load_opens;
#endif
#if defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12
    Key key12{};
    if(material12 && !image_key(s->image,key12))RE4DC_SPRITE03_RETURN(Refused,0,0,0);
#endif
#if RE4DC_UI_HANDLES
    Entry* e=resolve(s->image,nullptr,true);
#else
    Entry* e=load(s->image);
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    fx_resident_only=false;fx_new_loads+=load_opens-opens;
#endif
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
    fxCoreTextureAcquired(s->image,e);
#endif
#if defined(RE4DC_FX_PS2_NONE_CUT) && RE4DC_FX_PS2_NONE_CUT && defined(RE4DC_FX_EARLY_CUT) && RE4DC_FX_EARLY_CUT
    fxearly_armed=false;
    if(!e && fxearly_hit){fxearly_hit=false;fxearly_remember(s->image);++fxnone_cuts;RE4DC_SPRITE03_RETURN(PolicySkip,0,0,0);}
#endif
    if(!e){++fx_missing;RE4DC_SPRITE03_RETURN(Refused,0,0,0);}
#if defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12
    if(material12){
        if(stream_aborted)RE4DC_SPRITE03_RETURN(PartialAbort,0,0,0);
        if(frame12!=frame || epoch12!=handle_reset || !frame_ready || draining_parts || !e->valid || !(e->key==key12) ||
           e->frame!=frame || !e->package.upload_complete() || e->package.header().texture_count!=1 ||
           !e->package.pvr_texture(0) || e->package.header().flags ||
           !re4dc::effect_mask12::native_rgb(*e->package.textures()))RE4DC_SPRITE03_RETURN(Refused,0,0,0);
    }
#endif
#if defined(RE4DC_FX_PS2_NONE_CUT) && RE4DC_FX_PS2_NONE_CUT
#if defined(RE4DC_FX_EARLY_CUT) && RE4DC_FX_EARLY_CUT
    if(fx_none_cut(*e)){fxearly_remember(s->image);++fxnone_cuts;RE4DC_SPRITE03_RETURN(PolicySkip,0,0,0);}   // resident already (e.g. drawn elsewhere)
#else
    if(fx_none_cut(*e)){++fxnone_cuts;RE4DC_SPRITE03_RETURN(PolicySkip,0,0,0);}   // FX_PS2_NONE_CUT: a picture the PS2 dropped
#endif
#endif
#if RE4DC_VRAM_ROOM_LOG && defined(RE4DC_FX_PS2_PACK) && RE4DC_FX_PS2_PACK
    if(!RE4DC_COVER(e->package))vram_room_gcfx(*e);   // VRAM_ROOM_LOG: a GameCube effect picture (no PS2 conversion)
#endif
#if defined(RE4DC_FX_TEX_POOL) && RE4DC_FX_TEX_POOL
    {const unsigned i=unsigned(e-entries);
     if(i<kTextureCount && !fx_pool_pin[i] && e->valid){
         const unsigned b=e->package.vram_bytes();
         if(fx_pool_bytes+b<=unsigned(RE4DC_FX_TEX_POOL)*1024U){fx_pool_pin[i]=true;fx_pool_size[i]=b;fx_pool_bytes+=b;++fx_pool_pins;}
         else fx_pool_full=1;
     }}
#endif
#if RE4DC_FX_SPRITE_TRIM || RE4DC_FX_SPRITE_TRIM_DIAG
    Re4dcEffectSprite trimmed;    // FX_SPRITE_TRIM: the quad over its texture's alpha box or octagon (fxtrim.mk)
    float fx_oct_p[8],fx_oct_q[8];
#if defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12
    const int fx_trim_kind=material12?0:fx_trim(*s,e,trimmed,fx_oct_p,fx_oct_q);
#else
    const int fx_trim_kind=fx_trim(*s,e,trimmed,fx_oct_p,fx_oct_q);
#endif
#if RE4DC_FX_SPRITE_TRIM
    if(fx_trim_kind==2){
#if RE4DC_TA_BIN_DIAG
        {
            float xs[8],ys[8];
            for(unsigned i=0;i<8;++i){
                xs[i]=s->x[3]+fx_oct_p[i]*(s->x[2]-s->x[3])+fx_oct_q[i]*(s->x[0]-s->x[3]);
                ys[i]=s->y[3]+fx_oct_p[i]*(s->y[2]-s->y[3])+fx_oct_q[i]*(s->y[0]-s->y[3]);
            }
            (s->pad&2?tabin::fill_haze:s->pad&4?tabin::fill_mist:tabin::fill_fx)+=tabin::clip_area(xs,ys,8);
        }
#endif
        if(source_draws_finished){
            alignas(32) unsigned char packet[kFxOctPacket];fx_trim_oct_packet(*s,e,fx_oct_p,fx_oct_q,packet);
            stream_select(PVR_LIST_TR_POLY);
#if RE4DC_TA_BIN_DIAG
            tabin::skip_fill=true;stream_send(packet,kFxOctPacket);tabin::skip_fill=false;
#else
            stream_send(packet,kFxOctPacket);
#endif
            ++fx_direct;++fx_count;RE4DC_SPRITE03_DIRECT();
        }
        const unsigned required=kSpriteNode+kFxOctPacket,margin=RE4DC_FX_QUEUE_MARGIN;
        unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
        if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
            if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
            if(!deferred_spill || required>deferred_spill_top){
                if(!fx_r200_tail_select(required,storage,top)){++fx_dropped;RE4DC_FQ_DROP(true,required);RE4DC_SPRITE03_RETURN(Refused,0,0,0);}
            }else{storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill) DFA26_HIT(EffectQueueSpill)}
#else
            if(!deferred_spill || required>deferred_spill_top){++fx_dropped;RE4DC_FQ_DROP(true,required);RE4DC_SPRITE03_RETURN(Refused,0,0,0);}
            storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill) DFA26_HIT(EffectQueueSpill)
#endif
        }
        *top-=required;
        auto* node=new(storage+*top) DeferredPart{};node->lighting=kFxOctTag;
        fx_trim_oct_packet(*s,e,fx_oct_p,fx_oct_q,storage+*top+kSpriteNode);
        if(deferred_last)deferred_last->next=node;else deferred_first=node;
        deferred_last=node;++deferred_count;
        ++fx_queued;++fx_count;
        fx_peak=std::max(fx_peak,fx_count);
        frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
        RE4DC_SPRITE03_RETURN(Queued,1,0,1);
    }
#endif
    if(fx_trim_kind==1)s=&trimmed;
#endif
#if RE4DC_TA_BIN_DIAG
    {
        const float xs[4]={s->x[0],s->x[1],s->x[2],s->x[3]},ys[4]={s->y[0],s->y[1],s->y[2],s->y[3]};
        float a=tabin::clip_area(xs,ys,4);
        if((s->pad&1) && !s->screen)a*=0.671f;
        (s->pad&2?tabin::fill_haze:s->pad&4?tabin::fill_mist:tabin::fill_fx)+=a;
    }
#endif
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 4)
    if((s->pad&1) && !s->screen){
        if(source_draws_finished){
            AVD_EVENT(Direct,nullptr,nullptr,7);
        alignas(32) unsigned char packet[kOctPacket];oct_packet(*s,e,packet);
            stream_select(PVR_LIST_TR_POLY);
#if RE4DC_TA_BIN_DIAG
            tabin::skip_fill=true;stream_send(packet,kOctPacket);tabin::skip_fill=false;
#else
            stream_send(packet,kOctPacket);
#endif
            ++fx_direct;++fx_count;RE4DC_SPRITE03_DIRECT();
        }
        const unsigned required=kSpriteNode+kOctPacket,margin=RE4DC_FX_QUEUE_MARGIN;
        unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
        if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
            if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
            if(!deferred_spill || required>deferred_spill_top){
                if(!fx_r200_tail_select(required,storage,top)){++fx_dropped;RE4DC_FQ_DROP(true,required);RE4DC_SPRITE03_RETURN(Refused,0,0,0);}
            }else{storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill) DFA26_HIT(EffectQueueSpill)}
#else
            if(!deferred_spill || required>deferred_spill_top){++fx_dropped;RE4DC_FQ_DROP(true,required);RE4DC_SPRITE03_RETURN(Refused,0,0,0);}
            storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill) DFA26_HIT(EffectQueueSpill)
#endif
        }
        *top-=required;
        auto* node=new(storage+*top) DeferredPart{};node->lighting=kOctTag;
        oct_packet(*s,e,storage+*top+kSpriteNode);
        if(deferred_last)deferred_last->next=node;else deferred_first=node;
        deferred_last=node;++deferred_count;
    AVD_EVENT(Enqueue,node,nullptr,unsigned(uintptr_t(node->lighting)));
    ++fx_queued;++fx_count;
        fx_peak=std::max(fx_peak,fx_count);
        frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
        RE4DC_SPRITE03_RETURN(Queued,1,0,1);
    }
#endif
    if(source_draws_finished){
        AVD_EVENT(Direct,nullptr,nullptr,1);
#if defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12
        alignas(32) unsigned char packet[kSpritePacket];
#if defined(RE4DC_ESP_SETUP_BATCH)
        fx_packet(*s,e,packet,nullptr,material12);
#else
        fx_packet(*s,e,packet,material12);
#endif
#else
        alignas(32) unsigned char packet[kSpritePacket];fx_packet(*s,e,packet);
#endif
        stream_select(PVR_LIST_TR_POLY);fx_send(packet,s->screen);
        ++fx_direct;++fx_count;RE4DC_SPRITE03_DIRECT();
    }
    const unsigned required=kSpriteNode+kSpritePacket,margin=RE4DC_FX_QUEUE_MARGIN;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        // The spill tail holds only model snapshots and sprites (no UI lane): no margin.
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
        if(!deferred_spill || required>deferred_spill_top){
            if(!fx_r200_tail_select(required,storage,top)){++fx_dropped;RE4DC_FQ_DROP(true,required);RE4DC_SPRITE03_RETURN(Refused,0,0,0);}
        }else{storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill) DFA26_HIT(EffectQueueSpill)}
#else
        if(!deferred_spill || required>deferred_spill_top){++fx_dropped;RE4DC_FQ_DROP(true,required);RE4DC_SPRITE03_RETURN(Refused,0,0,0);}
        storage=deferred_spill;top=&deferred_spill_top; DFA26_HIT(DeferredSpill) DFA26_HIT(EffectQueueSpill)
#endif
    }
    *top-=required;
#if defined(RE4DC_ESP_SETUP_BATCH)
    auto* node=new(storage+*top) DeferredPart{};node->changed[0]=s->screen;
#if defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12
    const bool body_only=fx_packet(*s,e,storage+*top+kSpriteNode,deferred_last?deferred_last:node,material12);
#else
    const bool body_only=fx_packet(*s,e,storage+*top+kSpriteNode,deferred_last?deferred_last:node);
#endif
    node->lighting=body_only?kSpriteBodyTag:kSpriteTag;
#else
    auto* node=new(storage+*top) DeferredPart{};node->lighting=kSpriteTag;node->changed[0]=s->screen;
#if defined(RE4DC_EFFECT_MASK12) && RE4DC_EFFECT_MASK12
    fx_packet(*s,e,storage+*top+kSpriteNode,material12);
#else
    fx_packet(*s,e,storage+*top+kSpriteNode);
#endif
#endif
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
    AVD_EVENT(Enqueue,node,nullptr,unsigned(uintptr_t(node->lighting)));
    ++fx_queued;++fx_count;
    fx_peak=std::max(fx_peak,fx_count);
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    RE4DC_SPRITE03_RETURN(Queued,1,0,1);

#undef RE4DC_SPRITE03_DIRECT
#undef RE4DC_SPRITE03_RETURN
