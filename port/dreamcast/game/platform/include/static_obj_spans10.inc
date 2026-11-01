// Local to native_model.cpp. Leases cover metadata; owner stamps and the
// original SOB fence cover source backing across texture/packet callbacks.
struct PreparedSpans10 {
    static constexpr unsigned capacity=16;
    struct Span {
        Re4dcModelSpan10 source;
        Re4dcDrawOwnerStamp owner;
        const re4dc::render::NativeDrawPlan* plan;
        const re4dc::render::DrawPlanBounds* bounds;
        const re4dc::render::DrawLocalPlan* locals;
    } spans[capacity]{};
    struct Array {
        const void* address=nullptr;unsigned bytes=0;Re4dcDrawOwnerStamp owner;
        bool bind(const void* p,unsigned n){
            address=p;bytes=n;owner=re4dc_model_draw_owner_stamp(p,n);return owner.valid();
        }
        bool current()const{return !bytes || owner==re4dc_model_draw_owner_stamp(address,bytes);}
    } arrays[4];
    unsigned count=0;
    std::uint32_t max_uv=0,max_color=0;
    bool (*fence)(const void*)=nullptr;const void* context=nullptr;
    ~PreparedSpans10(){while(count){--count;re4dc_model_release_draw_plan();}}
    bool current()const{
        if(!fence || !fence(context))return false;
        for(const auto& a:arrays)if(!a.current())return false;
        for(unsigned i=0;i<count;++i){const auto& s=spans[i];
            if(!(s.owner==re4dc_model_draw_owner_stamp(s.source.part,32)) ||
               !(s.owner==re4dc_model_draw_owner_stamp(s.source.stream,s.source.bytes)))return false;
        }
        return true;
    }
    bool prepare(const Re4dcModelPart& p,const Re4dcModelSpan10* source,unsigned n,
                 bool (*alive)(const void*),const void* user){
        if(!source || n<2 || n>capacity || !alive || !alive(user) || p.world ||
           p.blend || p.alpha_state!=255 || p.depth_mode || (p.material_flags&4) || p.mask.pixels ||
           // Non-null stride-6 arrays may still await the registered source
           // skinning pass. Keep their ordinary per-part materialization path.
           p.position_stride!=8 || !p.position_count || !p.normal_count || !p.normal_stride ||
           p.position_count>~0U/p.position_stride || p.normal_count>~0U/p.normal_stride)return false;
        if(p.part!=source[0].part || p.stream!=source[0].stream || p.stream_bytes!=source[0].bytes)return false;
#if RE4DC_NATIVE_FE_CONTINUATION
        if(p.native_pose)return false;
#endif
        fence=alive;context=user;
        if(!arrays[0].bind(p.positions,p.position_count*p.position_stride) ||
           !arrays[1].bind(p.normals,p.normal_count*p.normal_stride))return false;
        for(unsigned i=0;i<n;++i){
            const auto owner=re4dc_model_draw_owner_stamp(source[i].part,32);
            if(!owner.valid() || !(owner==re4dc_model_draw_owner_stamp(source[i].stream,source[i].bytes)))return false;
            Re4dcModelPart part=p;part.part=source[i].part;part.stream=source[i].stream;part.stream_bytes=source[i].bytes;
            int invalid=0;const auto* plan=re4dc_model_acquire_draw_plan(&part,&invalid);
            if(!plan)return false;
            if(invalid){re4dc_model_release_draw_plan();return false;}
            spans[count++]={source[i],owner,plan,re4dc_model_acquired_bounds(),re4dc_model_acquired_locals()};
            max_uv=std::max(max_uv,plan->max_uv);max_color=std::max(max_color,plan->max_color);
        }
        if(max_uv>=~0U/4 || !arrays[2].bind(p.uv,(max_uv+1)*4))return false;
        if(p.lighting && (p.lighting->ambient_vertex || p.lighting->material_vertex)){
            if(max_color>=~0U/4 || !arrays[3].bind(p.colors,(max_color+1)*4))return false;
        }
        return current();
    }
};
