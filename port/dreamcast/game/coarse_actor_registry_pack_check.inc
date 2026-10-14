// NATIVE_MODEL_REGISTRY_PACK: the room package's complete validation (coarse_actor_registry_pack.inc), apart so the
// host test (tools/d367/model_registry_pack_test.cpp) runs this exact code on generated and malformed packages.
// Needs, declared before it: nmr::Descriptor / Chunk / Texture / Weight and kReg* (coarse_actor_owner_registry.inc),
// re4dc_material::Part / Texture / Model / Role / SourceBlob, kRoomRoles / kRoomBlobs (actor_material_records.inc)
// and coarse_finite (coarse_skin.h). Writes only the pack_* records below; publishes nothing.
#include <cstddef>
#include <cstring>
namespace {
using re4dc_material::kRoomRoles;using re4dc_material::kRoomBlobs;
// CH23 r11f retains all three PS2 Mendez forms and both mask passes. Allocate
// only the validated file + skin bytes; this is a ceiling, never a static arena.
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
constexpr unsigned kPackMaxBytes=640u*1024u;
constexpr unsigned pack_room_max(unsigned room) { return room==0x11fu?kPackMaxBytes:192u*1024u; }
constexpr unsigned pack_role_texture_max(unsigned room) { return room==0x11fu?9u:8u; }
#else
constexpr unsigned kPackMaxBytes=192u*1024u;
constexpr unsigned pack_room_max(unsigned) { return kPackMaxBytes; }
constexpr unsigned pack_role_texture_max(unsigned) { return 8u; }
#endif
constexpr unsigned kPackHeader=64,kPackKinds=12,kPackPayload=kPackHeader+kPackKinds*16;
enum PackKind : unsigned {kDesc,kRef,kGeom,kBlob,kTex,kParents,kBind,kFModel,kFPart,kFTex,kRole,kSBlob};
constexpr unsigned kPackRecord[kPackKinds]={48,16,64,1,16,1,48,96,32,68,32,32};
// CH23 closed/open em13 needs 35 source material facts; all three em35 forms
// need 124. Facts stay in the validated room package; no added static arena.
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
constexpr unsigned kPackModels=8,kPackParts=128,kPackTexFacts=16;
#elif RE4DC_ROUTE_CH22
// Complete Luis six-info body (74) plus its independent gun (9).
constexpr unsigned kPackModels=8,kPackParts=83,kPackTexFacts=16;
#elif defined(RE4DC_NMR_FACTS) && RE4DC_NMR_FACTS
// PS2_CAST_* (native_model_registry.mk): the chapter-1 PS2 cast packages' source material facts (merchant em18: 35).
constexpr unsigned kPackModels=8,kPackParts=RE4DC_NMR_FACTS,kPackTexFacts=16;
#else
constexpr unsigned kPackModels=8,kPackParts=32,kPackTexFacts=16;
#endif
constexpr unsigned kPackCapacity[kPackKinds]={kRegDescriptors,kRegChunks,kRegGeometry,kPackMaxBytes,kRegTextures,
    kRegDescriptors*kRegBones,kRegDescriptors*kRegBones,kPackModels,kPackParts,kPackTexFacts,kRoomRoles,kRoomBlobs};
static_assert(sizeof(re4dc_material::Part)==32 && offsetof(re4dc_material::Part,bytes)==16,"package part fact records");
static_assert(sizeof(re4dc_material::Texture)==68,"package texture fact records");
enum PackWhy : unsigned {
    kPwNone,kPwMissing,kPwSize,kPwAlloc,kPwRead,kPwHeader,kPwHash,kPwRoom,kPwTable,kPwDescriptor,kPwRef,kPwGeometry,
    kPwOverlap,kPwDuplicate,kPwTexture,kPwSkeleton,kPwFacts,kPwRole,kPwBlob,kPwBinding,kPwPreflight,kPwSkin,kPwCount
};
const char* const kPackWhy[kPwCount]={"none","missing","size","alloc","read","header","hash","room","table","descriptor",
    "ref","geometry","overlap","duplicate","texture","skeleton","facts","role","blob","binding","preflight","skin"};
// The view's records (bounded; written while validating, read only after the publish).
nmr::Descriptor pack_desc[kRegDescriptors];
nmr::Chunk pack_chunks[kRegChunks];
nmr::Texture pack_tex[kRegTextures];
re4dc_material::Model pack_models[kPackModels];
re4dc_material::Role pack_roles[kRoomRoles];
re4dc_material::SourceBlob pack_blobs[kRoomBlobs];
#if RE4DC_NMR_MASK
#endif

inline unsigned pu32(const unsigned char* p,unsigned at) {unsigned x;std::memcpy(&x,p+at,4);return x;}
struct PackHash {
    unsigned crc=~0u,fnv=2166136261u;
    void add(const unsigned char* b,unsigned n) {
        for(unsigned k=0;k<n;++k) {
            crc^=b[k];fnv=(fnv^b[k])*16777619u;
            for(unsigned j=0;j<8;++j)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));
        }
    }
    unsigned crc32() const {return ~crc;}
};
struct PackSection { unsigned at,bytes,count; };
struct PackSpan { unsigned at,bytes;
#if RE4DC_NMR_IMMUTABLE_ALIAS
    unsigned id; // geometry * 5 + array kind, used only by the v2 immutable-array contract
#endif
};
#if RE4DC_NMR_IMMUTABLE_ALIAS
bool pack_alias(const PackSpan& a,const PackSpan& b,const unsigned char* geom) {
    const unsigned kind=a.id%5u;
    if(a.at!=b.at || a.bytes!=b.bytes || kind!=b.id%5u || kind==3u)return false;
    const auto* p=geom+(a.id/5u)*64u;const auto* q=geom+(b.id/5u)*64u;
    // Same kind fixes stride (pos/nrm=8, uv=4, weights=16); equal span length
    // fixes element count. Check the encoded counts and skeleton/palette context too.
    const unsigned count_word=kind==0u?0u:kind==1u?4u:kind==2u?20u:8u;
    return pu32(p,count_word)==pu32(q,count_word) && pu32(p,8)==pu32(q,8) && pu32(p,28)==pu32(q,28);
}
#endif

