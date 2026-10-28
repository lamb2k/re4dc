// Shared verbatim by MeshDraw and ScenerySelector. No include guard: this
// file supplies the same selection members to both contexts.
    bool chunk_ok()const{
#if RE4DC_WORLD_PORTAL29 && RE4DC_PS2_INTERIOR_CULL!=2
        // A proof-qualified portal supplies its own world-grid tests below;
        // it no longer sends surviving parts through the legacy selector.
        // Independent old PVS/impostor/check restrictions remain unchanged.
        if(wp29_wq && pc_mode==1U){
            if(!package.lod() || (lean::kMode&8U) || sg_groups>8U)return false;
#if RE4DC_PS2_PVS
            if(pvs_set)return false;
#endif
#if RE4DC_QUALITY_ASSETS
            if(skip_clusters)return false;
#endif
            return true;
        }
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
        using namespace re4dc::dfa26;
        if(!package.lod()){hit(WorldChunkNoLod);return false;}
        if(lean::kMode&8U){hit(WorldChunkCheckMode);return false;}
        if(sg_groups>8U){hit(WorldChunkGroups);return false;}
#if RE4DC_PS2_PVS
        if(pvs_set){hit(WorldChunkPvs);return false;}
#endif
#if RE4DC_PS2_INTERIOR_CULL
        if(pc_mode){hit(WorldChunkInterior);return false;}
#endif
#if RE4DC_QUALITY_ASSETS
        if(skip_clusters){hit(WorldChunkImpostor);return false;}
#endif
        return true;
#else
        return package.lod() && !(lean::kMode&8U) && sg_groups<=8U
#if RE4DC_PS2_PVS
            && !pvs_set
#endif
#if RE4DC_PS2_INTERIOR_CULL
            && !pc_mode
#endif
#if RE4DC_QUALITY_ASSETS
            && !skip_clusters
#endif
            ;
#endif
    }
