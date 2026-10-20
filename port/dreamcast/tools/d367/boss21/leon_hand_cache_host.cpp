// Actual hand-loader namespace + unchanged public loadpoint/yield functions.
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <map>
#include <vector>
#include <iostream>
#include <stdexcept>
#include <string>
#include <kos.h>
extern "C" void re4dc_log(const char*,...);
struct ModelData {unsigned weight_ext_num,weight_palette_num,nVtx,nNrm;const unsigned char* vtxOrig;};
struct cModelInfo {const ModelData* pData;};
unsigned fingerprint(const void*){return 0;}
namespace leon4k {
struct Weight {unsigned char bytes[16];};
struct Chunk {unsigned asset,position_count,normal_count,palette_count,triangles,stream_bytes;const unsigned char* positions;const unsigned char* normals;const unsigned char* uv;const unsigned char* stream;const Weight* weights;};
Chunk chunks[8]{};
}
#include "source-under-test.inc"
#include "leon_hands_selected_fixture.hpp"
using namespace leon_hand_pack;
#ifndef TEST_FIXED
#define TEST_FIXED 1
#endif
struct Handle {unsigned pos;};
static std::map<int,Handle> handles;
static std::map<void*,unsigned> memory;
static std::vector<unsigned char> package_bytes,aica_bytes(0x100000);
static unsigned next_handle=1,io_reads,proof_resets,active_aica,alloc_aica,worker_starts;
static bool fail_aica,fail_payload,fail_thread;
static unsigned fail_motion;
extern "C" { alignas(32) unsigned char re4dc_dvd_buff[0x20000]; }
extern "C" void re4dc_log(const char*,...) {}
extern "C" void* re4dc_motion_alloc(unsigned n){if(fail_motion){--fail_motion;return nullptr;}void* p=nullptr;assert(!posix_memalign(&p,32,n));memory[p]=n;return p;}
extern "C" void re4dc_motion_free(void* p){assert(memory.erase(p)==1);std::free(p);}
namespace leon_hand_pack {void reset_role_ids(unsigned){++proof_resets;}}
file_t fs_open(const char*,int){int n=next_handle++;handles[n]={};return n;}
int fs_close(file_t f){assert(handles.erase(f));return 0;}
off_t fs_seek(file_t f,off_t o,int origin){assert(origin==SEEK_SET&&o>=0&&unsigned(o)<=package_bytes.size());handles.at(f).pos=unsigned(o);return o;}
ssize_t fs_read(file_t f,void* dst,size_t n){auto& h=handles.at(f);if(f==job_file)assert((reinterpret_cast<std::uintptr_t>(dst)&31u)==4);++io_reads;if(fail_payload&&h.pos>=832)return 0;assert(h.pos+n<=package_bytes.size());std::memcpy(dst,package_bytes.data()+h.pos,n);h.pos+=n;return n;}
unsigned snd_mem_malloc(unsigned n){if(fail_aica)return 0;assert(!active_aica&&n==kCellBytes);active_aica=n;++alloc_aica;return 0x1000;}
void snd_mem_free(unsigned p){assert(p==0x1000&&active_aica==kCellBytes);active_aica=0;std::fill(aica_bytes.begin(),aica_bytes.end(),0xcc);}
void spu_memload(unsigned to,const void* p,unsigned n){assert(active_aica&&to>=0x1000&&to+n<=0x1000+kCellBytes);std::memcpy(aica_bytes.data()+to,p,n);}
void spu_memread(void* p,unsigned from,unsigned n){assert(active_aica&&from>=0x1000&&from+n<=0x1000+kCellBytes);std::memcpy(p,aica_bytes.data()+from,n);}
unsigned long long timer_us_gettime64(){static unsigned long long n;return ++n;}
kthread_t* thd_create_ex(const kthread_attr_t* a,void*(*fn)(void*),void* arg){assert(a->stack_size==kJobStack);if(fail_thread)return nullptr;++worker_starts;return new kthread_t{fn,arg,false};}
static void complete(kthread_t* t){assert(t);if(!t->ran){t->fn(t->arg);t->ran=true;}}
int thd_join(kthread_t* t,void**){complete(t);delete t;return 0;}
static void put16(unsigned o,unsigned v){package_bytes.at(o)=v;package_bytes.at(o+1)=v>>8;}
static void put32(unsigned o,unsigned v){std::memcpy(package_bytes.data()+o,&v,4);}
static void build_package(){
    const unsigned nb=sizeof(selected_blobs)/sizeof(*selected_blobs),ns=sizeof(selected_sources)/sizeof(*selected_sources),dir=832; // selected directory span, with unused synthetic row padding
    package_bytes.assign(dir,0);put32(0,kMagic);put32(4,kVersion);put32(8,nb|(ns<<16));put32(12,kSlotBytes[0]);put32(16,kSlotBytes[1]);put32(20,dir);
    unsigned off=dir;
    for(unsigned b=0;b<nb;++b){Blob x=selected_blobs[b];x.offset32=off/32;std::memcpy(package_bytes.data()+32+b*24,&x,24);const unsigned n=blob_bytes(x);package_bytes.resize(off+n,static_cast<unsigned char>(b+1));off+=n;}
    std::memcpy(package_bytes.data()+32+nb*24,selected_sources,ns*4);put32(24,package_bytes.size());assert(package_bytes.size()==95520);
}
static void reset(){
    re4dc_leon_hands_yield();if(job_file!=FILEHND_INVALID){fs_close(job_file);job_file=FILEHND_INVALID;}assert(memory.empty()&&!active_aica&&handles.empty());
    std::memset(rows,0,sizeof rows);std::memset(blobs,0,sizeof blobs);std::memset(srcs,0,sizeof srcs);nrows=nblobs=nsrcs=file_bytes=0;dir_state=0;
    std::fill(slot_blob,slot_blob+2,-1);std::fill(cell_blob,cell_blob+4,-1);std::fill(refill,refill+4,-1);std::fill(cell_used,cell_used+4,0);use_clock=0;
    std::memset(slot5,0,sizeof slot5);std::memset(slot6,0,sizeof slot6);std::fill(want,want+2,-1);job_n=0;job_state=0;job_blob=-1;job_us=0;job_mem=nullptr;job_thd=nullptr;
    reads=read_bytes=copies=hits=misses=yields=refills=alloc_fails=hit_max_us=async_reads=async_fails=async_max_us=pick_max_us=0;
    io_reads=proof_resets=alloc_aica=worker_starts=0;fail_aica=fail_payload=fail_thread=false;fail_motion=0;next_handle=1;build_package();
}
static bool draw(unsigned side,int b){mutex_lock(&lh_mutex);refill_now();job_poll();bool ok=load(side,b);mutex_unlock(&lh_mutex);return ok;}
static void tick(){mutex_lock(&lh_mutex);refill_now();job_poll();mutex_unlock(&lh_mutex);if(job_thd)complete(job_thd);}
static void drain(){for(unsigned i=0;i<40&&(job_n||job_thd||job_state);++i)tick();assert(!job_n&&!job_thd&&!job_state);}
static void pose(unsigned side,int b){for(unsigned i=0;i<20&&slot_blob[side]!=b;++i){draw(side,b);if(job_thd)complete(job_thd);}assert(slot_blob[side]==b);const unsigned n=blob_bytes(blobs[b]);for(unsigned i=0;i<n;++i)assert(slot[side][i]==b+1);}
static void enter(){reset();re4dc_leon_hands_room_enter();assert(dir_state==1&&active_aica==kCellBytes&&slot_blob[0]==0&&slot_blob[1]==1);}
static void repeated_switches(){
    enter();re4dc_leon_hands_weapon("em/wep11.drs");pose(1,7);re4dc_leon_hands_weapon("em/wep02.drs");pose(1,1);drain();const unsigned before=reads,async_before=async_reads,io_before=io_reads;
    for(unsigned i=0;i<8;++i){re4dc_leon_hands_weapon("em/wep11.drs");pose(1,7);re4dc_leon_hands_weapon("em/wep02.drs");pose(1,1);}drain();
#if TEST_FIXED
    assert(reads==before&&io_reads==io_before&&async_reads==async_before&&cell_of(1)>=0&&cell_of(7)>=0);
#else
    assert(reads>before&&async_reads>async_before);
#endif
    assert(active_aica==kCellBytes&&alloc_aica==1);
    std::cout<<"hands repeat fixed="<<TEST_FIXED<<" additional_reads="<<reads-before<<" async="<<async_reads-async_before<<" cells="<<cell_blob[2]<<"/"<<cell_blob[3]<<"\n";
}
static void current_slot_and_queue_reuse(){
    enter();re4dc_leon_hands_yield();const unsigned before=reads;prefetch(1);
#if TEST_FIXED
    assert(reads==before);
#else
    assert(reads==before+1);
#endif
    enter();assert(load(1,7));prefetch(7);const unsigned cached=reads,started=worker_starts;drain();assert(slot_blob[1]==7);
#if TEST_FIXED
    assert(reads==cached&&worker_starts==started);
#else
    assert(reads==cached+1&&worker_starts==started+1);
#endif
    enter();int c=cell_of(1);assert(c>=0);const unsigned used=cell_used[c];assert(load(1,1));
#if TEST_FIXED
    assert(cell_used[c]>used);
#else
    assert(cell_used[c]==used);
#endif
}
static void landed_duplicate_and_stale(){
    enter();assert(load(1,7));job_poll();assert(job_thd&&job_state==1);prefetch(7);complete(job_thd);job_poll();unsigned count=0;for(int b:cell_blob)count+=b==7;
#if TEST_FIXED
    assert(count==1);
#else
    assert(count==2);
#endif
    enter();pose(1,7);pose(1,1);drain();assert(cell_of(7)>=0&&cell_of(1)>=0);assert(load(1,5));job_poll();assert(job_thd);assert(load(1,1));complete(job_thd);job_poll();assert(slot_blob[1]==1);
#if TEST_FIXED
    assert(cell_of(7)>=0&&cell_of(1)>=0&&cell_of(5)<0);
#else
    assert(cell_of(5)>=0);
#endif
}
static void exact_weapon_prefetch(){
    enter();re4dc_leon_hands_weapon("em/wep09.drs");assert(cell_of(11)>=0);const unsigned before=async_reads;pose(0,11);pose(0,0);assert(async_reads==before);
    // A named source pose retains loadpoint admission even with two demanded cells.
    re4dc_leon_hands_weapon("em/wep07.drs");assert(cell_of(10)>=0);pose(0,10);assert(async_reads==before);
}
static void yield_refill_and_failures(){
    enter();pose(1,7);pose(1,1);drain();re4dc_leon_hands_yield();const unsigned before=reads;refill_now();drain();assert(active_aica==kCellBytes);pose(1,7);pose(1,1);
#if TEST_FIXED
    assert(reads-before==2);
#else
    assert(reads-before>=4);
#endif
    assert(active_aica==kCellBytes);re4dc_leon_hands_yield();refill_now();drain();assert(active_aica==kCellBytes);
    enter();assert(load(1,7));job_poll();assert(job_thd);re4dc_leon_hands_yield();assert(memory.empty()&&!job_thd&&!job_n&&want[1]==-1&&!aica); // movie/sound yield joins then drops an in-flight owner
    enter();assert(load(1,7));fail_payload=true;job_poll();complete(job_thd);job_poll();assert(async_fails==1&&slot_blob[1]==1&&memory.empty()); // failed read never publishes or corrupts prior CPU slot
    enter();assert(load(1,7));fail_motion=1;job_poll();assert(async_fails==1&&!job_thd);drain();pose(1,7);assert(memory.empty());
    enter();assert(load(1,7));fail_thread=true;job_poll();assert(async_fails==1&&!job_thd&&memory.empty());fail_thread=false;drain();pose(1,7);assert(memory.empty());
    reset();fail_aica=true;re4dc_leon_hands_room_enter();assert(!aica&&slot_blob[0]==0&&slot_blob[1]==1);const unsigned unchanged=reads;for(unsigned i=0;i<5;++i)assert(draw(1,1));assert(reads==unchanged);
}
int main(){repeated_switches();current_slot_and_queue_reuse();landed_duplicate_and_stale();exact_weapon_prefetch();yield_refill_and_failures();reset();std::cout<<"actual Leon hand cache PASS fixed="<<TEST_FIXED<<" cell_bytes="<<kCellBytes<<"\n";}
