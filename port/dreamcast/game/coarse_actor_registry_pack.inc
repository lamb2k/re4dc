// NATIVE_MODEL_REGISTRY_PACK=1 (native_model_registry.mk; render only): the room-owned registry package. Included once
// by coarse_actor_owner_leon.inc after coarse_actor_material.inc: it fills the registry view of
// coarse_actor_owner_registry.inc, the room identity rows of actor_material_records.inc / actor_lifetime.inc and
// resets the registry IDs of coarse_actor_geometry_once.inc.
//
// re4dc_registry_room_enter (ui_bridge.cpp re4dc_room_enter, after the heap-4 room opens and before the room's
// archives load and adopt): dc/native/r<room>/registry.re4nmr (tools/d367/model_registry.py --package-room) is read
// into ONE heap-4 room cell (re4dc_static_alloc: the native static room storage, high end, 80 KiB source reserve)
// with its skin arena after it. Everything is validated before anything is visible: header magic / version /
// sizes / room, header and payload CRC32 + FNV-1a, the section table (kinds, order, 32-byte alignment, bounds, no
// overlap, record sizes, explicit capacities), every record (counts, offsets, spans inside the blob section,
// alignment, pairwise disjoint arrays, per-geometry hashes, finite binds and weights, parents as an index-ordered
// forest), every cross reference (descriptor -> chunk refs -> geometry / texture, geometry bones = descriptor
// bones, role rows = exactly the descriptor sections, fact model / part / texture ranges, source blob for every
// role's BIN), duplicates (identical geometry stored twice, texture keys, role keys, ambiguous descriptor source
// identities), then the target preflight of every geometry and every descriptor's skin stream. Only then are the
// view and the identity rows published (one generation; the lifetime epoch moves). Any failure frees the cell and
// publishes nothing: every actor keeps the whole source path. No pointer is read from the file.
//
// re4dc_registry_room_leave (ui_bridge.cpp re4dc_room_leave, before the UI / static retire and the heap-4 close):
// the transaction's owned records are revoked if a frame still holds them, the room rows leave every live
// lifetime record (records left with no row are dropped; the epoch moves), the registry IDs' immutable proofs are
// reset, the view / id mask / binding cache / skin state are cleared and the cell is freed. A room enter with a
// package still published retires it first, so two generations never overlap (peak overlap 0 cells).
#include <kos/fs.h>
#include <fcntl.h>
#include <cstddef>
#include <cstdio>
extern "C" void* re4dc_static_alloc(unsigned);
extern "C" void re4dc_static_free(void*);
extern "C" int re4dc_static_heap_free();
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
#include "coarse_actor_registry_pack_check.inc"
namespace {
struct PackState {
    unsigned char* cell;unsigned char* base;unsigned room,bytes,arena,generation,heap_before,heap_after;
    unsigned opens,publishes,refusals,retires,late_retires;
#if defined(RE4DC_NMR_PARTNER) && RE4DC_NMR_PARTNER
    unsigned char* cell2;unsigned arena2,partners;
#endif
};
PackState pack{};
#if RE4DC_GC_ASSET_GATE
re4dc_gcasset::PayloadProof gcasset_registry[2];
void gcasset_registry_capture(unsigned index,const void* base,unsigned bytes){
    auto& proof=gcasset_registry[index];
    re4dc_gcasset::payload_retire(proof);
    if(re4dc_gcasset::ensure_disc_catalog())
        (void)re4dc_gcasset::payload_capture(proof,&proof,base,bytes);
}
void gcasset_registry_retire(){for(auto& proof:gcasset_registry)re4dc_gcasset::payload_retire(proof);}
#endif
void registry_view_clear() {
    registry=RegistryView{};registry_mask_ready=false;
#if RE4DC_NMR_MASK
    registry_geom=registry_blob=nullptr;
#endif
#if defined(RE4DC_NMR_PARTNER) && RE4DC_NMR_PARTNER
    registry_geom2=registry_blob2=nullptr;registry_geom_base2=~0u;
#endif
    std::memset(registry_id_mask,0,sizeof(registry_id_mask));
    for(auto& b:registry_bindings)b=RegistryBinding{};
    registry_replace=0;registry_bound=nullptr;
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
    registry_tx=RegistryTxToken{};  // no plan token outlives its view
#endif
    std::memset(registry_skin_built,0,sizeof(registry_skin_built));std::memset(registry_skin_state,0,sizeof(registry_skin_state));
    std::memset(registry_skin_used,0,sizeof(registry_skin_used));registry_skin_next=0;registry_skin=nullptr;registry_skin_cap=0;
#if RE4DC_NATIVE_MODEL_REGISTRY == 2
    for(auto& s:registry_snaps)s.m=nullptr;
#endif
}
void pack_refuse(unsigned room,PackWhy why,unsigned detail) {
    ++pack.refusals;
    re4dc_log("NMRPACK refuse room=%04x why=%s detail=%u heap4_free=%d: every actor keeps the source path\n",room,
        kPackWhy[why<kPwCount?why:0],detail,re4dc_static_heap_free());
}
}