// Validation and the record build. On kPwNone the pack_* records describe the package at base; nothing is published.
// Descriptor word 44: 0, or under NATIVE_MODEL_REGISTRY_SHIFT the position shift 1..4 (0 = 4).
#if RE4DC_NMR_SHIFT
#define RE4DC_NMR_WORD44_BAD(w) ((w)>4)
#else
#define RE4DC_NMR_WORD44_BAD(w) (w)
#endif
#if RE4DC_NMR_IMMUTABLE_ALIAS
// Keep validation scratch out of room_enter's live frame during KOS fs_open,
// whose path normalization already retains two 4096-byte buffers on the task stack.
__attribute__((noinline))
#endif
PackWhy pack_validate(const unsigned char* p,unsigned size,unsigned room,unsigned& detail) {
    detail=0;
    if(size<kPackPayload || std::memcmp(p,"RE4NMR1\0",8))return kPwHeader;
    const unsigned version=pu32(p,8),header=pu32(p,12),total=pu32(p,16),kinds=pu32(p,20),table=pu32(p,24),skin=pu32(p,28),
        proom=pu32(p,32),pcrc=pu32(p,36),pfnv=pu32(p,40),hcrc=pu32(p,44),app0=pu32(p,48),max_bones=pu32(p,52);
#if RE4DC_NMR_IMMUTABLE_ALIAS
    const bool alias=version==2u && pu32(p,56)==1u && room==0x11fu && proom==0x11fu;
    const bool bad_version=!(version==1u && !pu32(p,56)) && !alias;
    if(bad_version || header!=kPackHeader || total!=size || kinds!=kPackKinds || table!=kPackHeader || app0!=nmr::appearance_first ||
              !max_bones || max_bones>kRegBones || pu32(p,60)){detail=version;return kPwHeader;}
#else
    if(version!=1 || header!=kPackHeader || total!=size || kinds!=kPackKinds || table!=kPackHeader || app0!=nmr::appearance_first ||
       !max_bones || max_bones>kRegBones || pu32(p,56) || pu32(p,60)){detail=version;return kPwHeader;}
#endif
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
    if(!skin || skin%8u || size>pack_room_max(room) || skin>pack_room_max(room) ||
       ((size+31u)&~31u)+skin>pack_room_max(room)){detail=skin;return kPwSize;}
#else
    if(!skin || skin%8u || ((size+31u)&~31u)+skin>kPackMaxBytes){detail=skin;return kPwSize;}
#endif
    {
        unsigned char h[kPackHeader];std::memcpy(h,p,kPackHeader);std::memset(h+44,0,4);
        PackHash a;a.add(h,kPackHeader);if(a.crc32()!=hcrc){detail=1;return kPwHash;}
        PackHash b;b.add(p+kPackHeader,size-kPackHeader);if(b.crc32()!=pcrc || b.fnv!=pfnv){detail=2;return kPwHash;}
    }
    if(proom!=room){detail=proom;return kPwRoom;}
    // ---- section table
    PackSection sec[kPackKinds];unsigned end=kPackPayload;
    for(unsigned k=0;k<kPackKinds;++k) {
        const unsigned at=kPackHeader+k*16,kind=pu32(p,at),off=pu32(p,at+4),bytes=pu32(p,at+8),count=pu32(p,at+12);
        detail=k;
        if(kind!=k+1 || off%32u || off<end || off>size || bytes>size-off || !count || count>kPackCapacity[k] ||
           bytes!=count*kPackRecord[k])return kPwTable;
#if RE4DC_ROUTE_CH22 && !RE4DC_ROUTE_CH23
        if(k==kFPart && room!=0x11cu && count>32u)return kPwTable;
#endif
        sec[k]={off,bytes,count};end=off+bytes;
    }
    const unsigned char* blob=p+sec[kBlob].at;
    // ---- textures: power-of-two sizes, unique keys
    for(unsigned t=0;t<sec[kTex].count;++t) {
        const unsigned char* r=p+sec[kTex].at+t*16;detail=t;
        const unsigned crc=pu32(r,0),fnv=pu32(r,4),w=pu32(r,8),h=pu32(r,12);
        if(w<8 || w>1024 || (w&(w-1)) || h<8 || h>1024 || (h&(h-1)))return kPwTexture;
        for(unsigned u=0;u<t;++u)if(pack_tex[u].crc==crc && pack_tex[u].fnv==fnv)return kPwDuplicate;
        pack_tex[t]={crc,fnv,w,h};
    }
    // ---- geometry: counts, aligned spans inside the blob section, hashes; every array disjoint from every other
    PackSpan spans[kRegGeometry*5];unsigned nspans=0,skin_sum=0;
    for(unsigned g=0;g<sec[kGeom].count;++g) {
        const unsigned char* r=p+sec[kGeom].at+g*64;detail=g;
        const unsigned np=pu32(r,0),nn=pu32(r,4),npal=pu32(r,8),tris=pu32(r,12),sbytes=pu32(r,16),uvb=pu32(r,20),
            sk=pu32(r,24),bones=pu32(r,28);
        if(!np || np>65535 || !nn || nn>65535 || !npal || npal>256 || !tris || sbytes<32 || sbytes>(1u<<20) || !uvb || uvb%4u ||
           !sk || sk%8u || !bones || bones>max_bones || pu32(r,60))return kPwGeometry;
        const unsigned want[5]={np*8u,nn*8u,uvb,sbytes,npal*16u};
        PackHash hsh;
        for(unsigned a=0;a<5;++a) {
            const unsigned at=pu32(r,32+a*4);
            if(at%32u || at>sec[kBlob].bytes || want[a]>sec[kBlob].bytes-at)return kPwGeometry;
#if RE4DC_NMR_IMMUTABLE_ALIAS
            spans[nspans++]={at,want[a],g*5u+a};hsh.add(blob+at,want[a]);
#else
            spans[nspans++]={at,want[a]};hsh.add(blob+at,want[a]);
#endif
        }
        if(hsh.crc32()!=pu32(r,52) || hsh.fnv!=pu32(r,56))return kPwHash;
        const auto* w=reinterpret_cast<const nmr::Weight*>(blob+pu32(r,48));
        for(unsigned j=0;j<npal;++j) {
            if(!w[j].count || w[j].count>3)return kPwGeometry;
            for(unsigned k=0;k<3;++k)
                if((k<w[j].count && w[j].bone[k]>=bones) || !coarse_finite(w[j].value[k]))return kPwGeometry;
        }
        // An identical geometry stored twice: the generator stores each once, so this package is malformed.
        for(unsigned u=0;u<g;++u) {
            const unsigned char* q=p+sec[kGeom].at+u*64;bool same=!std::memcmp(q,r,32) && pu32(q,52)==pu32(r,52) && pu32(q,56)==pu32(r,56);
            for(unsigned a=0;a<5 && same;++a)same=!std::memcmp(blob+pu32(q,32+a*4),blob+pu32(r,32+a*4),want[a]);
            if(same){detail=g*256+u;return kPwDuplicate;}
        }
#if RE4DC_NMR_MASK
#else
        skin_sum+=sk;
#endif
    }
#if !RE4DC_NMR_MASK
    if(skin_sum!=skin){detail=skin_sum;return kPwSize;}
#endif
    for(unsigned i=1;i<nspans;++i)for(unsigned j=i;j>0 && spans[j-1].at>spans[j].at;--j){const PackSpan t=spans[j];spans[j]=spans[j-1];spans[j-1]=t;}
    for(unsigned i=1;i<nspans;++i)if(spans[i-1].at+spans[i-1].bytes>spans[i].at){
#if RE4DC_NMR_IMMUTABLE_ALIAS
        // Exact equal-span groups retain a full representative at every step:
        // admitting aliases cannot hide a later partial or nested overlap.
        if(alias && pack_alias(spans[i-1],spans[i],p+sec[kGeom].at))continue;
#endif
        detail=i;return kPwOverlap;
    }
    // ---- descriptors, their chunk references, parents and binds
    const auto* parents=reinterpret_cast<const signed char*>(p+sec[kParents].at);
    const auto* bind=reinterpret_cast<const float (*)[12]>(p+sec[kBind].at);
    unsigned refs=0,parents_used=0,binds_used=0,geom_used[kRegGeometry]={},tex_used=0;
#if RE4DC_NMR_MASK
    unsigned geom_primary[kRegGeometry]={};  // geometries a section draws from (only their skin streams fill the arena)
#endif
    for(unsigned d=0;d<sec[kDesc].count;++d) {
        const unsigned char* r=p+sec[kDesc].at+d*48;detail=d;auto& desc=pack_desc[d];
        unsigned n=0;while(n<16 && r[n])++n;
        if(!n || n==16)return kPwDescriptor;
        for(unsigned k=0;k<n;++k)if(r[k]<0x20 || r[k]>0x7e)return kPwDescriptor;
        for(unsigned k=n;k<16;++k)if(r[k])return kPwDescriptor;
        const unsigned app=pu32(r,16),id=pu32(r,20),bones=pu32(r,24),sections=pu32(r,28),first=pu32(r,32),pat=pu32(r,36),bfirst=pu32(r,40);
        if(app!=nmr::appearance_first+d || id>255 || !bones || bones>max_bones || !sections || sections>8 || first!=refs ||
           pat!=parents_used || bfirst!=binds_used || RE4DC_NMR_WORD44_BAD(pu32(r,44)) || refs+sections>sec[kRef].count ||
           pat+bones>sec[kParents].count || bfirst+bones>sec[kBind].count)return kPwDescriptor;
        // Skeleton: an index-ordered forest rooted at bone 0, finite inverse binds.
        if(parents[pat]!=-1)return kPwSkeleton;
        for(unsigned k=1;k<bones;++k)if(parents[pat+k]<-1 || parents[pat+k]>=int(k))return kPwSkeleton;
        for(unsigned k=0;k<bones;++k)for(unsigned e=0;e<12;++e)if(!coarse_finite(bind[bfirst+k][e]))return kPwSkeleton;
        std::memset(desc.name,0,sizeof(desc.name));std::memcpy(desc.name,r,n);
        desc.appearance=app;desc.model_id=id;desc.bones=bones;desc.sections=sections;desc.first_chunk=first;desc.skin_bytes=0;
        desc.parents=parents+pat;desc.bind=bind+bfirst;
#if RE4DC_NMR_SHIFT
        desc.shift=pu32(r,44)?pu32(r,44):4u;
#endif
        for(unsigned i=0;i<sections;++i) {
            const unsigned char* f=p+sec[kRef].at+(first+i)*16;detail=d*256+i;
            const unsigned g=pu32(f,0),t=pu32(f,4);
#if RE4DC_ROUTE_CH22
            const bool luis=room==0x11cu && id==4u && bones==90u && sections==6u;
            const bool covered=pu32(f,8)==0x80000001u;
            if(pu32(f,8)!=i && !(luis && i==2u && covered))return kPwRef;
            if(covered) {
                const unsigned char* owner=p+sec[kRef].at+(first+1u)*16u;
                if(pu32(owner,8)!=1u || pu32(owner,0)!=g || pu32(owner,4)!=t || pu32(owner,12) || pu32(f,12))return kPwRef;
            }
#endif
#if RE4DC_NMR_MASK
            // Word 12: 0, or a masked section: opaque run geometry + 1 (bits 0..7), pair run geometry + 1 (8..15), the
            // pair's colour texture (16..23) and I4 mask texture (24..31).
            const unsigned mw=pu32(f,12);
#if RE4DC_ROUTE_CH22
            if(g>=sec[kGeom].count || t>=sec[kTex].count)return kPwRef;
#else
            if(g>=sec[kGeom].count || t>=sec[kTex].count || pu32(f,8)!=i)return kPwRef;
#endif
#else
#if RE4DC_ROUTE_CH22
            if(g>=sec[kGeom].count || t>=sec[kTex].count || pu32(f,12))return kPwRef;
#else
            if(g>=sec[kGeom].count || t>=sec[kTex].count || pu32(f,8)!=i || pu32(f,12))return kPwRef;
#endif
#endif
            const unsigned char* q=p+sec[kGeom].at+g*64;
            if(pu32(q,28)!=bones)return kPwRef;
            auto& c=pack_chunks[first+i];
            c.source_info=i;c.position_count=pu32(q,0);c.normal_count=pu32(q,4);c.palette_count=pu32(q,8);c.triangles=pu32(q,12);
            c.stream_bytes=pu32(q,16);c.uv_bytes=pu32(q,20);c.skin_bytes=pu32(q,24);c.texture=t;c.geometry=g;
#if RE4DC_ROUTE_CH22
            c.draw_owner=covered?1u:i;
#endif
            c.positions=blob+pu32(q,32);c.normals=blob+pu32(q,36);c.uv=blob+pu32(q,40);c.stream=blob+pu32(q,44);
            c.weights=reinterpret_cast<const nmr::Weight*>(blob+pu32(q,48));
            desc.skin_bytes+=c.skin_bytes;geom_used[g]=1;tex_used|=1u<<t;
#if RE4DC_NMR_MASK
            c.mask_geometry[0]=c.mask_geometry[1]=c.mask_texture[0]=c.mask_texture[1]=~0u;c.pair_crc=c.pair_fnv=0;
            if(!geom_primary[g]){geom_primary[g]=1;skin_sum+=c.skin_bytes;}
            if(mw) {
                const unsigned go=(mw&255u)-1u,gh=((mw>>8)&255u)-1u,tc=(mw>>16)&255u,tm=mw>>24;
#if RE4DC_ROUTE_CH22
                const bool mask_only=(mw&255u)==0;
                if(mask_only && !(luis && i==3u))return kPwRef;
                if((!mask_only && (go>=sec[kGeom].count || go==g || go==gh)) || gh>=sec[kGeom].count || gh==g || tc>=sec[kTex].count ||
#else
                if(go>=sec[kGeom].count || gh>=sec[kGeom].count || go==g || gh==g || go==gh || tc>=sec[kTex].count ||
#endif
                   tm>=sec[kTex].count || tc==tm || tc==t || tm==t || pack_tex[tc].width!=pack_tex[tm].width ||
                   pack_tex[tc].height!=pack_tex[tm].height)return kPwRef;
                const nmr::Chunk A=registry_geom_view(p+sec[kGeom].at,blob,g);
                // Both runs index this chunk's positions / normals / palettes: equal counts and bytes; the opaque run keeps
                // the chunk's UV words; the runs' triangles add up to the chunk's.
                const unsigned runs[2]={go,gh};
                for(const unsigned x:runs) {
#if RE4DC_ROUTE_CH22
                    if(mask_only && x==~0u)continue;
#endif
                    const nmr::Chunk X=registry_geom_view(p+sec[kGeom].at,blob,x);
                    if(X.position_count!=A.position_count || X.normal_count!=A.normal_count || X.palette_count!=A.palette_count ||
                       pu32(p+sec[kGeom].at+x*64,28)!=bones || std::memcmp(X.positions,A.positions,A.position_count*8u) ||
                       std::memcmp(X.normals,A.normals,A.normal_count*8u) || std::memcmp(X.weights,A.weights,A.palette_count*16u))return kPwRef;
                }
#if RE4DC_ROUTE_CH22
                const nmr::Chunk Hr=registry_geom_view(p+sec[kGeom].at,blob,gh);
                if(mask_only) {if(Hr.triangles!=A.triangles)return kPwRef;}
                else {
                    const nmr::Chunk O=registry_geom_view(p+sec[kGeom].at,blob,go);
                    if(O.uv_bytes!=A.uv_bytes || std::memcmp(O.uv,A.uv,A.uv_bytes) || O.triangles+Hr.triangles!=A.triangles)return kPwRef;
                }
#else
                const nmr::Chunk O=registry_geom_view(p+sec[kGeom].at,blob,go),Hr=registry_geom_view(p+sec[kGeom].at,blob,gh);
                if(O.uv_bytes!=A.uv_bytes || std::memcmp(O.uv,A.uv,A.uv_bytes) || O.triangles+Hr.triangles!=A.triangles)return kPwRef;
#endif
                c.mask_geometry[0]=go;c.mask_geometry[1]=gh;c.mask_texture[0]=tc;c.mask_texture[1]=tm;
                // native_ui.cpp model_mask_key: CRC-32 / FNV-1a of "R4MPv001" + colour crc, fnv, mask crc, fnv (LE words).
                const unsigned words[4]={pack_tex[tc].crc,pack_tex[tc].fnv,pack_tex[tm].crc,pack_tex[tm].fnv};
                PackHash ph;ph.add(reinterpret_cast<const unsigned char*>("R4MPv001"),8);
                ph.add(reinterpret_cast<const unsigned char*>(words),16);
                c.pair_crc=ph.crc32();c.pair_fnv=ph.fnv;
#if RE4DC_ROUTE_CH22
                if(!mask_only)geom_used[go]=1;
                geom_used[gh]=1;tex_used|=(1u<<tc)|(1u<<tm);
#else
                geom_used[go]=geom_used[gh]=1;tex_used|=(1u<<tc)|(1u<<tm);
#endif
            }
#endif
        }
        refs+=sections;parents_used+=bones;binds_used+=bones;
    }
    detail=0;
    if(refs!=sec[kRef].count || parents_used!=sec[kParents].count || binds_used!=sec[kBind].count)return kPwDescriptor;
    for(unsigned g=0;g<sec[kGeom].count;++g)if(!geom_used[g]){detail=g;return kPwRef;}
#if RE4DC_NMR_MASK
    if(skin_sum!=skin){detail=skin_sum;return kPwSize;}
#endif
    if(tex_used!=(sec[kTex].count==32?~0u:(1u<<sec[kTex].count)-1u))return kPwRef;
    // ---- source identity facts: models own contiguous part ranges; texture facts are read in place
    const auto* parts=reinterpret_cast<const re4dc_material::Part*>(p+sec[kFPart].at);
    const auto* tfacts=reinterpret_cast<const re4dc_material::Texture*>(p+sec[kFTex].at);
    unsigned parts_used=0;
    for(unsigned m=0;m<sec[kFModel].count;++m) {
        const unsigned char* r=p+sec[kFModel].at+m*96;detail=m;auto& model=pack_models[m];
        std::memcpy(model.header,r,40);
        const unsigned* dg=reinterpret_cast<const unsigned*>(r+40);
        model.positions={dg[0],dg[1],dg[2]};model.normals={dg[3],dg[4],dg[5]};model.weights={dg[6],dg[7],dg[8]};model.uv={dg[9],dg[10],dg[11]};
        const unsigned first=pu32(r,88),count=pu32(r,92);
        if(first!=parts_used || !count || count!=model.header[8] || first+count>sec[kFPart].count)return kPwFacts;
        model.parts=parts+first;parts_used+=count;
    }
    if(parts_used!=sec[kFPart].count)return kPwFacts;
    for(unsigned k=0;k<sec[kFPart].count;++k) {
        const unsigned char* r=p+sec[kFPart].at+k*32;detail=k;
        if(r[13] || r[14] || r[15])return kPwFacts;
    }
    // ---- role rows: one per descriptor section (appearance, role) and nothing else
    for(unsigned k=0;k<sec[kRole].count;++k) {
        const unsigned char* r=p+sec[kRole].at+k*32;detail=k;
        const unsigned app=pu32(r,0),role=pu32(r,4),bin=pu32(r,8),tpl=pu32(r,12),fm=pu32(r,16),tf=pu32(r,20),tn=pu32(r,24);
        if(app<nmr::appearance_first || app-nmr::appearance_first>=sec[kDesc].count ||
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
           role>=pack_desc[app-nmr::appearance_first].sections || fm>=sec[kFModel].count || !tn || tn>pack_role_texture_max(room) ||
#else
           role>=pack_desc[app-nmr::appearance_first].sections || fm>=sec[kFModel].count || !tn || tn>8 ||
#endif
           tf>sec[kFTex].count || tn>sec[kFTex].count-tf || pu32(r,28) || !bin || !tpl)return kPwRole;
        for(unsigned u=0;u<k;++u)if(pack_roles[u].appearance==app && pack_roles[u].role==role)return kPwDuplicate;
        pack_roles[k]={app,role,bin,tpl,&pack_models[fm],tfacts+tf,tn};
    }
    if(sec[kRole].count!=refs){detail=refs;return kPwRole;}
    // Two descriptors whose sections prove the same source identity (model + TPL rows) would be ambiguous.
    for(unsigned a=0;a<sec[kDesc].count;++a)for(unsigned b=a+1;b<sec[kDesc].count;++b) {
        if(pack_desc[a].sections!=pack_desc[b].sections)continue;
        bool same=true;
        for(unsigned i=0;i<pack_desc[a].sections && same;++i) {
            const re4dc_material::Role* x=nullptr;const re4dc_material::Role* y=nullptr;
            for(unsigned k=0;k<sec[kRole].count;++k) {
                if(pack_roles[k].appearance==pack_desc[a].appearance && pack_roles[k].role==i)x=&pack_roles[k];
                if(pack_roles[k].appearance==pack_desc[b].appearance && pack_roles[k].role==i)y=&pack_roles[k];
            }
            same=x && y && x->model==y->model && x->source_tpl==y->source_tpl && x->textures==y->textures;
        }
        if(same){detail=a*256+b;return kPwDuplicate;}
    }
    // ---- source blobs: one per fact model, enemy archives; every role's model has the blob of its BIN
    for(unsigned k=0;k<sec[kSBlob].count;++k) {
        const unsigned char* r=p+sec[kSBlob].at+k*32;detail=k;
        const unsigned fm=pu32(r,0),family=pu32(r,4),bin=pu32(r,8);
        if(fm>=sec[kFModel].count || family!=2 || !bin || !pu32(r,12) || pu32(r,24) || pu32(r,28))return kPwBlob;
        for(unsigned u=0;u<k;++u)if(pack_blobs[u].model==&pack_models[fm])return kPwDuplicate;
        pack_blobs[k]={&pack_models[fm],family,bin,{pu32(r,12),pu32(r,16),pu32(r,20)}};
    }
    for(unsigned k=0;k<sec[kRole].count;++k) {
        bool bound=false;detail=k;
        for(unsigned u=0;u<sec[kSBlob].count;++u)bound|=pack_blobs[u].model==pack_roles[k].model && pack_blobs[u].bin==pack_roles[k].source_bin;
        if(!bound)return kPwBinding;
    }
    for(unsigned u=0;u<sec[kSBlob].count;++u) {
        bool used=false;detail=u;
        for(unsigned k=0;k<sec[kRole].count;++k)used|=pack_roles[k].model==pack_blobs[u].model;
        if(!used)return kPwBinding;
    }
#if RE4DC_ROUTE_CH22
    // Alias and mask-only encodings belong only to this complete, reviewed pl14
    // source set. All six normalized source BIN digests remain mandatory.
    static const unsigned luis_bin[6]={4u,6u,8u,9u,10u,11u};
    static const unsigned luis_tpl[6]={5u,7u,7u,5u,5u,5u};
    static const unsigned luis_digest[6][3]={
        {74336u,0x1a039939u,0xf6f94446u},{21312u,0x112854f5u,0xbba97c84u},
        {29792u,0x49657759u,0xb6a55fe7u},{81312u,0x109e7365u,0x32a1c659u},
        {13312u,0xefcc04b2u,0xe438fb43u},{13120u,0x01e766c0u,0x671da641u}};
    for(unsigned d=0;d<sec[kDesc].count;++d) {
        const auto& desc=pack_desc[d];bool extended=false;detail=d;
        for(unsigned i=0;i<desc.sections;++i) {
            const auto& c=pack_chunks[desc.first_chunk+i];extended|=c.draw_owner!=i;
#if RE4DC_NMR_MASK
            extended|=c.mask_geometry[0]==~0u && c.mask_geometry[1]!=~0u;
#endif
        }
        if(!extended)continue;
        if(room!=0x11cu || desc.model_id!=4u || desc.bones!=90u || desc.sections!=6u)return kPwBinding;
        for(unsigned i=0;i<6u;++i) {
            const auto& c=pack_chunks[desc.first_chunk+i];
            if(c.draw_owner!=(i==2u?1u:i))return kPwBinding;
#if RE4DC_NMR_MASK
            if(i==3u) {if(c.mask_geometry[0]!=~0u || c.mask_geometry[1]==~0u)return kPwBinding;}
            else if(c.mask_geometry[0]!=~0u || c.mask_geometry[1]!=~0u)return kPwBinding;
#else
            return kPwBinding;
#endif
            const re4dc_material::Role* role=nullptr;
            for(unsigned k=0;k<sec[kRole].count;++k)
                if(pack_roles[k].appearance==desc.appearance && pack_roles[k].role==i)role=&pack_roles[k];
            if(!role || role->source_bin!=luis_bin[i] || role->source_tpl!=luis_tpl[i])return kPwBinding;
            bool exact=false;
            for(unsigned k=0;k<sec[kSBlob].count;++k) {
                const auto& b=pack_blobs[k];const auto& h=b.normalized;
                exact|=b.model==role->model && b.bin==luis_bin[i] && h.bytes==luis_digest[i][0] &&
                    h.crc==luis_digest[i][1] && h.fnv==luis_digest[i][2];
            }
            if(!exact)return kPwBinding;
        }
    }
#endif
    detail=0;return kPwNone;
}
}
