// Appended to coarse_ganado_cast.cpp. Original adapter remains unchanged off.
#if RE4DC_ACTOR_TRANSACTION
#include "coarse_actor_transaction.h"
#include "actor_lifetime.h"
#include "ganado_source_extras.h"
namespace {
unsigned owner_binding_revision[32]{};
unsigned char owner_info_count[32]{};
unsigned short owner_source_bin[32][5]{};
cModelInfo* owner_extra_info[32]{};
unsigned owner_current_slot;
// Lane crowd far tier: far chunks use their own immutable asset IDs (coarse_actor_geometry_once.inc grows by 20
// under RE4DC_CROWD_FAR). owner_plan_app is the tier appearance (a, or a + kApps) of the last plan.
constexpr unsigned kOwnerFarAsset=47u;
unsigned owner_plan_app;
inline unsigned owner_tier_app(const Re4dcActorPlan& p) {
#if RE4DC_CROWD_FAR
    return p.immutable_asset_id[0]>=kOwnerFarAsset?p.appearance+kApps:p.appearance;
#else
    return p.appearance;
#endif
}
bool owner_ganado_bind(cModel* m) {
    if(!m || m->id<0x10 || m->id>0x20 || m->nParts!=kBones ||
       !m->pList || (m->be_flag&0x4000))return false;
    unsigned count=0;
    for(auto* i=m->pModelInfo;i;i=i->pList)if(++count>5)return false;
    if(count<4)return false;
    const unsigned revision=re4dc_actor_binding_revision(m);if(!revision)return false;
    bound=nullptr;unsigned slot=32;
    for(unsigned k=0;k<32;++k) {
        auto& b=bindings[k];
        if(b.owner==m && b.serial==m->serial && b.list==m->pList &&
           owner_binding_revision[k]==revision && owner_info_count[k]==count){bound=&b;slot=k;break;}
    }
    cModelInfo* infos[5]{};
    if(bound) {
        if(!re4dc_actor_role_bindings(m,bound->appearance,infos,count))return false;
        for(unsigned r=0;r<4;++r)if(infos[r]!=bound->infos[r])return false;
        if(count==5 && infos[4]!=owner_extra_info[slot])return false;
    } else {
        unsigned app=0;
        while(app<kApps && !re4dc_actor_role_bindings(m,app,infos,count))++app;
        if(app==kApps)return false;
        slot=replacement++%32;auto& b=bindings[slot];b={};owner_binding_revision[slot]=0;
        owner_info_count[slot]=0;owner_extra_info[slot]=nullptr;
        auto* part=m->pList;
        for(unsigned k=0;k<kBones;++k){if(!part)return false;b.parts[k]=part;part=part->pList;}
        if(part)return false;
        for(unsigned k=0;k<kBones;++k) {
            const int parent=gc::parents[k];
            const cCoord* want=parent<0?(const cCoord*)m:(const cCoord*)b.parts[parent];
            if(b.parts[k]->pParent!=want)return false;
            for(unsigned row=0;row<3;++row)for(unsigned col=0;col<3;++col)
                if(__builtin_fabsf(b.parts[k]->lt_inv_mat[row][col]-gc::bind[app][k][row*4+col])>.001f)return false;
        }
        for(unsigned r=0;r<count;++r) {
            const unsigned bin=re4dc_actor_role_source_bin(m,infos[r],app,r);
            if(!bin || bin>65535)return false;
            // A reviewed body/head and exact source-selected hand/attachment.
            if((r==2 && bin!=448 && bin!=451) || (r==3 && bin!=453 && bin!=456) ||
               (r==4 && bin!=467 && bin!=484))return false;
            owner_source_bin[slot][r]=(unsigned short)bin;
        }
        b.owner=m;b.serial=m->serial;b.list=m->pList;b.appearance=app;
        for(unsigned r=0;r<4;++r)b.infos[r]=infos[r];
        owner_extra_info[slot]=count==5?infos[4]:nullptr;owner_info_count[slot]=(unsigned char)count;
        owner_binding_revision[slot]=revision;bound=&b;
    }
    // Current source pointers/owner revisions are checked even on a binding hit.
    for(unsigned r=0;r<count;++r)
        if(re4dc_actor_role_source_bin(m,infos[r],bound->appearance,r)!=owner_source_bin[slot][r])return false;
    for(unsigned i=0;i<kBones;++i)for(unsigned j=0;j<12;++j)
        if(!coarse_finite((&bound->parts[i]->lt_inv_mat[0][0])[j]) ||
           !coarse_finite((&bound->parts[i]->mat[0][0])[j]))return false;
    owner_current_slot=slot;return true;
}
#if RE4DC_ACTOR_BIND_REUSE
}
// ACTOR_BIND_REUSE (crowd.mk; render only, exact; perf-20261004 candidate 11, handover-actor-preparation-20261004):
// the palette build reuses the structural part of the plan's owner_ganado_bind in the SAME actor transaction, as
// NATIVE_MODEL_REGISTRY_TX does for registry actors. The plan leaves a token naming the transaction call, the model,
// its Ganado slot, that slot's binding revision and the lifetime serial right after its bind; the palette build
// consumes it once. Between the two only native code runs (layout, semantics, the crowd policy, the leases, the
// palette arena: the ACTOR_PROOF_LEAN audit), and every lifetime record change takes life::next(). On a token hit
// the class / skeleton prerequisites, the live info list, the slot's identity and the lifetime binding (read-only,
// re4dc_actor_binding_peek: model_retire clears it without an epoch move) are checked again; the role search
// (re4dc_actor_role_bindings, re4dc_actor_role_source_bin) is skipped; the finite-matrix scan runs live as in the
// full bind. Any miss runs the full bind. =2 (check build): the full bind always runs and decides; "ABR" lines count
// token hits whose reuse verdict or slot differed from it (bad must stay 0).
extern "C" unsigned re4dc_actor_tx_serial;              // coarse_actor_transaction.inc
extern "C" unsigned re4dc_actor_binding_peek(cModel*);  // actor_lifetime.inc
namespace re4dc_material { namespace life { extern unsigned serial; extern bool exhausted; } }
#if RE4DC_ACTOR_BIND_REUSE == 2
extern "C" void re4dc_log(const char*,...);
#endif
namespace {
struct OwnerBindToken { const cModel* m;unsigned tx,life_serial,revision,slot; };
OwnerBindToken owner_bind_token{};
#if RE4DC_ACTOR_BIND_REUSE == 2
unsigned abr_calls,abr_hits,abr_bad;
#endif
bool owner_ganado_bind_tx(cModel* m) {
    using namespace re4dc_material;
    const OwnerBindToken t=owner_bind_token;owner_bind_token.m=nullptr;  // one use
    bool reuse=t.m==m && m && t.tx==re4dc_actor_tx_serial && !life::exhausted && t.life_serial==life::serial && t.slot<32;
    unsigned count=0;
    if(reuse)reuse=m->id>=0x10 && m->id<=0x20 && m->nParts==kBones && m->pList && !(m->be_flag&0x4000);
    if(reuse) {
        const auto& b=bindings[t.slot];
        reuse=b.owner==m && b.serial==m->serial && b.list==m->pList && owner_binding_revision[t.slot]==t.revision;
        for(auto* i=m->pModelInfo;reuse && i;i=i->pList) {
            if(count>=owner_info_count[t.slot]){reuse=false;break;}
            reuse=i==(count<4?b.infos[count]:owner_extra_info[t.slot]);++count;
        }
        reuse=reuse && count==owner_info_count[t.slot] && count>=4 && re4dc_actor_binding_peek(m)==t.revision;
    }
#if RE4DC_ACTOR_BIND_REUSE == 2
    const bool full=owner_ganado_bind(m);
    ++abr_calls;if(reuse){++abr_hits;if(!full || owner_current_slot!=t.slot || bound!=&bindings[t.slot])++abr_bad;}
    if(abr_calls%600==0)re4dc_log("ABR calls=%u hits=%u bad=%u\n",abr_calls,abr_hits,abr_bad);
    return full;
#else
    if(!reuse)return owner_ganado_bind(m);
    bound=&bindings[t.slot];
    // The full bind's finite scan, same words, as one exact whole-array test (registry_all_finite's form): bit 31 of
    // (exponent field + 0x00800000) is set iff the exponent is all ones (inf / NaN), i.e. iff !coarse_finite.
    typedef unsigned __attribute__((may_alias)) Word;
    unsigned bad=0;
    for(unsigned i=0;i<kBones;++i) {
        const Word* a=reinterpret_cast<const Word*>(&bound->parts[i]->lt_inv_mat[0][0]);
        const Word* c=reinterpret_cast<const Word*>(&bound->parts[i]->mat[0][0]);
        for(unsigned j=0;j<12;++j)bad|=((a[j]&0x7f800000u)+0x00800000u)|((c[j]&0x7f800000u)+0x00800000u);
    }
    if(bad&0x80000000u)return false;
    owner_current_slot=t.slot;return true;
#endif
}
#endif
const ganado_extra::Chunk* owner_original_chunk(unsigned role) {
    const unsigned bin=owner_source_bin[owner_current_slot][role];
    if((role==2 && bin==451) || (role==3 && bin==456) || role==4)return ganado_extra::find(bin);
    return nullptr;
}
int owner_ganado_palettes(cModel* m,const Re4dcActorPlan& p,float* const* output) {
#if RE4DC_ACTOR_BIND_REUSE
    if(!owner_ganado_bind_tx(m) ||
#else
    if(!owner_ganado_bind(m) ||
#endif
       bound->appearance!=p.appearance || p.count!=owner_info_count[owner_current_slot] || !skin_init(owner_tier_app(p)))return 0;
    for(unsigned i=0;i<p.count;++i)
        if(p.info[i]!=(i<4?bound->infos[i]:owner_extra_info[owner_current_slot]) || !output[i])return 0;
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
    const unsigned a=p.appearance,ta=owner_tier_app(p);
    // Extra source palettes may reference bones absent from the reduced body.
    // Only those actors evaluate all34 matrices; default actors retain the set.
    bool extra=false;for(unsigned i=2;i<p.count;++i)extra|=owner_original_chunk(i)!=nullptr;
    const unsigned used=extra?kBones:skin_used[ta];
    for(unsigned u=0;u<used;++u) {
        const unsigned b=extra?u:skin_bone[ta][u];
        skin_jobs[u]={&bound->parts[b]->mat[0][0],&gc::bind[a][b][0],bone_T[b]};
    }
    re4dc_coarse_skin_bones(invx,skin_jobs,used);
    for(unsigned i=0;i<p.count;++i) {
        const auto* source=owner_original_chunk(i);
        const unsigned palettes=source?source->palette_count:cast_chunk(ta,i).palette_count;
        if(p.input[i].palette_count!=palettes)return 0;
        if(source)re4dc_coarse_skin_groups(source->groups,source->group_count,&bone_T[0][0],output[i],palettes);
        else re4dc_coarse_skin_groups(skin_stream+skin_first[ta][i],skin_groups[ta][i],&bone_T[0][0],output[i],palettes);
        for(unsigned j=0;j<palettes*12;++j)if(!coarse_finite(output[i][j]))return 0;
    }
    return 1;
}
bool owner_add_source_material(cModel* m,Re4dcActorPlan& p,unsigned role,unsigned& index) {
    Re4dcActorOwnedMaterial mat{};
    if(!re4dc_actor_source_material(m,p.info[role],p.appearance,role,&mat))return false;
    for(unsigned k=1;k<p.material_count;++k) {
        const auto& t=p.materials[k];
        if(t.crc==mat.crc && t.fnv==mat.fnv && t.image.width==mat.image.width && t.image.height==mat.image.height &&
           t.image.format==mat.image.format && t.wrap_s==mat.wrap_s && t.wrap_t==mat.wrap_t) {index=k;return true;}
    }
    if(p.material_count==kRe4dcActorMaterials)return false;
    index=p.material_count++;p.materials[index]=mat;return true;
}
}
#if RE4DC_ACTOR_EARLY_COARSE
extern "C" int re4dc_ganado_early_ready(cModel* m) {
    if(!owner_ganado_bind(m) || owner_info_count[owner_current_slot]!=4 || !m->pParts ||
       !skin_init(bound->appearance))return 0;
    for(unsigned role=0;role<4;++role) {
        if(owner_original_chunk(role) || gc::chunks[bound->appearance][role].palette_count>256)return 0;
        for(unsigned j=0;j<12;++j)if(!coarse_finite((&bound->infos[role]->mat[0][0])[j]))return 0;
    }
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    for(unsigned j=0;j<12;++j)if(!coarse_finite((&inv[0][0])[j]))return 0;
    return 1;
}
#endif
#if RE4DC_CROWD_FAR
extern "C" int re4dc_crowd_far(cModel*);  // coarse_actor_transaction.inc
#endif
#if RE4DC_CROWD
// Lane crowd (crowd.mk CROWD_CULL; render only, exact): the owner path's whole-actor form of COARSE_PREGATE. Called
// right after re4dc_actor_plan_ganado bound m. 1 when every visible chunk is provably outside one of the actor path's
// culling planes (gate_cull_once: per-bone balls from the cast chunk's own positions and weights), so
// re4dc_actor_submit_owned_runs would emit nothing for the actor. The balls cover the four cast chunks only: an actor
// with a fifth (attachment) info or an original source hand is never culled.
// The far plane is the actor path's fog-gate cull depth (native_actor_fast.cpp fog_gate_depth: the fogged View far
// when it lies between the projection near and far): a culled actor has every vertex beyond the source View far,
// which the GC clips. The actor path's own gate bound is looser (it can keep such a chunk and emit it fully fogged);
// the =2 check build counts those as violations with why=2 depth>fog.
extern "C" float re4dc_fog_gate_far();
#if RE4DC_CROWD_INVIS_SKIP
// CROWD_INVIS_SKIP (crowd.mk; lane iv; render only): the Trans-time decision for a Ganado the next Render would draw
// nothing of. Render notes each Ganado's path (re4dc_invis_note: the transaction's start, the owner admission inside
// the crowd policy, the plan's decline) with its info chain; Trans (re4dc_invis_begin, re4dc_invis_decide) predicts
// the same path for the same structure under the next Render's view and returns
//   1: owner path admitted last time and the crowd policy would skip it anyway (CROWD_FOGSKIP's root test, CROWD_CULL's
//      pregate balls with the fog far plane): exactly the Ganados the crowd policy keeps out of the actor path, so the
//      CROWD_LOD ranking (native_actor_fast.cpp crowd_rank: the models submitted last frame) sees the same models. A
//      near-plane test was dropped: a submitted Ganado that emits nothing still holds a near rank;
//   2: source path (the plan declined last time) and every drawn info's source-mesh balls lie outside one screen
//      edge or the near plane (bound below; skinned positions are convex combinations of the bones' balls);
//   0: anything else. =2 marks instead and re4dc_invis_check counts emitted triangles and path / view mismatches.
extern "C" void GXGetViewportv(float*);
namespace {
struct InvisRec {
    const cModel* m; unsigned serial; const void* parts;
    cModelInfo* info[6]; const ModelData* data[6];
    cModelInfo* role[4];
    unsigned app, bindkey, mark_gen;
    unsigned char count, outcome, cullable, mark, nparts;
#if RE4DC_PS2_INTERIOR_OWNER
    unsigned pc_gen;  // PS2_INTERIOR_ACTORS=2: the Trans (invis_gen) whose interior cell hides this owner-path Ganado
    unsigned char pc_cast;  // roles 0..3 drawn from the cast chunks at the owner admission (bit per role)
#endif
};
constexpr unsigned kInvisRecs = 48;
InvisRec invis_rec[kInvisRecs];
unsigned invis_rec_next, invis_gen;
// The next Render's view (re4dc_invis_begin) and the last Render's observation (a Ganado's transaction start).
struct InvisView { bool ok; float P[7], V[6], fog, near, far_owner, rows[3][3]; };
InvisView invis_view;
float invis_obs_V[6], invis_obs_fog;
bool invis_obs_valid;
unsigned invis_n[8], invis_unsettled;  // decided 0/1/2, no record, structure moved, unknown path, view invalid, declined test
#if RE4DC_CROWD_INVIS_SKIP == 2
unsigned invis_marked, invis_checked, invis_violations, invis_violation_tris, invis_path_mis, invis_view_mis,
    invis_fog_mis, invis_logs, invis_crowd_checked, invis_crowd_mis;
#endif
unsigned invis_builds, invis_build_fail;
#if RE4DC_PS2_INTERIOR_ACTORS
unsigned invis_pc_tests, invis_pc_hidden;  // PS2_INTERIOR_ACTORS: source-path Ganados tested / hidden by the cell
#endif
#if RE4DC_PS2_INTERIOR_OWNER
unsigned invis_pco_tests, invis_pco_hidden;  // PS2_INTERIOR_ACTORS=2: owner-path Ganados tested / marked
unsigned invis_pco_why[6];  // not marked: 0 no source-mesh bound for an original / fifth info, 1 no pregate balls, 2 beyond the fog proof, 3 box not finite, 4 not hidden by the cell, 5 fog prediction not believed
#endif
InvisRec* invis_find(const cModel* m, bool create) {
    for (unsigned k = 0; k < kInvisRecs; ++k) if (invis_rec[k].m == m) return &invis_rec[k];
    if (!create) return nullptr;
    InvisRec& r = invis_rec[invis_rec_next++ % kInvisRecs];
    r = InvisRec{};
    r.m = m;
    r.count = 0xFF;
    return &r;
}
bool invis_same(const InvisRec& r, const cModel* m) {
    if (r.count > 6 || r.serial != unsigned(m->serial) || r.parts != m->pList) return false;
    unsigned n = 0;
    for (cModelInfo* i = m->pModelInfo; i; i = i->pList) {
        if (n >= r.count || r.info[n] != i || r.data[n] != i->pData) return false;
        ++n;
    }
    return n == r.count;
}
void invis_capture(InvisRec& r, const cModel* m) {
    r.serial = unsigned(m->serial); r.parts = m->pList; r.count = 0xFF; r.outcome = 0; r.cullable = 0; r.bindkey = 0;
#if RE4DC_PS2_INTERIOR_OWNER
    // A replacement identity must not inherit a mark from an earlier owner in this Trans generation.
    r.pc_gen = invis_gen - 1u;
#endif
    unsigned n = 0;
    for (cModelInfo* i = m->pModelInfo; i; i = i->pList) {
        if (n == 6) return;
        r.info[n] = i; r.data[n] = i->pData; ++n;
    }
    r.count = (unsigned char)n;
}
// The parts chain (calcWeightMat's order, MakeWeightPalette's matrix index); 0 when longer than 64.
unsigned invis_parts(const cModel* m, cParts** parts) {
    unsigned n = 0;
    for (cParts* p = m->pList; p; p = p->pList) { if (n == 64) return 0; parts[n++] = p; }
    return n;
}
void invis_note_owner(cModel* m) {
    if (!bound || bound->owner != m) return;
    InvisRec* r = invis_find(m, false);
    if (!r || !invis_same(*r, m)) return;
    r->outcome = 1; r->app = owner_plan_app;
    r->cullable = owner_info_count[owner_current_slot] == 4 && !owner_original_chunk(2) && !owner_original_chunk(3);
    for (unsigned k = 0; k < 4; ++k) r->role[k] = bound->infos[k];
#if RE4DC_PS2_INTERIOR_OWNER
    r->pc_cast = 0;  // the roles drawn from the cast chunks (no original source chunk): the pregate balls bound them
    for (unsigned k = 0; k < 4 && k < owner_info_count[owner_current_slot]; ++k)
        if (!owner_original_chunk(k)) r->pc_cast |= (unsigned char)(1u << k);
#endif
}
// Source-mesh bound: per drawn info's ModelData and the skeleton's bind matrices, a ball per bone in the bone's bind
// frame around every position that bone moves with a positive rate (MakeWeightPalette's rates, the last one the
// remainder; all >= 0 or no bound), or one ball in model space for a rigid info (drawn from vtxOrig).
struct WeightV { unsigned char id[3], num, wht[4]; };                 // trans.cpp Weight
struct WeightExtV { unsigned short idx[3], num; unsigned char weight[4]; };  // trans.cpp WeightExt
struct InvisBall { float c[3], r; };
struct InvisMesh { const ModelData* d; unsigned key; unsigned short first, n; unsigned char np, ok; };
constexpr unsigned kInvisMeshes = 48, kInvisBalls = 1536;
InvisMesh invis_mesh[kInvisMeshes];
InvisBall invis_ball[kInvisBalls];
unsigned char invis_ball_bone[kInvisBalls];
unsigned invis_mesh_next, invis_ball_next;
inline bool invis_rigid(const ModelData* d) { return d->weight_palette_num <= 1 && d->weight_ext_num <= 0xFF && d->nParts == 1; }
// Entry e's bones and rates exactly as MakeWeightPalette(Ext) forms them; false when it has no bound.
bool invis_entry(const ModelData* d, unsigned e, unsigned np, unsigned* ids, bool* use, unsigned& num) {
    float total = 0.0f;
    if (d->weight_ext_num > 0xFF) {
        const WeightExtV& w = static_cast<const WeightExtV*>(d->pWeight)[e];
        num = w.num;
        if (num < 1 || num > 3) return false;
        for (unsigned j = 0; j < num; ++j) {
            float rate = float(w.weight[j]) * 0.01f;
            if (j == num - 1) rate = 1.0f - total;
            total += rate;
            if (!(rate >= 0.0f) || w.idx[j] >= np) return false;
            ids[j] = w.idx[j]; use[j] = rate > 0.0f;
        }
    } else {
        const WeightV& w = static_cast<const WeightV*>(d->pWeight)[e];
        num = w.num;
        if (num < 1 || num > 3) return false;
        for (unsigned j = 0; j < num; ++j) {
            float rate = float(w.wht[j]) * 0.01f;
            if (j == num - 1) rate = 1.0f - total;
            total += rate;
            if (!(rate >= 0.0f) || w.id[j] >= np) return false;
            ids[j] = w.id[j]; use[j] = rate > 0.0f;
        }
    }
    return true;
}
bool invis_build(InvisMesh& e, const ModelData* d, cParts* const* parts, unsigned np) {
    e.ok = 0; e.n = 0;
    if (!d->vtxOrig || d->shift > 20 || !d->nVtx) return false;
    const float q = 1.0f / float(1u << d->shift);
    const short* v = static_cast<const short*>(d->vtxOrig);
    const unsigned nv = d->nVtx;
    if (invis_rigid(d)) {
        float lo[3] = {3.0e38f, 3.0e38f, 3.0e38f}, hi[3] = {-3.0e38f, -3.0e38f, -3.0e38f};
        for (unsigned i = 0; i < nv; ++i)
            for (unsigned a = 0; a < 3; ++a) { const float x = float(v[i * 4 + a]) * q; if (x < lo[a]) lo[a] = x; if (x > hi[a]) hi[a] = x; }
        const float c[3] = {0.5f * (lo[0] + hi[0]), 0.5f * (lo[1] + hi[1]), 0.5f * (lo[2] + hi[2])};
        float r2 = 0.0f;
        for (unsigned i = 0; i < nv; ++i) {
            float s = 0.0f;
            for (unsigned a = 0; a < 3; ++a) { const float t = float(v[i * 4 + a]) * q - c[a]; s += t * t; }
            if (s > r2) r2 = s;
        }
        if (invis_ball_next + 1 > kInvisBalls) { invis_ball_next = 0; for (auto& x : invis_mesh) x.d = nullptr; }
        e.first = (unsigned short)invis_ball_next;
        invis_ball[invis_ball_next] = InvisBall{{c[0], c[1], c[2]}, __builtin_sqrtf(r2)};
        invis_ball_bone[invis_ball_next++] = 0xFF;
        e.n = 1; e.ok = 1;
        return true;
    }
    if (!d->pWeight || np > 64) return false;
    const unsigned nw = d->weight_ext_num > 0xFF ? d->weight_ext_num : d->weight_palette_num;
    float lo[64][3], hi[64][3], r2[64];
    unsigned long long used = 0;
    for (unsigned pass = 0; pass < 2; ++pass) {
        for (unsigned i = 0; i < nv; ++i) {
            const int e_ = v[i * 4 + 3];
            if (e_ < 0 || unsigned(e_) >= nw) return false;
            unsigned ids[3], num; bool use[3];
            if (!invis_entry(d, unsigned(e_), np, ids, use, num)) return false;
            const float x[3] = {float(v[i * 4]) * q, float(v[i * 4 + 1]) * q, float(v[i * 4 + 2]) * q};
            for (unsigned j = 0; j < num; ++j) {
                if (!use[j]) continue;
                const unsigned b = ids[j];
                const float (*B)[4] = parts[b]->lt_inv_mat;
                float y[3];
                for (unsigned a = 0; a < 3; ++a) y[a] = B[a][0] * x[0] + B[a][1] * x[1] + B[a][2] * x[2] + B[a][3];
                if (!pass) {
                    if (!((used >> b) & 1ULL)) {
                        used |= 1ULL << b; r2[b] = 0.0f;
                        for (unsigned a = 0; a < 3; ++a) lo[b][a] = hi[b][a] = y[a];
                    }
                    for (unsigned a = 0; a < 3; ++a) { if (y[a] < lo[b][a]) lo[b][a] = y[a]; if (y[a] > hi[b][a]) hi[b][a] = y[a]; }
                } else {
                    float s = 0.0f;
                    for (unsigned a = 0; a < 3; ++a) { const float t = y[a] - 0.5f * (lo[b][a] + hi[b][a]); s += t * t; }
                    if (s > r2[b]) r2[b] = s;
                }
            }
        }
    }
    unsigned count = 0;
    for (unsigned b = 0; b < np; ++b) count += (used >> b) & 1ULL;
    if (!count) return false;
    if (invis_ball_next + count > kInvisBalls) { invis_ball_next = 0; for (auto& x : invis_mesh) x.d = nullptr; }
    e.first = (unsigned short)invis_ball_next;
    for (unsigned b = 0; b < np; ++b) {
        if (!((used >> b) & 1ULL)) continue;
        for (unsigned a = 0; a < 3; ++a) { const float c = 0.5f * (lo[b][a] + hi[b][a]); if (!coarse_finite(c)) return false; invis_ball[invis_ball_next].c[a] = c; }
        invis_ball[invis_ball_next].r = __builtin_sqrtf(r2[b]);
        if (!coarse_finite(invis_ball[invis_ball_next].r)) return false;
        invis_ball_bone[invis_ball_next++] = (unsigned char)b;
    }
    e.n = (unsigned short)count; e.ok = 1;
    return true;
}
const InvisMesh* invis_mesh_for(const ModelData* d, unsigned key, cParts* const* parts, unsigned np) {
    const bool rigid = invis_rigid(d);
    for (const auto& e : invis_mesh)
        if (e.d == d && (rigid || (e.key == key && e.np == np))) return e.ok ? &e : nullptr;
    InvisMesh& e = invis_mesh[invis_mesh_next++ % kInvisMeshes];
    e.d = nullptr;
    ++invis_builds;
    const bool ok = invis_build(e, d, parts, np);
    e.d = d; e.key = key; e.np = (unsigned char)np;  // a failed build is remembered (never culled)
    if (!ok) { e.ok = 0; ++invis_build_fail; }
    return e.ok ? &e : nullptr;
}
inline void invis_xf(const float (*A)[4], const float* c, float* w) {
    for (unsigned r = 0; r < 3; ++r) w[r] = A[r][0] * c[0] + A[r][1] * c[1] + A[r][2] * c[2] + A[r][3];
}
// The screen rows applied to a world point: X', Y', W (gate_matrix's G with an identity model part) and the
// right / bottom rows, with their norms.
void invis_world_rows(float (*G)[4], float* norm) {
    const float (*v)[4] = pG->Cam.v_mat;
    const float (*rows)[3] = invis_view.rows;
    for (unsigned r = 0; r < 3; ++r)
        for (unsigned c = 0; c < 4; ++c) G[r][c] = rows[r][0] * v[0][c] + rows[r][1] * v[1][c] + rows[r][2] * v[2][c];
    for (unsigned c = 0; c < 4; ++c) { G[3][c] = G[0][c] - RE4DC_SCREEN_WF * G[2][c]; G[4][c] = G[1][c] - RE4DC_SCREEN_HF * G[2][c]; }
    for (unsigned f = 0; f < 5; ++f) norm[f] = __builtin_sqrtf(G[f][0] * G[f][0] + G[f][1] * G[f][1] + G[f][2] * G[f][2]);
}
// One ball against the live planes (bit 0 left, 1 top, 2 right, 3 bottom, 4 far, 5 near): the planes it is wholly
// outside of. gate_cull_once's tests plus the near plane (every point's W below the projection near).
inline unsigned invis_ball_out(const float (*G)[4], const float* norm, const float* w, float rho, unsigned planes, float far,
                               float near) {
    float d[5];
    d[0] = G[0][0] * w[0] + G[0][1] * w[1] + G[0][2] * w[2] + G[0][3];
    d[1] = G[1][0] * w[0] + G[1][1] * w[1] + G[1][2] * w[2] + G[1][3];
    d[2] = G[2][0] * w[0] + G[2][1] * w[1] + G[2][2] * w[2] + G[2][3];
    d[3] = G[3][0] * w[0] + G[3][1] * w[1] + G[3][2] * w[2] + G[3][3];
    d[4] = G[4][0] * w[0] + G[4][1] * w[1] + G[4][2] * w[2] + G[4][3];
    unsigned out = 0;
    if ((planes & 1U) && d[0] + rho * norm[0] < 0.0f) out |= 1;
    if ((planes & 2U) && d[1] + rho * norm[1] < 0.0f) out |= 2;
    const float wmin = d[2] - rho * norm[2];
    if ((planes & 4U) && wmin > 0.0f && d[3] - rho * norm[3] > 0.0f) out |= 4;
    if ((planes & 8U) && wmin > 0.0f && d[4] - rho * norm[4] > 0.0f) out |= 8;
    if ((planes & 16U) && wmin > far) out |= 16;
    if ((planes & 32U) && d[2] + rho * norm[2] < near) out |= 32;
    return planes & out;
}
// Owner path: the crowd policy's tests on the next Render's view (crowd_policy: re4dc_crowd_offscreen, then
// CROWD_FOGSKIP).
bool invis_owner(cModel* m, const InvisRec& r) {
    const InvisView& iv = invis_view;
#if RE4DC_CROWD_FOGSKIP
    if (iv.fog > 0.0f) {
        const float (*rt)[4] = m->pParts->mat; const float (*v)[4] = pG->Cam.v_mat;
        const float depth = -(v[2][0] * rt[0][3] + v[2][1] * rt[1][3] + v[2][2] * rt[2][3] + v[2][3]);
        if (depth - 2500.0f > iv.fog) return true;
    }
#endif
    if (!r.cullable) return false;
    Mtx mv[4];
    unsigned vis = 0;
    for (unsigned i = 0; i < 4; ++i) {
        if (!visible(r.role[i])) continue;
        Mtx pm;
        PSMTXConcat(m->pParts->mat, r.role[i]->mat, pm);
        PSMTXConcat(pG->Cam.v_mat, pm, mv[i]);
        vis |= 1U << i;
    }
    if (!vis) return true;  // re4dc_crowd_offscreen: no visible chunk is "all culled"
    if (!gate_init(r.app) || stress_layout) return false;
    Mtx inv;
    if (!PSMTXInverse(m->pParts->mat, inv)) return false;
    cParts* parts[64];
    if (invis_parts(m, parts) != kBones) return false;
    for (unsigned i = 0; i < 4; ++i) {
        if (!((vis >> i) & 1U)) continue;
        const unsigned n = gate_count[r.app][i], first = gate_first[r.app][i];
        if (!n) continue;  // gate_cull_once: a chunk without balls counts as culled
        float G[5][4], norm[5];
        gate_matrix(iv.rows, mv[i], inv, G, norm);
        unsigned planes = 31;  // re4dc_crowd_offscreen's planes (no near plane)
        for (unsigned j = 0; j < n && planes; ++j) {
            const GateBall& g = gate_ball[first + j];
            const float (*A)[4] = parts[gate_bone[first + j]]->mat;
            float w[3];
            invis_xf(A, g.c, w);
            planes = invis_ball_out(G, norm, w, g.r * gate_scale_sym(A) * 1.002f + 4.0f, planes, iv.far_owner, iv.near);
        }
        if (!planes) return false;
    }
    return true;
}
// Source path: every info commonModelTrans draws (be_flag 8) wholly outside one screen edge or the near plane.
bool invis_source(cModel* m, const InvisRec& r) {
    if (!r.bindkey) return false;
    cParts* parts[64];
    const unsigned np = invis_parts(m, parts);
    if (!np || np != r.nparts) return false;
    float G[5][4], norm[5];
    invis_world_rows(G, norm);
    float (*root)[4] = m->pParts->mat;
    Mtx inv;
    if (!PSMTXInverse(root, inv)) return false;
    const float sinv = gate_scale_sym(inv);
    for (unsigned k = 0; k < r.count; ++k) {
        cModelInfo* info = r.info[k];
        if (!(info->be_flag & 8)) continue;
        const ModelData* d = info->pData;
        if ((info->be_flag & 2) || d->nTex > 0xF7) return false;
        const InvisMesh* e = invis_mesh_for(d, r.bindkey, parts, np);
        if (!e) return false;
        unsigned planes = 47;  // left, top, right, bottom, near
        if (invis_rigid(d)) {
            const unsigned no = d->pHead->partsNo;
            if (no >= np) return false;
            const cParts* p = (m->be_flag & 0x2000) ? reinterpret_cast<const cParts*>(m->pParts) + no : parts[no];
            Mtx W;
            PSMTXConcat(p->mat, info->mat, W);
            const InvisBall& b = invis_ball[e->first];
            float w[3];
            invis_xf(W, b.c, w);
            planes = invis_ball_out(G, norm, w, b.r * gate_scale_sym(W) * 1.002f + 4.0f, planes, 3.0e38f, invis_view.near);
        } else {
            // Positions are skinned in the root frame (inv(root) parts bind), stored as s16 at d->shift and drawn
            // through root x info->mat: no ball may reach the s16 clamp; T = root x info->mat x inv(root).
            static const float I[3][4] = {{1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}};
            const bool ident = !std::memcmp(info->mat, I, sizeof(I));
            Mtx T;
            float sT = 1.0f;
            if (!ident) {
                Mtx t;
                PSMTXConcat(root, info->mat, t);
                PSMTXConcat(t, inv, T);
                sT = gate_scale_sym(T);
            }
            const float limit = 32000.0f / float(1u << d->shift);
            for (unsigned j = 0; j < e->n && planes; ++j) {
                const InvisBall& b = invis_ball[e->first + j];
                const float (*A)[4] = parts[invis_ball_bone[e->first + j]]->mat;
                const float sA = gate_scale_sym(A);
                float w[3], s[3];
                invis_xf(A, b.c, w);
                invis_xf(inv, w, s);
                const float rs = b.r * sA * sinv * 1.002f + 1.0f;
                for (unsigned a = 0; a < 3; ++a) if (!(__builtin_fabsf(s[a]) + rs < limit)) return false;
                float rho = b.r * sA * 1.002f;
                if (!ident) { float u[3]; invis_xf(T, w, u); w[0] = u[0]; w[1] = u[1]; w[2] = u[2]; rho *= sT * 1.002f; }
                planes = invis_ball_out(G, norm, w, rho + 4.0f, planes, 3.0e38f, invis_view.near);
            }
        }
        if (!planes) return false;
    }
    return true;
}
}
extern "C" void re4dc_invis_note(cModel* m, unsigned outcome) {
    if (!m || m->id < 0x10 || m->id > 0x20) return;
    if (outcome == 0) {
        InvisRec* r = invis_find(m, true);
        if (!invis_same(*r, m)) invis_capture(*r, m);
        r->outcome = 0;
        GXGetViewportv(invis_obs_V);
        invis_obs_fog = re4dc_fog_gate_far();
        invis_obs_valid = true;
#if RE4DC_CROWD_INVIS_SKIP == 2
        if (r->mark && r->mark_gen == invis_gen) {
            float P[7];
            GXGetProjectionv(P);
            const bool view = !std::memcmp(P, invis_view.P, sizeof(P)) && !std::memcmp(invis_obs_V, invis_view.V, sizeof(invis_obs_V));
            const bool fog = invis_view.fog < 0.0f || invis_obs_fog == invis_view.fog;
            if (!view) ++invis_view_mis;
            if (!fog) ++invis_fog_mis;
            if ((!view || !fog) && invis_logs < 64) {
                ++invis_logs;
                re4dc_log("INVIS2 VIEW t=%u id=%x kind=%u P=%g,%g,%g,%g,%g,%g/%g,%g,%g,%g,%g,%g V=%g,%g,%g,%g/%g,%g,%g,%g fog=%g/%g\n",
                          unsigned(pG->Frame_cnt), unsigned(m->id), r->mark, P[1], P[2], P[3], P[4], P[5], P[6],
                          invis_view.P[1], invis_view.P[2], invis_view.P[3], invis_view.P[4], invis_view.P[5], invis_view.P[6],
                          invis_obs_V[0], invis_obs_V[1], invis_obs_V[2], invis_obs_V[3], invis_view.V[0], invis_view.V[1],
                          invis_view.V[2], invis_view.V[3], invis_obs_fog, invis_view.fog);
            }
        }
#endif
        return;
    }
    if (outcome == 1) { invis_note_owner(m); return; }
    InvisRec* r = invis_find(m, false);
    if (!r || !invis_same(*r, m)) return;
    if (!r->bindkey) {
        cParts* parts[64];
        const unsigned np = invis_parts(m, parts);
        unsigned h = 2166136261u;
        for (unsigned i = 0; i < np; ++i) {
            const unsigned* w = reinterpret_cast<const unsigned*>(&parts[i]->lt_inv_mat[0][0]);
            for (unsigned j = 0; j < 12; ++j) h = (h ^ w[j]) * 16777619u;
        }
        r->bindkey = np ? (h | 1u) : 0u; r->nparts = (unsigned char)np;
    }
    r->outcome = 2;
}
// Trans: the next Render's projection (pG->Cam.ProjMat as CameraSetProjection(1) loads it; P null: not perspective)
// and its fogged View far as LightEnv predicts it, believed only when the last Render saw the same value.
#if RE4DC_PS2_INTERIOR_ACTORS
extern "C" void re4dc_ps2_interior_trans(const float* view, const float* P);  // native_static.cpp
#endif
#if RE4DC_PS2_INTERIOR_OWNER
// coarse_actor_transaction.inc: owned submissions skipped / declined by the replay, =2 crowd checks / mismatches.
extern "C" unsigned re4dc_pco_skipped, re4dc_pco_declined, re4dc_pco_checked, re4dc_pco_check_mis;
#endif
extern "C" void re4dc_invis_begin(const float* P, float fog_pred) {
    ++invis_gen;
#if RE4DC_PS2_INTERIOR_ACTORS
    re4dc_ps2_interior_trans(&pG->Cam.v_mat[0][0], P);
    if (!(invis_gen % 600)) re4dc_log("INVISPC t=%u tests=%u hidden=%u\n", unsigned(pG->Frame_cnt), invis_pc_tests, invis_pc_hidden);
#endif
#if RE4DC_PS2_INTERIOR_OWNER
    if (!(invis_gen % 120))
        re4dc_log("INVISPCO t=%u tests=%u marked=%u skipped=%u declined=%u checked=%u check_mis=%u why=%u,%u,%u,%u,%u,%u\n",
                  unsigned(pG->Frame_cnt), invis_pco_tests, invis_pco_hidden, re4dc_pco_skipped, re4dc_pco_declined,
                  re4dc_pco_checked, re4dc_pco_check_mis, invis_pco_why[0], invis_pco_why[1], invis_pco_why[2],
                  invis_pco_why[3], invis_pco_why[4], invis_pco_why[5]);
#endif
    InvisView& iv = invis_view;
    iv.ok = false;
    if (!P || !invis_obs_valid) return;
    std::memcpy(iv.P, P, sizeof(iv.P)); std::memcpy(iv.V, invis_obs_V, sizeof(iv.V));
    const float* V = iv.V;
    if (P[0] != 0.0f || !(V[2] > 0.0f) || !(V[3] > 0.0f)) return;
    const float far = P[6] / P[5], near = P[6] / (P[5] - 1.0f);
    if (!(near > 0.0f) || !(far > near) || !(far < 3.0e38f)) return;
    const float cx = (V[0] + V[2] * 0.5f) * RE4DC_SCREEN_WF / V[2], cy = (V[1] + V[3] * 0.5f) * RE4DC_SCREEN_HF / V[3];
    const float rows[3][3] = {{RE4DC_SCREEN_HALF_WF * P[1], 0.0f, RE4DC_SCREEN_HALF_WF * P[2] - cx},
                              {0.0f, -RE4DC_SCREEN_HALF_HF * P[3], -RE4DC_SCREEN_HALF_HF * P[4] - cy}, {0.0f, 0.0f, -1.0f}};
    std::memcpy(iv.rows, rows, sizeof(rows));
    iv.near = near;
    iv.fog = fog_pred == invis_obs_fog ? fog_pred : -1.0f;
    // re4dc_crowd_offscreen's far plane: the fogged View far when it lies between near and far, else the projection far
    // (with the fog unknown, the projection far: never nearer than the plane the Render will use).
    iv.far_owner = iv.fog > near && iv.fog < far ? iv.fog : far;
    iv.ok = true;
#if RE4DC_CROWD_INVIS_SKIP == 2
    if (!(invis_gen % 120))
        re4dc_log("INVIS2 t=%u marked=%u checked=%u violations=%u violation_tris=%u path_mis=%u view_mis=%u fog_mis=%u "
                  "crowd=%u/%u draw=%u owner=%u source=%u unsettled=%u norec=%u moved=%u unknown=%u noview=%u builds=%u "
                  "build_fail=%u\n",
                  unsigned(pG->Frame_cnt), invis_marked, invis_checked, invis_violations, invis_violation_tris, invis_path_mis,
                  invis_view_mis, invis_fog_mis, invis_crowd_mis, invis_crowd_checked, invis_n[0], invis_n[1], invis_n[2],
                  invis_unsettled, invis_n[3], invis_n[4], invis_n[5], invis_n[6], invis_builds, invis_build_fail);
#else
    if (!(invis_gen % 600))
        re4dc_log("INVIS t=%u draw=%u owner=%u source=%u unsettled=%u norec=%u moved=%u unknown=%u noview=%u builds=%u "
                  "build_fail=%u\n",
                  unsigned(pG->Frame_cnt), invis_n[0], invis_n[1], invis_n[2], invis_unsettled, invis_n[3], invis_n[4],
                  invis_n[5], invis_n[6], invis_builds, invis_build_fail);
#endif
}
// ModelTrans, after AddOt queued a Ganado (the caller checked kindid 0, ot_type 0, be_flag 1 without 0x4000,
// Shader_type 0, no shadow light, a coarse image): 1 owner path skip, 2 source path skip, 0 draw.
extern "C" int re4dc_actor_part_settled(const void* stream, unsigned bytes);  // native_actor_fast.cpp
// trans.cpp's PTR_INVALID.
static inline bool invis_bad_ptr(const void* p) { return int(uintptr_t(p)) >= 0 || uintptr_t(p) > RE4_MEM_HI; }
// Source path: every part of every info its draw would hand to the native parts (commonModelTrans's walk) settled.
static bool invis_settled(cModel* m) {
    for (cModelInfo* info = m->pModelInfo; info; info = info->pList) {
        if (invis_bad_ptr(info)) return false;
        if (!(info->be_flag & 8)) continue;
        const ModelData* d = info->pData;
        if (invis_bad_ptr(d) || d->nTex > 0xF7) return false;
        const unsigned char* part = reinterpret_cast<const unsigned char*>(d->pParts);
        for (unsigned i = 0; i < d->displist_num; ++i) {
            const unsigned size = reinterpret_cast<const ModelPart*>(part)->size;
            if (!re4dc_actor_part_settled(part + 0x20, size)) return false;
            part += 0x20 + size;
        }
    }
    return true;
}
#if RE4DC_PS2_INTERIOR_ACTORS
// PS2_INTERIOR_ACTORS (game30.mk; lane pc): a source-path Ganado the game's view test and invis_source keep is still
// skipped when the world box of its source-mesh balls (invis_source's balls, radii and margins, as world points)
// lies wholly outside the r100 house box and the Trans-time interior cell hides it (native_static.cpp
// re4dc_ps2_interior_actor_hidden). The skip is the source path's (invisReplayRender: TPL / texture-object step and
// the CROWD_LOD note kept) under the same settled-parts rule. Owner-path Ganados are not taken: their crowd ranking
// entries come from the cast chunks the pregate keeps, which this test does not reproduce.
extern "C" int re4dc_ps2_interior_actor_hidden(const float lo[3], const float hi[3]);  // native_static.cpp
#if RE4DC_PS2_INTERIOR_OWNER
extern "C" int re4dc_ps2_interior_owner_hidden(const float lo[3], const float hi[3]);  // native_static.cpp
#endif
static inline void invis_acc(float* lo, float* hi, const float* w, float rho) {
    for (unsigned a = 0; a < 3; ++a) { if (w[a] - rho < lo[a]) lo[a] = w[a] - rho; if (w[a] + rho > hi[a]) hi[a] = w[a] + rho; }
}
static bool invis_interior(cModel* m, const InvisRec& r) {
    if (!r.bindkey) return false;
    cParts* parts[64];
    const unsigned np = invis_parts(m, parts);
    if (!np || np != r.nparts) return false;
    float (*root)[4] = m->pParts->mat;
    Mtx inv;
    if (!PSMTXInverse(root, inv)) return false;
    float lo[3] = {3.0e38f, 3.0e38f, 3.0e38f}, hi[3] = {-3.0e38f, -3.0e38f, -3.0e38f};
    unsigned any = 0;
    for (unsigned k = 0; k < r.count; ++k) {
        cModelInfo* info = r.info[k];
        if (!(info->be_flag & 8)) continue;
        const ModelData* d = info->pData;
        if ((info->be_flag & 2) || d->nTex > 0xF7) return false;
        const InvisMesh* e = invis_mesh_for(d, r.bindkey, parts, np);
        if (!e) return false;
        if (invis_rigid(d)) {
            const unsigned no = d->pHead->partsNo;
            if (no >= np) return false;
            const cParts* p = (m->be_flag & 0x2000) ? reinterpret_cast<const cParts*>(m->pParts) + no : parts[no];
            Mtx W;
            PSMTXConcat(p->mat, info->mat, W);
            const InvisBall& b = invis_ball[e->first];
            float w[3];
            invis_xf(W, b.c, w);
            invis_acc(lo, hi, w, b.r * gate_scale_sym(W) * 1.002f + 4.0f);
            ++any;
        } else {
            static const float I[3][4] = {{1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}};
            const bool ident = !std::memcmp(info->mat, I, sizeof(I));
            Mtx T;
            float sT = 1.0f;
            if (!ident) {
                Mtx t;
                PSMTXConcat(root, info->mat, t);
                PSMTXConcat(t, inv, T);
                sT = gate_scale_sym(T);
            }
            for (unsigned j = 0; j < e->n; ++j) {
                const InvisBall& b = invis_ball[e->first + j];
                const float (*A)[4] = parts[invis_ball_bone[e->first + j]]->mat;
                float w[3];
                invis_xf(A, b.c, w);
                float rho = b.r * gate_scale_sym(A) * 1.002f;
                if (!ident) { float u[3]; invis_xf(T, w, u); w[0] = u[0]; w[1] = u[1]; w[2] = u[2]; rho *= sT * 1.002f; }
                invis_acc(lo, hi, w, rho + 4.0f);
                ++any;
            }
        }
    }
    if (!any) return false;
    for (unsigned a = 0; a < 3; ++a) if (!coarse_finite(lo[a]) || !coarse_finite(hi[a])) return false;
    ++invis_pc_tests;
    if (!re4dc_ps2_interior_actor_hidden(lo, hi)) return false;
    ++invis_pc_hidden;
    return true;
}
#if RE4DC_PS2_INTERIOR_OWNER
// PS2_INTERIOR_ACTORS=2: an owner-path Ganado (admitted last time, kept by the crowd policy: invis_owner false) whose
// drawn infos lie behind the house walls. Trans only marks it (pc_gen); its OT entry, ModelRender and the transaction
// (plan, semantics, crowd_policy, actor_acquire's leases) run unchanged and only the owned submission is skipped
// (coarse_actor_transaction.inc), after the CROWD_LOD notes its runs would have left (native_actor_fast.cpp
// re4dc_actor_owned_crowd_replay: CROWD_INVIS_SKIP's re4dc_actor_crowd_note under its settled-parts rule). Each drawn
// info (be_flag 8) is bounded by balls placed as their own tests place them: a role drawn from its cast chunk by the
// chunk's pregate balls (invis_owner: root x info x inv(root) x bone, radius x scales x 1.002 + 4); an original
// source chunk or a fifth info by its source-mesh balls (invis_interior's, the source ModelData the chunk was
// converted from). Taken only when every drawn info is bounded, each is kept by the actor path's fog gate (every ball
// wholly nearer than the fogged View far the next Render uses, 100 mm spare: the fog prediction must be believed), so
// each of its runs reaches crowd_tier, and the world box of all the balls lies wholly outside the house box and the
// Trans-time cell hides it.
static bool invis_owner_interior(cModel* m, const InvisRec& r) {
    const InvisView& iv = invis_view;
    if (iv.fog < 0.0f) { ++invis_pco_why[5]; return false; }
    float (*root)[4] = m->pParts->mat;
    Mtx inv;
    if (!PSMTXInverse(root, inv)) return false;
    cParts* parts[64];
    const unsigned np = invis_parts(m, parts);
    if (np != kBones) return false;
    const float (*v)[4] = pG->Cam.v_mat;
    const float vz = __builtin_sqrtf(v[2][0] * v[2][0] + v[2][1] * v[2][1] + v[2][2] * v[2][2]);
    float lo[3] = {3.0e38f, 3.0e38f, 3.0e38f}, hi[3] = {-3.0e38f, -3.0e38f, -3.0e38f};
    static const float I[3][4] = {{1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}};
    unsigned any = 0, bindkey = 0;
    for (unsigned k = 0; k < r.count; ++k) {
        cModelInfo* info = r.info[k];
        if (!(info->be_flag & 8)) continue;
        unsigned role = 4;
        for (unsigned i = 0; i < 4; ++i) if (r.role[i] == info && ((r.pc_cast >> i) & 1u)) role = i;
        const bool ident = !std::memcmp(info->mat, I, sizeof(I));
        Mtx T;
        float sT = 1.0f;
        if (!ident) {
            Mtx t;
            PSMTXConcat(root, info->mat, t);
            PSMTXConcat(t, inv, T);
            sT = gate_scale_sym(T);
        }
        float deepest = -3.0e38f;
        auto ball = [&](float* w, float rho) {
            invis_acc(lo, hi, w, rho);
            const float depth = -(v[2][0] * w[0] + v[2][1] * w[1] + v[2][2] * w[2] + v[2][3]) + rho * vz;
            if (!(depth <= deepest)) deepest = depth;
        };
        if (role < 4) {
            if (!gate_init(r.app) || stress_layout) { ++invis_pco_why[1]; return false; }
            const unsigned n = gate_count[r.app][role], first = gate_first[r.app][role];
            if (!n) { ++invis_pco_why[1]; return false; }
            for (unsigned j = 0; j < n; ++j) {
                const GateBall& g = gate_ball[first + j];
                const float (*A)[4] = parts[gate_bone[first + j]]->mat;
                float w[3];
                invis_xf(A, g.c, w);
                float rho = g.r * gate_scale_sym(A) * 1.002f;
                if (!ident) { float u[3]; invis_xf(T, w, u); w[0] = u[0]; w[1] = u[1]; w[2] = u[2]; rho *= sT * 1.002f; }
                ball(w, rho + 4.0f);
            }
        } else {
            // invis_interior's per-info bound (re4dc_invis_note's bindkey over the parts' bind matrices).
            const ModelData* d = info->pData;
            if ((info->be_flag & 2) || d->nTex > 0xF7) { ++invis_pco_why[0]; return false; }
            if (!bindkey) {
                unsigned h = 2166136261u;
                for (unsigned i = 0; i < np; ++i) {
                    const unsigned* w = reinterpret_cast<const unsigned*>(&parts[i]->lt_inv_mat[0][0]);
                    for (unsigned j = 0; j < 12; ++j) h = (h ^ w[j]) * 16777619u;
                }
                bindkey = h | 1u;
            }
            const InvisMesh* e = invis_mesh_for(d, bindkey, parts, np);
            if (!e) { ++invis_pco_why[0]; return false; }
            if (invis_rigid(d)) {
                const unsigned no = d->pHead->partsNo;
                if (no >= np) { ++invis_pco_why[0]; return false; }
                const cParts* p = (m->be_flag & 0x2000) ? reinterpret_cast<const cParts*>(m->pParts) + no : parts[no];
                Mtx W;
                PSMTXConcat(p->mat, info->mat, W);
                const InvisBall& b = invis_ball[e->first];
                float w[3];
                invis_xf(W, b.c, w);
                ball(w, b.r * gate_scale_sym(W) * 1.002f + 4.0f);
            } else {
                for (unsigned j = 0; j < e->n; ++j) {
                    const InvisBall& b = invis_ball[e->first + j];
                    const float (*A)[4] = parts[invis_ball_bone[e->first + j]]->mat;
                    float w[3];
                    invis_xf(A, b.c, w);
                    float rho = b.r * gate_scale_sym(A) * 1.002f;
                    if (!ident) { float u[3]; invis_xf(T, w, u); w[0] = u[0]; w[1] = u[1]; w[2] = u[2]; rho *= sT * 1.002f; }
                    ball(w, rho + 4.0f);
                }
            }
        }
        if (!(deepest + 100.0f <= iv.far_owner)) { ++invis_pco_why[2]; return false; }  // NaN fails too
        ++any;
    }
    if (!any) return false;
    for (unsigned a = 0; a < 3; ++a) if (!coarse_finite(lo[a]) || !coarse_finite(hi[a])) { ++invis_pco_why[3]; return false; }
    if (re4dc_ps2_interior_owner_hidden(lo, hi)) return true;
    ++invis_pco_why[4];
    return false;
}
#endif
#endif
extern "C" unsigned re4dc_invis_decide(cModel* m) {
    if (m->id < 0x10 || m->id > 0x20) return 0;
    if (!invis_view.ok) { ++invis_n[6]; return 0; }
    InvisRec* r = invis_find(m, false);
    if (!r) { ++invis_n[3]; return 0; }
    if (!invis_same(*r, m)) { ++invis_n[4]; return 0; }
    unsigned k = 0;
    if (r->outcome == 1) {
        k = invis_owner(m, *r) ? 1u : 0u;
#if RE4DC_PS2_INTERIOR_OWNER
        // Not a Trans skip (k stays 0): the mark lets the next Render's transaction skip the owned submission.
        if (!k) {
            ++invis_pco_tests;
            if (invis_owner_interior(m, *r)) { r->pc_gen = invis_gen; ++invis_pco_hidden; }
        }
#endif
    }
    else if (r->outcome == 2) {
        k = invis_source(m, *r) ? 2u : 0u;
#if RE4DC_PS2_INTERIOR_ACTORS
        if (!k && invis_interior(m, *r)) k = 2u;
#endif
        if (k && !invis_settled(m)) { ++invis_unsettled; k = 0; }
    }
    else { ++invis_n[5]; return 0; }
    ++invis_n[k];
#if RE4DC_CROWD_INVIS_SKIP == 2
    r->mark = (unsigned char)k; r->mark_gen = invis_gen;
    if (k) ++invis_marked;
    return 0;
#else
    return k;
#endif
}
#if RE4DC_PS2_INTERIOR_OWNER
// PS2_INTERIOR_ACTORS=2 (coarse_actor_transaction.inc, an owner-path Ganado's draw): 1 when this frame's Trans marked
// m as hidden by the interior cell (same structure, still owner path).
extern "C" int re4dc_invis_owner_marked(cModel* m) {
    if (!m || m->id < 0x10 || m->id > 0x20) return 0;
    const InvisRec* r = invis_find(m, false);
    return r && r->pc_gen == invis_gen && r->outcome == 1 && invis_same(*r, m);
}
#endif
#if RE4DC_CROWD_INVIS_SKIP == 2
// ModelRender (=2): the kind the knob would have taken for m in this image (0: none).
extern "C" unsigned re4dc_invis_marked(cModel* m) {
    if (!m || m->id < 0x10 || m->id > 0x20) return 0;
    const InvisRec* r = invis_find(m, false);
    return r && r->mark_gen == invis_gen ? r->mark : 0u;
}
// ModelRender (=2): a Ganado the knob would have skipped in this image must emit nothing and keep its path; for a
// source-path one, crowd (trans.cpp invisCrowdCheck: 1 / 0, -1 not checked) says whether the crowd entry its parts
// left equals the one re4dc_actor_crowd_note would leave.
extern "C" void re4dc_invis_check(cModel* m, unsigned emitted, int crowd) {
    if (!m || m->id < 0x10 || m->id > 0x20) return;
    InvisRec* r = invis_find(m, false);
    if (!r || !r->mark || r->mark_gen != invis_gen) return;
    ++invis_checked;
    if (crowd >= 0) { ++invis_crowd_checked; if (!crowd) ++invis_crowd_mis; }
    const bool path = r->outcome == r->mark;
    if (!path) ++invis_path_mis;
    if (emitted) { ++invis_violations; invis_violation_tris += emitted; }
    if ((emitted || !path || crowd == 0) && invis_logs < 64) {
        ++invis_logs;
        const float (*rt)[4] = m->pParts->mat;
        re4dc_log("INVIS2 BAD t=%u id=%x kind=%u outcome=%u emitted=%u crowd=%d root=%g,%g,%g\n", unsigned(pG->Frame_cnt),
                  unsigned(m->id), r->mark, r->outcome, emitted, crowd, rt[0][3], rt[1][3], rt[2][3]);
    }
    r->mark = 0;
}
#endif
#endif
extern "C" int re4dc_crowd_offscreen(cModel* m) {
#if RE4DC_CROWD_INVIS_SKIP
    invis_note_owner(m);
#endif
#if RE4DC_CROWD_CULL
    if(!bound || bound->owner!=m || owner_info_count[owner_current_slot]!=4)return 0;
    for(unsigned role=2;role<4;++role)if(owner_original_chunk(role))return 0;
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    float P[7];GXGetProjectionv(P);
    const float pnear=P[6]/(P[5]-1.0f),pfar=P[6]/P[5],view_far=re4dc_fog_gate_far();
    gate_far_limit=view_far>pnear && view_far<pfar?view_far:3.0e38f;
    Mtx mv[4];
    const unsigned skip=gate_cull_checked(m,owner_plan_app,bound->infos,bound->parts,inv,mv);
    gate_far_limit=3.0e38f;
    return skip==gate_visible;
#else
    (void)m;return 0;
#endif
}
#endif
extern "C" int re4dc_actor_plan_ganado(cModel* m,Re4dcActorPlan* out) {
#if RE4DC_ACTOR_BIND_REUSE
    owner_bind_token.m=nullptr;
    if(!out || !owner_ganado_bind(m))return 0;
    const unsigned bind_life_serial=re4dc_material::life::serial;  // right after the bind (its refresh included)
#else
    if(!out || !owner_ganado_bind(m))return 0;
#endif
    Re4dcActorPlan p{};const unsigned a=bound->appearance,t=gc::appearance_texture[a];
    p.count=owner_info_count[owner_current_slot];p.appearance=a;p.image=image_of(t);p.crc=RE4DC_GC_KEYS[t].crc;p.fnv=RE4DC_GC_KEYS[t].fnv;p.palettes=owner_ganado_palettes;
#define RE4DC_GANADO_ROLE(app,role,prefix) re4dc_actor::plan_chunk(p,role,bound->infos[role],gc::chunks[app][role],RE4DC_OWNER_INPUT(ganadocast,prefix,gc::chunks[app][role],34))
#define RE4DC_GANADO_APP(app) \
    case app: RE4DC_GANADO_ROLE(app,0,a##app##_i0);RE4DC_GANADO_ROLE(app,1,a##app##_i1); \
              RE4DC_GANADO_ROLE(app,2,a##app##_i2);RE4DC_GANADO_ROLE(app,3,a##app##_i3);break
    owner_plan_app=a;
#if RE4DC_CROWD_FAR
    if(re4dc_crowd_far(m) && skin_init(a+kApps)) {
#define RE4DC_GANADO_FAR_ROLE(app,role,prefix) re4dc_actor::plan_chunk(p,role,bound->infos[role],gc::far::chunks[app][role],RE4DC_OWNER_INPUT(ganadocast::far,prefix,gc::far::chunks[app][role],34))
#define RE4DC_GANADO_FAR_APP(app) \
    case app: RE4DC_GANADO_FAR_ROLE(app,0,a##app##_i0);RE4DC_GANADO_FAR_ROLE(app,1,a##app##_i1); \
              RE4DC_GANADO_FAR_ROLE(app,2,a##app##_i2);RE4DC_GANADO_FAR_ROLE(app,3,a##app##_i3);break
        switch(a) { RE4DC_GANADO_FAR_APP(0);RE4DC_GANADO_FAR_APP(1);RE4DC_GANADO_FAR_APP(2);RE4DC_GANADO_FAR_APP(3);RE4DC_GANADO_FAR_APP(4);default:return 0; }
#undef RE4DC_GANADO_FAR_APP
#undef RE4DC_GANADO_FAR_ROLE
        for(unsigned role=0;role<4;++role)p.immutable_asset_id[role]=kOwnerFarAsset+a*4u+role;
        const unsigned ft=far_texture(a);  // skin_init's far_same proved it is a near atlas
        p.image=image_of(ft);p.crc=RE4DC_GC_KEYS[ft].crc;p.fnv=RE4DC_GC_KEYS[ft].fnv;
        owner_plan_app=a+kApps;
    } else
#endif
    {
    switch(a) { RE4DC_GANADO_APP(0);RE4DC_GANADO_APP(1);RE4DC_GANADO_APP(2);RE4DC_GANADO_APP(3);RE4DC_GANADO_APP(4);default:return 0; }
    for(unsigned role=0;role<4;++role)p.immutable_asset_id[role]=9u+a*4u+role;
    }
#undef RE4DC_GANADO_APP
#undef RE4DC_GANADO_ROLE
    p.material_count=1;p.materials[0].image=p.image;p.materials[0].crc=p.crc;p.materials[0].fnv=p.fnv;
    for(unsigned role=0;role<p.count;++role) {
        if(const auto* source=owner_original_chunk(role)) {
            if(role<4)p.palette_bytes-=(p.input[role].palette_count*48u+31u)&~31u;
            auto* info=role<4?bound->infos[role]:owner_extra_info[owner_current_slot];
            re4dc_actor::plan_chunk(p,role,info,*source,source->input);p.immutable_asset_id[role]=source->asset_id;
        }
        auto& run=p.runs[p.run_count++];run.role=role;run.immutable_asset_id=p.immutable_asset_id[role];
        run.triangles=p.input[role].triangles;run.uv=p.input[role].uv;run.stream=p.input[role].stream;
        if(owner_original_chunk(role) && !owner_add_source_material(m,p,role,run.material))return 0;
    }
    // One optional six-entry source accessory adds at most288 palette bytes.
    if(p.palette_bytes>7776 || p.workspace_bytes>13696)return 0;
#if RE4DC_ACTOR_BIND_REUSE
    if(!re4dc_material::life::exhausted)
        owner_bind_token={m,re4dc_actor_tx_serial,bind_life_serial,owner_binding_revision[owner_current_slot],owner_current_slot};
#endif
    *out=p;return 1;
}
#endif
