#pragma once
// R4IM v1/v2/v3: instanced native scenery meshes (tools/convert_room_bins.py).
//
// One mesh per source BIN in the BIN's own model space; every placement that
// uses the BIN draws it with its live source modelview. A mesh part is matched
// to the source ModelPart by the part header's byte offset inside the BIN and
// its stream size, and the mesh to the live ModelData by its vertex and part
// counts, so a stale or foreign pointer can never select geometry. The offset
// is measured from the BIN's first part header (ModelData::pParts), because
// archive compaction may move the part block inside a BIN.
//
// v2 (convert_room_bins.py --lod) adds levels of detail without changing any
// v1 table: a MeshLodHeader follows the 80-byte header, each part owns a range
// of clusters, each cluster a range of levels ordered by increasing error
// (level 0 = source geometry), and each level a range of the part's meshlets.
// A part's meshlet range still covers every level, so lighting stays one pass.
// Only a LOD-aware runtime may adopt v2 (adopt(..., true)): a v1 draw loop
// would draw every level of a v2 part on top of each other.
//
// v3 (--lod --lod-share) is v2 plus indexed meshlets, so coarse levels reuse
// their part's finer-level vertices instead of storing copies. strip_count bit
// 15 (kIndexedMeshlet) marks one: first_vertex is then its part's vertex-pool
// base and its strip range starts with vertex_count u16 pool offsets (2-byte
// aligned, strip_bytes excludes them); strip indices address that table. Each
// part's vertices form one contiguous pool [lo, hi) that no other part touches,
// so lighting stays one pass per part over that range (part_pool()).
#include <cstddef>
#include <cstdint>
#include <cstring>
#include "room_package.hpp"

