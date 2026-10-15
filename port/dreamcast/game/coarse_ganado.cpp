// COARSE_GANADO=1: isolated, opaque 4K Leon presentation proof. The game owns
// the pose, part visibility and simulation. Input is the offline-qualified
// native actor representation; no source game data is overwritten.
#include "global.h"
#include "model.h"
#include "native_actor.hpp"
#include "ganado874_runtime.h" // private generated asset, outside the repository
#include <cstring>
#include <kos/fs.h>
#include "ganado874_variants.h"
#if RE4DC_COARSE_SKIN_FTRV
#include "coarse_skin.h"
#endif

extern "C" void re4dc_log(const char*, ...);
extern "C" void GXGetProjectionv(float*);
extern "C" void GXGetViewportv(float*);
extern "C" void re4dc_bind_actor_frame();
extern "C" int re4dc_coarse_leon_texture_ready(const Re4dcUiImage*,unsigned,unsigned);

namespace {
unsigned texture_token;
const Re4dcUiImage image{&texture_token,nullptr,512,512,6,0xffffffffU,0};
constexpr unsigned crc=0x2cfd7d1dU, fnv=0x85a7fa09U;
struct Binding { cModel* owner; unsigned serial; cParts* list; cParts* parts[34]; cModelInfo* infos[4]; const ModelData* qualified[4]; };
Binding bindings[32];
Binding* bound;
unsigned replacement;
int mesh_limit=RE4DC_COARSE_GANADO_LIMIT;
bool config_read;
int stress_layout;
unsigned frame_meshes, frame_emitted, frame_candidates, frame_fallback, frame_triangles;
Mtx local_skin[34];
alignas(32) float palette[256][12]; // one synchronous opaque info at a time
re4dc::render::SourceLighting light; // constant texture colour for this proof
unsigned attempts, drawn, fallback, rejected, missing_texture;
#if RE4DC_COARSE_SKIN_FTRV
// FTRV palettes: entries built once from the generated weights; T only for the bones they use.
constexpr unsigned kSkinStream = 8192;
alignas(32) unsigned char skin_stream[kSkinStream];
alignas(32) float bone_T[34][12];
CoarseBoneJob skin_jobs[34];
unsigned char skin_bone[34];
unsigned skin_first[4], skin_groups[4], skin_used, skin_state;  // first: byte offset; state: 0 not built, 1 ready, 2 does not fit
#if RE4DC_COARSE_SKIN_FTRV == 2
CoarseSkinCheck skin_chk;
#endif
bool skin_init() {
    if (skin_state) return skin_state == 1;
    unsigned n = 0, bytes = 0; unsigned char used[34] = {};
    for (unsigned i = 0; i < 4; ++i) {
        const auto& c = ganado874::chunks[i];
        for (unsigned j = 0; j < c.palette_count; ++j)
            for (unsigned k = 0; k < c.weights[j].count; ++k)
                if (c.weights[j].bone[k] >= 34) { skin_state = 2; return false; }
        skin_first[i] = bytes;
        const unsigned b = coarse_group_build(c.weights, c.palette_count, skin_stream + bytes, kSkinStream - bytes, &skin_groups[i], used);
        if (!b) { skin_state = 2; re4dc_log("COARSE_GANADO skin palette does not fit\n"); return false; }
        bytes += b; n += c.palette_count;
    }
    skin_used = 0;
    for (unsigned b = 0; b < 34; ++b) if (used[b]) skin_bone[skin_used++] = (unsigned char)b;
    re4dc_log("COARSE_GANADO skin ftrv=%d entries=%u bones=%u stream=%u\n", RE4DC_COARSE_SKIN_FTRV, n, skin_used, bytes);
    skin_state = 1;
    return true;
}
#endif

unsigned fingerprint(const void* data) {
    const auto* p=(const unsigned char*)data;unsigned h=2166136261U;
    for(unsigned i=0;i<64;++i)h=(h^p[i])*16777619U;
    return h;
}
bool bind_source(cModel* m) {
    if(!m || (m->id<0x10 || m->id>0x20) || m->nParts!=34 || !m->pList || (m->be_flag&0x4000))return false;
    bound=nullptr;
    for(auto& entry:bindings)if(entry.owner==m && entry.serial==m->serial && entry.list==m->pList){bound=&entry;break;}
    if(!bound){
        Binding& entry=bindings[replacement++%32];
        std::memset(&entry,0,sizeof(entry));
        cParts* p=m->pList;
        for(unsigned i=0;i<34;++i){
            if(!p)return false;entry.parts[i]=p;
            // Observed variants have identical bone axes and hierarchy, but
            // different rest translations. Retarget this benchmark mesh with
            // its own inverse bind; never overwrite the game's skeleton.
            for(unsigned row=0;row<3;++row)for(unsigned col=0;col<3;++col)
                if(__builtin_fabsf(p->lt_inv_mat[row][col]-ganado874::bind[i][row*4+col])>.001f)return false;
            p=p->pList;
        }
        if(p)return false;
        for(unsigned i=0;i<34;++i){
            const int parent=ganado874::parents[i];
            const cCoord* want=parent<0?(const cCoord*)m:(const cCoord*)entry.parts[parent];
            if(entry.parts[i]->pParent!=want)return false;
        }
        entry.owner=m;entry.serial=m->serial;entry.list=m->pList;bound=&entry;
    }
    auto& infos=bound->infos;auto& qualified=bound->qualified;
    std::memset(infos,0,sizeof(infos));
    unsigned count=0;
    for(cModelInfo* info=m->pModelInfo;info && count<32;info=info->pList,++count){
        const ModelData* d=info->pData;if(!d || !d->vtxOrig)continue;
        const unsigned n=d->weight_ext_num>255?d->weight_ext_num:d->weight_palette_num;
        for(const auto& s:ganado874::variants){
            const unsigned i=s.role;
            if(d->nVtx!=s.positions || d->nNrm!=s.normals || n!=s.palette)continue;
            if(qualified[i]!=d){if(fingerprint(d->vtxOrig)!=s.vertex_hash)continue;qualified[i]=d;}
            if(infos[i])return false;
            infos[i]=info;break; // one matched variant, not every signature for this role
        }
    }
    for(unsigned i=0;i<4;++i)if(!infos[i])return false;
    return true;
}
bool visible(const cModelInfo* info) {
    // ModelTrans queues ot_type 7 twice; commonModelTrans selects bit 0x40
    // in its second pass (and sets model bit 0x08000000 after the first).
    // Coarse submits Leon once, so include both source pass groups here.
    // Bit 8 and invisible_factor remain the actual presentation visibility.
    return (info->be_flag&8) && info->invisible_factor>0;
}
}