extern "C" void re4dc_registry_room_leave() {
#if RE4DC_GC_ASSET_GATE
    gcasset_registry_retire();
#endif
    if(!pack.cell)return;
    const unsigned room=pack.room,generation=pack.generation;
    const bool owned=actor_owned_live;
    // A frame that still holds owned records is revoked the transaction's own way (no traversal of their storage).
    if(owned)re4dc_actor_transaction_retire();
    unsigned infos=0,assets=0;
    const unsigned users_before=re4dc_material::life::room_rows_users();  // live records naming a room row now
    re4dc_material::life::room_rows_retire(infos,assets);
    const unsigned proofs=actor_immutable_reset_registry();
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
    if(registry.descriptor_count)scene_report(re4dc_ui_frame());  // this generation's census before its view goes
    while(registry_tracked_n)registry_note_retire(registry_tracked[0].m,"room-retire");
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_TX == 2
    registry_tx_report("room-leave");
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_PALBOUND == 2
    registry_pb_report("room-leave");
#endif
    registry_view_clear();
    re4dc_static_free(pack.cell);
#if defined(RE4DC_NMR_PARTNER) && RE4DC_NMR_PARTNER
    if(pack.cell2){re4dc_static_free(pack.cell2);pack.arena+=pack.arena2;pack.cell2=nullptr;pack.arena2=0;}
#endif
    const unsigned bytes=pack.arena;pack.cell=nullptr;pack.base=nullptr;pack.arena=0;++pack.retires;
    re4dc_log("NMRPACK retire room=%04x gen=%u bytes=%u owned_live=%u row_users_before=%u infos_dropped=%u assets_dropped=%u "
        "proofs_reset=%u row_users=%u heap4_free=%d retires=%u\n",room,generation,bytes,unsigned(owned),users_before,infos,assets,proofs,
        re4dc_material::life::room_rows_users(),re4dc_static_heap_free(),pack.retires);
}

