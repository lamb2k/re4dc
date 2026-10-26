// WORLD_SG_CELL=1 (lane worldopt26 2026-10-26; game30-side knob in worldopt26.mk; render only, default 0).
// Interior cell cull per strip group. With 256-vertex meshlets (SCENERY_N256) one meshlet box often reaches from the
// house into the outside, so the per-meshlet cell test (PS2_INTERIOR_CULL, pc::grid_hidden) keeps the whole meshlet;
// the 64-vertex meshlets it replaced were culled piece by piece (perf-t22-26: r100 house +2.2 ms MODELLED). Here a
// meshlet of a placement under the cell cull (pc_mode 1) tests each strip group's grid box: outside the frustum (the
// strip-group test, sg_select) or hidden from the eye's cell (no portal frustum sees it) drops the group; the corner
// range of the groups left is transformed and only their strips are walked (as PS2_STRIP_GROUPS does). Groups that meet
// the house box are kept (grid_hidden -1). No group dropped: the existing path runs unchanged.
// Hook: one macro on an existing native_static.cpp line (empty with the knob off: no line moves, knob-off object
// identical). Included from ps2_interior_cell.inc (inside namespace pc; the macro expands in the Emitter).
#ifndef RE4DC_WORLDOPT26_SG_CELL_INC
#define RE4DC_WORLDOPT26_SG_CELL_INC
#if defined(RE4DC_WORLD_SG_CELL) && RE4DC_WORLD_SG_CELL
#if !RE4DC_PS2_STRIP_GROUPS || !RE4DC_PS2_INTERIOR_CULL || RE4DC_MESH_VP_SCHED!=1 || RE4DC_SCENERY_DEDUP
#error WORLD_SG_CELL needs PS2_STRIP_GROUPS=1, PS2_INTERIOR_CULL, MESH_VP_SCHED=1 and SCENERY_DEDUP=0
#endif
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
#define RE4DC_WO26_COUNT(vn) re4dc::wc24::count(re4dc::wc24::Transformed,(vn));
#define RE4DC_WO26_EMPTY re4dc::wc24::count(re4dc::wc24::PickedEmpty);
#else
#define RE4DC_WO26_COUNT(vn)
#define RE4DC_WO26_EMPTY
#endif
inline unsigned wo26_meshlets=0,wo26_groups=0; // meshlets with groups dropped by this cull / groups dropped
#undef RE4DC_WO26_SG_CELL
#define RE4DC_WO26_SG_CELL \
    if(sg && pc_mode==1U && pc_wq && checks==vp::kChecksAll && sq && lean_am){ \
        const auto* wg=reinterpret_cast<const std::uint16_t*>(sg+16U*sg_groups*unsigned(&l-package.meshlets())); \
        unsigned wprev=0,wnr=0,wlo=255,whi=0,wcut=0;std::uint16_t w0[8],w1[8]; \
        if(!sg_whole && !sg_coef_ok){lean::sg_coef(mvq,near,sg_coef);sg_coef_ok=true;} \
        for(unsigned q=0;q<sg_groups;++q){ \
            const std::uint16_t* gq=wg+8U*q;const unsigned gend=gq[6]; \
            if(gend==wprev)continue; \
            bool out=false; \
            if(!sg_whole){unsigned a,b,c;std::uint16_t s0[1],s1[1];out=!lean::sg_select(gq,1,sg_coef,sg_mask,s0,s1,a,b,c);} \
            if(!out)out=pc::grid_hidden(pc_wq,gq,gq+3)>0; \
            if(out){++wcut;wprev=gend;continue;} \
            w0[wnr]=std::uint16_t(wprev);w1[wnr]=std::uint16_t(gend);++wnr; \
            const unsigned v0=gq[7]&255U,v1=gq[7]>>8; \
            if(v0<wlo)wlo=v0; \
            if(v1>whi)whi=v1; \
            wprev=gend; \
        } \
        if(wcut){ \
            ++lean::st.sg_tests;lean::st.sg_culled+=wcut;++lean::st.sg_meshlets;++pc::wo26_meshlets;pc::wo26_groups+=wcut; \
            if(!wnr){lean::st.sg_vskip+=l.vertex_count;RE4DC_WO26_EMPTY return 1;} \
            const unsigned vn=whi-wlo+1U;lean::st.sg_vskip+=l.vertex_count-vn; \
            RE4DC_WO26_COUNT(vn) \
            vp::transform_sched<vp::kChecksAll>(in+wlo,vn,cache+wlo,outcodes+wlo,k); \
            const std::uint8_t* const wsb=package.strip_begin(l); \
            for(unsigned i=0;i<wnr;++i){int result=1;strips_lean(wsb+w0[i],wsb+w1[i],base,batch,result);if(result<=0)return result;} \
            return 1; \
        } \
    }
#endif
#endif
