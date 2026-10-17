// SS_CERT=1 (crowd.mk, default 0; needs ACTOR_TRANSACTION=1 and SUBSCREEN=1): source archive certificates across the
// sub screen memory swap. Included once by actor_lifetime.inc after the record helpers; host-tested by
// tools/d367/swap_park_test.cpp with the real actor_lifetime.inc.
// While the screen is open its 3 MiB window holds sub screen bytes and the room's bytes sit in the backing
// (sscrn_bridge.cpp). Without this, SubScreenExitCore's MemDestroyHeap(12) -> re4dc_actor_forget_range revokes every
// room archive inside the window (first-visit r101: em26.drs), and the restored bytes keep no certificate: archive
// adoption only proves pristine bytes, so the cow draws through the source path for the rest of the room.
// Open (re4dc_subscreen_swap_open, after the backing saved the live spans, before the window is cleared): every live
// Archive overlapping the window leaves the live tables with its Assets, and so does every Info that depends on one
// or whose cModelInfo lies in the window. Nothing can find or prove them while the window holds sub screen data. An
// archive that cannot be parked (a byte in a skipped free cell, a conversion in progress, no park room, serials
// exhausted) is revoked at open instead, as close would have done.
// While open: a forget / data move / info retire wholly inside the window names sub screen memory (heap 12, the
// screen's allocations) and leaves parked records alone; live records are forgotten as before. Any other range, an
// archive retire of the same key, an overlapping adoption, a transient retire or forget_all drops what it reaches.
// Close (after the backing is restored and its hash checked): a parked archive is published again only when the
// restore succeeded, every byte of its extent (also any part outside the window) hashes as at open, no live owner
// uses its key or overlaps it, the room identity rows are those of the open, and fresh serials remain. It gets a new
// owner revision, its Assets new serials and must be current() again; an Info needs its asset and TPL owner back at
// their new serials, info_current() for every role bit it holds (which reads pData / TPL from its cModelInfo) and no
// live record of its own. Everything else is dropped and keeps the source path, as before SS_CERT. The global tables are
// never copied back wholesale.
extern "C" void re4dc_log(const char*,...);
namespace re4dc_material { namespace life {
#if RE4DC_ACTOR_GANADO_PS2_STUMP
// ACTOR_GANADO_PS2_STUMP (lane stump17): a Ganado archive also admits its stump / hand-pose BINs (up to 8 more assets:
// r100's em12 archive 12 -> 20), so the park keeps the room for one such archive. At 16 the r100 s20 movie window
// revoked it and its Ganados drew the source path for the rest of the room (h2: 2,753 GC rows).
constexpr unsigned kParkArchives=4,kParkAssets=24,kParkInfos=32,kParkNone=~0u;
#else
constexpr unsigned kParkArchives=4,kParkAssets=16,kParkInfos=32,kParkNone=~0u;
#endif
struct ParkArchive { Archive o;unsigned slot,hash; };                         // slot: archives[] index at open
#if RE4DC_NMR_PARK_UNRELOCATED
// PS2_CAST_* (native_model_registry.mk, lane ps2cast2): was_current = the asset's current() at open. An archive BIN that
// calcModelAddr has not relocated yet (no instance of it exists: r102's em18 is read ahead, the shop opens before
// setEm(0x4C) creates the merchant) is not current() at open and cannot be at close either; the bytes hash proves it is
// unchanged, so it is republished as it was instead of revoking the whole archive (which left the merchant on the source
// path for the rest of the room). An asset that was current at open must still be current at close.
struct ParkAsset { Asset a;unsigned slot,owner,new_slot,new_serial,was_current; };
#else
struct ParkAsset { Asset a;unsigned slot,owner,new_slot,new_serial; };       // owner: park_archives index
#endif
struct ParkInfo { Info i;unsigned asset_owner,tpl_owner; };                  // park_archives index or kParkNone
using ParkSaved=int(*)(const void*,unsigned);
struct Park {
    std::uintptr_t lo,hi;bool open;unsigned narchive,nasset,ninfo;
    unsigned rows_generation,rows_roles,rows_blobs;
    unsigned opens,nested,parked_archives,parked_infos,revoked_at_open,temporary,dropped_archives,dropped_infos,
             published_archives,published_assets,published_infos;
};
ParkArchive park_archives[kParkArchives];ParkAsset park_assets[kParkAssets];ParkInfo park_infos[kParkInfos];Park park{};
unsigned park_hash(const void* p,unsigned n) {
    const auto* b=static_cast<const unsigned char*>(p);unsigned h=2166136261u,k=0;
    for(;k+4<=n;k+=4)h=(h^u32at(b,k))*16777619u;
    for(;k<n;++k)h=(h^b[k])*16777619u;
    return h^n;
}
bool park_inside(const void* p,unsigned n) {
    const auto a=reinterpret_cast<std::uintptr_t>(p);
    return a>=park.lo && a<=park.hi && n<=park.hi-a;
}
void park_drop_info(ParkInfo& pi) {if(pi.i.info){pi.i={};++park.dropped_infos;}}
void park_drop_archive(unsigned k) {
    if(!park_archives[k].o.key)return;
    park_archives[k].o={};++park.dropped_archives;
    for(unsigned j=0;j<park.nasset;++j)if(park_assets[j].owner==k)park_assets[j].a={};
    for(unsigned j=0;j<park.ninfo;++j)if(park_infos[j].asset_owner==k || park_infos[j].tpl_owner==k)park_drop_info(park_infos[j]);
}
void park_drop_all() {
    for(unsigned k=0;k<park.narchive;++k)park_drop_archive(k);
    for(unsigned j=0;j<park.ninfo;++j)park_drop_info(park_infos[j]);
}
// forget_range / data_move: a range wholly inside the swapped window is sub screen memory.
void park_forget(const void* p,unsigned n) {
    if(!park.open || !p || !n)return;
    if(park_inside(p,n)){++park.temporary;return;}
    for(unsigned k=0;k<park.narchive;++k)if(park_archives[k].o.key && overlap(p,n,park_archives[k].o.base,park_archives[k].o.bytes))park_drop_archive(k);
    for(unsigned j=0;j<park.ninfo;++j)if(park_infos[j].i.info && overlap(p,n,park_infos[j].i.info,sizeof(cModelInfo)))park_drop_info(park_infos[j]);
}
void park_info_retire(const void* p) {
    if(!park.open || !p)return;
    if(park_inside(p,sizeof(cModelInfo))){++park.temporary;return;}
    for(unsigned j=0;j<park.ninfo;++j)if(park_infos[j].i.info==p)park_drop_info(park_infos[j]);
}
void park_drop_key(const void* key) {
    if(park.open && key)for(unsigned k=0;k<park.narchive;++k)if(park_archives[k].o.key==key)park_drop_archive(k);
}
void park_drop_overlap(const void* base,unsigned bytes) {
    if(park.open)for(unsigned k=0;k<park.narchive;++k)
        if(park_archives[k].o.key && overlap(base,bytes,park_archives[k].o.base,park_archives[k].o.bytes))park_drop_archive(k);
}
void park_drop_family(unsigned family) {
    if(park.open)for(unsigned k=0;k<park.narchive;++k)if(park_archives[k].o.key && park_archives[k].o.family==family)park_drop_archive(k);
}
void park_close(bool restored);
void park_open(const void* window,unsigned bytes,ParkSaved saved) {
    if(park.open){++park.nested;park_close(false);}
    park.lo=reinterpret_cast<std::uintptr_t>(window);park.hi=park.lo+bytes;park.open=true;
    park.narchive=park.nasset=park.ninfo=0;++park.opens;
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
    park.rows_generation=room_rows.generation;park.rows_roles=room_rows.role_count;park.rows_blobs=room_rows.blob_count;
#endif
    // Pass 1: which overlapping archives can be parked; the others are revoked now, with the tables intact.
    bool take[kArchives]{};unsigned na=0,nb=0,revoked=0;
    for(unsigned k=0;k<kArchives;++k) {
        const auto& o=archives[k];
        if(!o.key || !overlap(window,bytes,o.base,o.bytes))continue;
        unsigned need=0;bool ok=!exhausted && na<kParkArchives && saved(o.base,o.bytes);
        for(const auto& a:assets)if(a.data && a.archive==k){++need;if(a.pending)ok=false;}
        if(ok && nb+need<=kParkAssets){take[k]=true;++na;nb+=need;}
    }
    for(unsigned k=0;k<kArchives;++k)if(archives[k].key && !take[k] && overlap(window,bytes,archives[k].base,archives[k].bytes)){revoke(k);++revoked;}
    // Pass 2: park the rest with their assets (each keeps its open-time index to rebind its infos).
    for(unsigned k=0;k<kArchives;++k)if(take[k]) {
        const unsigned pk=park.narchive++;
        park_archives[pk]={archives[k],k,park_hash(archives[k].base,archives[k].bytes)};
#if RE4DC_NMR_PARK_UNRELOCATED
        for(unsigned j=0;j<kAssets;++j)if(assets[j].data && assets[j].archive==k) {
            auto& pa=park_assets[park.nasset++];pa={assets[j],j,pk,kParkNone,0};pa.was_current=current(assets[j])?1u:0u;assets[j]={};
        }
#else
        for(unsigned j=0;j<kAssets;++j)if(assets[j].data && assets[j].archive==k){park_assets[park.nasset++]={assets[j],j,pk,kParkNone,0};assets[j]={};}
#endif
        archives[k]={};
    }
    // Infos naming a parked asset / TPL owner, or whose cModelInfo is in the window (its bytes leave with it).
    for(auto& i:infos_live)if(i.info) {
        unsigned ao=kParkNone,to=kParkNone;
        for(unsigned j=0;j<park.nasset;++j)if(park_assets[j].slot==i.asset && park_assets[j].a.serial==i.asset_serial)ao=park_assets[j].owner;
        for(unsigned k=0;k<park.narchive;++k)if(park_archives[k].slot==i.tpl_owner && park_archives[k].o.revision==i.tpl_revision)to=k;
        const bool in_window=overlap(window,bytes,i.info,sizeof(cModelInfo));
        if(ao==kParkNone && to==kParkNone && !in_window)continue;
        if(park.ninfo<kParkInfos && (!in_window || saved(i.info,sizeof(cModelInfo))))park_infos[park.ninfo++]={i,ao,to};
        else ++park.dropped_infos;
        i={};
    }
    park.parked_archives+=park.narchive;park.parked_infos+=park.ninfo;park.revoked_at_open+=revoked;
    changed();
    re4dc_log("SSCERT park window=%p+%x archives=%u assets=%u infos=%u revoked=%u nested=%u exhausted=%u\n",window,bytes,
              park.narchive,park.nasset,park.ninfo,revoked,park.nested,unsigned(exhausted));
}
void park_close(bool restored) {
    if(!park.open)return;
    bool same_rows=true;
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
    same_rows=room_rows.generation==park.rows_generation && room_rows.role_count==park.rows_roles && room_rows.blob_count==park.rows_blobs;
#endif
    unsigned slot_of[kParkArchives],rev_of[kParkArchives],pa=0,pb=0,pi=0;
    // Archives: the restored bytes are those of the open, the owner is free, then a new revision.
    for(unsigned k=0;k<park.narchive;++k) {
        auto& p=park_archives[k];slot_of[k]=kParkNone;
        if(!p.o.key)continue;
        bool ok=restored && same_rows && !exhausted && park_hash(p.o.base,p.o.bytes)==p.hash;
        unsigned free=kArchives;
        for(unsigned s=0;s<kArchives && ok;++s) {
            if(!archives[s].key){if(free==kArchives)free=s;continue;}
            if(archives[s].key==p.o.key || overlap(archives[s].base,archives[s].bytes,p.o.base,p.o.bytes))ok=false;
        }
        const unsigned rev=ok && free<kArchives?next():0u;
        if(!rev){park_drop_archive(k);continue;}
        archives[free]=p.o;archives[free].revision=rev;slot_of[k]=free;rev_of[k]=rev;
    }
    // Assets: new serials under the new revision; each must be current() from the restored bytes.
    for(unsigned j=0;j<park.nasset;++j) {
        auto& a=park_assets[j];const unsigned k=a.owner;
        if(!a.a.data || slot_of[k]==kParkNone)continue;
        unsigned s=0;while(s<kAssets && assets[s].data)++s;
        const unsigned serial=s<kAssets?next():0u;
        if(serial) {
            assets[s]=a.a;assets[s].archive=slot_of[k];assets[s].owner_revision=rev_of[k];assets[s].serial=serial;assets[s].pending=0;
#if RE4DC_NMR_PARK_UNRELOCATED
            if(current(assets[s]) || !a.was_current){a.new_slot=s;a.new_serial=serial;continue;}
#else
            if(current(assets[s])){a.new_slot=s;a.new_serial=serial;continue;}
#endif
        }
        revoke(slot_of[k]);slot_of[k]=kParkNone;park_drop_archive(k);
    }
    for(unsigned k=0;k<park.narchive;++k)if(slot_of[k]!=kParkNone)++pa;
    for(unsigned j=0;j<park.nasset;++j)if(park_assets[j].a.data && slot_of[park_assets[j].owner]!=kParkNone)++pb;
    // Infos: rebound to the new indices / serials, or to the live owners they had when those are unchanged.
    for(unsigned j=0;j<park.ninfo;++j) {
        auto& p=park_infos[j];if(!p.i.info)continue;
        Info i=p.i;bool ok=restored && same_rows && !find_info(i.info);
        if(ok && p.asset_owner!=kParkNone) {
            ok=false;
            for(unsigned m=0;m<park.nasset;++m) {
                const auto& a=park_assets[m];
                if(a.a.data && a.owner==p.asset_owner && a.slot==i.asset && a.a.serial==i.asset_serial && slot_of[a.owner]!=kParkNone)
                    {i.asset=a.new_slot;i.asset_serial=a.new_serial;ok=true;break;}
            }
        } else if(ok)ok=i.asset<kAssets && assets[i.asset].data && assets[i.asset].serial==i.asset_serial;
        if(ok && p.tpl_owner!=kParkNone) {
            ok=slot_of[p.tpl_owner]!=kParkNone;
            if(ok){i.tpl_owner=slot_of[p.tpl_owner];i.tpl_revision=rev_of[p.tpl_owner];}
        } else if(ok)ok=i.tpl_owner<kArchives && archives[i.tpl_owner].key && archives[i.tpl_owner].revision==i.tpl_revision;
        bool any=false;
        for(unsigned r=0;r<kRoleMaskBits && ok;++r)if(i.roles[r/32]&(1u<<(r%32))){any=true;ok=info_current(i,r);}
        Info* slot=nullptr;
        if(ok && any)for(auto& s:infos_live)if(!s.info){slot=&s;break;}
        if(!slot){park_drop_info(p);continue;}
        *slot=i;++pi;
    }
    park.published_archives+=pa;park.published_assets+=pb;park.published_infos+=pi;
    re4dc_log("SSCERT unpark restored=%u rows=%u archives=%u/%u assets=%u/%u infos=%u/%u dropped=%u/%u temporary=%u serial=%u exhausted=%u\n",
              unsigned(restored),unsigned(same_rows),pa,park.narchive,pb,park.nasset,pi,park.ninfo,park.dropped_archives,
              park.dropped_infos,park.temporary,serial,unsigned(exhausted));
    for(auto& p:park_archives)p={};for(auto& a:park_assets)a={};for(auto& p:park_infos)p={};
    park.open=false;park.lo=park.hi=0;park.narchive=park.nasset=park.ninfo=0;
    changed();
}
} }
// sscrn_bridge.cpp: open after the backing saved the window (bytes intact), close after it restored and hashed it.
// saved(p,n): every byte of [p,p+n) inside the window lies in a saved span (none in a skipped free cell).
extern "C" void re4dc_actor_swap_park(const void* window,unsigned bytes,int(*saved)(const void*,unsigned)) {
    re4dc_material::life::park_open(window,bytes,saved);
}
extern "C" void re4dc_actor_swap_unpark(int restored) {re4dc_material::life::park_close(restored!=0);}