#if !(defined(RE4DC_NMR_PARTNER) && RE4DC_NMR_PARTNER)
extern "C" void re4dc_registry_room_enter(unsigned room) {
    // Never two generations at once: a package the room leave did not retire is retired before the next opens
    // (counted as late; the peak is one package cell either way).
    if(pack.cell){++pack.late_retires;re4dc_registry_room_leave();}
    char path[64];snprintf(path,sizeof(path),"/cd/dc/native/r%x%02x/registry.re4nmr",room>>8,room&255u);
    const file_t file=fs_open(path,O_RDONLY);
    if(file==FILEHND_INVALID){re4dc_log("NMRPACK room=%04x none (%s)\n",room,path);return;}
    ++pack.opens;
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23
    const unsigned size=unsigned(fs_total(file)),limit=pack_room_max(room);
    unsigned char head[kPackHeader];
    if(size<kPackPayload || size>limit || fs_read(file,head,kPackHeader)!=ssize_t(kPackHeader)) {
        fs_close(file);pack_refuse(room,size<kPackPayload || size>limit?kPwSize:kPwRead,size);return;
    }
    const unsigned skin=pu32(head,28);
    if(skin%8u || skin>limit || ((size+31u)&~31u)+skin>limit){fs_close(file);pack_refuse(room,kPwSize,skin);return;}
#else
    const unsigned size=unsigned(fs_total(file));
    unsigned char head[kPackHeader];
    if(size<kPackPayload || size>kPackMaxBytes || fs_read(file,head,kPackHeader)!=ssize_t(kPackHeader)) {
        fs_close(file);pack_refuse(room,size<kPackPayload || size>kPackMaxBytes?kPwSize:kPwRead,size);return;
    }
    const unsigned skin=pu32(head,28);
    if(skin%8u || skin>kPackMaxBytes || ((size+31u)&~31u)+skin>kPackMaxBytes){fs_close(file);pack_refuse(room,kPwSize,skin);return;}
#endif
    const unsigned arena=((size+31u)&~31u)+skin;
    const int heap_before=re4dc_static_heap_free();
    auto* cell=static_cast<unsigned char*>(re4dc_static_alloc(arena+32u));
    if(!cell){fs_close(file);pack_refuse(room,kPwAlloc,arena);return;}
    auto* base=reinterpret_cast<unsigned char*>((reinterpret_cast<std::uintptr_t>(cell)+31u)&~std::uintptr_t(31u));
    std::memcpy(base,head,kPackHeader);
    const ssize_t rest=ssize_t(size-kPackHeader);
    const bool read=fs_read(file,base+kPackHeader,rest)==rest;
    fs_close(file);
    unsigned detail=0;
    PackWhy why=read?pack_validate(base,size,room,detail):kPwRead;
    unsigned generation=0,cells=0,cell_bytes=0,stale=0,refused=0;
    re4dc_room4_state(&generation,&cells,&cell_bytes,&stale,&refused);
    if(why==kPwNone) {
#if RE4DC_GC_ASSET_GATE
        gcasset_registry_capture(0,base,size);
#endif
        // The target preflight of every unique geometry (through a chunk that references it: all do), then the
        // view is staged for every descriptor's skin stream.
        const unsigned nd=pu32(base,kPackHeader+kDesc*16+12),nc=pu32(base,kPackHeader+kRef*16+12),
            ng=pu32(base,kPackHeader+kGeom*16+12),nt=pu32(base,kPackHeader+kTex*16+12),geom_at=pu32(base,kPackHeader+kGeom*16+4);
        unsigned geometries=0;
        for(unsigned g=0;g<ng && why==kPwNone;++g) {
#if RE4DC_NMR_MASK
            // Every geometry from its own arrays (a masked section's run geometries are referenced by no chunk).
            const nmr::Chunk c=registry_geom_view(base+geom_at,base+pu32(base,kPackHeader+kBlob*16+4),g);(void)nc;const unsigned bones=pu32(base,geom_at+g*64+28);
#else
            unsigned ci=0;while(ci<nc && pack_chunks[ci].geometry!=g)++ci;
            const auto& c=pack_chunks[ci];const unsigned bones=pu32(base,geom_at+g*64+28);
#endif
            const re4dc_source::ChunkInput input{{c.positions,c.position_count*8u},{c.normals,c.normal_count*8u},{c.uv,c.uv_bytes},
                {c.stream,c.stream_bytes},{reinterpret_cast<const unsigned char*>(c.weights),c.palette_count*16u},
                c.position_count,c.normal_count,c.palette_count,c.triangles,bones};
            re4dc_source::ChunkProof proof{};
            const auto e=re4dc_source::preflight_chunk(input,proof);
            if(e!=re4dc_source::BlobError::None){why=kPwPreflight;detail=g*256+unsigned(e);}
            ++geometries;
        }
        if(why==kPwNone) {
            registry_view_clear();
            registry=RegistryView{pack_desc,pack_chunks,pack_tex,nd,nc,nt,ng,generation};
#if RE4DC_NMR_MASK
            registry_geom=base+geom_at;registry_blob=base+pu32(base,kPackHeader+kBlob*16+4);
#endif
            registry_skin=base+((size+31u)&~31u);registry_skin_cap=skin;
            for(unsigned d=0;d<nd && why==kPwNone;++d)if(!registry_skin_init(d)){why=kPwSkin;detail=d;}
            if(why==kPwNone && registry_skin_next!=skin){why=kPwSkin;detail=registry_skin_next;}
            if(why!=kPwNone)registry_view_clear();
        }
        if(why==kPwNone) {
            const unsigned nr=pu32(base,kPackHeader+kRole*16+12),nb=pu32(base,kPackHeader+kSBlob*16+12);
            const unsigned early=re4dc_material::life::live_family(2);
            re4dc_material::life::room_rows_publish(pack_roles,nr,pack_blobs,nb,generation);
            pack.cell=cell;pack.base=base;pack.room=room;pack.bytes=size;pack.arena=arena+32u;pack.generation=generation;
            pack.heap_before=unsigned(heap_before);pack.heap_after=unsigned(re4dc_static_heap_free());++pack.publishes;
            re4dc_log("NMRPACK open room=%04x gen=%u bytes=%u skin=%u cell=%u descriptors=%u chunks=%u geometry=%u textures=%u "
                "roles=%u blobs=%u preflight=%u heap4_free=%d->%d room4_cells=%u enemy_archives_before=%u publishes=%u late_retires=%u\n",
                room,generation,size,skin,arena+32u,nd,nc,ng,nt,nr,nb,geometries,heap_before,re4dc_static_heap_free(),cells,early,
                pack.publishes,pack.late_retires);
            return;
        }
    }
#if RE4DC_GC_ASSET_GATE
    gcasset_registry_retire();
#endif
    re4dc_static_free(cell);
    pack_refuse(room,why,detail);
}
#else
// PS2_ASHLEY_ROOMS (RE4DC_NMR_PARTNER): the room package (registry.re4nmr) and the room's partner package
// (partner.re4nmr: Ashley's draw-slot package) are both read and validated before anything is published; the view
// covers both (the partner's records follow the room package's, pack_validate's PackBase). Two heap-4 cells: the room
// package's cell also holds both skin arenas (one contiguous arena, as registry_skin_init allocates), the partner's
// cell its file. A room without registry.re4nmr publishes the partner alone; a partner that fails validation is
// refused alone (the room package still publishes, every partner actor keeps the source path). Retire frees both.
namespace {
struct PackFile { file_t file;unsigned size,skin;unsigned char head[kPackHeader]; };
bool pack_file_open(unsigned room,const char* name,PackFile& f) {
    char path[64];snprintf(path,sizeof(path),"/cd/dc/native/r%x%02x/%s.re4nmr",room>>8,room&255u,name);
    f.file=fs_open(path,O_RDONLY);
    if(f.file==FILEHND_INVALID){re4dc_log("NMRPACK room=%04x none (%s)\n",room,path);return false;}
    ++pack.opens;
    f.size=unsigned(fs_total(f.file));
    const unsigned limit=pack_room_max(room);
    if(f.size<kPackPayload || f.size>limit || fs_read(f.file,f.head,kPackHeader)!=ssize_t(kPackHeader)) {
        fs_close(f.file);pack_refuse(room,f.size<kPackPayload || f.size>limit?kPwSize:kPwRead,f.size);return false;
    }
    f.skin=pu32(f.head,28);
    if(f.skin%8u || f.skin>limit || ((f.size+31u)&~31u)+f.skin>limit){fs_close(f.file);pack_refuse(room,kPwSize,f.skin);return false;}
    return true;
}
bool pack_file_read(PackFile& f,unsigned char* base) {
    std::memcpy(base,f.head,kPackHeader);
    const ssize_t rest=ssize_t(f.size-kPackHeader);
    const bool ok=fs_read(f.file,base+kPackHeader,rest)==rest;
    fs_close(f.file);return ok;
}
inline unsigned pack_count(const unsigned char* base,unsigned k) {return pu32(base,kPackHeader+k*16+12);}
// The target preflight of every geometry of one package (geometry views from its own header table and blob).
PackWhy pack_preflight(const unsigned char* base,unsigned& detail,unsigned& geometries) {
    const unsigned ng=pack_count(base,kGeom),geom_at=pu32(base,kPackHeader+kGeom*16+4),blob_at=pu32(base,kPackHeader+kBlob*16+4);
    for(unsigned g=0;g<ng;++g) {
        const nmr::Chunk c=registry_geom_view(base+geom_at,base+blob_at,g);const unsigned bones=pu32(base,geom_at+g*64+28);
        const re4dc_source::ChunkInput input{{c.positions,c.position_count*8u},{c.normals,c.normal_count*8u},{c.uv,c.uv_bytes},
            {c.stream,c.stream_bytes},{reinterpret_cast<const unsigned char*>(c.weights),c.palette_count*16u},
            c.position_count,c.normal_count,c.palette_count,c.triangles,bones};
        re4dc_source::ChunkProof proof{};
        const auto e=re4dc_source::preflight_chunk(input,proof);
        if(e!=re4dc_source::BlobError::None){detail=g*256+unsigned(e);return kPwPreflight;}
        ++geometries;
    }
    return kPwNone;
}
}