namespace re4dc::room {
// Header reserved[0]: each vertex colour slot is (CLR0 palette index << 12) |
// 12-bit octahedral source normal until the runtime lights its part, then
// ARGB1555. MeshPart::reserved is that part's lit flag (0 in the file).
constexpr std::uint32_t kColorOctNormal=1;
// Header reserved[0] = 2 (convert_lod color_mode="prelit", tools/ps2_world_r4im.py): every colour slot
// is already the corner's final ARGB1555; the palette is one unused word. Only adopt(..., prelit=true).
constexpr std::uint32_t kColorArgb1555=2;
// Header reserved[0] = 3 (convert_room_bins.py --color oct-vertex): the colour slot is kColorOctNormal's with palette
// index 0 (12-bit octahedral normal), and each vertex's CLR0 is an ARGB8888 entry of the table at header reserved[1]
// (vertex_count words): lit at runtime exactly as kColorOctNormal, without its 16-colour palette limit. Only
// adopt_by_encoding adopts it.
constexpr std::uint32_t kColorOctVertex=3;
constexpr std::uint16_t kIndexedMeshlet=0x8000U; // v3 Meshlet::strip_count flag
#if defined(RE4DC_SCENERY_DEDUP) && RE4DC_SCENERY_DEDUP==3
// SDO3: offline-only alternate PS2 world data, never a generic source package.
constexpr std::uint32_t kOfflineDedupMarker=0x334f4453U; // little endian 'SDO3'
constexpr std::uint16_t kOfflineDedupY=0x5344U,kOfflineDedupZ=0x4f33U;
#endif
struct MeshHeader {
    char magic[4];
    std::uint32_t version, bytes, crc;
    std::uint32_t mesh_count, part_count, meshlet_count, vertex_count, strip_bytes, palette_count;
    std::uint32_t mesh_offset, part_offset, meshlet_offset, vertex_offset, strip_offset, palette_offset;
    std::uint32_t reserved[4];
};
struct MeshRecord {
    std::uint16_t bin; std::uint8_t common, owner;
    std::uint16_t source_vertices, source_parts;
    std::uint32_t source_flags, first_part, part_count;
    float origin[3], step[3], bounds_min[3], bounds_max[3];
};
struct MeshPart {
    std::uint32_t source_offset, source_size;
    std::uint8_t texture, alpha, flags, reserved;
    std::uint32_t first_meshlet, meshlet_count;
    float uv_bias[2], uv_scale[2];
};
struct Meshlet {
    std::uint32_t first_vertex, first_strip, strip_bytes;
    std::uint16_t vertex_count, strip_count;
    std::uint16_t bounds_min[3], bounds_max[3]; // mesh grid units
};
// v2/v3, at offset 80. class_offset / rule_offset are optional (0 = absent):
// one scenery class code (MeshClass) per mesh, in mesh order, and
// kClassRules x MeshClassRule, this room's distances for a runtime rule.
struct MeshLodHeader {
    std::uint32_t cluster_count, level_count, part_lod_offset, cluster_offset, level_offset;
    std::uint32_t class_offset, rule_offset, reserved;
};
enum MeshClass : std::uint8_t {
    kClassDefault=0,  // untagged: fog far only
    kClassGround=1,   // terrain, floors: fog far only
    kClassTree=2,     // full detail to full_dm, thinned to cull_dm, then culled
    kClassLandmark=3, // distant building: only drawn inside its distance
    kClassClutter=4,  // small props: culled past cull_dm
    kClassStructure=5 // buildings and walls near the play space: fog far
};
constexpr unsigned kClassRules=8; // codes 6 and 7 reserved
struct MeshClassRule { std::uint16_t full_dm, cull_dm; }; // decimetres; 0 = runtime default
struct MeshPartLod { std::uint32_t first_cluster, cluster_count; };
struct MeshCluster {
    std::uint16_t bounds_min[3], bounds_max[3]; // mesh grid units, covers every level
    std::uint32_t first_level, level_count;
};
struct MeshLevel {
    std::uint32_t first_meshlet, meshlet_count;
    float error; // model units; drawn while error * lod_scale <= nearest cluster depth
};
#if defined(RE4DC_TREE_IMPOSTOR) && RE4DC_TREE_IMPOSTOR
// v2/v3, game TREE_IMPOSTOR=1 (tools/mesh_annotate.py --impostors): runtime
// table words 0/1 = offset/count of these records, ascending by mesh, at most
// one per mesh. Runtime tables: LOD header word 7 ('reserved'; W9b took words
// 5/6) = offset of a 32-byte head {impostor offset, impostor count, texture
// offset, 5 zero words}. A runtime without the knob ignores them (geometry as before).
// The atlas holds 'views' cells (cell_w x cell_h texels, 'cols' per row, row
// 0 at the top) of the mesh rendered orthographically around its vertical
// axis; cell k looks along -back_k, back_k = (cos a, 0, -sin a), a = 2 pi k /
// views in model space, and spans half_w/half_h around 'centre'.
struct MeshImpostor {
    std::uint32_t mesh;             // MeshRecord index
    std::uint32_t key_crc, key_fnv; // atlas: /cd/dc/tex/<crc>-<fnv>.re4tex
    std::uint16_t views, cols, cell_w, cell_h, atlas_w, atlas_h;
    float centre[3];                // model units
    float half_w, half_h;           // model units
    std::uint32_t reserved;         // 0 in the file; runtime: cached mean lit colour
};
static_assert(sizeof(MeshImpostor)==48);
#endif
#if defined(RE4DC_MESH_TEXTURES) && RE4DC_MESH_TEXTURES
// v2/v3, game MESH_TEXTURES=1 (tools/mesh_annotate.py --textures): runtime
// table word 2 = offset of a u32 record count followed by these records,
// ascending by package part index, at most one per part. The part draws with
// that prepared texture package instead of its source image; its UVs address
// it directly (0..1). A runtime without the knob ignores them.
struct MeshTexture {
    std::uint32_t part;             // package part index (MeshRecord::first_part + i)
    std::uint16_t width, height;    // the package's texture size
    std::uint32_t key_crc, key_fnv; // /cd/dc/tex/<crc>-<fnv>.re4tex
};
static_assert(sizeof(MeshTexture)==16);
#endif
static_assert(sizeof(MeshHeader)==80);
static_assert(sizeof(MeshLodHeader)==32);
static_assert(sizeof(MeshPartLod)==8);
static_assert(sizeof(MeshCluster)==20);
static_assert(sizeof(MeshLevel)==12);
static_assert(sizeof(MeshRecord)==68);
static_assert(sizeof(MeshPart)==36);
static_assert(sizeof(Meshlet)==28);
static_assert(sizeof(CompactVertex12)==12);

class MeshPackage {
public:
    // Validates every offset, range, strip length/index and palette index once;
    // afterwards the draw path trusts the tables. data must be 4-byte aligned.
    // lod: the caller draws v2 levels (and still accepts v1); otherwise v1 only.
    // prelit: the package must use kColorArgb1555 (and nothing else may).
    bool adopt(const std::uint8_t* data,std::uint32_t size,bool lod=false,bool prelit=false){
        close();
        if(size<sizeof(MeshHeader) || (reinterpret_cast<std::uintptr_t>(data)&3U))return fail("size");
        std::memcpy(&h_,data,sizeof(h_));
        if(std::memcmp(h_.magic,"R4IM",4) || !(h_.version==1 || (lod && (h_.version==2 || h_.version==3))) || h_.bytes!=size)return fail("header");
        std::uint32_t head=sizeof(MeshHeader);
        if(h_.version>=2){
            head+=sizeof(MeshLodHeader);
            if(size<head)return fail("size");
            std::memcpy(&l_,data+sizeof(MeshHeader),sizeof(l_));
        }
        if(!section(h_.mesh_offset,h_.mesh_count,sizeof(MeshRecord),size,head) ||
           !section(h_.part_offset,h_.part_count,sizeof(MeshPart),size,head) ||
           !section(h_.meshlet_offset,h_.meshlet_count,sizeof(Meshlet),size,head) ||
           !section(h_.vertex_offset,h_.vertex_count,sizeof(CompactVertex12),size,head) ||
           !section(h_.strip_offset,h_.strip_bytes,1,size,head) ||
           !section(h_.palette_offset,h_.palette_count,4,size,head))return fail("section");
        if(h_.version>=2 && (!section(l_.part_lod_offset,h_.part_count,sizeof(MeshPartLod),size,head) ||
           !section(l_.cluster_offset,l_.cluster_count,sizeof(MeshCluster),size,head) ||
           !section(l_.level_offset,l_.level_count,sizeof(MeshLevel),size,head)))return fail("lod section");
        if(h_.version>=2 && ((l_.class_offset && !section(l_.class_offset,h_.mesh_count,1,size,head)) ||
           (l_.rule_offset && !section(l_.rule_offset,kClassRules,sizeof(MeshClassRule),size,head))))return fail("class section");
        if(h_.version>=2 && l_.class_offset)
            for(unsigned m=0;m<h_.mesh_count;++m)if(data[l_.class_offset+m]>=kClassRules)return fail("class");
        if(!h_.palette_count || h_.palette_count>65536U)return fail("palette");
        data_=data;
        if(h_.reserved[0]!=(prelit?kColorArgb1555:kColorOctNormal))return fail("color encoding");
        if(h_.palette_count>16U)return fail("palette");
#if defined(RE4DC_SCENERY_DEDUP) && RE4DC_SCENERY_DEDUP==3
        if(h_.reserved[3] && h_.reserved[3]!=kOfflineDedupMarker)return fail("offline marker");
        if(offline_dedup() && (!prelit || h_.version!=3))return fail("offline encoding");
        if(offline_dedup() && h_.reserved[1] && h_.reserved[1]<h_.bytes)return fail("offline source extent");
#endif
        if(!prelit)for(unsigned i=0;i<h_.vertex_count;++i)if((vertices()[i].color>>12)>=h_.palette_count)return fail("color");
        for(unsigned i=0;i<h_.part_count;++i)if(parts()[i].reserved)return fail("part state");
        for(unsigned m=0;m<h_.mesh_count;++m){
            const auto& r=meshes()[m];
            if(r.first_part>h_.part_count || r.part_count>h_.part_count-r.first_part)return fail("mesh parts");
            for(unsigned a=0;a<3;++a)if(!(r.step[a]>0.0f) || r.step[a]!=r.step[a])return fail("grid");
        }
        for(unsigned i=0;i<h_.part_count;++i){
            const auto& p=parts()[i];
            if(p.first_meshlet>h_.meshlet_count || p.meshlet_count>h_.meshlet_count-p.first_meshlet)return fail("part meshlets");
        }
        for(unsigned i=0;i<h_.meshlet_count;++i){
            const auto& l=meshlets()[i];
            const bool ix=indexed(l);
            const std::uint32_t table=ix?2U*l.vertex_count:0U;
            if(ix && h_.version!=3)return fail("meshlet");
            if(!l.vertex_count || l.vertex_count>256U || l.first_vertex>h_.vertex_count ||
               (!ix && l.vertex_count>h_.vertex_count-l.first_vertex) || (l.first_strip&(ix?1U:0U)) ||
               l.first_strip>h_.strip_bytes || table>h_.strip_bytes-l.first_strip ||
               l.strip_bytes>h_.strip_bytes-l.first_strip-table)return fail("meshlet");
            if(ix){
                const std::uint16_t* offsets=pool_offsets(l);
                for(unsigned k=0;k<l.vertex_count;++k)if(offsets[k]>=h_.vertex_count-l.first_vertex)return fail("pool index");
            }
            const std::uint8_t* s=strip_begin(l);const std::uint8_t* end=s+l.strip_bytes;
            unsigned count=0;
            while(s<end){
                const unsigned n=*s++;
                if(n<3 || n>unsigned(end-s))return fail("strip");
                for(unsigned k=0;k<n;++k)if(s[k]>=l.vertex_count)return fail("strip index");
                s+=n;++count;
            }
            if(count!=strip_total(l))return fail("strip count");
        }
#if defined(RE4DC_SCENERY_DEDUP) && RE4DC_SCENERY_DEDUP==3
        if(offline_dedup()){
            for(unsigned i=0;i<h_.meshlet_count;++i){
                const auto& l=meshlets()[i];const unsigned rep=repeat_count(l);
                if(!rep)continue;
                const unsigned n=l.vertex_count,u=n-rep;
                if(rep>=n)return fail("offline repeats");
                const auto* v=vertices()+l.first_vertex;
                for(unsigned k=u;k<n;++k)
                    if(v[k].x>=u || v[k].y!=kOfflineDedupY || v[k].z!=kOfflineDedupZ)
                        return fail("offline source");
            }
        }
#endif
        if(h_.version==3){
            // Part pools are ascending and disjoint: lighting a part's pool
            // once can never relight a corner another part already lit.
            std::uint32_t previous=0;
#if defined(RE4DC_SCENERY_DEDUP) && RE4DC_SCENERY_DEDUP==3
            unsigned covered=0,plain_end=0;
#endif
            for(unsigned i=0;i<h_.part_count;++i){
#if defined(RE4DC_SCENERY_DEDUP) && RE4DC_SCENERY_DEDUP==3
                if(offline_dedup()){
                    const auto& part=parts()[i];
                    if(part.first_meshlet!=covered)return fail("offline part partition");
                    covered+=part.meshlet_count;
                    unsigned pool_lo=h_.vertex_count,pool_hi=0;
                    for(unsigned j=0;j<part.meshlet_count;++j){
                        const auto& l=meshlets()[part.first_meshlet+j];
                        if(indexed(l)){
                            const auto* o=pool_offsets(l);
                            for(unsigned k=0;k<l.vertex_count;++k){
                                const unsigned v=l.first_vertex+o[k];
                                if(v<pool_lo)pool_lo=v;if(v+1U>pool_hi)pool_hi=v+1U;
                            }
                        }else{
                            if(l.first_vertex<plain_end)return fail("offline plain alias");
                            plain_end=l.first_vertex+l.vertex_count;
                        }
                    }
                    // Conservative indexed pool interval, one part at a time: linear in vertices.
                    for(unsigned j=0;j<part.meshlet_count;++j){
                        const auto& l=meshlets()[part.first_meshlet+j];
                        if(repeat_count(l) && pool_hi && l.first_vertex<pool_hi && l.first_vertex+l.vertex_count>pool_lo)
                            return fail("offline pool alias");
                    }
                }
#endif
                std::uint32_t lo,hi;
                if(!part_pool(parts()[i],lo,hi))continue;
                if(lo<previous)return fail("part pool");
                previous=hi;
            }
#if defined(RE4DC_SCENERY_DEDUP) && RE4DC_SCENERY_DEDUP==3
            if(offline_dedup() && covered!=h_.meshlet_count)return fail("offline part coverage");
#endif
        }
        if(h_.version>=2){
            // Every level of every cluster lies inside its own part's meshlet
            // range; errors are finite, non-negative and non-decreasing.
            for(unsigned i=0;i<h_.part_count;++i){
                const auto& p=parts()[i];const auto& pl=part_lods()[i];
                if(pl.first_cluster>l_.cluster_count || pl.cluster_count>l_.cluster_count-pl.first_cluster)return fail("part clusters");
                for(unsigned c=pl.first_cluster;c<pl.first_cluster+pl.cluster_count;++c){
                    const auto& cl=clusters()[c];
                    if(!cl.level_count || cl.first_level>l_.level_count || cl.level_count>l_.level_count-cl.first_level)return fail("cluster levels");
                    float previous=0.0f;
                    for(unsigned k=cl.first_level;k<cl.first_level+cl.level_count;++k){
                        const auto& lv=levels()[k];
                        if(!(lv.error>=previous) || !(lv.error<3.0e38f))return fail("level error");
                        previous=lv.error;
                        if(lv.first_meshlet<p.first_meshlet || lv.meshlet_count>p.meshlet_count ||
                           lv.first_meshlet-p.first_meshlet>p.meshlet_count-lv.meshlet_count)return fail("level meshlets");
                    }
                }
            }
        }
#if (defined(RE4DC_TREE_IMPOSTOR) && RE4DC_TREE_IMPOSTOR) || (defined(RE4DC_MESH_TEXTURES) && RE4DC_MESH_TEXTURES)
        rt_[0]=rt_[1]=rt_[2]=0;
        if(h_.version>=2 && l_.reserved){
            if(!section(l_.reserved,8,4,size,head))return fail("runtime tables");
            const std::uint32_t* t=at<std::uint32_t>(l_.reserved);
            for(unsigned i=3;i<8;++i)if(t[i])return fail("runtime tables");
            for(unsigned i=0;i<3;++i)rt_[i]=t[i];
        }
#endif
#if defined(RE4DC_TREE_IMPOSTOR) && RE4DC_TREE_IMPOSTOR
        if(h_.version>=2 && rt_[1]){
            if(!section(rt_[0],rt_[1],sizeof(MeshImpostor),size,head))return fail("impostor section");
            const auto pow2=[](unsigned n){return n>=8U && n<=1024U && !(n&(n-1U));};
            const auto finite=[](float f){return f==f && f<3.0e38f && f>-3.0e38f;};
            for(unsigned i=0;i<rt_[1];++i){
                const auto& r=impostors()[i];
                if(r.mesh>=h_.mesh_count || (i && r.mesh<=impostors()[i-1].mesh) || r.reserved ||
                   !r.views || r.views>64U || !r.cols || r.cols>r.views || !r.cell_w || !r.cell_h ||
                   !pow2(r.atlas_w) || !pow2(r.atlas_h) || unsigned(r.cols)*r.cell_w>r.atlas_w ||
                   unsigned((r.views+r.cols-1U)/r.cols)*r.cell_h>r.atlas_h ||
                   !finite(r.centre[0]) || !finite(r.centre[1]) || !finite(r.centre[2]) ||
                   !(r.half_w>0.0f) || !(r.half_h>0.0f) || !finite(r.half_w) || !finite(r.half_h))return fail("impostor");
            }
        }
#endif
#if defined(RE4DC_MESH_TEXTURES) && RE4DC_MESH_TEXTURES
        if(h_.version>=2 && rt_[2]){
            if(!section(rt_[2],1,4,size,head))return fail("texture section");
            const std::uint32_t count=*at<std::uint32_t>(rt_[2]);
            if(!count || !section(rt_[2]+4,count,sizeof(MeshTexture),size,head))return fail("texture section");
            const auto pow2=[](unsigned n){return n>=8U && n<=1024U && !(n&(n-1U));};
            for(unsigned i=0;i<count;++i){
                const auto& r=textures()[i];
                if(r.part>=h_.part_count || (i && r.part<=textures()[i-1].part) ||
                   !pow2(r.width) || !pow2(r.height))return fail("texture");
            }
        }
#endif
        return true;
    }
    void close(){
        data_=nullptr;error_=nullptr;l_={};
#if (defined(RE4DC_TREE_IMPOSTOR) && RE4DC_TREE_IMPOSTOR) || (defined(RE4DC_MESH_TEXTURES) && RE4DC_MESH_TEXTURES)
        rt_[0]=rt_[1]=rt_[2]=0;
#endif
    }
    bool valid()const{return data_!=nullptr;}
    bool lod()const{return data_ && h_.version>=2;}
    bool shared()const{return data_ && h_.version==3;}
    static bool indexed(const Meshlet& l){return (l.strip_count&kIndexedMeshlet)!=0;}
#if defined(RE4DC_SCENERY_DEDUP) && RE4DC_SCENERY_DEDUP==3
    bool offline_dedup()const{return h_.reserved[3]==kOfflineDedupMarker;}
    unsigned repeat_count(const Meshlet& l)const{return offline_dedup() && !indexed(l)?(l.strip_count>>7)&255U:0U;}
    unsigned strip_total(const Meshlet& l)const{
        return l.strip_count&(offline_dedup() && !indexed(l)?127U:unsigned(kIndexedMeshlet-1U));
    }
    std::uint32_t source_crc()const{return offline_dedup()?h_.reserved[2]:h_.crc;}
    // SDO3 word17 records original extent after exact strip-block sharing; zero is legacy byte-neutral.
    std::uint32_t source_bytes()const{return offline_dedup() && h_.reserved[1]?h_.reserved[1]:h_.bytes;}
    // Authenticate every selected group source range before publishing an SDO3 SG borrow.
    bool offline_groups(const std::uint8_t* data,unsigned bytes,unsigned groups)const{
        if(!groups || groups>8U || bytes%(16U*groups) || bytes/(16U*groups)!=h_.meshlet_count)return false;
        for(unsigned i=0;i<h_.meshlet_count;++i){
            const auto& l=meshlets()[i];const unsigned u=l.vertex_count-repeat_count(l);
            const auto* base=vertices()+l.first_vertex;const auto* sb=strip_begin(l);
            const auto* g=reinterpret_cast<const std::uint16_t*>(data+16U*groups*i);unsigned prev=0;
            for(unsigned j=0;j<groups;++j,g+=8){
                const unsigned end=g[6],lo=g[7]&255U,hi=g[7]>>8;
                if(end<prev || end>l.strip_bytes)return false;
                if(end==prev)continue;
                if(lo>hi || hi>=u)return false;
                for(const std::uint8_t* p=sb+prev;p<sb+end;){
                    const unsigned n=*p++;
                    if(n<3U || n>unsigned(sb+end-p))return false;
                    for(unsigned k=0;k<n;++k){
                        const unsigned c=p[k],q=c<u?c:base[c].x;
                        if(q<lo || q>hi)return false;
                    }
                    p+=n;
                }
                prev=end;
            }
            if(prev!=l.strip_bytes)return false;
        }
        return true;
    }
    // Used by generic/near/far clipping; source UV and colour always belong to in.
    static const CompactVertex12& offline_position(const CompactVertex12* base,unsigned unique,unsigned count,
                                                   const CompactVertex12& in){
        const auto a=reinterpret_cast<std::uintptr_t>(&in),b=reinterpret_cast<std::uintptr_t>(base);
        return base && a>=b+sizeof(*base)*unique && a<b+sizeof(*base)*count?base[in.x]:in;
    }
#else
    static unsigned strip_total(const Meshlet& l){return l.strip_count&unsigned(kIndexedMeshlet-1U);}
#endif
    // Indexed meshlet: vertex_count offsets from first_vertex (the part pool).
    const std::uint16_t* pool_offsets(const Meshlet& l)const{
        return reinterpret_cast<const std::uint16_t*>(strips()+l.first_strip);
    }
    const std::uint8_t* strip_begin(const Meshlet& l)const{
        return strips()+l.first_strip+(indexed(l)?2U*l.vertex_count:0U);
    }
    // Vertex range [lo, hi) every meshlet of part p reads; false when empty.
    bool part_pool(const MeshPart& p,std::uint32_t& lo,std::uint32_t& hi)const{
        lo=h_.vertex_count;hi=0;
        for(unsigned i=0;i<p.meshlet_count;++i){
            const auto& l=meshlets()[p.first_meshlet+i];
            std::uint32_t end=l.vertex_count;
            if(indexed(l)){
                end=0;const std::uint16_t* offsets=pool_offsets(l);
                for(unsigned k=0;k<l.vertex_count;++k)if(offsets[k]>=end)end=offsets[k]+1U;
            }
            if(l.first_vertex<lo)lo=l.first_vertex;
            if(l.first_vertex+end>hi)hi=l.first_vertex+end;
        }
        return lo<hi;
    }
    const MeshPartLod* part_lods()const{return at<MeshPartLod>(l_.part_lod_offset);}
    const MeshCluster* clusters()const{return at<MeshCluster>(l_.cluster_offset);}
    const MeshLevel* levels()const{return at<MeshLevel>(l_.level_offset);}
#if defined(RE4DC_TREE_IMPOSTOR) && RE4DC_TREE_IMPOSTOR
    const MeshImpostor* impostors()const{return at<MeshImpostor>(rt_[0]);}
    // Impostor record of mesh m; nullptr when it has none.
    const MeshImpostor* impostor(unsigned m)const{
        if(!lod())return nullptr;
        for(unsigned i=0;i<rt_[1] && impostors()[i].mesh<=m;++i)if(impostors()[i].mesh==m)return impostors()+i;
        return nullptr;
    }
#endif
#if defined(RE4DC_MESH_TEXTURES) && RE4DC_MESH_TEXTURES
    const MeshTexture* textures()const{return at<MeshTexture>(rt_[2]+4);}
    // Texture record of package part index 'part'; nullptr when it has none.
    const MeshTexture* texture(unsigned part)const{
        if(!lod() || !rt_[2])return nullptr;
        const std::uint32_t count=*at<std::uint32_t>(rt_[2]);
        for(unsigned i=0;i<count && textures()[i].part<=part;++i)if(textures()[i].part==part)return textures()+i;
        return nullptr;
    }
#endif
    // Scenery class of mesh m (kClassDefault when the package has no table).
    unsigned mesh_class(unsigned m)const{return l_.class_offset?data_[l_.class_offset+m]:unsigned(kClassDefault);}
    // This room's rule for class c; {0, 0} (runtime defaults) when absent.
    MeshClassRule class_rule(unsigned c)const{
        MeshClassRule r{0,0};
        if(l_.rule_offset && c<kClassRules)std::memcpy(&r,data_+l_.rule_offset+c*sizeof(MeshClassRule),sizeof(r));
        return r;
    }
    const char* error()const{return error_;}
    const MeshHeader& header()const{return h_;}
    const MeshRecord* meshes()const{return at<MeshRecord>(h_.mesh_offset);}
    const MeshPart* parts()const{return at<MeshPart>(h_.part_offset);}
    const Meshlet* meshlets()const{return at<Meshlet>(h_.meshlet_offset);}
    const CompactVertex12* vertices()const{return at<CompactVertex12>(h_.vertex_offset);}
    const std::uint8_t* strips()const{return data_+h_.strip_offset;}
    const std::uint32_t* palette()const{return at<std::uint32_t>(h_.palette_offset);}
    // Mesh index for a (bin, common) identity; mesh_count when absent.
    unsigned find(unsigned bin,bool common)const{
        for(unsigned m=0;m<h_.mesh_count;++m)
            if(meshes()[m].bin==bin && (meshes()[m].common!=0)==common)return m;
        return h_.mesh_count;
    }
    // Part of mesh m whose source header sits at offset/size; nullptr otherwise.
    const MeshPart* part(unsigned m,std::uint32_t offset,std::uint32_t size)const{
        const auto& r=meshes()[m];
        for(unsigned i=0;i<r.part_count;++i){
            const auto& p=parts()[r.first_part+i];
            if(p.source_offset==offset && p.source_size==size)return &p;
        }
        return nullptr;
    }
    // A released source BIN (tools/room_smd.py release: the room archive keeps
    // the header, nVtx = kReleasedVertices box corners and every part header in
    // order with no GX stream) is matched by part index: part k sits at offset
    // 32*k with size 0. Only meshes that carry every source part qualify.
    static constexpr unsigned kReleasedVertices=2;
    bool source_identity(unsigned m,unsigned vertices,unsigned part_total)const{
        const auto& r=meshes()[m];
        return part_total==r.source_parts &&
               (vertices==r.source_vertices || (vertices==kReleasedVertices && r.part_count==r.source_parts));
    }
    // Part of mesh m for a live source identity (vertices, part count, part
    // header offset from the first part header, stream size); nullptr otherwise.
    const MeshPart* source_part(unsigned m,unsigned vertices,unsigned part_total,std::uint32_t offset,std::uint32_t size)const{
        const auto& r=meshes()[m];
        if(!source_identity(m,vertices,part_total))return nullptr;
        if(vertices==r.source_vertices)return part(m,offset,size);
        if(size || (offset&31U) || offset/32U>=r.part_count)return nullptr;
        return &parts()[r.first_part+offset/32U];
    }
private:
    template<class T> const T* at(std::uint32_t offset)const{return reinterpret_cast<const T*>(data_+offset);}
    static bool section(std::uint32_t offset,std::uint32_t count,std::uint32_t stride,std::uint32_t size,std::uint32_t head){
        return offset>=head && offset<=size && (offset&3U)==0 &&
               std::uint64_t(count)*stride<=std::uint64_t(size-offset);
    }
#if defined(RE4DC_SCENERY_DEDUP) && RE4DC_SCENERY_DEDUP==3
    __attribute__((noinline,optimize("Os")))
#endif
    bool fail(const char* why){data_=nullptr;error_=why;return false;}
    MeshHeader h_{};
    MeshLodHeader l_{};
#if (defined(RE4DC_TREE_IMPOSTOR) && RE4DC_TREE_IMPOSTOR) || (defined(RE4DC_MESH_TEXTURES) && RE4DC_MESH_TEXTURES)
    std::uint32_t rt_[3]{}; // runtime tables (TREE_IMPOSTOR / MESH_TEXTURES): see open()
#endif
    const std::uint8_t* data_=nullptr;
    const char* error_=nullptr;
};
// Scenery adopt by the package's own validated colour encoding (game30.mk SCENERY_ENCODING): kColorOctNormal adopts
// as adopt(data, size, lod) always did (lit at the first draw); kColorArgb1555 adopts prelit and marks every part lit,
// so the runtime never decodes its colour slots as palette index + normal nor lights them again; kColorOctVertex is
// validated as kColorOctNormal (every slot's palette index must be 0) plus its vertex colour table, returned in
// *vertex_colors (nullptr otherwise) for the lighting to read in place of the palette; any other value is rejected
// ("color encoding"). data is the caller's writable copy of the file.
inline bool adopt_by_encoding(MeshPackage& p,std::uint8_t* data,std::uint32_t size,bool lod,
                              const std::uint32_t** vertex_colors=nullptr){
    if(vertex_colors)*vertex_colors=nullptr;
    std::uint32_t encoding=0,table=0,vertices=0;
    if(size>=sizeof(MeshHeader)){
        std::memcpy(&encoding,data+offsetof(MeshHeader,reserved),4);
        std::memcpy(&table,data+offsetof(MeshHeader,reserved)+4,4);
        std::memcpy(&vertices,data+offsetof(MeshHeader,vertex_count),4);
    }
    if(encoding==kColorOctVertex){
        // A bad table or palette: rejected as the plain reader rejects the encoding ("color encoding").
        const auto reject=[&]{p.adopt(data,size,lod,false);return false;};
        if(!vertex_colors || table<sizeof(MeshHeader) || (table&3U) || table>size ||
           std::uint64_t(vertices)*4U>std::uint64_t(size-table))return reject();
        // adopt() checks the oct slots (palette index < palette_count = 1) under kColorOctNormal; the file word is
        // restored after, so the storage keeps its own encoding.
        const std::uint32_t oct=kColorOctNormal;
        std::memcpy(data+offsetof(MeshHeader,reserved),&oct,4);
        const bool ok=p.adopt(data,size,lod,false);
        std::memcpy(data+offsetof(MeshHeader,reserved),&encoding,4);
        if(!ok)return false;
        if(p.header().palette_count!=1)return reject();
        *vertex_colors=reinterpret_cast<const std::uint32_t*>(data+table);
        return true;
    }
    const bool prelit=encoding==kColorArgb1555;
    if(!p.adopt(data,size,lod,prelit))return false;
    if(prelit)for(unsigned i=0;i<p.header().part_count;++i)
        reinterpret_cast<MeshPart*>(data+p.header().part_offset)[i].reserved=1;
    return true;
}
} // namespace re4dc::room
