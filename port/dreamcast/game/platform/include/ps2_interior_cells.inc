// PS2_INTERIOR_CELLS=1 (game30.mk, lane interior-cells26 2026-10-26; included by ps2_interior_cell.inc inside
// native_static.cpp namespace pc). The interior cell becomes per room and data driven: no package constants are compiled
// in. The open room's package reads /cd/dc/native/rXXX/interior.cell (PCL2, tools/d367/ps2world/interior/cell_file.py
// pack2), which carries its own room, package mesh CRC / sidecar CRC / mesh bytes, near margin, counts and one outer box
// per house (r101: houses and church). The cell is adopted only when every identity word equals the open package's; a
// missing file, a stale one or a short heap 4 leaves the cull off for that room (drawn as with the knob off).
// Kept out of native_static.cpp so the knob-off object is byte-identical (no line moves there: only macro hooks on
// existing lines, which expand to nothing with the knob off; see ps2_interior_cell.inc).
//
// PCL2 layout (little endian): header 64 B 'PCL2', room, mesh_crc, sidecar_crc, mesh_bytes, cell_count, portal_count,
// file_bytes, near_max (f32), house_count, 0 x 6; houses house_count x 32 B: outer lo xyz, hi xyz (f32), first cell,
// cell count (u16), 0 (u32); cells (pc::Cell) and portals (pc::Portal) as PCL1. Each house's cells are one run.
unsigned kPcRoom=0,kPcCellCount=0,kPcPortalCount=0,kPcFileBytes=0;
float kPcNearMax=0,kPcOuter[6]={0,0,0,0,0,0}; // kPcOuter: house 0's box (logs only); the test uses the eye's house
constexpr unsigned kPcMeshCrc=0,kPcSidecarCrc=0,kPcMeshBytes=0; // unused: the file carries the package identity
unsigned live_room=0,live_mesh=0,live_sidecar=0,live_bytes=0;   // the open package (adopt_live)
constexpr unsigned kPcl2Header=64U;
struct House { float outer[6]; std::uint16_t first,count; std::uint32_t pad; };
unsigned kPcHouseCount=0; const House* houses=nullptr;
// The outer box of the house whose run holds this cell (null: none).
inline const float* house_of(int cell){
    for(unsigned k=0;k<kPcHouseCount;++k)
        if(unsigned(cell)>=houses[k].first && unsigned(cell)<unsigned(houses[k].first)+houses[k].count)return houses[k].outer;
    return nullptr;
}
// At the package open: remember the package; the cell file is checked against it by the load that follows.
inline bool adopt_live(unsigned room,unsigned mesh,unsigned sidecar,unsigned bytes){
    live_room=room;live_mesh=mesh;live_sidecar=sidecar;live_bytes=bytes;kPcRoom=0;
    return true;
}
// Reads the room's PCL2 cell into one heap-4 block (file + both states' frustum arrays). D / S: pc::Data / pc::State
// (declared after this file). Returns false (and clears st.ok) on any mismatch.
template<class D,class S> inline bool load_cells(D& data,S& st,S& tst,unsigned frbytes,unsigned maxfr){
    if(data.block)return true;
    if(!st.ok)return false;
    const int before=re4dc_static_heap_free();
    const char* why=nullptr;
    char path[40];
    std::snprintf(path,sizeof(path),"/cd/dc/native/r%03x/interior.cell",live_room&0xfffU);
    const file_t file=fs_open(path,O_RDONLY);
    unsigned char* b=nullptr;
    std::uint32_t w[16]={0};
    if(file==FILEHND_INVALID)why="missing";
    else{
        const unsigned total=unsigned(fs_total(file));
        if(total<kPcl2Header || fs_read(file,w,kPcl2Header)!=ssize_t(kPcl2Header))why="read";
        else if(std::memcmp(w,"PCL2",4))why="magic";
        else if(w[1]!=live_room || w[2]!=live_mesh || w[3]!=live_sidecar || w[4]!=live_bytes)why="package";
        else if(w[7]!=total || w[5]==0 || w[5]>4096U || w[6]>16384U || w[9]==0 || w[9]>64U ||
                total!=kPcl2Header+w[9]*unsigned(sizeof(House))+w[5]*unsigned(sizeof(Cell))+w[6]*unsigned(sizeof(Portal)))why="size";
        else if(!(b=static_cast<unsigned char*>(re4dc_static_alloc(total+2U*frbytes))))why="heap4";
        else if(fs_seek(file,0,SEEK_SET)!=0 || fs_read(file,b,total)!=ssize_t(total))why="read";
        fs_close(file);
    }
    const House* hs=b?reinterpret_cast<const House*>(b+kPcl2Header):nullptr;
    const Cell* cells=b?reinterpret_cast<const Cell*>(b+kPcl2Header+w[9]*sizeof(House)):nullptr;
    for(unsigned i=0;!why && i<w[5];++i)
        if(cells[i].count>maxfr || unsigned(cells[i].first)+cells[i].count>w[6])why="cells";
    for(unsigned k=0;!why && k<w[9];++k)
        if(!hs[k].count || unsigned(hs[k].first)+hs[k].count>w[5])why="houses";
    if(why){
        if(b)re4dc_static_free(b);
        ++data.fails;st.ok=false;kPcRoom=0;kPcHouseCount=0;houses=nullptr;
        re4dc_log("PCCULL cell %s %s: not culling (heap4=%d)\n",path,why,before);
        return false;
    }
    kPcRoom=w[1];kPcCellCount=w[5];kPcPortalCount=w[6];kPcFileBytes=w[7];kPcHouseCount=w[9];houses=hs;
    std::memcpy(&kPcNearMax,&w[8],4);std::memcpy(kPcOuter,hs[0].outer,24);
    data.block=b;data.cells=cells;data.portals=reinterpret_cast<const Portal*>(b+kPcl2Header+w[9]*sizeof(House)+kPcCellCount*sizeof(Cell));
    st.fr=reinterpret_cast<decltype(st.fr)>(b+kPcFileBytes);tst.fr=reinterpret_cast<decltype(st.fr)>(b+kPcFileBytes+frbytes);
    ++data.loads;
    re4dc_log("PCCULL cell %s loaded %u B (+%u B states) houses=%u cells=%u portals=%u heap4=%d->%d loads=%u lends=%u\n",path,
              kPcFileBytes,2U*frbytes,kPcHouseCount,kPcCellCount,kPcPortalCount,before,re4dc_static_heap_free(),data.loads,data.lends);
    return true;
}
// Hooks on existing native_static.cpp lines (empty with the knob off, ps2_interior_cell.inc).
#define PC_STATE_EXTRA const float* outer=nullptr; // the eye's house box
#define PC_PICK_HOUSE(s) {s.outer=house_of(s.cell);if(!s.outer){s.cell=-1;return;}}
#define PC_COPY_EXTRA(s,t) s.outer=t.outer;
#define PC_OUTER_DECL(s) const float* kPcOuter=s.outer;
#define PC_OUTER_RENDER pc::st.outer
#define PC_ADOPT_PRE(r,m,s,b) pc::adopt_live(unsigned(r),unsigned(m),unsigned(s),unsigned(b)) ||
#if RE4DC_GC_ASSET_GATE
#define PC_LOAD_HOOK {if(data.block)return true;re4dc_gcasset::payload_retire(data.asset_proof);\
    if(!load_cells(data,st,trans_state(),kFrBytes,kMaxFr))return false;gcasset_static_invalidate_all();\
    const auto gcasset_digest_=re4dc_gcasset::fingerprint(data.block,kPcFileBytes);\
    re4dc_gcasset::payload_capture_receipt(data.asset_proof,&data,gcasset_digest_,kPcFileBytes);return true;}
#else
#define PC_LOAD_HOOK return load_cells(data,st,trans_state(),kFrBytes,kMaxFr);
#endif
