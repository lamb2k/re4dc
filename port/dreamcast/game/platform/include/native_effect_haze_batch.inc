// All-or-none private haze replacement. Scratch quads may be resolution-scaled;
// no texture upload, spill allocation, source mutation or direct stream write.
// A successful empty/cull-only batch intentionally replaces an invisible group.
// Existing guard order is preserved. Diagnose only the first rejected batch in
// a native frame; the source adapter logs its source frame/room separately.
static unsigned haze_batch_bits(float value){unsigned bits;memcpy(&bits,&value,4);return bits;}
static int haze_batch_refuse(unsigned why,unsigned count,unsigned got=0,unsigned want=0,unsigned item=0,unsigned component=0){
    static unsigned last_frame;static bool reported;
    if(!reported || last_frame!=frame){
        re4dc_log("PS2FXCOMMON_BATCH f=%u why=%u count=%u got=%08x want=%08x item=%u component=%u fx=%u\n",
            frame,why,count,got,want,item,component,fx_count);
        reported=true;last_frame=frame;
    }
    return 0;
}
extern "C" int re4dc_effect_haze_batch(Re4dcEffectSprite* sprites,unsigned count,unsigned* submitted){
    if(submitted)*submitted=0;
    if(!frame_ready)return haze_batch_refuse(1,count,0,1);
    if(stream_aborted)return haze_batch_refuse(2,count,1,0);
    if(draining_parts)return haze_batch_refuse(3,count,1,0);
    if(source_draws_finished)return haze_batch_refuse(4,count,1,0);
    if(count>12)return haze_batch_refuse(5,count,count,12);
    if(!sprites && count)return haze_batch_refuse(6,count,0,1);
    if(fx_frame!=frame){fx_frame=frame;fx_count=0;
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
        fx_new_loads=0;
#endif
    }
    unsigned mask=0,visible=0;
    for(unsigned n=0;n<count;++n){
        Re4dcEffectSprite& s=sprites[n];
        if(s.src!=4)return haze_batch_refuse(7,count,s.src,4,n);
        if(s.dst!=5)return haze_batch_refuse(8,count,s.dst,5,n);
        if(s.screen)return haze_batch_refuse(9,count,s.screen,0,n);
        if(s.pad&~2U)return haze_batch_refuse(10,count,s.pad,2,n);
        if(!same_image(s.image,sprites[0].image))return haze_batch_refuse(11,count,0,1,n);
        for(unsigned i=0;i<4;++i){
            if(!re4dc::render::is_finite(s.x[i]))return haze_batch_refuse(12,count,haze_batch_bits(s.x[i]),0,n,i);
            if(!re4dc::render::is_finite(s.y[i]))return haze_batch_refuse(13,count,haze_batch_bits(s.y[i]),0,n,i);
            if(!re4dc::render::is_finite(s.z[i]))return haze_batch_refuse(14,count,haze_batch_bits(s.z[i]),0,n,i);
            if(s.z[i]<=0)return haze_batch_refuse(15,count,haze_batch_bits(s.z[i]),0,n,i);
            if(!re4dc::render::is_finite(s.u[i]))return haze_batch_refuse(16,count,haze_batch_bits(s.u[i]),0,n,i);
            if(!re4dc::render::is_finite(s.v[i]))return haze_batch_refuse(17,count,haze_batch_bits(s.v[i]),0,n,i);
#if RE4DC_RES_MODES
            s.x[i]*=re4dc_ui_sx;s.y[i]*=re4dc_ui_sy;
            if(!re4dc::render::is_finite(s.x[i]))return haze_batch_refuse(18,count,haze_batch_bits(s.x[i]),0,n,i);
            if(!re4dc::render::is_finite(s.y[i]))return haze_batch_refuse(19,count,haze_batch_bits(s.y[i]),0,n,i);
#endif
        }
        if(!(s.color>>24))continue;
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
        float x0=s.x[0],x1=x0,y0=s.y[0],y1=y0,zmax=s.z[0];
        for(unsigned i=1;i<4;++i){x0=std::min(x0,s.x[i]);x1=std::max(x1,s.x[i]);
            y0=std::min(y0,s.y[i]);y1=std::max(y1,s.y[i]);zmax=std::max(zmax,s.z[i]);}
        if(x1<0 || x0>RE4DC_SCREEN_WF || y1<0 || y0>RE4DC_SCREEN_HF)continue;
        const float fog_far=re4dc_fog_gate_far?re4dc_fog_gate_far():0.0f;
        if(fog_far>0 && zmax*fog_far<1.0f)continue;
#endif
        mask|=1U<<n;++visible;
    }
    if(!visible){fx_culled+=count;return 1;}
    if(fx_count>RE4DC_EFFECT_SPRITE_MAX || visible>RE4DC_EFFECT_SPRITE_MAX-fx_count){
        ++fx_capped;return fx_count>RE4DC_EFFECT_SPRITE_MAX?haze_batch_refuse(20,count,fx_count,RE4DC_EFFECT_SPRITE_MAX):
            haze_batch_refuse(21,count,visible,RE4DC_EFFECT_SPRITE_MAX-fx_count);
    }
    const unsigned stride=kSpriteNode+kSpritePacket,required=visible*stride,margin=RE4DC_FX_QUEUE_MARGIN;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        // Borrow an already-existing spill tail only; the candidate adds no allocator.
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
        if(!deferred_spill || required>deferred_spill_top){
            if(!fx_r200_tail_select(required,storage,top)){
                ++fx_dropped;return !deferred_spill?haze_batch_refuse(22,count,0,required):
                    haze_batch_refuse(23,count,deferred_spill_top,required);
            }
        }else{storage=deferred_spill;top=&deferred_spill_top;}
#else
        if(!deferred_spill || required>deferred_spill_top){
            ++fx_dropped;return !deferred_spill?haze_batch_refuse(22,count,0,required):
                haze_batch_refuse(23,count,deferred_spill_top,required);
        }
        storage=deferred_spill;top=&deferred_spill_top;
#endif
    }
    const Re4dcUiImage& image=sprites[0].image;
    if(!image.pixels)return haze_batch_refuse(24,count,0,1);
    if(!image.width)return haze_batch_refuse(25,count,0,1);
    if(!image.height)return haze_batch_refuse(26,count,0,1);
    if(image.width>1024)return haze_batch_refuse(27,count,image.width,1024);
    if(image.height>1024)return haze_batch_refuse(28,count,image.height,1024);
    if(!image_size(image))return haze_batch_refuse(29,count,image.format,0);
    Key key{};if(!image_key(image,key))return haze_batch_refuse(30,count,image.format,0);
    Entry* texture=nullptr;
    for(auto& e:entries)if(e.valid && e.key==key){texture=&e;break;}
    if(!texture){++fx_missing;return haze_batch_refuse(31,count,image.format,0);}
    // No operation below can fail: reserve once, build every packet, then link.
    texture->frame=frame;
    const unsigned base=*top-required;
    DeferredPart* first=nullptr;DeferredPart* last=nullptr;unsigned offset=base;
    for(unsigned n=0;n<count;++n)if(mask&(1U<<n)){
#if defined(RE4DC_ESP_SETUP_BATCH)
        auto* node=new(storage+offset) DeferredPart{};node->changed[0]=0;
        const bool body_only=fx_packet(sprites[n],texture,storage+offset+kSpriteNode,last?last:deferred_last?deferred_last:node);
        node->lighting=body_only?kSpriteBodyTag:kSpriteTag;
#else
        auto* node=new(storage+offset) DeferredPart{};node->lighting=kSpriteTag;node->changed[0]=0;
        fx_packet(sprites[n],texture,storage+offset+kSpriteNode);
#endif
        AVD_EVENT(Enqueue,node,nullptr,unsigned(uintptr_t(node->lighting))); // Pre-splice, no remaining failure path.
        if(last)last->next=node;else first=node;last=node;offset+=stride;
    }
    *top=base;if(deferred_last)deferred_last->next=first;else deferred_first=first;deferred_last=last;
    deferred_count+=visible;fx_queued+=visible;fx_count+=visible;fx_culled+=count-visible;
    fx_peak=std::max(fx_peak,fx_count);
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
#if RE4DC_TA_BIN_DIAG
    for(unsigned n=0;n<count;++n)if(mask&(1U<<n)){
        const auto& s=sprites[n];(s.pad&2?tabin::fill_haze:tabin::fill_fx)+=tabin::clip_area(s.x,s.y,4);
    }
#endif
    if(submitted)*submitted=visible;
    return 1;
}
