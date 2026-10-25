#pragma once
// Explicit world-only R4IM v4 reader; generic MeshPackage stays unchanged.
#include "instanced_mesh.hpp"
#include <cstddef>
namespace re4dc::record_split {
// GCC may_alias explicitly permits viewing the ordinary Meshlet prefix/suffix.
struct __attribute__((may_alias)) Emit16 {std::uint32_t first_vertex,first_strip,strip_bytes;std::uint16_t vertex_count,strip_count;};
struct __attribute__((may_alias)) Bounds12 {std::uint16_t bounds_min[3],bounds_max[3];};
static_assert(sizeof(Emit16)==16 && sizeof(Bounds12)==12);
static_assert(sizeof(room::Meshlet)==28 && offsetof(room::Meshlet,bounds_min)==16);
struct Record : Emit16 {
    const std::uint16_t* bounds_min;const std::uint16_t* bounds_max;unsigned id;
    Record(const Emit16& e,const Bounds12& b,unsigned i):Emit16(e),bounds_min(b.bounds_min),bounds_max(b.bounds_max),id(i){}
    Record(const room::Meshlet& l):Emit16{l.first_vertex,l.first_strip,l.strip_bytes,l.vertex_count,l.strip_count},bounds_min(l.bounds_min),bounds_max(l.bounds_max),id(0){}
};
class SplitPackage {
    room::MeshHeader h_{};room::MeshLodHeader l_{};
    const std::uint8_t* data_=nullptr;const char* error_=nullptr;
    template<class T> const T* at(unsigned off)const{return reinterpret_cast<const T*>(data_+off);}
    bool fail(const char* why){data_=nullptr;error_=why;return false;}
    bool validate_records();
public:
    void close(){data_=nullptr;error_=nullptr;h_={};l_={};}
    bool valid()const{return data_!=nullptr;}
    const char* error()const{return error_;}
    const room::MeshHeader& header()const{return h_;}
    const room::MeshRecord* meshes()const{return at<room::MeshRecord>(h_.mesh_offset);}
    const room::MeshPart* parts()const{return at<room::MeshPart>(h_.part_offset);}
    const room::MeshPartLod* part_lods()const{return at<room::MeshPartLod>(l_.part_lod_offset);}
    const room::MeshCluster* clusters()const{return at<room::MeshCluster>(l_.cluster_offset);}
    const room::MeshLevel* levels()const{return at<room::MeshLevel>(l_.level_offset);}
    const room::CompactVertex12* vertices()const{return at<room::CompactVertex12>(h_.vertex_offset);}
    const std::uint8_t* strips()const{return data_+h_.strip_offset;}
    const std::uint32_t* palette()const{return at<std::uint32_t>(h_.palette_offset);}
    const Emit16& emit(unsigned id)const{return at<Emit16>(h_.meshlet_offset)[id];}
    const Bounds12& bounds(unsigned id)const{return at<Bounds12>(h_.reserved[1])[id];}
    bool source_identity(unsigned crc,unsigned bytes)const{return h_.reserved[2]==crc && h_.reserved[3]==bytes;}
    unsigned mesh_class(unsigned id)const{return l_.class_offset?data_[l_.class_offset+id]:unsigned(room::kClassDefault);}
    room::MeshClassRule class_rule(unsigned id)const{
        room::MeshClassRule rule{};
        if(l_.rule_offset && id<room::kClassRules)std::memcpy(&rule,data_+l_.rule_offset+id*sizeof(rule),sizeof(rule));
        return rule;
    }
    bool adopt(const std::uint8_t* bytes,unsigned size);
    const char* group_error(const std::uint8_t* records,unsigned bytes,unsigned groups)const;
};
inline bool SplitPackage::adopt(const std::uint8_t* bytes,unsigned size){
    close();
    if(size<112U || (reinterpret_cast<std::uintptr_t>(bytes)&3U))return fail("split size/alignment");
    std::memcpy(&h_,bytes,80);std::memcpy(&l_,bytes+80,32);
    if(std::memcmp(h_.magic,"R4IM",4) || h_.version!=4U || h_.bytes!=size ||
       h_.reserved[0]!=room::kColorArgb1555 || h_.reserved[3]<112U || l_.reserved)return fail("split header");
    if(h_.meshlet_count>65536U)return fail("split meshlet id capacity");
    unsigned cursor=112;
    const auto section=[&](unsigned off,unsigned count,unsigned stride){
        if(cursor>0xffffffe0U || off!=((cursor+31U)&~31U) || off>size || count>(size-off)/stride)return false;
        cursor=off+count*stride;return true;
    };
    if(!section(h_.mesh_offset,h_.mesh_count,sizeof(room::MeshRecord)) ||
       !section(h_.part_offset,h_.part_count,sizeof(room::MeshPart)) ||
       !section(h_.meshlet_offset,h_.meshlet_count,sizeof(Emit16)) ||
       !section(h_.reserved[1],h_.meshlet_count,sizeof(Bounds12)) ||
       !section(h_.vertex_offset,h_.vertex_count,sizeof(room::CompactVertex12)) ||
       !section(h_.strip_offset,h_.strip_bytes,1) || !section(h_.palette_offset,h_.palette_count,4) ||
       !section(l_.part_lod_offset,h_.part_count,sizeof(room::MeshPartLod)) ||
       !section(l_.cluster_offset,l_.cluster_count,sizeof(room::MeshCluster)) ||
       !section(l_.level_offset,l_.level_count,sizeof(room::MeshLevel)) ||
       (l_.class_offset && !section(l_.class_offset,h_.mesh_count,1)) ||
       (l_.rule_offset && !section(l_.rule_offset,room::kClassRules,sizeof(room::MeshClassRule))) ||
       cursor>0xffffffe0U || ((cursor+31U)&~31U)!=size)return fail("split section layout");
    if(!h_.palette_count || h_.palette_count>16U)return fail("split palette");
    data_=bytes;
    return validate_records();
}
inline bool SplitPackage::validate_records(){
    unsigned covered=0;
    for(unsigned i=0;i<h_.mesh_count;++i){
        const auto& m=meshes()[i];
        if(m.owner!=0x50U || m.common)return fail("split source owner");
        if(m.first_part!=covered || m.part_count>h_.part_count-covered)return fail("split mesh parts");
        covered+=m.part_count;
        for(unsigned a=0;a<3;++a)if(!(m.step[a]>0.0f) || !(m.step[a]<3.0e38f))return fail("split grid");
        if(mesh_class(i)>=room::kClassRules)return fail("split class");
    }
    if(covered!=h_.part_count)return fail("split mesh coverage");
    covered=0;
    for(unsigned i=0;i<h_.part_count;++i){
        const auto& p=parts()[i];const auto& lod=part_lods()[i];
        if(p.reserved || p.first_meshlet!=covered || p.meshlet_count>h_.meshlet_count-covered)return fail("split part meshlets");
        covered+=p.meshlet_count;
        if(lod.first_cluster>l_.cluster_count || lod.cluster_count>l_.cluster_count-lod.first_cluster)return fail("split part clusters");
        unsigned remaining=p.meshlet_count;
        for(unsigned c=lod.first_cluster;c<lod.first_cluster+lod.cluster_count;++c){
            const auto& cl=clusters()[c];
            for(unsigned a=0;a<3;++a)if(cl.bounds_min[a]>cl.bounds_max[a])return fail("split cluster bounds");
            if(!cl.level_count || cl.first_level>l_.level_count || cl.level_count>l_.level_count-cl.first_level)return fail("split cluster levels");
            float previous=0.0f;unsigned largest=0;
            for(unsigned k=cl.first_level;k<cl.first_level+cl.level_count;++k){
                const auto& lv=levels()[k];
                if(!(lv.error>=previous) || !(lv.error<3.0e38f))return fail("split level error");
                previous=lv.error;
                if(lv.first_meshlet<p.first_meshlet || lv.meshlet_count>p.meshlet_count ||
                   lv.first_meshlet-p.first_meshlet>p.meshlet_count-lv.meshlet_count)return fail("split level meshlets");
                if(lv.meshlet_count>largest)largest=lv.meshlet_count;
                for(unsigned id=lv.first_meshlet;id<lv.first_meshlet+lv.meshlet_count;++id){
                    const auto& b=bounds(id);
                    for(unsigned a=0;a<3;++a)if(b.bounds_min[a]<cl.bounds_min[a] || b.bounds_max[a]>cl.bounds_max[a])
                        return fail("split cluster enclosure");
                }
            }
            if(largest>remaining)return fail("split pick capacity");
            remaining-=largest;
        }
    }
    if(covered!=h_.meshlet_count)return fail("split part coverage");
    for(unsigned i=0;i<h_.meshlet_count;++i){
        const auto& e=emit(i);const auto& b=bounds(i);
        const bool indexed=(e.strip_count&room::kIndexedMeshlet)!=0;
        const unsigned table=indexed?2U*e.vertex_count:0U;
        if(!e.vertex_count || e.vertex_count>256U || e.first_vertex>h_.vertex_count ||
           (!indexed && e.vertex_count>h_.vertex_count-e.first_vertex) || (indexed && (e.first_strip&1U)) ||
           e.first_strip>h_.strip_bytes || table>h_.strip_bytes-e.first_strip ||
           e.strip_bytes>h_.strip_bytes-e.first_strip-table)return fail("split emit range");
        for(unsigned a=0;a<3;++a)if(b.bounds_min[a]>b.bounds_max[a])return fail("split bounds");
        const auto* offsets=reinterpret_cast<const std::uint16_t*>(strips()+e.first_strip);
        for(unsigned v=0;v<e.vertex_count;++v){
            const unsigned local=indexed?offsets[v]:v;
            if(local>=h_.vertex_count-e.first_vertex)return fail("split pool index");
            const auto& p=vertices()[e.first_vertex+local];
            if(p.x<b.bounds_min[0] || p.x>b.bounds_max[0] || p.y<b.bounds_min[1] ||
               p.y>b.bounds_max[1] || p.z<b.bounds_min[2] || p.z>b.bounds_max[2])return fail("split vertex bounds");
        }
        const auto* p=strips()+e.first_strip+table;const auto* end=p+e.strip_bytes;unsigned count=0;
        while(p<end){
            const unsigned n=*p++;
            if(n<3U || n>unsigned(end-p))return fail("split strip range");
            for(unsigned v=0;v<n;++v)if(p[v]>=e.vertex_count)return fail("split strip index");
            p+=n;++count;
        }
        if(count!=(e.strip_count&unsigned(room::kIndexedMeshlet-1U)))return fail("split strip count");
    }
    // Same conservative low/extent rule as MeshPackage::part_pool. Indexed
    // offset zero need not be used; the pool base still belongs to its part.
    unsigned previous=0;
    for(unsigned p=0;p<h_.part_count;++p){
        const auto& part=parts()[p];unsigned lo=h_.vertex_count,hi=0;
        for(unsigned id=part.first_meshlet;id<part.first_meshlet+part.meshlet_count;++id){
            const auto& e=emit(id);unsigned end=e.vertex_count;
            if(e.strip_count&room::kIndexedMeshlet){
                end=0;const auto* offsets=reinterpret_cast<const std::uint16_t*>(strips()+e.first_strip);
                for(unsigned v=0;v<e.vertex_count;++v)if(offsets[v]>=end)end=offsets[v]+1U;
            }
            if(e.first_vertex<lo)lo=e.first_vertex;
            if(e.first_vertex+end>hi)hi=e.first_vertex+end;
        }
        if(lo<hi){if(lo<previous)return fail("split part pool");previous=hi;}
    }
    return true;
}
// R4SG CRC/physical binding is checked by the loader. Validate the trusted
// selector ranges against actual strip boundaries and referenced positions
// before publishing the borrow; a bad sidecar keeps whole-meshlet rendering.
inline const char* SplitPackage::group_error(const std::uint8_t* records,unsigned bytes,unsigned groups)const{
    if(!valid() || !groups || groups>8U || bytes!=16U*groups*h_.meshlet_count)return "split group size";
    for(unsigned id=0;id<h_.meshlet_count;++id){
        const auto& e=emit(id);const bool indexed=(e.strip_count&room::kIndexedMeshlet)!=0;
        const auto* offsets=reinterpret_cast<const std::uint16_t*>(strips()+e.first_strip);
        const auto* raw=strips()+e.first_strip+(indexed?2U*e.vertex_count:0U);unsigned start=0;
        for(unsigned q=0;q<groups;++q){
            std::uint16_t g[8];std::memcpy(g,records+16U*(id*groups+q),16);
            const unsigned end=g[6],lo=g[7]&255U,hi=g[7]>>8;
            if(end<start || end>e.strip_bytes)return "split group extent";
            if(end==start){if(lo<=hi)return "split group empty range";continue;}
            if(lo>hi || hi>=e.vertex_count)return "split group range";
            for(unsigned a=0;a<3;++a)if(g[a]>g[a+3])return "split group bounds";
            unsigned cursor=start;
            while(cursor<end){
                const unsigned n=raw[cursor++];
                if(n<3U || n>end-cursor)return "split group strip boundary";
                for(unsigned v=0;v<n;++v){
                    const unsigned k=raw[cursor+v];
                    if(k<lo || k>hi)return "split group corner range";
                    const auto& p=vertices()[e.first_vertex+(indexed?offsets[k]:k)];
                    if(p.x<g[0] || p.y<g[1] || p.z<g[2] || p.x>g[3] || p.y>g[4] || p.z>g[5])
                        return "split group enclosure";
                }
                cursor+=n;
            }
            start=end;
        }
        if(start!=e.strip_bytes)return "split group coverage";
    }
    return nullptr;
}
class WorldPackage;
class RecordView {
    const room::MeshPackage* regular_=nullptr;const SplitPackage* split_=nullptr;
public:
    struct Range;
    RecordView(const room::MeshPackage& p):regular_(&p){}
    RecordView(const SplitPackage& p):split_(&p){}
    RecordView(const WorldPackage& p);
    bool split()const{return split_!=nullptr;}
    bool valid()const{return split_?split_->valid():regular_->valid();}
    bool lod()const{return split_ || regular_->lod();}
    bool shared()const{return split_ || regular_->shared();}
    const room::MeshHeader& header()const{return split_?split_->header():regular_->header();}
    const room::MeshRecord* meshes()const{return split_?split_->meshes():regular_->meshes();}
    const room::MeshPart* parts()const{return split_?split_->parts():regular_->parts();}
    const room::MeshPartLod* part_lods()const{return split_?split_->part_lods():regular_->part_lods();}
    const room::MeshCluster* clusters()const{return split_?split_->clusters():regular_->clusters();}
    const room::MeshLevel* levels()const{return split_?split_->levels():regular_->levels();}
    const room::CompactVertex12* vertices()const{return split_?split_->vertices():regular_->vertices();}
    const std::uint8_t* strips()const{return split_?split_->strips():regular_->strips();}
    const std::uint32_t* palette()const{return split_?split_->palette():regular_->palette();}
    const Emit16& emit(unsigned id)const{return split_?split_->emit(id):*reinterpret_cast<const Emit16*>(regular_->meshlets()+id);}
    const Bounds12& bounds(unsigned id)const{return split_?split_->bounds(id):*reinterpret_cast<const Bounds12*>(regular_->meshlets()[id].bounds_min);}
    Record record(unsigned id)const{return {emit(id),bounds(id),id};}
    Range meshlets()const;
    template<class R> static bool indexed(const R& r){return (r.strip_count&room::kIndexedMeshlet)!=0;}
    template<class R> static unsigned strip_total(const R& r){return r.strip_count&unsigned(room::kIndexedMeshlet-1U);}
    template<class R> const std::uint16_t* pool_offsets(const R& r)const{return reinterpret_cast<const std::uint16_t*>(strips()+r.first_strip);}
    template<class R> const std::uint8_t* strip_begin(const R& r)const{return strips()+r.first_strip+(indexed(r)?2U*r.vertex_count:0U);}
    unsigned mesh_class(unsigned id)const{return split_?split_->mesh_class(id):regular_->mesh_class(id);}
    room::MeshClassRule class_rule(unsigned id)const{return split_?split_->class_rule(id):regular_->class_rule(id);}
    unsigned find(unsigned bin,bool common)const{
        for(unsigned i=0;i<header().mesh_count;++i)if(meshes()[i].bin==bin && (meshes()[i].common!=0)==common)return i;
        return header().mesh_count;
    }
    bool part_pool(const room::MeshPart&,std::uint32_t&,std::uint32_t&)const;
#if defined(RE4DC_TREE_IMPOSTOR) && RE4DC_TREE_IMPOSTOR
    const room::MeshImpostor* impostor(unsigned id)const{return split_?nullptr:regular_->impostor(id);}
#endif
#if defined(RE4DC_MESH_TEXTURES) && RE4DC_MESH_TEXTURES
    const room::MeshTexture* texture(unsigned id)const{return split_?nullptr:regular_->texture(id);}
#endif
};
struct RecordView::Range {
    RecordView view;unsigned first=0;
    Record operator[](unsigned i)const{return view.record(first+i);}
    Range operator+(unsigned i)const{return {view,first+i};}
};
inline RecordView::Range RecordView::meshlets()const{return {*this,0};}
inline std::ptrdiff_t operator-(const Record* record,const RecordView::Range& range){return std::ptrdiff_t(record->id)-std::ptrdiff_t(range.first);}
inline bool RecordView::part_pool(const room::MeshPart& part,std::uint32_t& lo,std::uint32_t& hi)const{
    lo=header().vertex_count;hi=0;
    for(unsigned i=0;i<part.meshlet_count;++i){
        const auto& e=emit(part.first_meshlet+i);unsigned end=e.vertex_count;
        if(indexed(e)){end=0;const auto* offsets=pool_offsets(e);for(unsigned k=0;k<e.vertex_count;++k)if(offsets[k]>=end)end=offsets[k]+1U;}
        if(e.first_vertex<lo)lo=e.first_vertex;
        if(e.first_vertex+end>hi)hi=e.first_vertex+end;
    }
    return lo<hi;
}
class WorldPackage {
    room::MeshPackage regular_;SplitPackage split_;bool tried_split_=false;
public:
    void close(){regular_.close();split_.close();tried_split_=false;}
    bool adopt(const std::uint8_t* data,unsigned bytes,bool lod=false,bool prelit=false){
        close();unsigned version=0;if(bytes>=8U)std::memcpy(&version,data+4,4);
        tried_split_=version==4U;
        if(tried_split_)return lod && prelit && split_.adopt(data,bytes);
        return regular_.adopt(data,bytes,lod,prelit);
    }
    RecordView view()const{return tried_split_?RecordView(split_):RecordView(regular_);}
    bool is_split()const{return tried_split_ && split_.valid();}
    bool source_identity(unsigned crc,unsigned bytes)const{return is_split() && split_.source_identity(crc,bytes);}
    const char* group_error(const std::uint8_t* p,unsigned bytes,unsigned groups)const{return split_.group_error(p,bytes,groups);}
    bool valid()const{return view().valid();}
    bool lod()const{return view().lod();}
    bool shared()const{return view().shared();}
    const char* error()const{return tried_split_?split_.error():regular_.error();}
    const room::MeshHeader& header()const{return view().header();}
    const room::MeshRecord* meshes()const{return view().meshes();}
    const room::MeshPart* parts()const{return view().parts();}
    const room::MeshPartLod* part_lods()const{return view().part_lods();}
    const room::MeshCluster* clusters()const{return view().clusters();}
    const room::MeshLevel* levels()const{return view().levels();}
    const room::CompactVertex12* vertices()const{return view().vertices();}
    const std::uint8_t* strips()const{return view().strips();}
    RecordView::Range meshlets()const{return view().meshlets();}
    template<class R> static bool indexed(const R& r){return RecordView::indexed(r);}
    template<class R> const std::uint16_t* pool_offsets(const R& r)const{return view().pool_offsets(r);}
    template<class R> const std::uint8_t* strip_begin(const R& r)const{return view().strip_begin(r);}
    unsigned mesh_class(unsigned id)const{return view().mesh_class(id);}
    room::MeshClassRule class_rule(unsigned id)const{return view().class_rule(id);}
    bool part_pool(const room::MeshPart& p,std::uint32_t& lo,std::uint32_t& hi)const{return view().part_pool(p,lo,hi);}
};
inline RecordView::RecordView(const WorldPackage& p):RecordView(p.view()){}
inline bool source_header(const room::MeshHeader& h,unsigned bytes){
    return !std::memcmp(h.magic,"R4IM",4) && (h.version==2U || h.version==3U) && h.bytes==bytes &&
        h.reserved[0]==room::kColorArgb1555 && !h.reserved[1] && !h.reserved[2] && !h.reserved[3];
}
}