extern "C" void re4dc_registry_room_enter(unsigned room) {
    if(pack.cell){++pack.late_retires;re4dc_registry_room_leave();}
    PackFile a{},b{};
    bool has_a=pack_file_open(room,"registry",a);
    bool has_b=pack_file_open(room,"partner",b);
    if(!has_a && !has_b)return;
    if(!has_a){a=b;has_a=true;has_b=false;}  // the partner alone is the room's package
    const unsigned skin_all=a.skin+(has_b?b.skin:0u);
    const unsigned arena=((a.size+31u)&~31u)+skin_all;
    const int heap_before=re4dc_static_heap_free();
    auto* cell=static_cast<unsigned char*>(re4dc_static_alloc(arena+32u));
    if(!cell){fs_close(a.file);if(has_b)fs_close(b.file);pack_refuse(room,kPwAlloc,arena);return;}
    auto* base=reinterpret_cast<unsigned char*>((reinterpret_cast<std::uintptr_t>(cell)+31u)&~std::uintptr_t(31u));
    unsigned detail=0;
    PackWhy why=pack_file_read(a,base)?pack_validate(base,a.size,room,detail):kPwRead;
    if(why!=kPwNone){if(has_b)fs_close(b.file);re4dc_static_free(cell);pack_refuse(room,why,detail);return;}
    const PackBase pb{pack_count(base,kDesc),pack_count(base,kRef),pack_count(base,kGeom),pack_count(base,kTex),
        pack_count(base,kFModel),pack_count(base,kRole),pack_count(base,kSBlob)};
    unsigned char* cell2=nullptr;unsigned char* base2=nullptr;unsigned arena2=0;
    if(has_b) {
        arena2=(b.size+31u)&~31u;
        cell2=static_cast<unsigned char*>(re4dc_static_alloc(arena2+32u));
        PackWhy w2=kPwAlloc;unsigned d2=arena2;
        if(cell2) {
            base2=reinterpret_cast<unsigned char*>((reinterpret_cast<std::uintptr_t>(cell2)+31u)&~std::uintptr_t(31u));
            w2=pack_file_read(b,base2)?pack_validate(base2,b.size,room,d2,pb):kPwRead;
        } else fs_close(b.file);
        if(w2!=kPwNone) {
            re4dc_log("NMRPACK partner refuse room=%04x why=%s detail=%u: the partner's actors keep the source path\n",room,
                kPackWhy[w2<kPwCount?w2:0],d2);
            ++pack.refusals;
            if(cell2)re4dc_static_free(cell2);
            cell2=nullptr;base2=nullptr;arena2=0;has_b=false;
        }
    }
    const unsigned skin_used=a.skin+(has_b?b.skin:0u);
    unsigned generation=0,cells=0,cell_bytes=0,stale=0,refused=0;
    re4dc_room4_state(&generation,&cells,&cell_bytes,&stale,&refused);
    unsigned geometries=0;
#if RE4DC_GC_ASSET_GATE
    gcasset_registry_capture(0,base,a.size);
    if(has_b)gcasset_registry_capture(1,base2,b.size);
#endif
    why=pack_preflight(base,detail,geometries);
    if(why==kPwNone && has_b){why=pack_preflight(base2,detail,geometries);if(why!=kPwNone)detail+=0x10000u;}
    const unsigned nd=pb.desc+(has_b?pack_count(base2,kDesc):0u),nc=pb.ref+(has_b?pack_count(base2,kRef):0u),
        ng=pb.geom+(has_b?pack_count(base2,kGeom):0u),nt=pb.tex+(has_b?pack_count(base2,kTex):0u),
        nr=pb.role+(has_b?pack_count(base2,kRole):0u),nb=pb.blob+(has_b?pack_count(base2,kSBlob):0u);
    if(why==kPwNone) {
        registry_view_clear();
        registry=RegistryView{pack_desc,pack_chunks,pack_tex,nd,nc,nt,ng,generation};
#if RE4DC_NMR_MASK
        registry_geom=base+pu32(base,kPackHeader+kGeom*16+4);registry_blob=base+pu32(base,kPackHeader+kBlob*16+4);
        if(has_b) {
            registry_geom2=base2+pu32(base2,kPackHeader+kGeom*16+4);registry_blob2=base2+pu32(base2,kPackHeader+kBlob*16+4);
            registry_geom_base2=pb.geom;
        }
#endif
        registry_skin=base+((a.size+31u)&~31u);registry_skin_cap=skin_used;
        for(unsigned d=0;d<nd && why==kPwNone;++d)if(!registry_skin_init(d)){why=kPwSkin;detail=d;}
        if(why==kPwNone && registry_skin_next!=skin_used){why=kPwSkin;detail=registry_skin_next;}
        if(why!=kPwNone)registry_view_clear();
    }
    if(why==kPwNone) {
        const unsigned early=re4dc_material::life::live_family(2);
        re4dc_material::life::room_rows_publish(pack_roles,nr,pack_blobs,nb,generation);
        pack.cell=cell;pack.base=base;pack.room=room;pack.bytes=a.size;pack.arena=arena+32u;pack.generation=generation;
        pack.cell2=cell2;pack.arena2=cell2?arena2+32u:0u;pack.partners+=has_b?1u:0u;
        pack.heap_before=unsigned(heap_before);pack.heap_after=unsigned(re4dc_static_heap_free());++pack.publishes;
        re4dc_log("NMRPACK open room=%04x gen=%u bytes=%u skin=%u cell=%u descriptors=%u chunks=%u geometry=%u textures=%u "
            "roles=%u blobs=%u preflight=%u heap4_free=%d->%d room4_cells=%u enemy_archives_before=%u publishes=%u late_retires=%u\n",
            room,generation,a.size,skin_used,arena+32u,nd,nc,ng,nt,nr,nb,geometries,heap_before,re4dc_static_heap_free(),cells,early,
            pack.publishes,pack.late_retires);
        if(has_b)re4dc_log("NMRPACK partner room=%04x bytes=%u skin=%u cell=%u descriptors=%u chunks=%u geometry=%u textures=%u "
            "base=%u/%u/%u/%u partners=%u\n",room,b.size,b.skin,arena2+32u,nd-pb.desc,nc-pb.ref,ng-pb.geom,nt-pb.tex,pb.desc,pb.ref,
            pb.geom,pb.tex,pack.partners);
        return;
    }
#if RE4DC_GC_ASSET_GATE
    gcasset_registry_retire();
#endif
    if(cell2)re4dc_static_free(cell2);
    re4dc_static_free(cell);
    pack_refuse(room,why,detail);
}
#endif