#if RE4DC_SCENERY_STREAM && RE4DC_SG_SELECT_LEAN && !RE4DC_SCENERY_RECORD_SPLIT && !RE4DC_SCENERY_CONE && \
    !(defined(RE4DC_PREF_WALK) && RE4DC_PREF_WALK) && !(defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24) && \
    !(defined(RE4DC_SCENERY_SELECT_LEAN2) && RE4DC_SCENERY_SELECT_LEAN2)
    // SCENERY_STREAM: chunk_select below for this configuration as one tight loop: the same tests, expressions and
    // picks (box_class / box_mask_lean / sg_select_lean, or the knob-off functions under the runtime switch; the same LOD
    // rule), with the diagnostic counters dropped and the runtime switch read once per part.
    __attribute__((noinline)) unsigned chunk_select(Pick* out){
        const auto& lod=package.part_lods()[part_index];
        const auto* levels=package.levels();const auto* all=package.meshlets();
        const bool groups=sg && lean_am,box2=(lean::kMode&2U) && lean_am,slean=re4dc_sg_lean_on!=0;
        unsigned np=0;
        const auto* cl=package.clusters()+lod.first_cluster;
        for(const auto* const cend=cl+lod.cluster_count;cl!=cend;++cl){
#if RE4DC_WORLD_PORTAL29 && RE4DC_PS2_INTERIOR_CULL!=2
            if(wp29_wq && pc::grid_hidden(wp29_wq,cl->bounds_min,cl->bounds_max)>0){++pc::st.clusters;continue;}
#endif
            float lo[3],hi[3];
            for(unsigned a=0;a<3;++a){lo[a]=float(cl->bounds_min[a]);hi[a]=float(cl->bounds_max[a]);}
            unsigned cin;
            if(lean_inside)cin=2;
            else if(box2)cin=lean::box_class(lo,hi,mvq,lean_am,near,cull_far,nullptr);
            else {
                const re4dc::render::DrawBounds bounds{{lo[0],lo[1],lo[2]},{hi[0],hi[1],hi[2]}};
                cin=re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0)?1U:0U;
            }
            if(!cin)continue;
            float depth=-mvq[11],radius=0;
            for(unsigned a=0;a<3;++a){
                depth-=mvq[8+a]*(lo[a]+hi[a])*0.5f;
                radius+=std::fabs(mvq[8+a])*(hi[a]-lo[a])*0.5f;
            }
            depth-=radius;
            if(depth<near)depth=near;
            unsigned level=cl->level_count-1;
            while(level && levels[cl->first_level+level].error*lod_scale>depth)--level;
#if RE4DC_PS2_WORLD_NONEMPTY_LOD
            if(ps2)level=re4dc::room::nonempty_lod(levels+cl->first_level,cl->level_count,level);
#endif
            const auto& lv=levels[cl->first_level+level];
            const unsigned li0=lv.first_meshlet,li1=li0+lv.meshlet_count;
            if(cin==2 || !groups){
                for(unsigned li=li0;li<li1;++li){
#if RE4DC_WORLD_PORTAL29 && RE4DC_PS2_INTERIOR_CULL!=2
                    if(wp29_wq && pc::grid_hidden(wp29_wq,all[li].bounds_min,all[li].bounds_max)>0){++pc::st.meshlets;continue;}
#endif
                    if(cin!=2){
                        const auto& l=all[li];
                        const re4dc::render::DrawBounds bounds{
                            {float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])},
                            {float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])}};
                        if(!re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0))continue;
                    }
                    Pick& pk=out[np++];pk.let=std::uint16_t(li);pk.nr=0xffU;
                }
                continue;
            }
            const std::uint8_t* gsrc=sg+16U*sg_groups*li0;
            for(unsigned li=li0;li<li1;++li,gsrc+=16U*sg_groups){
                const auto& l=all[li];
#if RE4DC_WORLD_PORTAL29 && RE4DC_PS2_INTERIOR_CULL!=2
                if(wp29_wq && pc::grid_hidden(wp29_wq,l.bounds_min,l.bounds_max)>0){++pc::st.meshlets;continue;}
#endif
                const float blo[3]={float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])};
                const float bhi[3]={float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])};
                const int mk=slean?lean::box_mask_lean(blo,bhi,mvq,lean_am,near,cull_far)
                                  :lean::box_mask(blo,bhi,mvq,lean_am,near,cull_far);
                if(mk<0)continue;
                Pick& pk=out[np++];
                pk.let=std::uint16_t(li);pk.nr=0xffU;
                if(!mk)continue;
                const auto* g=reinterpret_cast<const std::uint16_t*>(gsrc);
                unsigned glo,ghi,culled,nr;std::uint16_t r0[8],r1[8];
                if(slean){
                    if(!sg_lp_ok){lean::sg_coef_lean(mvq,near,sg_lp);sg_lp_ok=true;}
                    nr=lean::sg_select_lean(g,sg_groups,sg_lp,unsigned(mk),r0,r1,glo,ghi,culled);
                }else{
                    if(!sg_coef_ok){lean::sg_coef(mvq,near,sg_coef);sg_coef_ok=true;}
                    nr=lean::sg_select(g,sg_groups,sg_coef,unsigned(mk),r0,r1,glo,ghi,culled);
                }
                if(culled){
                    unsigned bits=0,prev=0,j=0;
                    for(unsigned k=0;k<sg_groups && j<nr;++k){
                        const unsigned gend=g[8*k+6];
                        if(gend==prev)continue;
                        if(r0[j]==prev && r1[j]==gend){bits|=1U<<k;++j;}
                        prev=gend;
                    }
                    pk.nr=std::uint8_t(nr);pk.gmask=std::uint8_t(bits);pk.lo=std::uint8_t(glo);pk.hi=std::uint8_t(ghi);
                }
            }
        }
        return np;
    }
