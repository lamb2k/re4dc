#include "include/gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
#include "include/native_io.h"
#include "../../room/room_storage.hpp"
#include <kos/fs.h>
#include <fcntl.h>
#include <cstdio>
#include <cstring>
#include <atomic>
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
#include <arch/timer.h>
extern "C" void re4dc_log(const char*,...);
static unsigned re4dc_gca_disc_reads; static unsigned long long re4dc_gca_disc_us;
namespace re4dc_gcasset {
unsigned prof_disc_reads(){return re4dc_gca_disc_reads;}
unsigned long long prof_disc_us(){return re4dc_gca_disc_us;}
}
#endif
#ifndef RE4DC_GC_ASSET_CATALOG_SHA256
#define RE4DC_GC_ASSET_CATALOG_SHA256 "0"
#endif
namespace re4dc_gcasset {
namespace {
file_t disc_catalog=FILEHND_INVALID;
enum DiscState : unsigned { Initial, Ready, Failed, Installing, Retired, FreshInstall };
std::atomic<unsigned> disc_state{Initial};
std::atomic_flag disc_lock=ATOMIC_FLAG_INIT;
struct DiscGuard {
    bool held;
    DiscGuard():held(!disc_lock.test_and_set(std::memory_order_acquire)){}
    ~DiscGuard(){if(held)disc_lock.clear(std::memory_order_release);}
};
void disc_failed(){disc_state.store(Failed);retire_catalog();}
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
struct DiscProf{unsigned long long t0;DiscProf():t0(timer_us_gettime64()){}
    ~DiscProf(){++re4dc_gca_disc_reads;re4dc_gca_disc_us+=timer_us_gettime64()-t0;}};
#endif
unsigned disc_read(void*,unsigned offset,void* destination,unsigned bytes){
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    DiscProf prof;
#endif
    DiscGuard guard;
    if(!guard.held){disc_failed();return 0;}
    const unsigned state=disc_state.load();
    if((state!=Ready && state!=Installing) || disc_catalog==FILEHND_INVALID)return 0;
    const file_t source=disc_catalog;
    Re4dcIoScope io;
    if(fs_seek(source,offset,SEEK_SET)!=off_t(offset)){disc_failed();return 0;}
    if(disc_state.load()!=state)return 0;
    const ssize_t count=fs_read(source,destination,bytes);
    if(disc_state.load()!=state)return 0;
    if(count<0 || unsigned(count)!=bytes){disc_failed();return 0;}
    return unsigned(count);
}
// Whole-catalog sequential read at install through the shared 16 KiB storage
// bounce (room_storage read_chunks): ~55 aligned reads instead of ~250.
struct DiscStream{void (*sink)(void*,const unsigned char*,unsigned);void* context;};
bool disc_stream(void*,void (*sink)(void*,const unsigned char*,unsigned),void* sink_context){
    DiscGuard guard;
    if(!guard.held){disc_failed();return false;}
    if(disc_state.load()!=Installing || disc_catalog==FILEHND_INVALID)return false;
    Re4dcIoScope io;
    const off_t total=fs_total(disc_catalog);
    if(total<0 || fs_seek(disc_catalog,0,SEEK_SET)!=0){disc_failed();return false;}
    DiscStream s{sink,sink_context};
    const bool ok=re4dc::storage::read_chunks(disc_catalog,std::size_t(total),[](const std::uint8_t* p,std::size_t n,void* ctx){
        auto& d=*static_cast<DiscStream*>(ctx);d.sink(d.context,p,unsigned(n));return true;
    },&s);
    if(!ok)disc_failed();
    return ok && disc_state.load()==Installing;
}
bool disc_pin(Digest& digest){
    const char* text=RE4DC_GC_ASSET_CATALOG_SHA256;
    if(std::strlen(text)!=64)return false;
    for(unsigned i=0;i<64;++i){
        const unsigned char c=text[i];unsigned value;
        if(c>='0' && c<='9')value=c-'0';else if(c>='a' && c<='f')value=c-'a'+10;else return false;
        if(i&1)digest.bytes[i/2]|=value;else digest.bytes[i/2]=value<<4;
    }
    return true;
}
}
bool ensure_disc_catalog(){
    const unsigned state=disc_state.load();
    if(state==Ready)return true;
    if(state!=Initial && state!=FreshInstall)return false;
    disc_state.store(Installing);Digest expected{};
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
    struct InstallProf{unsigned long long t0=timer_us_gettime64();~InstallProf(){re4dc_log("GC-ASSET-PROF install_us=%llu\n",timer_us_gettime64()-t0);}} install_prof;
#endif
    if(!disc_pin(expected)){disc_failed();unresolved(SourceGeometry,"catalog-pin-missing");return false;}
    off_t bytes=-1;
    {
        DiscGuard guard;
        if(!guard.held){disc_failed();return false;}
        // Only Initial or an explicit safe-owner retirement can reach here.
        if(disc_catalog!=FILEHND_INVALID){disc_failed();return false;}
        {
            Re4dcIoScope io;
            disc_catalog=fs_open("/cd/dc/gc-assets.idx",O_RDONLY);
            if(disc_state.load()==Installing && disc_catalog!=FILEHND_INVALID)bytes=fs_total(disc_catalog);
        }
        if(disc_state.load()!=Installing)return false;
        if(disc_catalog==FILEHND_INVALID){disc_failed();unresolved(SourceGeometry,"catalog-file-missing");return false;}
    }
    if(bytes<128 || bytes>128+16376*112 || !install_index_stream(disc_stream,nullptr,disc_read,nullptr,unsigned(bytes),expected)){
        // Retain the exact fd, even after failure. Never close a busy reader or
        // silently retry/reopen; explicit safe-owner retirement is required.
        if(disc_state.load()==Installing)disc_failed();
        unresolved(SourceGeometry,"catalog-install");return false;
    }
    if(disc_state.load()!=Installing)return false;
    disc_state.store(Ready);return true;
}
void retire_disc_catalog(){
    disc_state.store(Retired);
    retire_catalog(); // epoch/latch first, before a close attempt or callback
    DiscGuard guard;
    if(!guard.held)return; // exact busy fd stays retained; no deferred auto-close
    if(disc_catalog!=FILEHND_INVALID){
        Re4dcIoScope io;const file_t source=disc_catalog;
        if(fs_close(source)<0)return;
        disc_catalog=FILEHND_INVALID;
    }
    // This is not Ready and does not restore old tokens. Only a fresh complete
    // explicit install can clear the retired/failure state after this retry.
    disc_state.store(FreshInstall);
}
}
#endif
