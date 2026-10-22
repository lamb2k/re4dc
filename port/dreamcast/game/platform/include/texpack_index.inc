// texpack_index.inc - TEX_PACK index (included by native_ui.cpp inside `namespace {`, TEX_PACK=1 builds; compiled
// unchanged by the host test tests/test_texpack_index.py with a mock reader).
// Needs: Key {crc, fnv}, mutex_t / MUTEX_INITIALIZER / mutex_lock / mutex_unlock, re4dc_log,
// re4dc::texture::read_file_range (texture_package.hpp) and its RangeRead result.
//
// dc/tex.pak (tools/d367/texpack.py): every dc/tex/<n>/<crc>-<fnv>.re4tex of the disc in one file, so a load seeks
// inside one file instead of a lookup in a ~200-entry directory per texture (IO_PROBE, r100 entry: 130 opens = 3.9
// of 6.5 s, 234 directory-sector reads; on a GD-ROM each is a seek to the directory area and back). Layout: 2048-byte
// header {"RE4PAK1\0", version 1, count, index_offset, data_offset, index_crc32}, the index sorted by (crc, fnv) as
// {crc, fnv, offset, size} (128 per sector), then the packages at 2048-byte boundaries, byte for byte the .re4tex
// files. RAM: the first key of each index sector; a lookup reads one sector.
//
// Failure policy (architect review 2026-10-03, P1/P2; retry spacing: review 2026-10-04):
// - Pack absent (fs_open fails): per-file loads, as before. A key not in a ready pack (texlow, a missing file)
//   also takes the per-file path.
// - A read error (header, index or a lookup's sector) is transient: find() returns kError, the caller loads
//   nothing this time and does not remember the key as missing. Init attempts are spaced in UI frames (find()'s
//   `now`), so a burst of lookups in one frame (a room preload) spends one attempt, not all of them: kRetryNow
//   attempts kRetryFrames apart, then one every kRetrySlowFrames (this also covers the first room after boot,
//   which no room leave re-arms). A room load (room_loaded()) allows the next attempt at once and restarts the
//   fast spacing. Between attempts find() returns kError without I/O. Nothing is published until a complete init.
//   A lookup's index sector that failed to read is re-read at most once per kRetryFrames (one log line each).
// - An invalid pack (header fields, count, extents, key order, index CRC, a file shorter than its header) is
//   terminal: one loud log line, then per-file loads (a packed-only disc will miss its packed textures; that disc
//   is broken media).
namespace texpack {
constexpr const char* kPath="/cd/dc/tex.pak";
constexpr unsigned kMaxSectors=64;               // 8,192 entries (texpack.py enforces the same cap)
constexpr unsigned kMaxCount=kMaxSectors*128;
constexpr unsigned kRetryNow=3;                  // fast init attempts after a read error (per room load)
constexpr unsigned kRetryFrames=30;              // UI frames between fast attempts / re-reads of a failed sector
constexpr unsigned kRetrySlowFrames=300;         // UI frames between later attempts, until the next room load
enum State { kUntried, kReady, kAbsent, kInvalid, kRetry };
enum Result { kNotInPack, kFound, kError };      // kNotInPack: per-file path (no usable pack, or key not in it)
mutex_t lock=MUTEX_INITIALIZER;
State state=kUntried;
unsigned count=0,data_offset=0,sectors=0,cached=~0U,hits=0,misses=0,errors=0;
unsigned attempts=0,streak=0,room_gen=0,attempt_gen=0,retry_at=0;  // retry_at: UI frame of the next init attempt
unsigned bad_sector=~0U,bad_until=0;             // the index sector whose last lookup read failed, re-read from bad_until
unsigned long long pack_bytes=0;
Key first[kMaxSectors];
#if RE4DC_TEX_PAYLOAD_RETRY
unsigned sector_crc[kMaxSectors]{}; // exact ordinal identity when a validated sector is re-read
// A failed lookup invalidates the shared sector buffer. Remember every failed
// sector independently: alternating failures must not erase each other's wait.
unsigned index_bad_bits[2]{};
unsigned index_bad_until[kMaxSectors]{};
bool index_blocked(unsigned s,unsigned now){
    return (index_bad_bits[s>>5]&(1U<<(s&31))) && int(now-index_bad_until[s])<0;
}
void index_failed(unsigned s,unsigned now){
    index_bad_until[s]=now+kRetryFrames;index_bad_bits[s>>5]|=1U<<(s&31);
}
void index_succeeded(unsigned s){index_bad_bits[s>>5]&=~(1U<<(s&31));}
unsigned payload_epoch=1;
bool payload_epoch_exhausted;
// All bitmap operations and epoch publication use this existing index mutex.
// A caller can yield in a package read after find() unlocks; a late completion
// must never change the next room/index epoch's retry bits.
void payload_reset_locked(){
    texpack_payload_retry::reset();
    std::memset(index_bad_bits,0,sizeof(index_bad_bits));
    if(payload_epoch!=~0U)++payload_epoch;
    else if(!payload_epoch_exhausted){
        payload_epoch_exhausted=true;
        re4dc_log("tex pack: payload retry epoch exhausted; new packed loads refused until restart\n");
    }
}
bool payload_current(unsigned member,unsigned epoch){return !payload_epoch_exhausted && epoch && epoch==payload_epoch && member<kMaxCount;}
bool payload_blocked(unsigned member,unsigned now,unsigned epoch){
    mutex_lock(&lock);const bool blocked=!payload_current(member,epoch) || texpack_payload_retry::blocked(member,now);mutex_unlock(&lock);return blocked;
}
void payload_failed(unsigned member,unsigned now,unsigned epoch){
    mutex_lock(&lock);if(payload_current(member,epoch))texpack_payload_retry::failed(member,now);mutex_unlock(&lock);
}
void payload_succeeded(unsigned member,unsigned epoch){
    mutex_lock(&lock);if(payload_current(member,epoch))texpack_payload_retry::succeeded(member);mutex_unlock(&lock);
}
#endif
alignas(32) unsigned char sector[2048];    // read by re4dc::texture::read_file_range: its own handle per read
unsigned word(const unsigned char* p){return p[0]|p[1]<<8|p[2]<<16|unsigned(p[3])<<24;}
bool less(const Key& a,const Key& b){return a.crc<b.crc || (a.crc==b.crc && a.fnv<b.fnv);}
// zlib crc32 (texpack.py writes zlib.crc32 of the padded index): bitwise, init only (20-26 sectors).
unsigned crc_update(unsigned crc,const unsigned char* p,unsigned n){
    for(unsigned i=0;i<n;++i){crc^=p[i];for(unsigned b=0;b<8;++b)crc=(crc>>1)^(0xedb88320U&(0U-(crc&1U)));}
    return crc;
}
re4dc::texture::RangeRead read_sector(unsigned offset,unsigned long long* bytes=nullptr){
#if defined(RE4DC_TEX_PACK_FAULT) && RE4DC_TEX_PACK_FAULT
    // Test only (game30.mk TEX_PACK_FAULT=N, default 0): the first N pack reads fail as read errors.
    static unsigned faults=RE4DC_TEX_PACK_FAULT;
    if(faults){--faults;re4dc_log("tex pack: test fault: read at %u fails (%u left)\n",offset,faults);
        return re4dc::texture::RangeRead::io_error;}
#endif
    return re4dc::texture::read_file_range(kPath,offset,sector,2048,bytes);
}
bool invalid(const char* why,unsigned a,unsigned b){
    re4dc_log("tex pack: %s INVALID: %s (0x%x, 0x%x); the pack is not used, per-file loads\n",kPath,why,a,b);
    state=kInvalid;cached=~0U;return false;
}
bool read_failed(const char* what,unsigned offset,unsigned now){
    if(attempt_gen!=room_gen)streak=0;           // a room load since the last failure: fast spacing again
    ++attempts;++streak;++errors;attempt_gen=room_gen;state=kRetry;cached=~0U;
    const unsigned wait=streak<kRetryNow?kRetryFrames:kRetrySlowFrames;
    retry_at=now+wait;
    if(streak<=kRetryNow || !(streak%16U))       // the slow cadence logs every 16th failure
        re4dc_log("tex pack: %s read error (%s at %u), attempt %u; next attempt in %u frames or at the next room load\n",
                  kPath,what,offset,attempts,wait);
    return false;
}
// Complete init or nothing: header and every index sector validated, index CRC checked, then published.
bool open_locked(unsigned now){
    if(state==kReady)return true;
    if(state==kAbsent || state==kInvalid)return false;
    // after a read error: wait for retry_at (frame arithmetic wraps), unless a room load came since the failure
    if(state==kRetry && attempt_gen==room_gen && int(now-retry_at)<0)return false;
    unsigned long long total=0;
    const re4dc::texture::RangeRead h=read_sector(0,&total);
    if(h==re4dc::texture::RangeRead::absent){
        re4dc_log("tex pack: %s not on the disc, per-file loads\n",kPath);state=kAbsent;return false;
    }
    if(h==re4dc::texture::RangeRead::short_file)return invalid("file shorter than its header",unsigned(total),2048);
    if(h!=re4dc::texture::RangeRead::ok)return read_failed("header",0,now);
    if(std::memcmp(sector,"RE4PAK1\0",8) || word(sector+8)!=1)return invalid("magic/version",word(sector+8),0);
    const unsigned n=word(sector+12),index_at=word(sector+16),data_at=word(sector+20),crc=word(sector+24);
    if(n<1 || n>kMaxCount)return invalid("count",n,kMaxCount);           // before any multiplication
    if(index_at!=2048)return invalid("index offset",index_at,2048);
    const unsigned nsec=(n*16U+2047U)/2048U;
    const unsigned long long index_end=2048ULL+2048ULL*nsec;
    if(data_at<index_end || data_at%2048U || data_at>total)return invalid("data offset",data_at,unsigned(index_end));
    Key keys[kMaxSectors];
#if RE4DC_TEX_PAYLOAD_RETRY
    unsigned checked_crc[kMaxSectors]; // publish only after the complete index CRC/order validation
#endif
    Key prev{};unsigned crc_run=0xffffffffU;
    for(unsigned s=0;s<nsec;++s){
        const re4dc::texture::RangeRead ir=read_sector(2048U*(s+1));
        if(ir==re4dc::texture::RangeRead::short_file)return invalid("index past the end of the file",2048U*(s+1),unsigned(total));
        if(ir!=re4dc::texture::RangeRead::ok)return read_failed("index",2048U*(s+1),now);
        crc_run=crc_update(crc_run,sector,2048);
#if RE4DC_TEX_PAYLOAD_RETRY
        checked_crc[s]=~crc_update(0xffffffffU,sector,2048);
#endif
        const unsigned m=std::min(128U,n-128U*s);
        for(unsigned i=0;i<m;++i){
            const unsigned char* e=sector+16*i;
            const Key k{word(e),word(e+4)};const unsigned off=word(e+8),size=word(e+12);
            if((s|i) && !less(prev,k))return invalid("key order at entry",128*s+i,k.crc);
            if(!size || off%2048U || off<data_at || (unsigned long long)off+size>total)
                return invalid("entry extent",128*s+i,off);
            if(!i)keys[s]=k;
            prev=k;
        }
    }
    if(~crc_run!=crc)return invalid("index crc",~crc_run,crc);
    for(unsigned s=0;s<nsec;++s)first[s]=keys[s];
#if RE4DC_TEX_PAYLOAD_RETRY
    // Publication is the only ready-index replacement boundary. Drop old ordinal
    // receipts before publishing a newly validated immutable pack index.
    payload_reset_locked();
    std::memset(sector_crc,0,sizeof(sector_crc));
    for(unsigned s=0;s<nsec;++s)sector_crc[s]=checked_crc[s];
#endif
    count=n;data_offset=data_at;sectors=nsec;pack_bytes=total;cached=nsec-1;state=kReady;
    re4dc_log("tex pack: %s count=%u index_sectors=%u bytes=%llu%s\n",kPath,count,sectors,pack_bytes,
              attempts?" (after read errors)":"");
    return true;
}
// The pack is no longer retrying: ready, absent or invalid (native_ui.cpp re-runs a room preload that met a read error).
bool settled(){
    mutex_lock(&lock);const bool s=state==kReady || state==kAbsent || state==kInvalid;mutex_unlock(&lock);
    return s;
}
// A room load (native_ui.cpp re4dc_ui_retire_room) allows the next init attempt at once and restarts the fast
// spacing; it also lets a failed lookup sector be re-read at once.
void room_loaded(){mutex_lock(&lock);++room_gen;bad_sector=~0U;
#if RE4DC_TEX_PAYLOAD_RETRY
    payload_reset_locked();
#endif
    mutex_unlock(&lock);}
// The key's package in the pack: kFound with its offset and size; kNotInPack for the per-file path; kError for a
// read error (load nothing now, do not remember the key as missing). now: the caller's UI frame (retry spacing).
Result find(const Key& key,unsigned& offset,unsigned& size,unsigned now
#if RE4DC_TEX_PAYLOAD_RETRY
            ,unsigned* member=nullptr,unsigned* epoch=nullptr
#endif
){
    mutex_lock(&lock);
    Result r=kNotInPack;
    if(open_locked(now)){
        unsigned s=0;
        while(s+1<sectors && !less(key,first[s+1]))++s;
        if(!less(key,first[s])){
            if(cached!=s){
#if RE4DC_TEX_PAYLOAD_RETRY
                if(index_blocked(s,now))r=kError;
#else
                if(s==bad_sector && int(now-bad_until)<0)r=kError;   // failed lately: no re-read before bad_until
#endif
                else{
                    cached=~0U;
                    if(read_sector(2048U*(s+1))!=re4dc::texture::RangeRead::ok || word(sector)!=first[s].crc ||
                       word(sector+4)!=first[s].fnv
#if RE4DC_TEX_PAYLOAD_RETRY
                       || ~crc_update(0xffffffffU,sector,2048)!=sector_crc[s]
#endif
                       ){
                        ++errors;r=kError;bad_sector=s;bad_until=now+kRetryFrames;
#if RE4DC_TEX_PAYLOAD_RETRY
                        index_failed(s,now);
#endif
                        re4dc_log("tex pack: %s index sector %u read error (lookup %08x-%08x); re-read in %u frames\n",
                                  kPath,s,key.crc,key.fnv,kRetryFrames);
                    } else {
                        cached=s;if(s==bad_sector)bad_sector=~0U;
#if RE4DC_TEX_PAYLOAD_RETRY
                        index_succeeded(s);
#endif
                    }
                }
            }
            if(cached==s){
                unsigned lo=0,hi=std::min(128U,count-128U*s);
                while(lo<hi){
                    const unsigned mid=(lo+hi)/2;const unsigned char* e=sector+16*mid;
                    const Key k{word(e),word(e+4)};
                    if(k==key){offset=word(e+8);size=word(e+12);r=kFound;
#if RE4DC_TEX_PAYLOAD_RETRY
                        if(member)*member=128*s+mid; // unique ordinal in the validated <=8192-member index
                        if(epoch)*epoch=payload_epoch_exhausted?0:payload_epoch;
#endif
                        break;}
                    if(less(k,key))lo=mid+1;else hi=mid;
                }
            }
        }
    } else if(state==kRetry) r=kError;
    if(r==kFound)++hits;else if(r==kNotInPack)++misses;
    mutex_unlock(&lock);
    return r;
}
}
