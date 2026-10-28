// WORLD_PORTAL29: PCL2/WP29 uses pc's existing allocation, movie lending and
// retirement. Legacy PCL1/PCL2 cells cannot become new proof authority.
unsigned kPcRoom=0,kPcCellCount=0,kPcPortalCount=0,kPcFileBytes=0;
float kPcNearMax=0,kPcOuter[6]{};
constexpr unsigned kPcMeshCrc=0,kPcSidecarCrc=0,kPcMeshBytes=0;
unsigned live_room=0,live_mesh=0,live_sidecar=0,live_bytes=0;
struct House { float outer[6]; std::uint16_t first,count; std::uint32_t pad; };
unsigned kPcHouseCount=0;const House* houses=nullptr;
const re4dc::portal29::Witness* wp29_witnesses=nullptr;
unsigned wp29_count=0,wp29_generation=0;
extern "C" void* re4dc_world_portal29_alloc(unsigned);
inline void wp29_clear(){
    wp29_witnesses=nullptr;wp29_count=0;houses=nullptr;kPcHouseCount=0;
    if(!++wp29_generation)++wp29_generation;
}
inline const float* house_of(int cell){
    for(unsigned k=0;k<kPcHouseCount;++k)
        if(unsigned(cell)>=houses[k].first && unsigned(cell)<unsigned(houses[k].first)+houses[k].count)return houses[k].outer;
    return nullptr;
}
inline bool adopt_live(unsigned room,unsigned mesh,unsigned sidecar,unsigned bytes){
    live_room=room;live_mesh=mesh;live_sidecar=sidecar;live_bytes=bytes;kPcRoom=0;return true;
}
template<class D,class S> inline bool load_cells(D& data,S& st,S& tst,unsigned frbytes,unsigned){
    if(data.block)return true;
    if(!st.ok)return false;
    wp29_clear();
    const int before=re4dc_static_heap_free();const char* why=nullptr;
    char path[40];::snprintf(path,sizeof(path),"/cd/dc/native/r%03x/interior.cell",live_room&0xfffU);
    const file_t file=fs_open(path,O_RDONLY);
    unsigned char* b=nullptr;unsigned total=0;re4dc::portal29::Layout h;
    if(file==FILEHND_INVALID)why="missing";
    else {
        total=unsigned(fs_total(file));
        // Count limits in layout cap valid files below this bound; reject
        // untrusted allocation sizes before reading any generated geometry.
        if(total<64U || total>524288U || (total&3U))why="size";
        else if(!(b=static_cast<unsigned char*>(re4dc_world_portal29_alloc(total+2U*frbytes))))why="heap4";
        else if(fs_read(file,b,total)!=ssize_t(total))why="read";
        else if(!re4dc::portal29::layout(b,total,h))why="WP29 layout/proof";
        else if(h.room!=live_room || h.mesh_crc!=live_mesh || h.policy_crc!=live_sidecar || h.mesh_bytes!=live_bytes)why="package";
        fs_close(file);
    }
    if(why){
        if(b)re4dc_static_free(b);
        ++data.fails;st.ok=false;kPcRoom=0;
        re4dc_log("WP29 cell %s %s: draw all (heap4=%d)\n",path,why,before);return false;
    }
    kPcRoom=h.room;kPcCellCount=h.cells;kPcPortalCount=h.portals;kPcFileBytes=h.bytes;
    kPcNearMax=h.near_max;kPcHouseCount=h.houses;houses=reinterpret_cast<const House*>(b+64);
    std::memcpy(kPcOuter,houses[0].outer,24);
    data.block=b;data.cells=reinterpret_cast<const Cell*>(b+64U+32U*h.houses);
    data.portals=reinterpret_cast<const Portal*>(b+64U+32U*h.houses+28U*h.cells);
    st.fr=reinterpret_cast<decltype(st.fr)>(b+total);tst.fr=reinterpret_cast<decltype(st.fr)>(b+total+frbytes);
    wp29_witnesses=reinterpret_cast<const re4dc::portal29::Witness*>(b+h.proof_offset);wp29_count=h.witnesses;
    ++data.loads;
    re4dc_log("WP29 cell %s loaded %u B (+%u B states) houses=%u cells=%u portals=%u witnesses=%u heap4=%d->%d\n",
              path,total,2U*frbytes,h.houses,h.cells,h.portals,h.witnesses,before,re4dc_static_heap_free());
    return true;
}
#define PC_STATE_EXTRA const float* outer=nullptr;
#define PC_PICK_HOUSE(s) {s.outer=house_of(s.cell);if(!s.outer){s.cell=-1;return;}}
#define PC_COPY_EXTRA(s,t) s.outer=t.outer;
#define PC_OUTER_DECL(s) const float* kPcOuter=s.outer;
#define PC_OUTER_RENDER pc::st.outer
#define PC_ADOPT_PRE(r,m,s,b) pc::adopt_live(unsigned(r),unsigned(m),unsigned(s),unsigned(b)) ||
#if RE4DC_GC_ASSET_GATE
#define PC_LOAD_HOOK {if(data.block)return true;re4dc_gcasset::payload_retire(data.asset_proof);\
    if(!load_cells(data,st,trans_state(),kFrBytes,kMaxFr))return false;gcasset_static_invalidate_all();\
    const auto wp29_digest_=re4dc_gcasset::fingerprint(data.block,kPcFileBytes);\
    re4dc_gcasset::payload_capture_receipt(data.asset_proof,&data,wp29_digest_,kPcFileBytes);return true;}
#else
#define PC_LOAD_HOOK return load_cells(data,st,trans_state(),kFrBytes,kMaxFr);
#endif
