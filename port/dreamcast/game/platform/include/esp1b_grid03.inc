// Existing source grid, bounded2..64 cells per axis. One call-local cell; no
// source pointers survive re4dc_effect_quad_result's copied FIFO publication.
static re4dc::NativeDrawResult Esp1bGridDraw03(cEsp* esp){
    using O=re4dc::NativeDrawOutcome;
    if(!Esp1bGridClass03(esp))return {O::UnsupportedBeforePublication};
    const Esp1bSpWork work=*reinterpret_cast<const Esp1bSpWork*>(&esp->pad_EC[0xC]);
    const auto* w=&work;
    Mtx transform;memcpy(transform,esp->m_Mat,sizeof transform);
    if(w->div<2 || w->div>64)return {O::UnsupportedBeforePublication};
    const Vec controls[3]={w->p1,w->p2,w->p3};
    for(const Vec& p:controls)if(!__builtin_isfinite(p.x) || !__builtin_isfinite(p.y) || !__builtin_isfinite(p.z))
        return {O::UnsupportedBeforePublication};
    for(const auto& row:transform)for(float f:row)if(!__builtin_isfinite(f))return {O::UnsupportedBeforePublication};
    const EspTexWk* tw=&g_pEspSys->Esp_tex_tbl[esp->m_Tex_id];
    if(tw->Owner==0xD2 || !tw->pTpl || esp->m_Ptn_no>=tw->pTpl->numDescriptors)return {O::UnsupportedBeforePublication};
    const TEXDescriptor* td=TEXGet(tw->pTpl,RE4DC_FX_FLIP_PTN(esp->m_Ptn_no,tw->pTpl->numDescriptors));
    const TEXHeader* h=td?td->textureHeader:nullptr;
    // Same qualified opaque RGB565/clamp single-stage material as EF12.
    if(!h || !h->data || !h->width || !h->height || h->format!=4 || td->CLUTHeader || h->wrapS || h->wrapT)
        return {O::UnsupportedBeforePublication};
    re4dc::effect_uv12::Matrix24 tex;
    if(!re4dc::effect_uv12::capture(tw->mtx,tex))return {O::UnsupportedBeforePublication};
#if defined(RE4DC_MIST_CUT)
    const unsigned cls=MistCutClass(esp);
    if(re4dc_mist_cut&cls){MistCutNote(cls);return {O::PolicySkip};}
#endif
    unsigned r=s_effect_col.r,g=s_effect_col.g,b=s_effect_col.b,a=s_effect_col.a;
    if(esp->m_Tool_flg&0x80){r=r*4>255?255:r*4;g=g*4>255?255:g*4;b=b*4>255?255:b*4;}
    if(esp->m_Tool_flg&0x20000)a=a*4>255?255:a*4;
    if(a<=1)return {O::PolicySkip}; // source alpha >1; RGB565 sampled alpha is1
    Re4dcEffectQuad q{};q.image={h->data,nullptr,h->width,h->height,h->format,0xffffffffU,0};
    q.color=(a<<24)|(r<<16)|(g<<8)|b;q.src=esp->xA5;q.dst=esp->xA6;
    RE4DC_GXF_GET_PROJECTION(q.projection);RE4DC_GXF_GET_VIEWPORT(q.viewport);
    if(q.projection[0]!=0 || q.viewport[2]<=0 || q.viewport[3]<=0)return {O::UnsupportedBeforePublication};
    for(float f:q.projection)if(!__builtin_isfinite(f))return {O::UnsupportedBeforePublication};
    for(float f:q.viewport)if(!__builtin_isfinite(f))return {O::UnsupportedBeforePublication};
    const float near=q.projection[6]/(q.projection[5]-1),far=q.projection[6]/q.projection[5];
    if(!__builtin_isfinite(near) || !__builtin_isfinite(far) || near<=0 || far<=near)return {O::UnsupportedBeforePublication};
    Vec p0={0,1,1},p1={w->p1.x+1,w->p1.y+1,w->p1.z+1},
        p2={w->p2.x+1,w->p2.y,w->p2.z+1},p3={w->p3.x,w->p3.y,w->p3.z+1};
    const float step=1.0f/float(w->div);
    re4dc::NativeDrawProgress progress;
    float v=0,tv=0;
    for(unsigned i=0;i<w->div;++i){
        const float v1=v+step,tv1=tv+step;float u=0,tu=0;
        for(unsigned j=0;j<w->div;++j){
            const float u1=u+step,tu1=tu+step;
            const float us[4]={u,u1,u1,u},vs[4]={v,v,v1,v1};
            const float ts[4]={tu,tu1,tu1,tu},tt[4]={tv,tv,tv1,tv1};
            for(unsigned k=0;k<4;++k){
                Vec local,view;GetPosXY(&p0,&p1,&p2,&p3,us[k],vs[k],&local);
                PSMTXMultVec(transform,&local,&view);
                q.positions[k][0]=view.x;q.positions[k][1]=view.y;q.positions[k][2]=view.z;
                if(!re4dc::effect_uv12::transform(tex,ts[k],tt[k],q.u[k],q.v[k])){
                    progress.add({O::UnsupportedBeforePublication});return progress.result;
                }
            }
            // Quad emitter preserves source diagonal012/023 and clips near/far.
            if(!progress.add(re4dc_effect_quad_result(&q)))return progress.result;
            u=u1;tu=tu1;
        }
        v+=step;tv+=step;
    }
    return progress.result;
}