// These hooks are called before model_bridge casts a cModelInfo pointer.
#if defined(RE4DC_GC_CENSUS_TRIM) && RE4DC_GC_CENSUS_TRIM
#include "chunk_find.h"
#endif
extern "C" int re4dc_coarse_ganado_source(const void* info,Re4dcActorSource* out) {
#if defined(RE4DC_GC_CENSUS_TRIM) && RE4DC_GC_CENSUS_TRIM
    if(const auto* p=re4dc_chunk_find(ganado874::chunks,info)){
        const auto& c=*p;*out={c.positions,c.normals,c.position_count,c.normal_count,c.palette_count,0};return 1;
    }
#else
    for(const auto& c:ganado874::chunks)if(info==&c){
        *out={c.positions,c.normals,c.position_count,c.normal_count,c.palette_count,0};return 1;
    }
#endif
    return 0;
}
extern "C" int re4dc_coarse_ganado_texture_key(const Re4dcUiImage* i,unsigned* c,unsigned* f) {
    if(i->pixels!=image.pixels || i->width!=512 || i->height!=512 || i->format!=6 || i->palette_bytes)return 0;
    *c=crc;*f=fnv;return 1;
}

// Called with coarse store queues closed. Opaque submissions complete here;
// none borrow the shared palette after the next info overwrites it.
extern "C" int re4dc_coarse_ganado(cModel* m) {
    ++frame_candidates;
    if(mesh_limit>=0 && frame_meshes>=unsigned(mesh_limit))return stress_layout?1:0;
    ++attempts;
    if(!bind_source(m)){
        ++frame_fallback;
        if(++fallback<=12)re4dc_log("COARSE_GANADO unsupported id=%u parts=%u\n",m?m->id:255,m?m->nParts:0);
        return 0;
    }
    auto& infos=bound->infos;auto& parts=bound->parts;
    if(m->invisible_factor*m->invisible_factor2<=0)return 1;
    if(m->invisible_factor*m->invisible_factor2<.999f)return 0;
    for(unsigned i=0;i<4;++i)if(visible(infos[i])) {
        if(infos[i]->blend_mode || infos[i]->invisible_factor<.999f)return 0;
        // The approved face is a bone-driven expression simplification (info 3).
        // Other morphing geometry and animated materials remain unsupported.
        if(((infos[i]->be_flag&2) && i!=3) || infos[i]->flagsDC)return 0;
    }
    if(!re4dc_coarse_leon_texture_ready(&image,crc,fnv)){
        if(++missing_texture<=3)re4dc_log("COARSE_GANADO texture unavailable\n");return 0;
    }
    re4dc_bind_actor_frame();
    Mtx inv,relative,mv,pm;
    if(!PSMTXInverse(m->pParts->mat,inv))return 0;
#if RE4DC_COARSE_SKIN_FTRV
    if(!skin_init())return 0;
    {
        alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
        for(unsigned u=0;u<skin_used;++u){
            const unsigned b=skin_bone[u];
            skin_jobs[u]={&parts[b]->mat[0][0],ganado874::bind[b],bone_T[b]};
        }
        re4dc_coarse_skin_bones(invx,skin_jobs,skin_used);
    }
#endif
#if RE4DC_COARSE_SKIN_FTRV != 1
    for(unsigned i=0;i<34;++i){
        PSMTXConcat(inv,parts[i]->mat,relative);
        PSMTXConcat(relative,(const float (*)[4])ganado874::bind[i],local_skin[i]);
    }
#endif
    unsigned triangles=0,mask=0;
    const unsigned emitted_before=re4dc_actor_stats()->triangles;
    for(unsigned i=0;i<4;++i){
        auto& c=ganado874::chunks[i];cModelInfo* src=infos[i];
        if(!visible(src))continue;
        if(c.palette_count>256)return 0;
#if RE4DC_COARSE_SKIN_FTRV
        re4dc_coarse_skin_groups(skin_stream+skin_first[i],skin_groups[i],&bone_T[0][0],&palette[0][0],c.palette_count);
#if RE4DC_COARSE_SKIN_FTRV == 2
        for(unsigned j=0;j<c.palette_count;++j)skin_chk.entry(c.weights[j],local_skin,palette[j]);
#endif
#else
        for(unsigned j=0;j<c.palette_count;++j){
            const auto& w=c.weights[j];
            for(unsigned col=0;col<4;++col)for(unsigned row=0;row<3;++row){
                float value=0;
                for(unsigned k=0;k<w.count;++k)value+=local_skin[w.bone[k]][row][col]*w.value[k];
                palette[j][col*3+row]=value;
            }
        }
#endif
        if(!re4dc_actor_skin_register(pG->Frame_cnt,&c,nullptr,&palette[0][0],c.palette_count)){
            ++rejected;continue;
        }
        RE4DC_RENDER_MTXConcat(m->pParts->mat,src->mat,pm);
        RE4DC_RENDER_MTXConcat(pG->Cam.v_mat,pm,mv);
        if(stress_layout){
            // Arrange the existing live poses in camera space for a bounded
            // renderer stress test. Source positions, bones, AI and camera
            // remain untouched. This placement must never ship as gameplay.
            const unsigned slot=frame_meshes%7,row=frame_meshes/7;
            const int order[7]={0,-1,1,-2,2,-3,3};
            mv[0][3]=float(order[slot])*(row?850.f:650.f);
            mv[1][3]=row?-350.f:-1100.f;
            mv[2][3]=row?-6500.f:-4200.f;
        }
        Re4dcModelPart p{};
        p.model=m;p.info=&c;p.part=&c;p.position_count=c.position_count;p.normal_count=c.normal_count;
        p.position_stride=6;p.normal_stride=6;p.normal_shift=14;p.shift=4;
        p.stream=c.stream;p.stream_bytes=c.stream_bytes;p.uv=c.uv;
        p.lighting=&light;p.image=image;p.source_key[2]=1;
        p.depth_mode=m->z_mode;p.cull=0;p.alpha_state=255;
        std::memcpy(p.modelview,mv,sizeof(mv));GXGetProjectionv(p.projection);GXGetViewportv(p.viewport);
        if(!re4dc_actor_submit(&p)){++rejected;continue;}
        triangles+=c.triangles;mask|=1U<<i;
    }
    ++drawn;++frame_meshes;frame_triangles+=triangles;
    frame_emitted+=re4dc_actor_stats()->triangles>emitted_before;
#if RE4DC_COARSE_SKIN_FTRV == 2
    if(drawn<=3 || drawn%120==0)skin_chk.log("ganado",pG->Frame_cnt);
#endif
    if(drawn<=3 || drawn%120==0)re4dc_log("COARSE_GANADO t=%u draws=%u tris=%u mask=%02x fallback=%u rejected=%u texture_miss=%u\n",
        pG->Frame_cnt,drawn,triangles,mask,fallback,rejected,missing_texture);
    return 1;
}

