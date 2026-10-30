#pragma once
#if (defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11) || (defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11)
namespace re4dc::cloth_pub11 {
// The existing per-slot grid/pose generation also fences the exact material
// reader. Unknown zero never wraps back into a valid held source view.
inline unsigned grid_generation[8]={1,1,1,1,1,1,1,1};
inline void grid_write(unsigned slot){if(slot<8 && grid_generation[slot])++grid_generation[slot];}
}
#endif
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
namespace re4dc::cloth_material11 {
// Source admission only: retirement closes before a pool/heap can disappear.
// A completed Set in the same incarnation is the only reopening operation.
// This four-byte mask never changes source gameplay be_flag or pool layout.
inline unsigned open_slots=0;
inline bool admitted(unsigned slot){return slot<8 && (open_slots&(1U<<slot));}
inline void close(unsigned slot){if(slot<8)open_slots&=~(1U<<slot);}
inline void reopen(unsigned slot,unsigned epoch){if(slot<8 && epoch)open_slots|=1U<<slot;}
}
#endif
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
#include "native_draw_result.hpp"
namespace re4dc::cloth_pub11 {
// CF11-PUB-01 diagnostic only. One game/render-context writer, never an IRQ
// callback. No heap, log, source address, stack address or texture pointer.
// A drain is a stream-send observation, NEVER proof of presentation.
constexpr unsigned kCapacity=16;
// ON storage: Collector 1,816 + source generation table 32 = 1,848 bytes.
// O(1) draw/prepare/publication/drain/read; reset/abort visit exactly 16 rows.
// At most 254*49=12,446 cell packets per supported 255x50 source draw. No
// additional queue bytes, heap, I/O or unbounded retries. OFF emits no state.
enum Flags : unsigned { FrameMismatch=1, FrameAborted=2, GenerationUnknown=4, SourceChanged=8 };
struct Source { unsigned slot,incarnation,source_frame,grid_generation,material; };
struct Receipt {
    unsigned id,slot,incarnation,source_frame,grid_generation,native_frame,material;
    unsigned prepared,texture_slot,upload_incarnation,primary_slot,primary_upload;
    unsigned outcome,finished,submitted,queued,direct,accepted,drained,discarded,send_aborted,flags;
    unsigned end_incarnation,end_source_frame,end_grid_generation,end_native_frame;
    unsigned last_drain_frame,last_discard_frame;
};
// outcome/submitted/queued are final only when finished=1. Texture fields are
// valid only when prepared=1. direct/drained mean the native stream-send call
// returned, send_aborted means that call returned with stream_aborted set,
// discarded means a reset retired still-pending queue ownership. FrameAborted
// is set when stream_aborted is observed at reset or frame completion, which
// may be later than the source call. None of these fields certifies GPU output.
static_assert(sizeof(unsigned)==4 && sizeof(Receipt)==112);
// Exact writer meaning: entry to move() or SetPosAng() advances this per-slot
// grid/pose write generation, even if the operation is a no-op. Set() has a new
// owner incarnation and its settling move() calls advance this too. Zero means
// exhausted/unknown, never a wrapped generation. This adds no simulation guard.
inline void barrier(){asm volatile("" ::: "memory");}
struct Collector {
    // External read: read sequence, reject odd/0, copy header/receipt, reread
    // sequence and require equality, then require exact id. An expected prior
    // sequence additionally rejects stale snapshots. Never read a saved row
    // index without its id. Ring overwrite loses evidence, not rendering.
    // This follows completed_frame's single-CPU publication protocol. It is
    // not a C++ inter-thread synchronization API or an IRQ/NMI-safe logger.
    // IDs never reset at a frame/room boundary: at UINT_MAX, new observations
    // refuse (token 0) while rendering continues. The sequence also never wraps;
    // on exhaustion it freezes odd at UINT_MAX, rejecting every later snapshot
    // and update for this process lifetime. No stale node can revive a receipt.
    volatile unsigned sequence=0;
    // Counters saturate. lost_pending counts accepted packets whose receipt
    // was overwritten; their later tokens become stale, never another owner.
    unsigned newest=0,overwritten=0,lost_pending=0,stale=0,exhausted=0;
    Receipt receipts[kCapacity]{};
    bool enter(){
        if(sequence>=~0U-2U){sequence=~0U;exhausted=1;return false;}
        ++sequence;barrier();return true;
    }
    void leave(){barrier();++sequence;}
    static void saturate(unsigned& n){if(n!=~0U)++n;}
    Receipt* find(unsigned id){
        if(!id)return nullptr;
        auto& r=receipts[(id-1)%kCapacity];
        if(r.id==id)return &r;
        saturate(stale);return nullptr;
    }
    unsigned begin(Source s,unsigned native_frame){
        if(!enter())return 0;
        if(newest==~0U){exhausted=1;leave();return 0;}
        const unsigned id=++newest;auto& r=receipts[(id-1)%kCapacity];
        if(r.id){saturate(overwritten);
            const unsigned pending=r.accepted-r.drained-r.discarded-r.send_aborted;
            lost_pending=pending>~0U-lost_pending?~0U:lost_pending+pending;}
        r={};r.id=id;r.slot=s.slot;r.incarnation=s.incarnation;r.source_frame=s.source_frame;
        r.grid_generation=s.grid_generation;r.material=s.material;r.native_frame=native_frame;
        r.texture_slot=r.primary_slot=~0U;r.outcome=unsigned(NativeDrawOutcome::Refused);
        r.last_drain_frame=r.last_discard_frame=~0U;
        if(native_frame!=s.source_frame)r.flags|=FrameMismatch;
        if(!s.grid_generation)r.flags|=GenerationUnknown;
        leave();return id;
    }
    void prepare(unsigned id,unsigned texture,unsigned upload,unsigned primary,unsigned primary_upload){
        if(!id || !enter())return;
        if(auto* r=find(id)){r->prepared=1;r->texture_slot=texture;r->upload_incarnation=upload;
            r->primary_slot=primary;r->primary_upload=primary_upload;}
        leave();
    }
    void publication(unsigned id,bool queued){
        if(!id || !enter())return;
        if(auto* r=find(id)){if(queued)saturate(r->accepted);else saturate(r->direct);}
        leave();
    }
    void finish(unsigned id,NativeDrawResult result,unsigned epoch,unsigned source_frame,unsigned grid,unsigned native_frame){
        if(!id || !enter())return;
        if(auto* r=find(id)){r->outcome=unsigned(result.outcome);r->submitted=result.submitted;
            r->queued=result.queued;r->finished=1;r->end_incarnation=epoch;r->end_source_frame=source_frame;
            r->end_grid_generation=grid;r->end_native_frame=native_frame;
            if(epoch!=r->incarnation || source_frame!=r->source_frame || grid!=r->grid_generation)r->flags|=SourceChanged;
            if(native_frame!=r->native_frame)r->flags|=FrameMismatch;}
        leave();
    }
    void drain(unsigned id,unsigned native_frame,bool aborted){
        if(!id || !enter())return;
        if(auto* r=find(id)){
            if(native_frame!=r->native_frame)r->flags|=FrameMismatch;
            if(r->drained+r->discarded+r->send_aborted<r->accepted){
                r->last_drain_frame=native_frame;
                if(aborted){saturate(r->send_aborted);r->flags|=FrameAborted;}
                else saturate(r->drained);
            }else saturate(stale);
        }
        leave();
    }
    void reset(unsigned native_frame,bool aborted){
        if(!enter())return;
        for(auto& r:receipts)if(r.id){
            const unsigned pending=r.accepted-r.drained-r.discarded-r.send_aborted;
            r.discarded+=pending;
            if(pending)r.last_discard_frame=native_frame;
            if(pending && native_frame!=r.native_frame)r.flags|=FrameMismatch;
            if(aborted && (pending || native_frame==r.native_frame))r.flags|=FrameAborted;
        }
        leave();
    }
    void abort(unsigned native_frame){
        if(!enter())return;
        for(auto& r:receipts)if(r.id && (r.native_frame==native_frame || (r.finished && r.end_native_frame==native_frame) ||
            ((r.drained || r.send_aborted) && r.last_drain_frame==native_frame)))r.flags|=FrameAborted;
        leave();
    }
    unsigned snapshot(unsigned id,unsigned expected_sequence,Receipt* out) const {
        if(!id || !out)return 0;
        const unsigned before=sequence;
        if(!before || (before&1) || (expected_sequence && expected_sequence!=before))return 0;
        barrier();Receipt copy=receipts[(id-1)%kCapacity];barrier();
        if(sequence!=before || copy.id!=id)return 0;
        *out=copy;return before;
    }
};
static_assert(sizeof(Collector)==1816);
}
extern "C" {
// Inspect this bounded symbol via current-ELF readback and the protocol above.
extern re4dc::cloth_pub11::Collector re4dc_cloth_publication11;
unsigned re4dc_cloth_observe_begin11(re4dc::cloth_pub11::Source);
void re4dc_cloth_observe_finish11(unsigned,re4dc::NativeDrawResult,unsigned epoch,unsigned source_frame,unsigned grid);
unsigned re4dc_cloth_snapshot11(unsigned id,unsigned expected_sequence,re4dc::cloth_pub11::Receipt*);
}
#endif