#else
    // Picks appended at out (room for part.meshlet_count); returns how many.
    __attribute__((noinline)) unsigned chunk_select(Pick* out){
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        const re4dc::wc24::Scope wc_selection(re4dc::wc24::Selection);
        unsigned wc_indexed=0,wc_plain=0,wc_empty=0;
#endif
        const auto& lod=package.part_lods()[part_index];
#if RE4DC_SCENERY_RECORD_SPLIT
        const auto* clusters=package.clusters();const auto* levels=package.levels();
#else
        const auto* clusters=package.clusters();const auto* levels=package.levels();const auto* all=package.meshlets();
#endif
        const bool groups=sg && lean_am;
        unsigned np=0;
#if RE4DC_SCENERY_CONE
        // SCENERY_CONE: the eye in grid coordinates (view = M g + t: e = -M^-1 t) and the culled side's sign (part cull
        // 1 CCW / 2 CW, det(M), and the projection's fixed handedness RE4DC_SCENERY_CONE_SIGN).
        bool cone_on=sg && cone::pkg==static_cast<const void*>(&package) && p.cull>0U && p.cull<=2U;
        float ex=0,ey=0,ez=0,csgn=1;
        if(cone_on){
            const float* m=mvq;
            const float c0=m[5]*m[10]-m[6]*m[9],c1=m[6]*m[8]-m[4]*m[10],c2=m[4]*m[9]-m[5]*m[8];
            const float det=m[0]*c0+m[1]*c1+m[2]*c2;
            if(!(std::fabs(det)>1e-20f))cone_on=false;
            else{
                const float id=-1.0f/det,tx=m[3],ty=m[7],tz=m[11];
                // e = -adj(M) t / det
                ex=id*(c0*tx+(m[2]*m[9]-m[1]*m[10])*ty+(m[1]*m[6]-m[2]*m[5])*tz);
                ey=id*(c1*tx+(m[0]*m[10]-m[2]*m[8])*ty+(m[2]*m[4]-m[0]*m[6])*tz);
                ez=id*(c2*tx+(m[1]*m[8]-m[0]*m[9])*ty+(m[0]*m[5]-m[1]*m[4])*tz);
                csgn=float(RE4DC_SCENERY_CONE_SIGN)*(p.cull==1U?1.0f:-1.0f)*(det>0.0f?1.0f:-1.0f);
            }
        }
#endif
        for(unsigned c=lod.first_cluster;c<lod.first_cluster+lod.cluster_count;++c){
            const auto& cl=clusters[c];
#if RE4DC_WORLD_PORTAL29 && RE4DC_PS2_INTERIOR_CULL!=2
            if(wp29_wq && pc::grid_hidden(wp29_wq,cl.bounds_min,cl.bounds_max)>0){++pc::st.clusters;continue;}
#endif
            float lo[3],hi[3];
            for(unsigned a=0;a<3;++a){lo[a]=float(cl.bounds_min[a]);hi[a]=float(cl.bounds_max[a]);}
            unsigned cin;
            if(lean_inside){cin=2;++lean::st.skipped;}
            else if((lean::kMode&2U) && lean_am)cin=lean::box_class(lo,hi,mvq,lean_am,near,cull_far,nullptr);
            else {
                const re4dc::render::DrawBounds bounds{{lo[0],lo[1],lo[2]},{hi[0],hi[1],hi[2]}};
                cin=re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0)?1U:0U;
            }
            if(!cin){++stats.clusters_culled;continue;}
            if(cin==2)++lean::st.cl_inside;
            ++stats.clusters_visible;
            float depth=-mvq[11],radius=0;
            for(unsigned a=0;a<3;++a){
                depth-=mvq[8+a]*(lo[a]+hi[a])*0.5f;
                radius+=std::fabs(mvq[8+a])*(hi[a]-lo[a])*0.5f;
            }
            depth-=radius;
            if(depth<near)depth=near;
            unsigned level=cl.level_count-1;
            while(level && levels[cl.first_level+level].error*lod_scale>depth)--level;
#if RE4DC_PS2_WORLD_NONEMPTY_LOD
            if(ps2)level=re4dc::room::nonempty_lod(levels+cl.first_level,cl.level_count,level);
#endif
            ++stats.lod_draws[level<3?level:3];
            const auto& lv=levels[cl.first_level+level];
            for(unsigned i=0;i<lv.meshlet_count;++i){
                const unsigned li=lv.first_meshlet+i;
#if RE4DC_SCENERY_RECORD_SPLIT
                const auto& l=package.bounds(li); // emit metadata is requested only when needed
#else
                const auto& l=all[li];
#endif
#if RE4DC_WORLD_PORTAL29 && RE4DC_PS2_INTERIOR_CULL!=2
                if(wp29_wq && pc::grid_hidden(wp29_wq,l.bounds_min,l.bounds_max)>0){++pc::st.meshlets;continue;}
#endif
#if defined(RE4DC_PREF_WALK) && RE4DC_PREF_WALK
#if RE4DC_SCENERY_RECORD_SPLIT
                if(li+1U<package.header().meshlet_count && RE4DC_C20_PREF_ON())RE4DC_C20_PREF(&package.bounds(li+1U));
#else
                if(RE4DC_C20_PREF_ON())RE4DC_C20_PREF(&all[li+1]);   // PREF_WALK: the next meshlet header (bounds)
#endif
#endif
                unsigned mask=0;
                if(cin==2)++lean::st.skipped;
                else if(groups){
#if defined(RE4DC_SCENERY_SELECT_LEAN2) && RE4DC_SCENERY_SELECT_LEAN2
#if RE4DC_SG_SELECT_LEAN
                    const int mk=re4dc_sg_lean_on?lean::box_mask_grid_lean(l,mvq,lean_am,near,cull_far)
                                                 :lean::box_mask_grid(l,mvq,lean_am,near,cull_far);
#else
                    const int mk=lean::box_mask_grid(l,mvq,lean_am,near,cull_far);
#endif
#else
                    const float blo[3]={float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])};
                    const float bhi[3]={float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])};
