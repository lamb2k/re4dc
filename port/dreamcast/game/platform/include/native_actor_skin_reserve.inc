// ACTOR_SKIN_RESERVE: included after the source/owner skin registry. No heap,
// source-data reads, palette handles or extra slots. Empty-palette entries only
// reserve keys; every palette/materialization reader must reject them.
static_assert(kSkins>=kRe4dcActorSkinKeys && kSkins<=256,"reservation indices must fit the existing skin table");
extern "C" int re4dc_actor_skin_reserve(unsigned source_frame,const void* const* infos,unsigned n) {
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if(skin_recipe_building)return 0;
#endif
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    if(skin_admission_pending.serial)return 0;
#endif
    if(!infos || !n || n>kRe4dcActorSkinKeys)return 0;
    for(unsigned k=0;k<n;++k){
        if(!infos[k])return 0;
        for(unsigned j=0;j<k;++j)if(infos[j]==infos[k])return 0;
    }
    const bool current=source_frame==skin_frame;
    // A source plan cannot retake live owner slots within the same frame.
    if(current)for(unsigned i=0;i<skin_count;++i)if(owned_skins[i].serial)return 0;
    // The source batch remains bounded to 64 keys even with the optional
    // 80-entry registry. Byte indices cover either table without more scratch.
    unsigned char index[kRe4dcActorSkinKeys];unsigned high=current?skin_count:0;
    for(unsigned k=0;k<n;++k){
        unsigned at=kSkins;
        if(current)for(unsigned i=0;i<skin_count;++i)
            if(skins[i].info==infos[k] && !skins[i].positions){at=i;break;}
        if(at==kSkins){
            for(unsigned i=0;i<high;++i){
                bool chosen=false;for(unsigned j=0;j<k;++j)chosen|=index[j]==i;
                if(!chosen && !skins[i].info && !owned_skins[i].serial){at=i;break;}
            }
            if(at==kSkins){if(high==kSkins)return 0;at=high++;}
        }
        index[k]=at;
    }
    // Validate the entire batch before starting a source frame or changing a
    // slot. Frame replacement revokes old owners exactly as source register.
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if(!current){owned_skin_clear();owned_skin_invalidate_frames();
        skin_recipe_frame_retire();
        skin_frame=source_frame;skin_count=0;}
#else
    if(!current){owned_skin_clear();owned_skin_invalidate_frames();skin_frame=source_frame;skin_count=0;}
#endif
    for(unsigned k=0;k<n;++k){
        const unsigned i=index[k];
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
        if(i>=skin_count || !skins[i].info)skins[i]={infos[k],nullptr,nullptr,0,kSkinRecipeNominee};
#else
        if(i>=skin_count || !skins[i].info)skins[i]={infos[k],nullptr,nullptr,0,0};
#endif
    }
    skin_count=high;
    return 1;
}