extern "C" void re4dc_coarse_ganado_begin(){
    if(!config_read){
        config_read=true;
        const file_t file=fs_open("/cd/dc/coarse-crowd.txt",O_RDONLY);
        if(file>=0){
            char text[16]={};const int size=fs_read(file,text,15);fs_close(file);
            int value=0;unsigned i=0;const bool neg=text[0]=='-';if(neg)i=1;
            const unsigned start=i;
            while(i<unsigned(size>0?size:0) && text[i]>='0' && text[i]<='9'){value=value*10+text[i++]-'0';}
            if(i>start && value<=64){if(neg)value=-value;if(value>=-1)mesh_limit=value;}
            while(i<unsigned(size>0?size:0) && (text[i]==' ' || text[i]=='\t'))++i;
            if(i<unsigned(size>0?size:0) && text[i]=='1')stress_layout=1;
        }
        re4dc_log("COARSE_CROWD config mesh_limit=%d layout=%d source=diagnostic-file ACT_CAP=0\n",mesh_limit,stress_layout);
    }
    frame_meshes=frame_emitted=frame_candidates=frame_fallback=frame_triangles=0;
}
extern "C" void re4dc_coarse_ganado_end(){
#if defined(RE4DC_COARSE_FREEZE_AT) && RE4DC_COARSE_FREEZE_AT
    // Diagnostic (COARSE_FREEZE_AT=N, captures only): stop the CPU inside frame N's actor pass. Frame N-1,
    // already submitted, stays on screen, so every capture after the marker shows exactly that frame.
    if(pG->Frame_cnt>=RE4DC_COARSE_FREEZE_AT){
        re4dc_log("COARSE_FREEZE t=%u: the screen holds frame %u\n",pG->Frame_cnt,pG->Frame_cnt-1);
        for(;;)__asm__ volatile("nop");
    }
#endif
    if(pG->Frame_cnt%120==0)re4dc_log("COARSE_CROWD t=%u limit=%d layout=%d candidates=%u meshes=%u emitted=%u tris=%u unsupported=%u rejected=%u texture_miss=%u\n",
        pG->Frame_cnt,mesh_limit,stress_layout,frame_candidates,frame_meshes,frame_emitted,frame_triangles,frame_fallback,rejected,missing_texture);
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    // Trace builds only (never a timing arm): per-frame Ganado submission and Leon's life for the
    // scripted village-fight fixture, so a timing window and visible-versus-submitted counts are
    // chosen from exact frames. Read-only; logic_trace_diff / dtcmp ignore this line.
    re4dc_log("CROWDF t=%u c=%u m=%u e=%u fb=%u tri=%u hp=%d/%d\n",pG->Frame_cnt,frame_candidates,frame_meshes,
        frame_emitted,frame_fallback,frame_triangles,(int)(short)pG->pl_life,(int)pG->pl_life_max);
#endif
}

extern "C" int re4dc_coarse_ganado_layout(){return stress_layout;}