#if RE4DC_SG_SELECT_LEAN
                    const int mk=re4dc_sg_lean_on?lean::box_mask_lean(blo,bhi,mvq,lean_am,near,cull_far)
                                                 :lean::box_mask(blo,bhi,mvq,lean_am,near,cull_far);
#else
                    const int mk=lean::box_mask(blo,bhi,mvq,lean_am,near,cull_far);
#endif
#endif
                    if(mk<0){++stats.groups_culled;continue;}
                    mask=unsigned(mk);
                }else{
                    const re4dc::render::DrawBounds bounds{
                        {float(l.bounds_min[0]),float(l.bounds_min[1]),float(l.bounds_min[2])},
                        {float(l.bounds_max[0]),float(l.bounds_max[1]),float(l.bounds_max[2])}};
                    if(!re4dc::render::group_visible(bounds,mvq,p.projection,p.viewport,near,cull_far,0)){++stats.groups_culled;continue;}
                }
                Pick& pk=out[np++];
                pk.let=std::uint16_t(li);pk.nr=0xffU;
                if(groups && mask){
                    const auto* g=reinterpret_cast<const std::uint16_t*>(sg+16U*sg_groups*li);
#if defined(RE4DC_SCENERY_SELECT_LEAN2) && RE4DC_SCENERY_SELECT_LEAN2
#if RE4DC_SG_SELECT_LEAN
                    if(re4dc_sg_lean_on){
                        if(!sg_lp_ok){lean::sg_coef_lean(mvq,near,sg_lp);sg_lp_ok=true;}
                        const unsigned selected=lean::sg_pick_lean(g,sg_groups,sg_lp,mask);
                        ++lean::lst.calls;++lean::st.sg_tests;
                        const unsigned culled=(selected>>24)&15U;
                        if(culled){
                            const unsigned nr=selected>>28,glo=(selected>>8)&255U,ghi=(selected>>16)&255U;
                            lean::st.sg_culled+=culled;++lean::st.sg_meshlets;
#if RE4DC_SCENERY_RECORD_SPLIT
                            lean::st.sg_vskip+=nr?package.emit(li).vertex_count-(ghi-glo+1U):package.emit(li).vertex_count;
#else
                            lean::st.sg_vskip+=nr?l.vertex_count-(ghi-glo+1U):l.vertex_count;
#endif
                            pk.nr=std::uint8_t(nr);pk.gmask=std::uint8_t(selected);
                            pk.lo=std::uint8_t(glo);pk.hi=std::uint8_t(ghi);
                        }
                    }else{
#endif
                    unsigned glo,ghi,culled;std::uint16_t r0[8],r1[8];
                    if(!sg_coef_ok){lean::sg_coef(mvq,near,sg_coef);sg_coef_ok=true;}
                    const unsigned nr=lean::sg_select(g,sg_groups,sg_coef,mask,r0,r1,glo,ghi,culled);
                    ++lean::st.sg_tests;
                    if(culled){
                        lean::st.sg_culled+=culled;++lean::st.sg_meshlets;
#if RE4DC_SCENERY_RECORD_SPLIT
                        lean::st.sg_vskip+=nr?package.emit(li).vertex_count-(ghi-glo+1U):package.emit(li).vertex_count;
#else
                        lean::st.sg_vskip+=nr?l.vertex_count-(ghi-glo+1U):l.vertex_count;
#endif
                        // the visible groups as bits: group k (a record whose strip end moves) is kept when its range
                        // is the next one sg_select returned
                        unsigned bits=0,prev=0,j=0;
                        for(unsigned k=0;k<sg_groups && j<nr;++k){
                            const unsigned gend=g[8*k+6];
                            if(gend==prev)continue;
                            if(r0[j]==prev && r1[j]==gend){bits|=1U<<k;++j;}
                            prev=gend;
                        }
                        pk.nr=std::uint8_t(nr);pk.gmask=std::uint8_t(bits);pk.lo=std::uint8_t(glo);pk.hi=std::uint8_t(ghi);
                    }
#if RE4DC_SG_SELECT_LEAN
                    }
#endif
#else
                    unsigned glo,ghi,culled,nr;std::uint16_t r0[8],r1[8];
#if RE4DC_SG_SELECT_LEAN
                    if(re4dc_sg_lean_on){
                        if(!sg_lp_ok){lean::sg_coef_lean(mvq,near,sg_lp);sg_lp_ok=true;}
                        nr=lean::sg_select_lean(g,sg_groups,sg_lp,mask,r0,r1,glo,ghi,culled);
                        ++lean::lst.calls;
                    }else{
                        if(!sg_coef_ok){lean::sg_coef(mvq,near,sg_coef);sg_coef_ok=true;}
                        nr=lean::sg_select(g,sg_groups,sg_coef,mask,r0,r1,glo,ghi,culled);
                    }
#else
                    if(!sg_coef_ok){lean::sg_coef(mvq,near,sg_coef);sg_coef_ok=true;}
                    nr=lean::sg_select(g,sg_groups,sg_coef,mask,r0,r1,glo,ghi,culled);
#endif
                    ++lean::st.sg_tests;
                    if(culled){
                        lean::st.sg_culled+=culled;++lean::st.sg_meshlets;
#if RE4DC_SCENERY_RECORD_SPLIT
                        lean::st.sg_vskip+=nr?package.emit(li).vertex_count-(ghi-glo+1U):package.emit(li).vertex_count;
#else
                        lean::st.sg_vskip+=nr?l.vertex_count-(ghi-glo+1U):l.vertex_count;
#endif
                        // the visible groups as bits: group k (a record whose strip end moves) is kept when its range
                        // is the next one sg_select returned
                        unsigned bits=0,prev=0,j=0;
                        for(unsigned k=0;k<sg_groups && j<nr;++k){
                            const unsigned gend=g[8*k+6];
                            if(gend==prev)continue;
                            if(r0[j]==prev && r1[j]==gend){bits|=1U<<k;++j;}
                            prev=gend;
                        }
                        pk.nr=std::uint8_t(nr);pk.gmask=std::uint8_t(bits);pk.lo=std::uint8_t(glo);pk.hi=std::uint8_t(ghi);
                    }
#endif
                }
