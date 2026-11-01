// Current source proof, never retained across a loader/queue operation.
static int EspMaskClass12(cEsp* esp){
    if(!esp || !pG || !g_pEspSys || esp->m_Id>=0xff || EspTransTbl[esp->m_Id]!=EspCommonTrans ||
       !(esp->m_Tool_flg&0x4000) || (esp->m_Flg&0x10) || esp->m_Id==0x1b ||
       esp->m_Id==0x15 || esp->m_Id==0x48 || esp->m_Shimmer_type ||
       (esp->m_Tool_flg&(0x40|0x80|0x2000|0x10000|0x100000|0x200000|0x808000)) ||
       esp->xA4!=1 || esp->xA5!=4 || esp->xA6!=5 || !EspSpriteEligible12(esp,true,false))return 0;
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    if(re4dc_rtt_capturing())return 0;
#endif
    const EspTexWk& base=g_pEspSys->Esp_tex_tbl[esp->m_Tex_id];
    const EspTexWk& mask=g_pEspSys->Esp_tex_tbl[esp->m_MaskTex_id];
    if(base.Owner==0xD2 || mask.Owner==0xD2 || !base.pTpl || !mask.pTpl ||
       esp->m_Ptn_no>=base.pTpl->numDescriptors || esp->m_MaskPtn_no>=mask.pTpl->numDescriptors ||
       !base.pTexObj || esp->m_Ptn_no>=base.nTexObj)return 0;
    const auto* color=TEXGet(base.pTpl,esp->m_Ptn_no);
    const auto* alpha=TEXGet(mask.pTpl,esp->m_MaskPtn_no);
    if(!color || !alpha || !color->textureHeader || !alpha->textureHeader || alpha->CLUTHeader)return 0;
    const auto* a=alpha->textureHeader;
    const auto* c=color->textureHeader;
    if(a->format!=4 || !a->data || !a->width || !a->height || a->width>1024 || a->height>1024 ||
       !c->data || !c->width || !c->height || c->width>1024 || c->height>1024)return 0;
    // EspTexSet binds this actual pattern object, not header wrap fields.
    unsigned object[8];
    static_assert(sizeof(GXTexObj)==sizeof object,"bounded GX word snapshot");
    std::memcpy(object,&base.pTexObj[esp->m_Ptn_no],sizeof object);
    if(object[0]!=reinterpret_cast<std::uintptr_t>(c->data) || object[1]!=((unsigned(c->width)<<16)|c->height) ||
       object[2]!=c->format || !re4dc::cloth_material11::linear_clamp(object))return 0;
    for(unsigned r=0;r<2;++r)for(unsigned col=0;col<4;++col){
        if(base.mtx[r][col]!=(r==col?1.0f:0.0f) || !__builtin_isfinite(mask.mtx[r][col]))return 0;
    }
    return 1;
}
