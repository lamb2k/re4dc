// Source candidate, included ONCE by coarse_actor_owner_leon.inc instead of
// coarse_actor_certificate_pending.inc. No source preparation or texture load.
// The comparison executes synchronously at the original Render callback; no
// result or borrowed pointer survives it. This is not a source-allocation lease.
#include <cstdint>
#include <cstring>
#include "player.h" // canonical pPL declaration for the reviewed Leon identity
#include "actor_lifetime.h"
#include "actor_material_policy.h"
extern u8 gxCsScale[];
namespace re4dc_material {
struct Digest { unsigned bytes,crc,fnv; };
struct Part { unsigned char material[13]; unsigned bytes,polygons,crc,fnv; };
struct Texture {
    unsigned crc,fnv,width,height,format;
    unsigned sampler[8]; // wrap S/T, min/mag, LOD bits, edge, min/max LOD
    unsigned palette_format; Digest palette;
};
struct Model {
    unsigned header[10]; // see archive-materials.json header_fields
    Digest positions,normals,weights,uv;
    const Part* parts;
};
struct Role {
    unsigned appearance,role,source_bin,source_tpl;
    const Model* model; const Texture* textures; unsigned texture_count;
};
struct SourceBlob { const Model* model; unsigned family,bin; Digest normalized; };

enum Need : unsigned {
    Diffuse=1, Specular=2, Mask=4, Bump=8, Morph=16,
    SourceLighting=32, SourcePass=64, AtlasSampler=128
};
enum class Error : unsigned {
    None, UnknownAppearance, MissingRole, FrameOwner, BadRange,
    Geometry, ConvertedStream, Material, Texture, Palette, Sampler,
    LiveModifier, PassGroup, Capability, MissingOwnerProof, IncompleteColourProof
};
struct Result { Error error; unsigned role,part,required,identity_roles; };
// These are direct SOURCE archive facts, not declarations that the atlas
// implements the material. No production default is enabled by this table.
#include "actor_material_records.inc"

inline bool readable(const void* p,unsigned n) {
    const auto a=reinterpret_cast<std::uintptr_t>(p);
    return a>=0x8c000000u && a<=0x8d000000u && n<=0x8d000000u-a;
}
inline unsigned u32at(const void* p,unsigned at) {
    unsigned x;std::memcpy(&x,static_cast<const unsigned char*>(p)+at,4);return x;
}
inline unsigned u16at(const void* p,unsigned at) {
    unsigned short x;std::memcpy(&x,static_cast<const unsigned char*>(p)+at,2);return x;
}
inline const void* ptrat(const void* p,unsigned at) {
    return reinterpret_cast<const void*>(std::uintptr_t(u32at(p,at)));
}
inline unsigned floatbits(float f) { unsigned x;std::memcpy(&x,&f,4);return x; }
bool digest(const void* p,const Digest& want) {
    if(!readable(p,want.bytes))return false;
    unsigned crc=~0u,fnv=2166136261u;
    auto* b=static_cast<const unsigned char*>(p);
    for(unsigned k=0;k<want.bytes;++k) {
        crc^=b[k];fnv=(fnv^b[k])*16777619u;
        for(unsigned j=0;j<8;++j)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));
    }
    return ~crc==want.crc && fnv==want.fnv;
}
const Role* find(unsigned appearance,unsigned role) {
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
    for(unsigned k=0;k<RE4DC_ROLE_COUNT;++k)if(RE4DC_ROLE(k).appearance==appearance && RE4DC_ROLE(k).role==role)return &RE4DC_ROLE(k);
#else
    for(const auto& r:roles)if(r.appearance==appearance && r.role==role)return &r;
#endif
    return nullptr;
}
// Exact certified descriptors have a single base level. Source
// commonModelTrans calls GXInitTexObjLOD (and applies global aniso) only
// when minLOD != maxLOD, so room aniso is inapplicable to these textures.
inline bool base_level_sampler(const unsigned* s) {
    return s[0]==1 && s[1]==1 && s[2]==1 && s[3]==1 &&
           s[4]==0 && s[5]==0 && s[6]==0 && s[7]==0;
}
// cModel::type selects the authored appearance, not a shader modifier.
// Em12Set and Em15Set bind precisely these body/head/TPL families. The
// per-role immutable owner and complete material checks still run below.
inline bool source_appearance_type(unsigned appearance,unsigned id,unsigned type) {
    if(appearance==0x100)return id==0 && type==0;
#if RE4DC_ACTOR_PL08
    // pl08 is the same player cModel (id 0, type 0); its costume is proved by the 0x108 role rows, not by type.
    if(appearance==0x108)return id==0 && type==0;
#if RE4DC_LEON_HEADLESS
    if(appearance==0x109)return id==0 && type==0;  // LEON_HEADLESS: pl08 after setHead(0), proved by the 0x109 rows
    if(appearance==0x10A)return id==1;  // LEON_HEADLESS v2: the flying head cObj01 (ObjMgr id 1), proved by the 0x10A row
#endif
#endif
    static const unsigned char types[5]={1,0,3,4,11};
#if RE4DC_ACTOR_APPEARANCE_ALIAS
    if(appearance<5 && id==(appearance==0?0x12u:0x15u) && type==types[appearance])return true;
    // ACTOR_APPEARANCE_ALIAS (crowd.mk): other Ganado modules' types whose EmXXSet loads byte-identical source
    // entries for every model slot and reachable role BIN/TPL of the appearance (generated and proved from the
    // original archives by tools/native_appearance_alias.py). The role/owner/material proofs below still run.
    static const unsigned char alias[][3]={
#if RE4DC_ACTOR_APPEARANCE_ALIAS == 2
#include "actor_appearance_aliases_ext.inc"
#else
#include "actor_appearance_aliases.inc"
#endif
    };
    for(const auto& r:alias)if(r[0]==appearance && r[1]==id && r[2]==type)return true;
    return false;
#else
    return appearance<5 && id==(appearance==0?0x12u:0x15u) && type==types[appearance];
#endif
}
inline bool room_colour_scale(unsigned scale,bool flat_native_look) {
    // The approved native look uses its existing constant lighting. Room
    // TEV scales 0/1/2 are valid source environment states, not actor fades.
    return flat_native_look ? scale<=2 : scale==2;
}
#if RE4DC_NATIVE_MODEL_REGISTRY && defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22
inline unsigned source_model_tev_group(const cModel* m,bool leon,bool registry) {
#if defined(RE4DC_NMR_PL_ASHLEY) && RE4DC_NMR_PL_ASHLEY && RE4DC_NMR_ASHLEY >= 2
    // cPlAshley::setModel assigns source TEV group1. registry_model already
    // proved the exact model0/141-joint/seven-role descriptor before this call.
    if(registry && m && m==(const cModel*)pPL && m->id==0u && m->nParts==141u)return 1u;
#endif
    // cSubLuis::init uses group 1. pSubEm is player.h's canonical pSUB alias;
    // registry_model and frame membership have already proved this descriptor.
#if defined(RE4DC_NMR_ASHLEY) && RE4DC_NMR_ASHLEY
    // PS2_ASHLEY on route builds: the partner is Luis (id 4) or Ashley (id 3, pl_ashley.cpp TevScaleGroup = 1).
    return registry && m && m==(const cModel*)pSubEm && (m->id==4 || m->id==3) ? 1u : (leon?1u:0u);
#else
    return registry && m && m==(const cModel*)pSubEm && m->id==4 ? 1u : (leon?1u:0u);
#endif
}
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY && defined(RE4DC_NMR_ASHLEY) && RE4DC_NMR_ASHLEY && !(defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22)
// PS2_ASHLEY: the partner Ashley (pSUB, model id 3) is set up with TEV group 1 like Leon and Luis (pl_ashley.cpp
// TevScaleGroup = 1; census: ACTOR_MATERIAL live tevgrp=1); her registry descriptor is drawn with the same native look.
inline unsigned source_model_tev_group(const cModel* m,bool leon,bool registry) {
#if defined(RE4DC_NMR_PL_ASHLEY) && RE4DC_NMR_PL_ASHLEY && RE4DC_NMR_ASHLEY >= 2
    // cPlAshley::setModel assigns source TEV group1. registry_model already
    // proved the exact model0/141-joint/seven-role descriptor before this call.
    if(registry && m && m==(const cModel*)pPL && m->id==0u && m->nParts==141u)return 1u;
#endif
    return registry && m && m==(const cModel*)pSubEm && m->id==3 ? 1u : (leon?1u:0u);
}
#endif
#if RE4DC_ACTOR_PLAN
} // re4dc_material
#include "actor_plan.h"
namespace re4dc_material {
namespace life { extern unsigned serial; extern bool exhausted; }  // actor_lifetime.inc
// ACTOR_PLAN (actorplan.mk): texture()'s verdict is a function of the row entry e and the bytes it reads: the
// descriptor's two words, the 36 header bytes at h and the 32 R4NREF bytes at n (a palette-less row). A None verdict is
// kept with a copy of those bytes, keyed on the descriptor, the row entry and the lifetime serial (room rows are
// republished only through a serial move); a reuse compares the 19 words again and returns None only when every one is
// equal, so the same verdict follows. Palette rows (a digest of the CLUT), the key-0 bump rows and unaligned headers
// are never kept. The hand TPL textures of Leon's pose infos are checked this way every pass (re4dc_material::hand_info).
struct TexMemo { const void* descriptor;const Texture* e;unsigned serial;unsigned words[19]; };
constexpr unsigned kTexMemos=16;  // Leon's two pose hands (a few textures each) and the Ganado source materials
RE4DC_PLAN_ARRAY(TexMemo,tex_memo,kTexMemos,kRe4dcPlanTexOff);unsigned tex_memo_next;
Error texture_full(const void* descriptor,const Texture& e);
inline bool tex_words(const void* descriptor,unsigned* w) {
    if(!readable(descriptor,8) || (reinterpret_cast<std::uintptr_t>(descriptor)&3u))return false;
    const unsigned* d=static_cast<const unsigned*>(descriptor);
    const void* h=reinterpret_cast<const void*>(std::uintptr_t(d[0]));
    if(d[1] || !readable(h,36) || (reinterpret_cast<std::uintptr_t>(h)&3u))return false;
    const unsigned* hw=static_cast<const unsigned*>(h);
    const void* n=reinterpret_cast<const void*>(std::uintptr_t(hw[2]));
    if(!readable(n,32) || (reinterpret_cast<std::uintptr_t>(n)&3u))return false;
    const unsigned* nw=static_cast<const unsigned*>(n);
    w[0]=d[0];w[1]=d[1];
    for(unsigned k=0;k<9;++k)w[2+k]=hw[k];
    for(unsigned k=0;k<8;++k)w[11+k]=nw[k];
    return true;
}
Error texture(const void* descriptor,const Texture& e) {
    const bool plan=RE4DC_PLAN_ON && !life::exhausted && !e.palette.bytes && (e.crc || e.fnv);
    if(plan) {
        for(const auto& t:tex_memo) {
            if(t.descriptor!=descriptor || t.e!=&e || t.serial!=life::serial)continue;
            unsigned w[19];
            const bool hit=tex_words(descriptor,w) && !std::memcmp(w,t.words,sizeof(w));
#if RE4DC_ACTOR_PLAN == 2
            const Error full=texture_full(descriptor,e);
            re4dc_actor_plan_note(APLAN_HAND,hit,hit && full!=Error::None);
            return full;
#else
            re4dc_actor_plan_note(APLAN_HAND,hit,0);
            if(hit)return Error::None;
            break;
#endif
        }
    }
    const Error r=texture_full(descriptor,e);
    if(plan && r==Error::None) {
        TexMemo t{descriptor,&e,life::serial,{}};
        if(tex_words(descriptor,t.words))tex_memo[tex_memo_next++%kTexMemos]=t;
    }
    return r;
}
Error texture_full(const void* descriptor,const Texture& e) {
#else
Error texture(const void* descriptor,const Texture& e) {
#endif
    if(!readable(descriptor,8))return Error::BadRange;
    const void* h=ptrat(descriptor,0);const void* clut=ptrat(descriptor,4);
    if(!readable(h,36))return Error::BadRange;
    const auto* b=static_cast<const unsigned char*>(h);
    if(u16at(h,2)!=e.width || u16at(h,0)!=e.height || u32at(h,4)!=e.format)return Error::Texture;
    unsigned sampler[8]={u32at(h,12),u32at(h,16),u32at(h,20),u32at(h,24),u32at(h,28),b[32],b[33],b[34]};
    if(std::memcmp(sampler,e.sampler,sizeof(sampler)))return Error::Sampler;
    // Keep the exact row comparison above and reject any changed sampler,
    // LOD range, bias or edge flag. Only the source-inapplicable global aniso
    // test is removed; no mipmapped descriptor gains admission here.
    if(!base_level_sampler(sampler))return Error::Sampler;
#if RE4DC_NMR_DROP_BUMP || RE4DC_NMR_CROW
    // NATIVE_MODEL_REGISTRY_DROP_BUMP (and PS2_CROW): a registry row with key 0-0 is a texture the source path only binds as a bump
    // map (never drawn, so the disc keeps its raw pixels, not an R4NREF); its exact header and sampler matched above.
    if(!e.crc && !e.fnv && !e.palette.bytes)return clut?Error::Palette:Error::None;
#endif
    const void* n=ptrat(h,8);const unsigned size=e.palette.bytes?64u:32u;
    if(!readable(n,size))return Error::BadRange;
    const char* magic=e.palette.bytes?"R4PREF\0":"R4NREF\0";
    if(std::memcmp(n,magic,8) || u32at(n,8)!=e.crc || u32at(n,12)!=e.fnv ||
       u32at(n,16)!=e.width || u32at(n,20)!=e.height || u32at(n,24)!=e.format)return Error::Texture;
    if(e.palette.bytes) {
        if(!readable(clut,12) || u16at(clut,0)*2u!=e.palette.bytes || u32at(clut,4)!=e.palette_format ||
           u32at(n,32)!=e.palette_format || u32at(n,36)!=e.palette.bytes ||
           u32at(n,40)!=e.palette.crc || u32at(n,44)!=e.palette.fnv ||
           !digest(ptrat(clut,8),e.palette))return Error::Palette;
    } else if(clut)return Error::Palette;
    return Error::None;
}
} // re4dc_material
#include "actor_lifetime.inc"
#if RE4DC_ACTOR_PROOF_LEAN
// ACTOR_PROOF_LEAN: re4dc_actor_source_material's body for a row the caller already resolved in this evaluation.
static int lean_source_material(cModel*,cModelInfo*,unsigned,unsigned,const re4dc_material::Role*,Re4dcActorOwnedMaterial*);
#endif
#if RE4DC_ACTOR_MATERIAL_RECORD
#if RE4DC_ACTOR_PROOF_LEAN != 1
#error ACTOR_MATERIAL_RECORD extends the ACTOR_PROOF_LEAN=1 certificate (a separate compare build from ACTOR_PROOF_LEAN=2)
#endif
// ACTOR_MATERIAL_RECORD (native_model_registry.mk): a certificate's lifetime-epoch facts, kept per model between
// evaluations. A record holds only what is fixed while life::epoch is unchanged and life is not exhausted: each
// role's lifetime record slot (find_info) and unique current row, and the archive verdict of info() (the role
// TPL's descriptors / headers / R4xREF / CLUT bytes and the ModelPart header bytes, all inside the record's owner
// archives) with the required bits it adds. Every life::changed() (adopt, retire, revoke, forget, room rows publish /
// retire, swap park / unpark) moves the epoch; a stream conversion (pending) and every cModel / cModelInfo / ModelData
// header / modifier / gxCsScale / plan / run value stay live. A hit is taken only when the epoch, appearance and
// count match, every plan info is in the model's info list (actor_current_role's walk) and each role's record slot
// still names that info with info_current() true for its row, which is then exactly actor_current_role's result;
// anything else evaluates the whole certificate and stores it again on success.
namespace re4dc_material { namespace record {
constexpr unsigned kRoles=sizeof(Re4dcActorPlan::info)/sizeof(Re4dcActorPlan::info[0]),kRecords=16;
static_assert(life::kInfos<=256,"record slot is a byte");
struct Record {
    cModel* m;unsigned epoch,appearance;unsigned char count,need,slot[kRoles];unsigned short row[kRoles];
};
Record records[kRecords];unsigned replace;
const Record* hit(cModel* m,const Re4dcActorPlan* p) {
    using namespace life;
    // compare()'s own precondition first, before any lookup or dereference: a failure takes no record and
    // compare_core returns BadRange exactly as the whole certificate does.
    if(!m || !p || !readable(m,sizeof(*m)))return nullptr;
    if(exhausted)return nullptr;
    const Record* r=nullptr;for(const auto& x:records)if(x.m==m){r=&x;break;}
    if(!r || r->epoch!=epoch || r->appearance!=p->appearance || r->count!=p->count || p->count>kRoles)return nullptr;
    unsigned n=0,seen=0;
    for(auto* q=m->pModelInfo;q && n<kRe4dcActorRoles+1;q=q->pList,++n)
        for(unsigned k=0;k<p->count;++k)if(q==p->info[k])seen|=1u<<k;
    if(n>kRe4dcActorRoles || seen!=(1u<<p->count)-1u)return nullptr;
    for(unsigned k=0;k<p->count;++k) {
        const auto& i=infos_live[r->slot[k]];
        if(i.info!=p->info[k] || !info_current(i,r->row[k]))return nullptr;
    }
    return r;
}
void store(cModel* m,const Re4dcActorPlan* p,const Result& res,const Role* const* rows) {
    using namespace life;
    if(exhausted || !m || p->count>kRoles)return;
    Record x{};x.m=m;x.epoch=epoch;x.appearance=p->appearance;x.count=(unsigned char)p->count;
    x.need=(unsigned char)(res.required&(Mask|SourcePass|Bump|Specular));
    for(unsigned k=0;k<p->count;++k) {
        const Info* i=find_info(p->info[k]);if(!i || !rows[k])return;
        unsigned r=0;while(r<RE4DC_ROLE_COUNT && &RE4DC_ROLE(r)!=rows[k])++r;
        if(r>=RE4DC_ROLE_COUNT || r>0xffffu)return;
        x.slot[k]=(unsigned char)(i-infos_live);x.row[k]=(unsigned short)r;
    }
    Record* at=nullptr;
    for(auto& y:records)if(y.m==m){at=&y;break;}
    if(!at)for(auto& y:records)if(!y.m || y.epoch!=epoch){at=&y;break;}
    if(!at)at=&records[replace++%kRecords];
    *at=x;
}
#if RE4DC_ACTOR_MATERIAL_RECORD == 2
// Compare build counters ("AMR" lines every 600 frames): evaluations, record hits (whose result is compared with the
// whole certificate, which decides), stores, and hits whose result differed (bad must be 0).
struct Count { unsigned calls,hits,stores,bad,last; } c;
#endif
} }
#endif
namespace re4dc_material {
#if RE4DC_NMR_CROW
bool crow_rows;  // PS2_CROW: compare() is proving a registry crow (model id 0x23) plan
#endif
#if RE4DC_NMR_BOAT
bool boat_rows;  // PS2_CAST_BOAT: compare() is proving a registry boat (pl0f, model id 0x0f) plan
#endif
#if RE4DC_NMR_ROLES5
// NATIVE_MODEL_REGISTRY_ROLES5 (lane cast16): compare() is proving a registry castle armour plan (em3c 0x3c / em25 0x25),
// whose descriptors drop "bump" and "alt-specular" (flag 0x80, specularSetup2: GX only on the DC source path, the crow's rule).
bool armor_rows;
#else
constexpr bool armor_rows=false;
#endif
#if RE4DC_ACTOR_MATERIAL_RECORD
// archive=false: a record hit; the archive verdict (TPL and ModelPart header bytes, checked last) is the record's.
Error info(cModelInfo* i,const Role& row,Result& out,bool diagnostic,bool archive) {
#else
Error info(cModelInfo* i,const Role& row,Result& out,bool diagnostic) {
#endif
    if(!readable(i,sizeof(*i)) || !readable(i->pData,sizeof(ModelData)))return Error::BadRange;
    const auto& e=*row.model;const auto& d=*i->pData;
    unsigned h[10]={d.flags,d.shift,d.nParts,d.nVtx,d.nNrm,d.nTex,
      d.weight_palette_num,d.weight_ext_num,d.displist_num,d.version};
    if(std::memcmp(h,e.header,sizeof(h)))return Error::Geometry;
    // Immutable arrays are scanned ONLY by the explicit diagnostic entry.
    // Production requires the current owner/revision proof before this reader.
    if(diagnostic && (!digest(d.vtxOrig,e.positions) || !digest(d.nrmOrig,e.normals) ||
       !digest(d.pWeight,e.weights) || !digest(d.pTex,e.uv)))return Error::Geometry;
    // These are exact infos including their hidden state and second-pass bit.
    // Source visibility bit8 can vary; all other unproved bits decline.
    unsigned expected=1;
#if RE4DC_LEON_HEADLESS
    // LEON_HEADLESS: 0x109's role 3 is the neck (setHead(0) adds it plain: no shape bit).
    if(RE4DC_LEON_LIKE(row.appearance) && row.role==3 && row.appearance!=0x109u)expected|=2;
#else
    if(RE4DC_LEON_LIKE(row.appearance) && row.role==3)expected|=2;
#endif
    if(RE4DC_LEON_LIKE(row.appearance) && row.role==7)expected|=0x40;
#if RE4DC_NATIVE_MODEL_REGISTRY && (RE4DC_ROUTE_CH22 || RE4DC_ROUTE_CH23 || RE4DC_NMR_MERCHANT)
    // The source merchant explicitly gives its robe and selected coat their own material color.
    // Exact source-role ownership was proved before info(); all color/modifier
    // checks immediately below and the transaction lighting check still apply.
    if(re4dc_registry_merchant_robe(row.appearance,row.role,row.source_bin,row.source_tpl))expected|=0x20u;
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY && defined(RE4DC_NMR_ASHLEY) && RE4DC_NMR_ASHLEY >= 2
    // PS2_ASHLEY=2: Ashley's head (role 1) keeps the source shape bit; the owner path draws its PS2 rest face (the
    // source shapes still run on the GC buffer; user look decision pending).
#if defined(RE4DC_NMR_PL_ASHLEY) && RE4DC_NMR_PL_ASHLEY
    // NATIVE_MODEL_REGISTRY_PL_ASHLEY: playable Ashley's face (role 1, BIN 7 / TPL 9) keeps the shape bit as the
    // partner's head does; her skirt (role 3, BIN 8 / TPL 5) keeps be_flag 0x40 (cPlAshley::setModel), which the
    // transaction draws in the ot_type 7 second pass as the source does. Any other bit or ordinal still declines.
    const int pl_ashley=re4dc_registry_player_ashley_role(row.appearance,row.role,row.source_bin,row.source_tpl);
    const bool ashley_face=re4dc_registry_ashley_face(row.appearance,row.role)!=0 || pl_ashley==1;
    if(pl_ashley==2)expected|=0x40u;
#else
    const bool ashley_face=re4dc_registry_ashley_face(row.appearance,row.role)!=0;
#endif
    if(ashley_face)expected|=2;
#endif
    if((i->be_flag&~8u)!=expected)return Error::PassGroup;
    if(i->invisible_factor!=1.0f || i->blend_mode || i->colorWord!=0xffffffffu ||
       i->color2[0] || i->color2[1] || i->color2[2] || i->color2[3] ||
       (i->flagsDC && !RE4DC_NMR_BLEND_IDLE(i,row.appearance)) || i->pAddTpl || i->nAddTex ||
       ((i->blendRatio || i->blendType) && !RE4DC_NMR_BLEND_ICE(i,row.appearance)) ||
       (i->texBlendTbl && !RE4DC_NMR_BLEND_IDLE(i,row.appearance)) || i->pTexAnim || i->uvU || i->uvV || i->uvScrollU || i->uvScrollV)return Error::LiveModifier;
    if(i->be_flag&2) {
        // shape.cpp writes the prepared destination buffer, not vtxOrig.
        // Native-look explicitly retains the reviewed bone-driven Leon face.
        // Source callback/ShapeMove still runs; this does not emulate morphs.
#if RE4DC_NATIVE_MODEL_REGISTRY && defined(RE4DC_NMR_ASHLEY) && RE4DC_NMR_ASHLEY >= 2
        const bool face=(RE4DC_ACTOR_LEON_NATIVE_LOOK && RE4DC_LEON_LIKE(row.appearance) && row.role==3) || ashley_face;
#else
        const bool face=RE4DC_ACTOR_LEON_NATIVE_LOOK && RE4DC_LEON_LIKE(row.appearance) && row.role==3;
#endif
        if(i->pShape && !readable(i->pShape,4))return Error::BadRange;
        for(const auto& shape:i->shape) {
            if(!coarse_finite(shape.rate) || (shape.data && !readable(shape.data,4)))return Error::BadRange;
            if(shape.rate!=0.0f && (!face || !shape.data))return Error::LiveModifier;
        }
        out.required|=Morph;
    }
#if RE4DC_ACTOR_MATERIAL_RECORD
    if(!archive){++out.identity_roles;return Error::None;}
#endif
    const void* tp=i->tpl_addr;
    if(!readable(tp,12) || u32at(tp,4)!=row.texture_count)return Error::Texture;
    const void* td=ptrat(tp,8);
    if(!readable(td,row.texture_count*8u))return Error::BadRange;
    for(unsigned k=0;k<row.texture_count;++k) {
        Error r=texture(static_cast<const unsigned char*>(td)+k*8,row.textures[k]);
        if(r!=Error::None)return r;
    }
    auto* p=reinterpret_cast<const unsigned char*>(d.pParts);
    for(unsigned k=0;k<d.displist_num;++k) {
        out.part=k;const auto& want=e.parts[k];
        if(!readable(p,32))return Error::BadRange;
        if(std::memcmp(p+11,want.material,13) || u32at(p,24)!=want.bytes ||
           u32at(p,28)!=want.polygons)return Error::Material;
        if(!readable(p+32,want.bytes))return Error::BadRange;
        // In-place FE conversion destroys original GX bytes. Do not pretend
        // header/pointer identity proves its UV/topology/material admission.
        if(diagnostic && want.bytes && p[32]==0xfe)return Error::ConvertedStream;
        if(diagnostic && !digest(p+32,{want.bytes,want.crc,want.fnv}))return Error::Geometry;
        const auto* mat=want.material;const unsigned f=mat[0];
        if(mat[1]>=row.texture_count)return Error::Material;
        if(f&4) {
            if(mat[3]>=row.texture_count)return Error::Material;
            out.required|=Mask|SourcePass;
        }
        if(f&1) {
            if(mat[2]>=row.texture_count)return Error::Material;
            out.required|=Bump;
        }
        if(f&0x13)out.required|=Specular;
        // All material bytes, including alphaRef/specType/specPow/specTexOrg,
        // already matched. Unknown source flag programs remain unsupported.
#if RE4DC_NMR_CROW && RE4DC_NMR_BOAT
        // PS2_CROW + PS2_CAST_BOAT: the crow's and the boat's flag 0x80, as below.
        if(f&~((crow_rows || boat_rows || armor_rows)?0x87u:7u))return Error::Material;
#elif RE4DC_NMR_CROW
        // PS2_CROW (Phase 2 A3): the crow body's flag 0x80 (specularSetup2) is GX only on the DC source path, so a crow
        // registry plan (crow_rows, set by compare for model id 0x23) drawing none is the source image (model_registry.py
        // source_drops "alt-specular").
        if(f&~((crow_rows || armor_rows)?0x87u:7u))return Error::Material;
#elif RE4DC_NMR_BOAT
        // PS2_CAST_BOAT: the boat's flag 0x80 (specularSetup2) is GX only on the DC source path (as the crow's).
        if(f&~((boat_rows || armor_rows)?0x87u:7u))return Error::Material;
#else
        if(f&~(armor_rows?0x87u:7u))return Error::Material;
#endif
        p+=32+want.bytes;
    }
    ++out.identity_roles;return Error::None;
}
#if RE4DC_LEON_HAND_POSES
// LEON_HAND_POSES: a player hand info of any pose. The same live-state rules as info() (visible pass group, no
// colour / texture / UV modifiers, no morph) and the player hand TPL's textures against the standard hand row;
// the pose geometry and its ModelPart materials are not compared (the plan draws the PS2 hand, not this data).
Error hand_info(cModelInfo* i,const Role& row,Result& out) {
    if(!readable(i,sizeof(*i)) || !readable(i->pData,sizeof(ModelData)))return Error::BadRange;
    if((i->be_flag&~8u)!=1u)return Error::PassGroup;
    if(i->invisible_factor!=1.0f || i->blend_mode || i->colorWord!=0xffffffffu ||
       i->color2[0] || i->color2[1] || i->color2[2] || i->color2[3] ||
       i->flagsDC || i->pAddTpl || i->nAddTex || i->blendRatio || i->blendType ||
       i->texBlendTbl || i->pTexAnim || i->uvU || i->uvV || i->uvScrollU || i->uvScrollV)return Error::LiveModifier;
    const void* tp=i->tpl_addr;
    if(!readable(tp,12) || u32at(tp,4)!=row.texture_count)return Error::Texture;
    const void* td=ptrat(tp,8);
    if(!readable(td,row.texture_count*8u))return Error::BadRange;
    for(unsigned k=0;k<row.texture_count;++k) {
        Error r=texture(static_cast<const unsigned char*>(td)+k*8,row.textures[k]);
        if(r!=Error::None)return r;
    }
    ++out.identity_roles;return Error::None;
}
#endif
#if RE4DC_ACTOR_MATERIAL_RECORD
// rec: a record hit (its rows and archive verdict); rows_out: the rows this evaluation used (for a store).
Result compare_core(cModel* m,const Re4dcActorPlan* p,bool diagnostic,const record::Record* rec,const Role** rows_out) {
#else
Result compare(cModel* m,const Re4dcActorPlan* p,bool diagnostic) {
#endif
    Result out{Error::None,0,0,Diffuse|SourceLighting|AtlasSampler,0};
    if(!m || !p || !readable(m,sizeof(*m))) {out.error=Error::BadRange;return out;}
    re4dc_source::FrameIdentity frame{};re4dc_source::ModelIdentity owner{};
    if(re4dc_actor_transaction_identity(m,&frame,&owner)!=1
#if RE4DC_ACTOR_EARLY_COARSE
       && !re4dc_actor_early_proof_active(m)
#endif
    ) {out.error=Error::FrameOwner;return out;}
    const bool leon=RE4DC_LEON_LIKE(p->appearance);
#if RE4DC_NATIVE_MODEL_REGISTRY
    // NATIVE_MODEL_REGISTRY: a registry appearance names its descriptor's model id, bone count and section count; its
    // appearance is the exact source BIN + TPL rows every role proves below (no cModel::type table: the TPL row is
    // the authored appearance). Registry actors retain the flat native look; CH22 Luis has source TEV group 1.
    const bool registry=re4dc_registry_sections(p->appearance)!=0;
#if RE4DC_NMR_CROW
    crow_rows=registry && m->id==0x23;
#endif
#if RE4DC_NMR_BOAT
    boat_rows=registry && m->id==0x0f;
#endif
#if RE4DC_NMR_ROLES5
    armor_rows=registry && (m->id==0x3cu || m->id==0x25u);
#endif
    if(registry ? !re4dc_registry_model(m,p) :
       ((leon && (p->count!=(RE4DC_ACTOR_PL08 && p->appearance==0x108u?9u:RE4DC_LEON_HEADLESS && p->appearance==0x109u?7u:8u) || m!=(cModel*)pPL || m->id || RE4DC_LEON_OT_BAD(m))) ||
        (!leon && !RE4DC_HEAD_APP(p->appearance) && (p->appearance>=5 || p->count<4 || p->count>5 || m->id<0x10 || m->id>0x20 || m->ot_type)) ||
        (RE4DC_HEAD_APP(p->appearance) && (p->count!=1 || m->id!=1 || m->nParts!=1 || m->ot_type)))) {
        out.error=Error::UnknownAppearance;return out;
    }
    if(m->pTexChg || m->Shader_type || m->CullMode ||
       (!registry && !source_appearance_type(p->appearance,m->id,m->type)) ||
#if RE4DC_ACTOR_GANADO_DEATH_FADE
       ((!actor_fade_eligible(m,*p)) && (m->invisible_factor!=1.0f || m->invisible_factor2!=1.0f)) || m->alpha_omit!=255 ||
#else
       m->invisible_factor!=1.0f || m->invisible_factor2!=1.0f || m->alpha_omit!=255 ||
#endif
#if (defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22) || (defined(RE4DC_NMR_ASHLEY) && RE4DC_NMR_ASHLEY)
       m->TevScaleGroup!=source_model_tev_group(m,leon,registry) ||
#else
       m->TevScaleGroup!=(leon?1:0) ||
#endif
       !room_colour_scale(gxCsScale[m->TevScaleGroup],!leon || RE4DC_ACTOR_LEON_NATIVE_LOOK) ||
       m->AddAmb_r || m->AddAmb_g || m->AddAmb_b) {out.error=Error::LiveModifier;return out;}
#else
    if((leon && (p->count!=(RE4DC_ACTOR_PL08 && p->appearance==0x108u?9u:RE4DC_LEON_HEADLESS && p->appearance==0x109u?7u:8u) || m!=(cModel*)pPL || m->id || RE4DC_LEON_OT_BAD(m))) ||
       (!leon && !RE4DC_HEAD_APP(p->appearance) && (p->appearance>=5 || p->count<4 || p->count>5 || m->id<0x10 || m->id>0x20 || m->ot_type)) ||
       (RE4DC_HEAD_APP(p->appearance) && (p->count!=1 || m->id!=1 || m->nParts!=1 || m->ot_type))) {
        out.error=Error::UnknownAppearance;return out;
    }
    if(m->pTexChg || m->Shader_type || m->CullMode ||
       !source_appearance_type(p->appearance,m->id,m->type) ||
#if RE4DC_ACTOR_GANADO_DEATH_FADE
       ((!actor_fade_eligible(m,*p)) && (m->invisible_factor!=1.0f || m->invisible_factor2!=1.0f)) || m->alpha_omit!=255 ||
#else
       m->invisible_factor!=1.0f || m->invisible_factor2!=1.0f || m->alpha_omit!=255 ||
#endif
       m->TevScaleGroup!=(leon?1:0) ||
       !room_colour_scale(gxCsScale[m->TevScaleGroup],!leon || RE4DC_ACTOR_LEON_NATIVE_LOOK) ||
       m->AddAmb_r || m->AddAmb_g || m->AddAmb_b) {out.error=Error::LiveModifier;return out;}
#endif
#if RE4DC_ACTOR_PROOF_LEAN
    // ACTOR_PROOF_LEAN: each role's current row is looked up once in this evaluation (nothing between the lookups
    // writes the lifetime records, the rows or the plan: info / texture / source material only read). A non-null
    // actor_current_role implies re4dc_actor_material_owner_proof (same membership, find_info and scan, which stops
    // at the first match where the row lookup needs exactly one), so that second scan is not repeated; the run loop
    // and the source material reuse the row. =2: the =0 lookups also run, decide, and are counted.
    constexpr unsigned kLeanRoles=sizeof(Re4dcActorPlan::info)/sizeof(Re4dcActorPlan::info[0]);
    const Role* rows[kLeanRoles]{};
    if(p->count>kLeanRoles){out.error=Error::BadRange;return out;}
    for(unsigned k=0;k<p->count;++k) {
#if RE4DC_LEON_HAND_POSES
        // LEON_HAND_POSES: the player's current hand infos (any pose) are certified by their live state and the
        // player hand TPL against the standard hand row; their geometry is never drawn (the PS2 hand is).
        if(leon && !diagnostic && re4dc_leon_hand_role(m,p->info[k])==k) {
            out.role=k;const auto* row=find(p->appearance,k);
            if(!row){out.error=Error::MissingRole;return out;}
            rows[k]=row;
#if RE4DC_ACTOR_MATERIAL_RECORD
            if(rows_out)rows_out[k]=row;
#endif
            out.error=hand_info(p->info[k],*row,out);if(out.error!=Error::None)return out;
            continue;
        }
#endif
#if RE4DC_ACTOR_MATERIAL_RECORD
        out.role=k;const auto* row=diagnostic?find(p->appearance,RE4DC_PLAN_ROLE(p,k)):rec?&RE4DC_ROLE(rec->row[k]):
                                   actor_current_role(m,p->info[k],p->appearance,RE4DC_PLAN_ROLE(p,k));
#else
        out.role=k;const auto* row=diagnostic?find(p->appearance,RE4DC_PLAN_ROLE(p,k)):actor_current_role(m,p->info[k],p->appearance,RE4DC_PLAN_ROLE(p,k));
#endif
        if(!row){out.error=Error::MissingRole;return out;}
#if RE4DC_ACTOR_PROOF_LEAN == 2
        if(!diagnostic) {
            ++actor_lean_c.owner;
            if(!re4dc_actor_material_owner_proof(m,p->info[k],p->appearance,RE4DC_PLAN_ROLE(p,k),RE4DC_ACTOR_MATERIAL_RECORD_REVISION)) {
                ++actor_lean_c.owner_bad;out.error=Error::MissingOwnerProof;return out;
            }
        }
#endif
        rows[k]=row;
#if RE4DC_ACTOR_MATERIAL_RECORD
        if(rows_out)rows_out[k]=row;
        out.error=info(p->info[k],*row,out,diagnostic,!rec);if(out.error!=Error::None)return out;
#else
        out.error=info(p->info[k],*row,out,diagnostic);if(out.error!=Error::None)return out;
#endif
    }
#if RE4DC_ACTOR_MATERIAL_RECORD
    if(rec)out.required|=rec->need;
#endif
#else
    for(unsigned k=0;k<p->count;++k) {
#if RE4DC_LEON_HAND_POSES
        if(leon && !diagnostic && re4dc_leon_hand_role(m,p->info[k])==k) {
            out.role=k;const auto* row=find(p->appearance,k);
            if(!row){out.error=Error::MissingRole;return out;}
            out.error=hand_info(p->info[k],*row,out);if(out.error!=Error::None)return out;
            continue;
        }
#endif
        out.role=k;const auto* row=diagnostic?find(p->appearance,RE4DC_PLAN_ROLE(p,k)):actor_current_role(m,p->info[k],p->appearance,RE4DC_PLAN_ROLE(p,k));
        if(!row){out.error=Error::MissingRole;return out;}
        if(!diagnostic && !re4dc_actor_material_owner_proof(m,p->info[k],p->appearance,RE4DC_PLAN_ROLE(p,k),RE4DC_ACTOR_MATERIAL_RECORD_REVISION)) {
            out.error=Error::MissingOwnerProof;return out;
        }
        out.error=info(p->info[k],*row,out,diagnostic);if(out.error!=Error::None)return out;
    }
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY
    // Registry runs: one per role in source order, each drawing its chunk's own descriptor texture package.
    if(registry) {
        if(!re4dc_registry_runs_match(p)){out.error=Error::Material;return out;}
    } else
#endif
    // LEON_HEADLESS v2: the flying head (0x10A) is certified like Leon's roles: its runs are proved by
    // re4dc_actor_material_runs_capability (atlas + hair pair 1, ordered, TR no-depth-write hair).
    if(!leon && !RE4DC_HEAD_APP(p->appearance)) {
        unsigned source_material_seen=1;
        for(unsigned j=0;j<p->run_count;++j) {
            const auto& run=p->runs[j];const unsigned role=run.role;
            if(role>=p->count || run.material>=p->material_count){out.error=Error::Material;return out;}
#if RE4DC_ACTOR_PROOF_LEAN
            const auto* row=diagnostic?actor_current_role(m,p->info[role],p->appearance,role):rows[role];
#if RE4DC_ACTOR_PROOF_LEAN == 2
            if(!diagnostic) {
                const auto* full=actor_current_role(m,p->info[role],p->appearance,role);
                ++actor_lean_c.rows;if(full!=row)++actor_lean_c.rows_bad;row=full;
            }
#endif
#else
            const auto* row=actor_current_role(m,p->info[role],p->appearance,role);
#endif
            if(!row){out.error=Error::MissingOwnerProof;return out;}
            const bool original=!RE4DC_GRIP_VARIANT_RUN(run) && ((role==2 && row->source_bin==451) ||
                (role==3 && row->source_bin==456) || role==4);
            if(!original) {if(run.material!=0){out.error=Error::Material;return out;}continue;}
            Re4dcActorOwnedMaterial want{};
#if RE4DC_ACTOR_PROOF_LEAN == 1
            if(!(diagnostic?re4dc_actor_source_material(m,p->info[role],p->appearance,role,&want):
                 lean_source_material(m,p->info[role],p->appearance,role,row,&want))) {out.error=Error::Material;return out;}
#elif RE4DC_ACTOR_PROOF_LEAN == 2
            const int got=re4dc_actor_source_material(m,p->info[role],p->appearance,role,&want);
            if(!diagnostic) {
                Re4dcActorOwnedMaterial lean{};
                const int lean_got=lean_source_material(m,p->info[role],p->appearance,role,row,&lean);
                ++actor_lean_c.materials;
                if(lean_got!=got || (got && (lean.image.pixels!=want.image.pixels || lean.image.palette!=want.image.palette ||
                   lean.image.width!=want.image.width || lean.image.height!=want.image.height ||
                   lean.image.format!=want.image.format || lean.image.palette_bytes!=want.image.palette_bytes ||
                   lean.crc!=want.crc || lean.fnv!=want.fnv || lean.wrap_s!=want.wrap_s || lean.wrap_t!=want.wrap_t)))
                    ++actor_lean_c.materials_bad;
            }
            if(!got) {out.error=Error::Material;return out;}
#else
            if(!re4dc_actor_source_material(m,p->info[role],p->appearance,role,&want)) {out.error=Error::Material;return out;}
#endif
            const auto& have=p->materials[run.material];
            if(have.image.pixels!=want.image.pixels || have.crc!=want.crc || have.fnv!=want.fnv ||
               have.image.width!=want.image.width || have.image.height!=want.image.height ||
               have.image.format!=want.image.format || have.image.palette || have.image.palette_bytes ||
               have.material_flags || have.blend || have.depth_mode || have.mask_ref!=256 ||
               have.wrap_s!=want.wrap_s || have.wrap_t!=want.wrap_t) {out.error=Error::Material;return out;}
            source_material_seen|=1u<<run.material;
        }
        if(source_material_seen!=(1u<<p->material_count)-1){out.error=Error::Material;return out;}
    }
    // The diagnostic still hashes only the legacy sections. Production's
    // whole normalized BIN proof also covers pClr, heads, blend/flip and padding.
    if(diagnostic) {out.error=Error::IncompleteColourProof;return out;}
    // User-approved flat Ganado look: constant light/specular omission and the
    // reviewed atlas are deliberate, while all source material bytes, masks,
    // samplers, current modifiers and pass identity must still match above.
    unsigned implemented=Diffuse|SourceLighting|AtlasSampler|Specular;
#if RE4DC_NMR_DROP_BUMP
    // NATIVE_MODEL_REGISTRY_DROP_BUMP (PS2_DELLAGO): Del Lago's registry plan (em2f, 0x2F) draws no bump stage, which
    // is what the source path draws too (trans.cpp bumpSetup only reaches the GX stubs; model_bridge binds the colour
    // texture alone), so the bump need is met by the same image (model_registry.py "source_drops").
    if(registry && m->id==0x2F)implemented|=Bump;
#if RE4DC_NMR_BOAT
    // PS2_CAST_BOAT: the lake boat's (pl0f, model 0x0f) source bump setup reaches the same GX stubs as Del Lago's
    // (model_registry.py source_drops "bump", "alt-specular").
    if(registry && m->id==0x0fu)implemented|=Bump;
#endif
#if RE4DC_NMR_ROLES5
    // NATIVE_MODEL_REGISTRY_ROLES5: the castle armour's (em3c 0x3c / em25 0x25) source bump setup reaches the same GX stubs
    // (model_registry.py source_drops "bump").
    if(registry && (m->id==0x3cu || m->id==0x25u))implemented|=Bump;
#endif
#if RE4DC_NMR_CH1CAST
    // PS2_CAST_CH1: the chapter 1 snake (em24, 0x24) and lake fish (em27, 0x27) source bump setups reach the same GX stubs
    // as Del Lago's (model_registry.py source_drops "bump").
    if(registry && (m->id==0x24u || m->id==0x27u))implemented|=Bump;
#endif
#if defined(RE4DC_NMR_ASHLEY) && RE4DC_NMR_ASHLEY
    // PS2_ASHLEY: the partner Ashley's (pSUB, model 3) source bump setup reaches the same GX stubs (model_registry.py
    // source_drops "bump"); =2 also draws her head at the PS2 rest face (the GC shapes are not shown; user look decision
    // pending), which is the head role's Morph need (info() above admits only that role's shape bit).
    if(registry && m->id==3u && m==(cModel*)pSubEm)implemented|=RE4DC_NMR_ASHLEY>=2?unsigned(Bump|Morph):unsigned(Bump);
#if defined(RE4DC_NMR_PL_ASHLEY) && RE4DC_NMR_PL_ASHLEY && RE4DC_NMR_ASHLEY >= 2
    // The same opt-in PS2 rest-face contract belongs to the exact playable
    // owner too. info() has proved its face BIN7/TPL9 and every live modifier;
    // registry_runs_match has proved its mask/material passes above.
    if(registry && m==(cModel*)pPL && m->id==0u && m->nParts==141u &&
       re4dc_registry_player_ashley_face(p->appearance,1u))implemented|=Bump|Morph;
#endif
#endif
#if RE4DC_ROUTE_CH22
    // Qualified Luis source rows retain the material/TPL proof; the source
    // bump setup reaches the same unimplemented GX stage as Del Lago.
    if(registry && m->id==4u)implemented|=Bump;
#endif
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
    // CH23 em35: the qualified registry identities above retain every source
    // material/TPL fact and their mask runs. PS2 atlases contain diffuse RGB,
    // not a baked bump/specular stage. As on the existing em2f path, trans.cpp
    // bumpSetup only reaches GXLoadTexObj / indirect GX stubs; it does not
    // replace model_bridge's diffuse selection. This allowance covers that
    // source-path limitation only; target visual acceptance remains separate.
    if(registry && m->id==0x35)implemented|=Bump;
#endif
#endif
#if RE4DC_NMR_POOL && RE4DC_NMR_DROP_BUMP
    // NATIVE_MODEL_REGISTRY_POOL: a pool plan's source bump setup (the zealot accessory 0x213) reaches the same GX stubs
    // as Del Lago's (model_registry.py source_drops "bump").
    if(registry && p->pool)implemented|=Bump;
#endif
#if defined(RE4DC_NMR_BUMP_FLAT) && RE4DC_NMR_BUMP_FLAT
    // NATIVE_BUMP_FLAT (lane cast16 2026-10-16, coordinator decision): every registry plan meets the bump need without a
    // bump stage. The source path draws none either (trans.cpp bumpSetup only reaches the GX stubs; model_bridge binds
    // the colour texture alone), and model_registry.py admits a bump-material descriptor only with source_drops "bump".
    // Covers the single-section castle / island descriptors (em1b / em1c type 10, em25, em2d, soldier bodies).
    if(registry)implemented|=Bump;
#endif
#if RE4DC_NMR_CROW
    // PS2_CROW (Phase 2 A3, user decision 2026-10-11): a registry crow (em23, 0x23) draws no bump stage (as the source
    // path: bumpSetup only reaches the GX stubs) and its folded wing as the solid PS2 wing (the GC I4 mask pass and its
    // second pass are replaced, an accepted visible approximation): model_registry.py source_drops "bump", "mask".
    if(registry && m->id==0x23)implemented|=Bump|Mask|SourcePass;
#endif
#if RE4DC_NMR_MASK
    // NATIVE_MODEL_REGISTRY_MASK: a registry plan whose masked sections draw their colour + I4 mask pair run (TR, blended,
    // no depth write: the Leon hair's native-look material) meets the source's mask pass and second-pass needs;
    // re4dc_registry_runs_match above proved every run, material and pair key.
    if(registry && re4dc_registry_masked(p))implemented|=Mask|SourcePass;
#endif
    if(leon || RE4DC_HEAD_APP(p->appearance)) {
        implemented=Diffuse; // source-exact mode has no proven shader substitute
#if RE4DC_ACTOR_LEON_NATIVE_LOOK
        const unsigned runs=re4dc_actor_material_runs_capability(p);
        constexpr unsigned need=RE4DC_ACTOR_RUN_LEASES|RE4DC_ACTOR_RUN_ORDER|RE4DC_ACTOR_RUN_HAIR_TR_NOWRITE;
        if((runs&need)==need)
            implemented=Diffuse|SourceLighting|AtlasSampler|Specular|Bump|Mask|SourcePass|Morph;
        // Known colour/mask pairs + ordered second-pass TR/no-depth-write is
        // an opt-in Dreamcast approximation. It is NOT GC coverage equivalence.
#endif
    }
    if(out.required&~implemented)out.error=Error::Capability;
    return out;
}
#if RE4DC_ACTOR_MATERIAL_RECORD
Result compare(cModel* m,const Re4dcActorPlan* p,bool diagnostic) {
    if(diagnostic)return compare_core(m,p,true,nullptr,nullptr);
    const Role* rows[record::kRoles]{};
    const auto* rec=record::hit(m,p);
#if RE4DC_ACTOR_MATERIAL_RECORD == 2
    // The whole certificate decides; a hit's result is computed beside it and compared. The decline position
    // (role / part) is compared only for a decline: on success part is the last ModelPart index a whole evaluation
    // visited, which a hit does not walk.
    auto& c=record::c;++c.calls;
    const Result full=compare_core(m,p,false,nullptr,rows);
    if(rec) {
        ++c.hits;const Result held=compare_core(m,p,false,rec,nullptr);
        if(held.error!=full.error || held.required!=full.required || held.identity_roles!=full.identity_roles ||
           held.role!=full.role || (full.error!=Error::None && held.part!=full.part)) {
            if(c.bad++<8)re4dc_log("AMR bad t=%u app=%u error=%u/%u role=%u/%u part=%u/%u need=%x/%x matched=%u/%u\n",
                unsigned(pG->Frame_cnt),p->appearance,unsigned(full.error),unsigned(held.error),full.role,held.role,
                full.part,held.part,full.required,held.required,full.identity_roles,held.identity_roles);
        }
    } else if(full.error==Error::None){record::store(m,p,full,rows);++c.stores;}
    if(pG->Frame_cnt/600!=c.last){c.last=pG->Frame_cnt/600;
        re4dc_log("AMR periodic t=%u calls=%u hits=%u stores=%u bad=%u epoch=%u\n",unsigned(pG->Frame_cnt),c.calls,c.hits,
                  c.stores,c.bad,life::epoch);}
    return full;
#else
    const Result out=compare_core(m,p,false,rec,rec?nullptr:rows);
    if(!rec && out.error==Error::None)record::store(m,p,out,rows);
    return out;
#endif
}
#endif
}
#if RE4DC_ACTOR_GANADO_APP0_GRIP
// Appearance 0 may use only its two proven GC grip hands and its exact TPL.
// Keep this check at both entry points: the lean certificate bypasses the
// public owner lookup after resolving the current role earlier in the call.
static bool app0_grip_source_material(unsigned role,const re4dc_material::Role* row) {
    using namespace re4dc_material;
    return row && row->appearance==0 && row->role==role && row->source_tpl==473 &&
        row->textures==t_em12_473 && row->texture_count==3 &&
        ((role==2 && row->source_bin==451 && row->model==&m_extra_451) ||
         (role==3 && row->source_bin==456 && row->model==&m_extra_456));
}
#endif
extern "C" int re4dc_actor_source_material(cModel* m,cModelInfo* info,unsigned app,unsigned role,Re4dcActorOwnedMaterial* out) {
    using namespace re4dc_material;
#if RE4DC_ACTOR_GANADO_APP0_GRIP
    if(!out || app>4 || role<2 || role>4)return 0;
#else
    if(!out || app<1 || app>4 || role<2 || role>4)return 0;
#endif
    const auto* row=actor_current_role(m,info,app,role);if(!row)return 0;
#if RE4DC_ACTOR_GANADO_APP0_GRIP
    if(!app && !app0_grip_source_material(role,row))return 0;
#endif
#if RE4DC_ACTOR_PROOF_LEAN
    return lean_source_material(m,info,app,role,row,out);
}
static int lean_source_material(cModel* m,cModelInfo* info,unsigned app,unsigned role,const re4dc_material::Role* row,
                                Re4dcActorOwnedMaterial* out) {
    using namespace re4dc_material;(void)m;
#if RE4DC_ACTOR_GANADO_APP0_GRIP
    if(!out || app>4 || role<2 || role>4 || !row)return 0;
    if(!app && !app0_grip_source_material(role,row))return 0;
#else
    if(!out || app<1 || app>4 || role<2 || role>4 || !row)return 0;
#endif
#endif
    const bool hand=(role==2 && row->source_bin==451) || (role==3 && row->source_bin==456);
    if(!hand && !(role==4 && (row->source_bin==467 || row->source_bin==484)))return 0;
    const unsigned slot=hand?2u:0u;
    // These four sources have only identical ordinary opaque material states.
    for(unsigned k=0;k<row->model->header[8];++k) {
        const auto* a=row->model->parts[k].material;
        if(a[0] || a[1]!=slot || a[2]!=255 || a[3]!=255 || a[4]!=255)return 0;
    }
    const void* tp=info->tpl_addr;
    if(!readable(tp,12) || u32at(tp,4)!=row->texture_count || slot>=row->texture_count)return 0;
    const auto* d=static_cast<const unsigned char*>(ptrat(tp,8));
    if(!readable(d,row->texture_count*8))return 0;d+=slot*8;
    const auto& e=row->textures[slot];if(e.palette.bytes || texture(d,e)!=Error::None)return 0;
    const void* h=ptrat(d,0);Re4dcActorOwnedMaterial value{};
    value.image={ptrat(h,8),nullptr,e.width,e.height,e.format,0xffffffffu,0};
    value.crc=e.crc;value.fnv=e.fnv;value.wrap_s=e.sampler[0];value.wrap_t=e.sampler[1];
    *out=value;return 1;
}
extern "C" int re4dc_actor_material_certificate(cModel* m,const Re4dcActorPlan* p) {
    const auto r=re4dc_material::compare(m,p,false);
#if defined(RE4DC_MCHECK_LEONGC) && RE4DC_MCHECK_LEONGC
    extern unsigned re4dc_leon_gc_cert_error,re4dc_leon_gc_cert_role;
    if(m==(cModel*)pPL && r.error!=re4dc_material::Error::None){re4dc_leon_gc_cert_error=unsigned(r.error);re4dc_leon_gc_cert_role=r.role;}
#endif
    if(r.error!=re4dc_material::Error::None) {
        static unsigned logged;
        if(logged++<8)re4dc_log("ACTOR_MATERIAL decline=%u app=%u role=%u part=%u need=%x matched=%u\n",
          unsigned(r.error),p?p->appearance:~0u,r.role,r.part,r.required,r.identity_roles);
#if RE4DC_ACTOR_TRANSACTION_DIAG
        // WP2 census: the model-level modifier state behind a LiveModifier decline (bounded).
        static unsigned live_logged;
        if(r.error==re4dc_material::Error::LiveModifier && m && live_logged++<16)
            re4dc_log("ACTOR_MATERIAL live m=%p id=%02x type=%u app=%u role=%u texchg=%p shader=%u cull=%u inv=%d/%d alpha=%u "
                      "tevgrp=%u csscale=%u amb=%u,%u,%u info_be=%x\n",m,unsigned(m->id),unsigned(m->type),p?p->appearance:~0u,r.role,
                      m->pTexChg,unsigned(m->Shader_type),unsigned(m->CullMode),int(m->invisible_factor*1000),
                      int(m->invisible_factor2*1000),unsigned(m->alpha_omit),unsigned(m->TevScaleGroup),
                      unsigned(gxCsScale[m->TevScaleGroup]),unsigned(m->AddAmb_r),unsigned(m->AddAmb_g),unsigned(m->AddAmb_b),
                      p && r.role<p->count && p->info[r.role]?unsigned(p->info[r.role]->be_flag):0u);
#endif
        return 0;
    }
    return 1;
}
// Not called by admission or any installed path. A future bounded diagnostic
// may call this from the same valid original callback, before GX conversion.
// IncompleteColourProof means the stated stored digests/headers matched, not
// complete source identity. No diagnostic result is itself an owner proof.
extern "C" unsigned re4dc_actor_material_diagnose(cModel* m,const Re4dcActorPlan* p,unsigned* need,unsigned* matched) {
    const auto r=re4dc_material::compare(m,p,true);
    if(need)*need=r.required;if(matched)*matched=r.identity_roles;
    return unsigned(r.error);
}
#if RE4DC_ACTOR_TEX_PREP
#include "actor_tex_prep_material.inc"
#endif
#if defined(RE4DC_TEX_PKG_SKIP) && RE4DC_TEX_PKG_SKIP && RE4DC_NATIVE_MODEL_REGISTRY_PACK
// TEX_PKG_SKIP: 1 when (crc, fnv) is a source texture fact of a published room package role row (a GC TPL texture a
// registry descriptor replaces with its own atlas).
extern "C" int re4dc_registry_source_key(unsigned crc,unsigned fnv) {
    if(!(crc|fnv))return 0;
    const auto& R=re4dc_material::room_rows;
    for(unsigned k=0;k<R.role_count;++k){
        const auto& row=R.roles[k];
        for(unsigned t=0;t<row.texture_count;++t)if(row.textures[t].crc==crc && row.textures[t].fnv==fnv)return 1;
    }
    return 0;
}
#endif