#if RE4DC_SCENERY_CONE
                if(cone_on && pk.nr){
                    // the groups still drawn (all non-empty ones for a whole pick), then each one's cone
                    const auto* g=reinterpret_cast<const std::uint16_t*>(sg+16U*sg_groups*li);
                    const std::uint8_t* cr=cone::rec+8U*sg_groups*li;
                    unsigned keep=0,prev=0;
                    for(unsigned q=0;q<sg_groups;++q){const unsigned gend=g[8*q+6];if(gend!=prev)keep|=1U<<q;prev=gend;}
                    if(pk.nr!=0xffU)keep&=pk.gmask;
                    unsigned rej=0;
                    for(unsigned q=0;q<sg_groups;++q){
                        const std::uint8_t* r=cr+8U*q;
                        if(!((keep>>q)&1U) || !r[3])continue;
                        const std::uint16_t* b=g+8*q;
                        const float vx=0.5f*(float(b[0])+float(b[3]))-ex,vy=0.5f*(float(b[1])+float(b[4]))-ey,
                                    vz=0.5f*(float(b[2])+float(b[5]))-ez;
                        const float d=csgn*(float(std::int8_t(r[0]))*vx+float(std::int8_t(r[1]))*vy+float(std::int8_t(r[2]))*vz);
                        float R;std::memcpy(&R,r+4,4);
                        ++cone::tests;
                        if(d>R){const float e=d-R;if(e*e>cone::tab2[r[3]]*(vx*vx+vy*vy+vz*vz))rej|=1U<<q;}
                    }
                    if(rej){
                        keep&=~rej;
                        unsigned nr=0,vlo=255,vhi=0;
#if RE4DC_SCENERY_RECORD_SPLIT
                        const unsigned was=pk.nr==0xffU?package.emit(li).vertex_count:unsigned(pk.hi-pk.lo+1U);
#else
                        const unsigned was=pk.nr==0xffU?l.vertex_count:unsigned(pk.hi-pk.lo+1U);
#endif
                        for(unsigned q=0;q<sg_groups;++q)if((keep>>q)&1U){
                            ++nr;const unsigned v0=g[8*q+7]&255U,v1=g[8*q+7]>>8;
                            if(v0<vlo)vlo=v0;
                            if(v1>vhi)vhi=v1;
                        }
                        cone::rejects+=__builtin_popcount(rej);
                        if(!nr){--np;++cone::picks_dropped;cone::vskip+=was;continue;}
                        cone::vskip+=was-(vhi-vlo+1U);
                        pk.nr=std::uint8_t(nr);pk.gmask=std::uint8_t(keep);pk.lo=std::uint8_t(vlo);pk.hi=std::uint8_t(vhi);
                    }
                }
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
                // Only retained picks: a cone rejection above removes its
                // provisional record. nr==0 still owns a replay/setup pick.
#if RE4DC_SCENERY_RECORD_SPLIT
                if(package.indexed(package.emit(li)))++wc_indexed;else ++wc_plain;
#else
                if(package.indexed(l))++wc_indexed;else ++wc_plain;
#endif
                if(!pk.nr)++wc_empty;
#endif
            }
        }
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
        re4dc::wc24::count(re4dc::wc24::PickedIndexed,wc_indexed);
        re4dc::wc24::count(re4dc::wc24::PickedPlain,wc_plain);
        re4dc::wc24::count(re4dc::wc24::PickedEmpty,wc_empty);
#endif
        return np;
    }
#endif
