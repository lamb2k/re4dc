// DOOR_PREFETCH=1 (Makefile; lane doorprefetch16, 2026-10-16; default 0: this file is not compiled with the knob off).
// Included by native_ui.cpp (file scope, after the texture cache, the preload pass and VRAM_ROOM_LOG).
//
// A room change has two waits in which the drive is idle (DOOR-PAUSE-CH1-20261016.md):
//   window 1, gameDoordemo: after the door press the game waits for every sound to fade (SndStatDisp, ~0.5 s on 11 of
//     13 chapter 1 doors). The old room is still loaded (heap 4, KOS, its textures); the door's next room is known.
//   window 2, gameRoomInit: SndRoomBgmLoad waits for the old music to let go of its slot (0.9..1.3 s on the 5 music
//     doors, ~0.1..0.2 s on others). The new room's heap 4 is in place; its enemy archives and the room-entry texture
//     preload come only after the wait (ScenarioRoomInit).
// During both, this loads the room's KNOWN textures into VRAM, a time slice per frame (DOOR_PREFETCH_STEP_MS):
//   - its PS2 world's part textures (dc/native/r<room>/ps2-world.r4pw, the R4PW sidecar's part table: crc, fnv, size;
//     PS2_PRELOAD_LEAN's room pass picks the same keys from the open package);
//   - its resident list (dc/resident.bin records of the room: ROOM_RESIDENT, lane resident16's lists; core keys, room
//     0, are not listed: CORE_PIN keeps them).
// No main RAM: the lists are read in 2 KB pieces into a stack buffer, the pictures go straight to VRAM through the
// cache's own load() (tex.pak, the same packages and formats as the preload pass). The room-entry preload pass that
// follows finds them resident and does not read them again; nothing else changes:
//   - the regular preload pass keeps its timing and picks (window 2 defers it until the wait ends, as before the
//     prefetch it ran after the wait); enemy textures still come with their archives;
//   - picks are budgeted like the preload pass (slots, bytes, the reserve) and stop at the KOS floor (RETIRE_KOS_FLOOR,
//     else 64 KiB): KOS above it is what the room change keeps for the next room's start;
//   - evictions go through load()'s LRU (oldest first: the old room's textures; the window's own loads are newest);
//   - window 1 does not touch the door freeze picture (no release, nothing drawn): only uploads in idle frame time;
//   - VRAM_ROOM_LOG: window 1's uploads are moved out of the old room's visit (they are not gameplay uploads of that
//     room; vram_gate.py would fail them in a room with a resident list); window 2's count as the new room's preload.
// The game task only sets requests (re4dc_dpf_begin / re4dc_dpf_end); the main loop's frame start opens, steps and
// closes the window (re4dc_dpf_frame). Window 2's busy loop sleeps one frame per check (re4dc_dpf_yield), so the main
// loop runs while the old music fades; base builds ran no main loop frame there (the frames are not presented anyway:
// the door picture is released for the pending preload and held, DOOR_FREEZE's door_held).
// Log: "DOORPF: open window=W room=R frame=F" and at the close "DOORPF: close window=W room=R ..." (counts, bytes, us).
#if !RE4DC_TEX_RESIDENT || !RE4DC_UI_VRAM || !RE4DC_TEX_META_EVICT || !RE4DC_TEX_PACK
#error "DOOR_PREFETCH=1 needs TEX_RESIDENT, UI_VRAM, TEX_META_EVICT and TEX_PACK"
#endif
namespace {
// Load-time code, a few calls per room change: kept small and out of the frame path (image size: heap 4 pays it).
#define RE4DC_DPF_FN __attribute__((noinline,cold,optimize("Os")))
#ifndef RE4DC_DOOR_PREFETCH_STEP_MS
#define RE4DC_DOOR_PREFETCH_STEP_MS 28
#endif
constexpr unsigned long long kDpfStepUs=RE4DC_DOOR_PREFETCH_STEP_MS*1000ULL;
#if defined(RE4DC_DOOR_PREFETCH_KOS_FLOOR) && RE4DC_DOOR_PREFETCH_KOS_FLOOR
constexpr unsigned kDpfKosFloor=RE4DC_DOOR_PREFETCH_KOS_FLOOR;
#elif defined(RE4DC_RETIRE_KOS_FLOOR) && RE4DC_RETIRE_KOS_FLOOR
constexpr unsigned kDpfKosFloor=RE4DC_RETIRE_KOS_FLOOR;
#else
constexpr unsigned kDpfKosFloor=65536U;
#endif
// Requests from the game task (single words; read at the main loop's frame start).
volatile unsigned dpf_req,dpf_req_room,dpf_end_req,dpf_task_window;
volatile unsigned dpf_w2_idle;
volatile unsigned dpf_se_ready;  // window 1: SndStatDisp saw the door sound read complete (the queue is free again)   // main loop: window 2 has nothing left to load (its busy loop spins again, as before)
// Main loop state.
unsigned dpf_open,dpf_room,dpf_n,dpf_next,dpf_frame0,dpf_vroom;
bool dpf_built;
struct DpfStats { unsigned parts,keys,resident,picked,loaded,failed,kb,steps,reads,evicted,evicted_kb,kos_closed; unsigned long long us,build_us; const char* stop; };
DpfStats dpf;

// The window's budget (as the preload pass) and its picks so far.
struct DpfPick { unsigned limit,byte_limit,n,resident,bytes; };
// One key of the room's lists: resident (touched: newest in the LRU order, counted once per frame) or a new pick.
RE4DC_DPF_FN void dpf_pick(DpfPick& k,unsigned crc,unsigned fnv,unsigned w,unsigned h,unsigned fmt){
    if(!w || !h || w>1024 || h>1024)return;
    const Key key{crc,fnv};
    for(auto& e:entries)if(e.valid && e.key==key){
        if(e.frame!=frame){e.frame=frame;++k.resident;k.bytes+=e.package.vram_bytes();}
        return;
    }
    for(const auto& m:missing_keys)if((m.crc|m.fnv) && m==key)return;
    for(unsigned i=0;i<k.n;++i)if(preload_picks[i].key==key)return;
    ++dpf.keys;
    const unsigned least=preload_least(w,h);
    if(k.n+k.resident>=k.limit || k.bytes+least>k.byte_limit)return;
    preload_picks[k.n++]={key,(unsigned short)w,(unsigned short)h,(unsigned short)fmt};k.bytes+=least;
}

// Reads [first, need) of `path` in 2 KB pieces (sector-aligned offsets, a 32-byte aligned stack buffer: one DMA read
// each, like texpack's sector reads) and picks each 16-byte record: resident.bin rows of the room (res) or R4PW parts.
RE4DC_DPF_FN void dpf_records(DpfPick& k,const char* path,unsigned first,unsigned need,bool res){
    alignas(32) unsigned char buf[2048];
    for(unsigned off=first&~2047U;off<need;off+=sizeof(buf)){
        const unsigned len=need-off<sizeof(buf)?need-off:unsigned(sizeof(buf));
        ++dpf.reads;
        if(re4dc::texture::read_file_range(path,off,buf,len,nullptr)!=re4dc::texture::RangeRead::ok)return;
        for(unsigned i=off<first?first-off:0;i+16<=len;i+=16){
            const unsigned char* p=buf+i;std::uint16_t r[4];std::uint32_t c[2];
            if(res){std::memcpy(r,p,8);std::memcpy(c,p+8,8);if(r[0] && r[0]==dpf_room)dpf_pick(k,c[0],c[1],r[1],r[2],r[3]);}
            else{std::memcpy(c,p,8);std::memcpy(r,p+8,4);dpf_pick(k,c[0],c[1],r[0],r[1],5);}
        }
    }
}

RE4DC_DPF_FN void dpf_build(){
    dpf_built=true;
    const unsigned long long t0=timer_us_gettime64();
    const unsigned budget=vram_budget,reserve=RE4DC_TEX_RESIDENT_RESERVE_KB*1024U;
    unsigned pinned=0,pinned_bytes=0;
    for(const auto& e:entries)if(e.valid && RE4DC_ENTRY_PINNED(e)){++pinned;pinned_bytes+=e.package.vram_bytes();}
    DpfPick k{kTextureCount>RE4DC_TEX_RESIDENT_RESERVE_SLOTS+pinned?kTextureCount-RE4DC_TEX_RESIDENT_RESERVE_SLOTS-pinned:0,
              budget>reserve+pinned_bytes?budget-reserve-pinned_bytes:0,0,0,0};
    // 1. The PS2 world's part textures (R4PW sidecar: 32-byte header, then 16-byte parts crc, fnv, width, height, ...),
    //    in part order, repeats skipped, as the PS2_PRELOAD_LEAN room pass. 2. The room's dc/resident.bin rows.
    char path[48];
    std::sprintf(path,"/cd/dc/native/r%03x/ps2-world.r4pw",dpf_room&0xFFFU);
    std::uint32_t h[8]{};
    unsigned long long total=0;
    ++dpf.reads;
    if(re4dc::texture::read_file_range(path,0,h,sizeof(h),&total)==re4dc::texture::RangeRead::ok &&
       !std::memcmp(h,"R4PW",4) && h[1]==1 && h[3] && h[3]<=4096 && 32ULL+16ULL*h[3]<=total){
        dpf.parts=h[3];
        dpf_records(k,path,32,32+16*h[3],false);
    }
    total=0;
    ++dpf.reads;
    if(re4dc::texture::read_file_range("/cd/dc/resident.bin",0,h,16,&total)==re4dc::texture::RangeRead::ok &&
       total>=16 && total<=65536)
        dpf_records(k,"/cd/dc/resident.bin",0,unsigned(total)&~15U,true);
    unsigned n=k.n;
    // Package-name order (disc order), large ones first with PRELOAD_LARGE_FIRST, as the preload pass.
    for(unsigned i=1;i<n;++i){
        const PreloadPick p=preload_picks[i];unsigned j=i;
        for(;j && (preload_picks[j-1].key.crc>p.key.crc || (preload_picks[j-1].key.crc==p.key.crc && preload_picks[j-1].key.fnv>p.key.fnv));--j)preload_picks[j]=preload_picks[j-1];
        preload_picks[j]=p;
    }
#if RE4DC_PRELOAD_LARGE_FIRST
    {
        constexpr unsigned kPreloadLarge=16U*1024U;
        unsigned m=0;
        for(unsigned i=0;i<n;++i)if(preload_least(preload_picks[i].width,preload_picks[i].height)>=kPreloadLarge){
            const PreloadPick p=preload_picks[i];
            for(unsigned j=i;j>m;--j)preload_picks[j]=preload_picks[j-1];
            preload_picks[m++]=p;
        }
    }
#endif
    dpf_n=n;dpf_next=0;dpf.resident=k.resident;dpf.picked=n;
    dpf.build_us=timer_us_gettime64()-t0;
}

// ROOM_CHANGE_EVICT, early: the old room's kept textures that the next room's first preload pass will close anyway
// (not drawn in the old room's last RE4DC_ROOM_CHANGE_EVICT frames; window 2: the rule against the retirement frame
// itself, rce_retire_frame) close before the window's uploads, so these fill one large free pool instead of the old
// room's holes (fewer "fragmented VRAM" retries) and their descriptors give back KOS. Entries the room's lists touched
// (frame >= dpf_frame0) and pinned ones stay. Not for a re-entry of the same room (ROOM_REENTRY_EVICT's own rule).
RE4DC_DPF_FN void dpf_early_evict(){
#if defined(RE4DC_ROOM_CHANGE_EVICT) && RE4DC_ROOM_CHANGE_EVICT
    re4dc::profile::Source src{};
#if defined(__sh__)
    re4dc_profile_source(&src);
#endif
    unsigned ref;
    if(dpf_open==1){
        if(dpf_room==unsigned(src.room))return;
        ref=frame;
    }else{
        if(!rce_armed)return;
#if defined(RE4DC_ROOM_REENTRY_EVICT) && RE4DC_ROOM_REENTRY_EVICT
        if(dpf_room==rce_last_room)return;
#endif
        ref=rce_retire_frame;
    }
    // The bound enemy / player / weapon tables are pinned first, as the regular pass's selection does before its own
    // room-change evict (no picks: byte limit 0); without it the old room's villagers that the next room shares were
    // closed here and read again (weak drive d05: +25 loads, +0.7 s).
    {
        unsigned n0=0,r0=0,b0=0;
        for(auto& t:enemy_identities)if(t.archive)preload_select(t.table,n0,r0,b0,~0U,0);
        preload_select(player_identities,n0,r0,b0,~0U,0);preload_select(weapon_identities,n0,r0,b0,~0U,0);
    }
    for(auto& e:entries){
        if(!e.valid || RE4DC_ENTRY_PINNED(e) || RE4DC_CORE_PINNED(e) || e.frame>=dpf_frame0)continue;
        if(e.frame+RE4DC_ROOM_CHANGE_EVICT>=ref)continue;
        const unsigned sz=e.package.vram_bytes();
        close_entry(e);++dpf.evicted;dpf.evicted_kb+=(sz+512)/1024;
    }
#endif
}
// Window 1 (old room still loaded): KOS below the floor closes the least recently used old-room texture, as
// RETIRE_KOS_FLOOR would at the retirement; false when none is left (the window stops).
RE4DC_DPF_FN bool dpf_kos_room(){
    if(dpf_open!=1)return false;
    Entry* victim=nullptr;
    for(auto& e:entries){
        if(!e.valid || RE4DC_ENTRY_PINNED(e) || RE4DC_CORE_PINNED(e) || e.frame>=dpf_frame0)continue;
        if(!victim || e.frame<victim->frame)victim=&e;
    }
    if(!victim)return false;
    close_entry(*victim);++dpf.kos_closed;
    return true;
}

RE4DC_DPF_FN void dpf_step(){
    if(!dpf_built){dpf_build();dpf_early_evict();}
    const unsigned long long t0=timer_us_gettime64();
    const unsigned budget=vram_budget,reserve=RE4DC_TEX_RESIDENT_RESERVE_KB*1024U;
#if RE4DC_VRAM_ROOM_LOG
    const unsigned loads0=loads;
#endif
    ++dpf.steps;
    while(dpf_next<dpf_n){
        if(timer_us_gettime64()-t0>=kDpfStepUs)break;
        if(kos_headroom()<kDpfKosFloor){
            if(dpf_kos_room())continue;
            dpf.stop="kos";dpf_next=dpf_n;break;
        }
        const PreloadPick& p=preload_picks[dpf_next];
        // Budget as the preload pass (TEX_KEEP form): this window's uploads and touches count as pinned, the rest is
        // evictable; stop when the next pick cannot fit.
        unsigned pins=0,stale=0;
        for(const auto& e:entries)if(e.valid){
            const unsigned sz=e.package.vram_bytes();
            if(RE4DC_ENTRY_PINNED(e) || e.frame>=dpf_frame0)pins+=sz;else stale+=sz;
        }
        if(pins+reserve>=budget || (unsigned)pvr_mem_available()+stale<reserve+preload_least(p.width,p.height)){
            dpf.stop="full";dpf_next=dpf_n;break;
        }
        ++dpf_next;
        bool have=false;
        for(auto& e:entries)if(e.valid && e.key==p.key){e.frame=frame;have=true;break;}
        if(have)continue;
        const Re4dcUiImage image{reinterpret_cast<const void*>(1),nullptr,p.width,p.height,p.format,0xffffffffU,0};
        if(Entry* e=load(image,true,&p.key)){++dpf.loaded;dpf.kb+=(e->package.vram_bytes()+512)/1024;}
        else ++dpf.failed;
    }
#if RE4DC_VRAM_ROOM_LOG
    // Window 1 runs at the end of the old room's visit: its uploads are the next room's, not that room's gameplay.
    if(dpf_open==1 && vroom.room==dpf_vroom)vroom.base[11]+=loads-loads0;
#endif
    dpf.us+=timer_us_gettime64()-t0;
    if(dpf_open==2 && dpf_next>=dpf_n)dpf_w2_idle=1;
}

RE4DC_DPF_FN void dpf_close(){
    re4dc_log("DOORPF: close window=%u room=%03x frames=%u steps=%u parts=%u keys=%u resident=%u picked=%u loaded=%u failed=%u left=%u kb=%u us=%u build_us=%u reads=%u stop=%s free=%u kos=%u evict=%u/%u kos_closed=%u\n",
        dpf_open,dpf_room,frame-dpf_frame0,dpf.steps,dpf.parts,dpf.keys,dpf.resident,dpf.picked,dpf.loaded,dpf.failed,
        dpf_n>dpf_next?dpf_n-dpf_next:0U,dpf.kb,unsigned(dpf.us),unsigned(dpf.build_us),dpf.reads,dpf.stop,
        (unsigned)pvr_mem_available(),kos_headroom(),dpf.evicted,dpf.evicted_kb,dpf.kos_closed);
    dpf_open=0;dpf_n=dpf_next=0;
}

// Main loop, frame start, where the preload pass would run. Returns true when the window owns this frame's texture
// work (the regular preload pass waits): window 2 always; window 1 only while no preload pass is due (a pass the old
// room still has pending runs first, as without the prefetch).
RE4DC_DPF_FN bool dpf_frame(bool ready){
    const unsigned end=dpf_end_req;
    if(dpf_open && end==dpf_open){dpf_end_req=0;dpf_close();}
    const unsigned req=dpf_req;
    if(req && !dpf_open){
        dpf_req=0;
        if(dpf_end_req==req){dpf_end_req=0;re4dc_log("DOORPF: skip window=%u room=%03x (no wait)\n",req,dpf_req_room);return false;}
        dpf_open=req;dpf_room=dpf_req_room;dpf_frame0=frame;dpf_built=false;dpf=DpfStats{};dpf.stop="-";
#if RE4DC_VRAM_ROOM_LOG
        dpf_vroom=vroom.room;
#endif
        re4dc_log("DOORPF: open window=%u room=%03x frame=%u free=%u kos=%u\n",dpf_open,dpf_room,frame,(unsigned)pvr_mem_available(),kos_headroom());
    }
    if(!dpf_open || (dpf_open==1 && preload_pending))return false;
    // Window 1 starts after the door sound's own read: before it, the window's reads (and the main loop's longer
    // frames, which step the source DVD queue) would delay the read the wait is for (weak drive: +1.0..1.5 s).
    if(dpf_open==1 && !dpf_se_ready)return true;
    if(ready && !vram_claims && dpf_next<=dpf_n && (!dpf_built || dpf_next<dpf_n))dpf_step();
    return true;
}
}  // namespace

// Game task side (game.cpp / snd.cpp through platform/include/door_prefetch.h).
extern "C" void re4dc_dpf_begin(int window,unsigned room){
    if(window!=1 && window!=2)return;
    dpf_req_room=room&0xFFFFU;
    dpf_w2_idle=0;
    if(window==1)dpf_se_ready=0;
    dpf_task_window=unsigned(window);
    dpf_req=unsigned(window);
}
extern "C" void re4dc_dpf_end(int window){
    if(dpf_task_window!=unsigned(window))return;
    dpf_task_window=0;
    dpf_end_req=unsigned(window);
}
extern "C" void re4dc_dpf_read(int read){if(read && dpf_task_window==1)dpf_se_ready=1;}
extern "C" int re4dc_dpf_yield(void){return dpf_task_window==2 && !dpf_w2_idle;}
