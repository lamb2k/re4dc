#pragma once
#include "gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
namespace re4dc_gcasset {
// Source DVD boundaries, after a successful read and before the original copy.
// Hash only declared source spans; completion/catalog I/O is deferred to pump.
void bank_begin(const void* owner,unsigned bank,unsigned part,unsigned bytes);
void bank_piece(const void* owner,unsigned part,unsigned offset,const void*,unsigned bytes);
void bank_end(const void* owner,unsigned part);
unsigned bank_generation(unsigned bank);
void bank_pump(); // main-thread unlocked boundary; may read pinned catalog
void stream_source(const Digest&); // complete immutable AIS1 container, reader outside locks
void stream_source_failed();
unsigned stream_generation();
struct AudioUse {AudioTicket tickets[2]{};CheckedAsset assets[2]{};Digest pending[2]{};unsigned kinds[2]{};unsigned count=0;Consumer consumer=SoundBank;};
// Capture before key-on and finish after the actual accepted key-on, within
// the same existing g_lock/G2 critical section. Both operations copy only.
AudioUse bank_ticket(unsigned bank,unsigned generation);
AudioUse play_ticket(Consumer,CheckedAsset);
AudioUse stream_ticket(unsigned generation);
void played(const AudioUse&);
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
void audio_test_records_lock(bool);
void audio_test_before_publish(void (*)());
#endif
}
#define RE4DC_GCA_BANK_BEGIN(...) re4dc_gcasset::bank_begin(__VA_ARGS__)
#define RE4DC_GCA_BANK_PIECE(owner,part,offset,data,bytes) do{if((part)==1 || (part)==2)re4dc_gcasset::bank_piece(owner,part,offset,data,bytes);}while(0)
#define RE4DC_GCA_BANK_END(owner,part) do{if((part)==1 || (part)==2)re4dc_gcasset::bank_end(owner,part);}while(0)
#else
#define RE4DC_GCA_BANK_BEGIN(...) ((void)0)
#define RE4DC_GCA_BANK_PIECE(...) ((void)0)
#define RE4DC_GCA_BANK_END(...) ((void)0)
#endif
