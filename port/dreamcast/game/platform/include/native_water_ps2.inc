// WATER_PS2 (lane water16, 2026-10-16; render only, default 0; included by native_ui.cpp in the WATER45_NATIVE block):
// one PS2 water layer (espgen45.cpp re4dc_water_ps2_draw: a PS2 Esp08 world plane from water_ps2_table.inc) as an
// eye-centred grid over the plane: kWaterCells x kWaterCells cells spaced t*|t| out to the fog reach (fine near the
// eye), clamped to the plane. Queued in source OT order as a small node (the compiled header and the layer's
// parameters, about 200 bytes); the vertices are generated while the translucent queue drains, straight into the TA
// stream in chunks, so the frame's deferred storage holds no vertex data. Cells fully fogged, behind the eye or off
// one screen edge are skipped; a run of cells in front of the near margin is one strip (two vertices per corner
// column); cells crossing the near plane go through the model clipper. Textured layers use UV repeat (the PS2
// sprite's Work8 tiling: texture repeats per mm), MODULATEALPHA, table fog, depth test without write. Nothing here
// reads or writes game state.
extern "C" float re4dc_fog_amount(float z);   // native_static.cpp (WATER45_NATIVE): the fog table's amount at depth z
namespace {
DeferredLighting* const kWaterTag=reinterpret_cast<DeferredLighting*>(0x57);   // unique: 1..8 taken (see kGradeTag)
struct WaterNode { pvr_poly_hdr_t header; Re4dcWaterLayer layer; float reach; unsigned textured; };
constexpr unsigned kWaterNode=(sizeof(DeferredPart)+31)&~31U;
constexpr unsigned kWaterCells=8;
unsigned water_queued,water_dropped,water_missing,water_cells,water_clipped,water_verts,water_log_frame,water_cover;
unsigned water_reach_frame=~0U;float water_reach_mm;

// Eye depth (mm) where the fog table reaches 99.5 % (cached for the frame); 400 m without fog.
float water_reach(){
    if(water_reach_frame==frame)return water_reach_mm;
    water_reach_frame=frame;
    float lo=500.0f,hi=400000.0f;
    if(re4dc_fog_amount(hi)<0.995f){water_reach_mm=hi;return hi;}
    for(unsigned i=0;i<24;++i){const float m=0.5f*(lo+hi);(re4dc_fog_amount(m)>=0.995f?hi:lo)=m;}
    water_reach_mm=hi;return hi;
}

// Corner of the grid: view position, projected screen position (when in front of the near plane), fog, texture.
struct WaterCorner { float vx,vy,vz,depth,sx,sy,sz,fog,u,v; };

struct WaterOut {
    alignas(32) pvr_vertex_t buf[32];
    unsigned n=0,total=0;
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    bool aborted=false;
#endif
    void put(const pvr_vertex_t& v){buf[n++]=v;++total;if(n==32)flush();}
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    void flush(){if(n){stream_send(buf,n*sizeof(pvr_vertex_t));n=0;
        aborted|=stream_aborted;
    }}
#else
    void flush(){if(n){stream_send(buf,n*sizeof(pvr_vertex_t));n=0;}}
#endif
};

#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
#define RE4DC_WATER03_EMPTY(state) return {re4dc::NativeDrawOutcome::state}
re4dc::NativeDrawResult water_emit_result03(const WaterNode& w){
#else
#define RE4DC_WATER03_EMPTY(state) return
void water_emit(const WaterNode& w){
#endif
    const Re4dcWaterLayer& L=w.layer;
    const float* P=L.projection;const float* V=L.viewport;
    const float near=P[6]/(P[5]-1.0f),far=P[6]/P[5];
    if(!(near>0.0f) || !(far>near) || V[2]<=0.0f || V[3]<=0.0f)RE4DC_WATER03_EMPTY(UnsupportedBeforePublication);
    Re4dcSubscreenQuad q{};
    std::memcpy(q.projection,P,sizeof(q.projection));std::memcpy(q.viewport,V,sizeof(q.viewport));
    const re4dc::render::ClipParameters clip{near,far,RE4DC_SCREEN_WF,RE4DC_SCREEN_HF,re4dc::subscreen::project,&q};
    const float safe=near*1.5f;
    // grid lines (local mm), clamped to the plane; repeated lines collapse into empty cells
    constexpr unsigned n=kWaterCells;
    float gx[n+1],gz[n+1];
    for(unsigned i=0;i<=n;++i){
        float t=float(int(2*i)-int(n))/float(n);t*=t<0?-t:t;
        float x=L.eye_x+t*w.reach,z=L.eye_z+t*w.reach;
        gx[i]=x<-L.half_x?-L.half_x:x>L.half_x?L.half_x:x;
        gz[i]=z<-L.half_z?-L.half_z:z>L.half_z?L.half_z:z;
    }
    if(gx[n]-gx[0]<1.0f || gz[n]-gz[0]<1.0f)RE4DC_WATER03_EMPTY(Culled);   // the plane is outside the reach
    WaterCorner row[2][n+1];
    const unsigned a=(L.argb>>24)&0xFFU;
    const float lr=float((L.argb>>16)&0xFFU)*(1.0f/255.0f),lg=float((L.argb>>8)&0xFFU)*(1.0f/255.0f),
                lb=float(L.argb&0xFFU)*(1.0f/255.0f),la=float(a)*(1.0f/255.0f);
    WaterOut out;
    stream_send(&w.header,sizeof(w.header));
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    const bool header_aborted=stream_aborted;
#endif
    for(unsigned j=0;j<=n;++j){
        WaterCorner* cur=row[j&1];
        for(unsigned i=0;i<=n;++i){
            WaterCorner& c=cur[i];
            const float x=gx[i],z=gz[j];
            c.vx=L.mv[0][0]*x+L.mv[0][2]*z+L.mv[0][3];
            c.vy=L.mv[1][0]*x+L.mv[1][2]*z+L.mv[1][3];
            c.vz=L.mv[2][0]*x+L.mv[2][2]*z+L.mv[2][3];
            c.depth=-c.vz;
            c.fog=c.depth>0.0f?re4dc_fog_amount(c.depth):0.0f;
            c.sx=c.vx;c.sy=c.vy;c.sz=c.vz;
            if(c.depth>=near)re4dc::subscreen::project(c.sx,c.sy,c.sz,&q);
            c.u=x*L.u_per_mm+L.u0;c.v=z*L.v_per_mm+L.v0;
        }
        if(!j)continue;
        const WaterCorner* prev=row[(j-1)&1];
        // classify the row's cells: 0 skip, 1 direct, 2 clip
        unsigned char kind[n];
        for(unsigned i=0;i<n;++i){
            const WaterCorner* k[4]={&prev[i],&prev[i+1],&cur[i],&cur[i+1]};
            kind[i]=0;
            if(gx[i+1]-gx[i]<1.0f || gz[j]-gz[j-1]<1.0f)continue;
            bool fogged=true,behind=true,direct=true;
            for(const WaterCorner* p:k){
                if(p->fog<0.995f)fogged=false;
                if(p->depth>=near)behind=false;
                if(p->depth<safe)direct=false;
            }
            if(fogged || behind)continue;
            if(direct){
                bool l=true,r=true,t=true,b=true;
                for(const WaterCorner* p:k){
                    if(p->sx>=0.0f)l=false;if(p->sx<=RE4DC_SCREEN_WF)r=false;
                    if(p->sy>=0.0f)t=false;if(p->sy<=RE4DC_SCREEN_HF)b=false;
                }
                if(l||r||t||b)continue;
                kind[i]=1;
            } else kind[i]=2;
        }
        for(unsigned i=0;i<n;){
            if(kind[i]==1){
                unsigned e=i;while(e<n && kind[e]==1)++e;   // run i..e-1
                const float bu=std::floor(prev[i].u),bv=std::floor(prev[i].v);
                for(unsigned c=i;c<=e;++c){
                    const WaterCorner* pc[2]={&prev[c],&cur[c]};
                    for(unsigned s=0;s<2;++s){
                        pvr_vertex_t v;
                        v.flags=(c==e && s==1)?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
                        v.x=pc[s]->sx;v.y=pc[s]->sy;v.z=pc[s]->sz;
                        v.u=pc[s]->u-bu;v.v=pc[s]->v-bv;v.argb=L.argb;v.oargb=0;
                        out.put(v);
                    }
                }
                water_cells+=e-i;i=e;continue;
            }
            if(kind[i]==2){
                const WaterCorner* k[4]={&prev[i],&prev[i+1],&cur[i],&cur[i+1]};
                const float bu=std::floor(k[0]->u),bv=std::floor(k[0]->v);
                re4dc::render::RenderVertex rv[4]{};
                for(unsigned s=0;s<4;++s){
                    auto& p=rv[s].position;
                    p.world_x=k[s]->vx;p.world_y=k[s]->vy;p.world_z=k[s]->vz;p.depth=k[s]->depth;
                    p.x=k[s]->sx;p.y=k[s]->sy;p.z=k[s]->sz;
                    rv[s].u=k[s]->u-bu;rv[s].v=k[s]->v-bv;
                    rv[s].light_red=lr;rv[s].light_green=lg;rv[s].light_blue=lb;
                }
                constexpr unsigned strips[2][3]={{0,1,2},{2,1,3}};
                for(const auto& ix:strips){
                    const re4dc::render::RenderVertex tri[]={rv[ix[0]],rv[ix[1]],rv[ix[2]]};
                    const float a3[3]={la,la,la};
                    pvr_vertex_t tmp[12];
                    const unsigned m=3*re4dc::render::clip_projected_triangle(tri,tmp,0,clip,nullptr,a3);
                    for(unsigned s=0;s<m;++s)out.put(tmp[s]);
                }
                ++water_cells;++water_clipped;
            }
            ++i;
        }
    }
    out.flush();
    water_verts+=out.total;
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    // Even zero visible vertices follow a published header. No replay is legal.
    return {header_aborted || out.aborted || stream_aborted?re4dc::NativeDrawOutcome::PartialAbort:
        re4dc::NativeDrawOutcome::Submitted,1,0};
#endif
}
#undef RE4DC_WATER03_EMPTY
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
void water_emit(const WaterNode& w){
    const auto result=water_emit_result03(w);
    if(result.outcome==re4dc::NativeDrawOutcome::PartialAbort)stream_aborted=true;
}
#endif
}  // namespace

#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
#define RE4DC_WATER03_RETURN(state,legacy,sent,queued) return {re4dc::NativeDrawOutcome::state,sent,queued}
extern "C" re4dc::NativeDrawResult re4dc_water_layer_result(const Re4dcWaterLayer* L,int* legacy_admitted){
    if(legacy_admitted)*legacy_admitted=0;
#else
#define RE4DC_WATER03_RETURN(state,legacy,sent,queued) return legacy
extern "C" int re4dc_water_layer(const Re4dcWaterLayer* L){
#endif
    if(!L || !frame_ready || stream_aborted || draining_parts)RE4DC_WATER03_RETURN(Refused,0,0,0);
    if(L->projection[0]!=0.0f)RE4DC_WATER03_RETURN(UnsupportedBeforePublication,0,0,0);
    for(float f:L->projection)if(!re4dc::render::is_finite(f))RE4DC_WATER03_RETURN(UnsupportedBeforePublication,0,0,0);
    for(float f:L->viewport)if(!re4dc::render::is_finite(f))RE4DC_WATER03_RETURN(UnsupportedBeforePublication,0,0,0);
    for(const auto& r:L->mv)for(float f:r)if(!re4dc::render::is_finite(f))RE4DC_WATER03_RETURN(UnsupportedBeforePublication,0,0,0);
    if(frame-water_log_frame>=600U){
        water_log_frame=frame;
        re4dc_log("WATERPS2 f=%u queued=%u dropped=%u missing=%u cells=%u clipped=%u verts=%u cover=%u reach=%u\n",frame,
                  water_queued,water_dropped,water_missing,water_cells,water_clipped,water_verts,water_cover,
                  unsigned(water_reach()));
    }
    WaterNode w{};
    w.layer=*L;w.reach=water_reach();
    pvr_poly_cxt_t c;
    if(L->image.pixels){
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
        fxCoreBeginFxFrame();
#else
        if(fx_frame!=frame){fx_frame=frame;fx_count=0;
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
            fx_new_loads=0;
#endif
        }
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
        fx_resident_only=frame-fx_evict_frame<=1 || fx_new_loads>=kFxNewLoads;
        const unsigned opens=load_opens;
#endif
#if RE4DC_UI_HANDLES
        Entry* e=resolve(L->image,nullptr,true);
#else
        Entry* e=load(L->image);
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
        fx_resident_only=false;fx_new_loads+=load_opens-opens;
#endif
        if(!e){++water_missing;RE4DC_WATER03_RETURN(Refused,0,0,0);}
        const auto& t=e->package.textures()[0];
        if(RE4DC_COVER_W(e->package,L->image.width)!=t.width || RE4DC_COVER_H(e->package,L->image.height)!=t.height)
            ++water_cover;   // a picture smaller than its texture: the repeat wraps at the texture edge
        pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,re4dc::texture::pvr_format(t),t.width,t.height,
                         const_cast<void*>(e->package.pvr_texture(0)),PVR_FILTER_BILINEAR);
        c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.uv_clamp=PVR_UVCLAMP_NONE;
        w.textured=1;
    } else {
        pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    }
    c.gen.culling=PVR_CULLING_NONE;c.gen.shading=PVR_SHADE_GOURAUD;c.gen.alpha=PVR_ALPHA_ENABLE;
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=(pvr_blend_mode_t)L->src;c.blend.dst=(pvr_blend_mode_t)L->dst;
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=PVR_FOG_TABLE;
#else
    c.gen.fog_type=PVR_FOG_DISABLE;
#endif
    pvr_poly_compile(&w.header,&c);
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    if(source_draws_finished){AVD_EVENT(Direct,nullptr,nullptr,4);stream_select(PVR_LIST_TR_POLY);
        if(legacy_admitted)*legacy_admitted=1;
        const auto result=water_emit_result03(w);++water_queued;return result;
    }
#else
    if(source_draws_finished){AVD_EVENT(Direct,nullptr,nullptr,4);stream_select(PVR_LIST_TR_POLY);water_emit(w);++water_queued;return 1;}
#endif
    const unsigned required=kWaterNode+((sizeof(WaterNode)+31)&~31U),margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++water_dropped;RE4DC_WATER03_RETURN(Refused,0,0,0);}
        storage=deferred_spill;top=&deferred_spill_top;
    }
    *top-=required;auto* node=new(storage+*top) DeferredPart{};
    node->lighting=kWaterTag;
    std::memcpy(storage+*top+kWaterNode,&w,sizeof(w));
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;
    AVD_EVENT(Enqueue,node,nullptr,unsigned(uintptr_t(node->lighting)));
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    ++water_queued;
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    if(legacy_admitted)*legacy_admitted=1;
#endif
    RE4DC_WATER03_RETURN(Queued,1,0,1);
}
#undef RE4DC_WATER03_RETURN
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
extern "C" int re4dc_water_layer(const Re4dcWaterLayer* L){
    int admitted=0;(void)re4dc_water_layer_result(L,&admitted);return admitted;
}
#endif
