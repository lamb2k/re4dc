#pragma once
#include "gc_asset_motion_source.h"
// Source FCV identities stay archive-owned. Only evaluated key payloads move.
struct Re4dcMotionStats {
    unsigned hits, misses, evictions, loads, failures, resident_bytes, peak_cache_bytes;
    unsigned pinned_bytes, peak_pinned_bytes, metadata_bytes, hot_bytes;
    unsigned long long bytes_read, worst_wait_us;
};
extern "C" {
int re4dc_motion_bind(void* archive, unsigned bytes);
void re4dc_motion_unbind(void* archive);
void re4dc_motion_retire_all();
int re4dc_motion_acquire(const void* header, unsigned** table);
#if RE4DC_GC_ASSET_MOTION_SOURCE
void re4dc_motion_gcasset_publish(int token,const void* header);
int re4dc_motion_gcasset_idle();
#endif
void re4dc_motion_release(int token);
int re4dc_motion_thread_busy(const void* owner);
void re4dc_motion_get_stats(Re4dcMotionStats*);
int re4dc_motion_current_heap();
void* re4dc_motion_alloc(unsigned bytes);
void re4dc_motion_free(void*);
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
// Exact source SDK request/owner; called after its first allocation failed.
void* re4dc_motion_required_alloc(int heap, unsigned bytes);
int re4dc_motion_capacity_retire();
#endif
#if defined(RE4DC_MOTION_RESUME) && RE4DC_MOTION_RESUME
void re4dc_motion_movie_begin();
unsigned re4dc_motion_movie_evict_one();
void re4dc_motion_movie_finish(int retiring);
unsigned re4dc_motion_movie_restore();
#endif
}
// Leased tables are local to the evaluation; source work retains its resident
// proxy table even during evaluation. Pin release retains the cache entry.
class Re4dcMotionLease {
    unsigned** destination_;
    unsigned* saved_;
    int token_;
public:
    Re4dcMotionLease(const void* header, unsigned** destination, unsigned* restore)
        : destination_(destination), saved_(restore), token_(0) {
        unsigned* table=nullptr;
        token_=re4dc_motion_acquire(header,&table);
        if(token_) *destination_=table;
#if RE4DC_GC_ASSET_MOTION_SOURCE
        if(token_) re4dc_motion_gcasset_publish(token_,header);
#endif
    }
    ~Re4dcMotionLease() {
        if(token_) { *destination_=saved_; re4dc_motion_release(token_); }
    }
    bool external() const { return token_!=0; }
    Re4dcMotionLease(const Re4dcMotionLease&)=delete;
    Re4dcMotionLease& operator=(const Re4dcMotionLease&)=delete;
};
