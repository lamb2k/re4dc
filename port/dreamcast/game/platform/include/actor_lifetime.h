#pragma once
#ifndef RE4DC_ACTOR_TRANSACTION
#define RE4DC_ACTOR_TRANSACTION 0
#endif
class cModel;
class cModelInfo;
#include "actor_ganado_ps2_stump.h"
#if RE4DC_ACTOR_GANADO_PS2_STUMP
#define RE4DC_ACTOR_MATERIAL_RECORD_REVISION 0x20261017u
#else
#define RE4DC_ACTOR_MATERIAL_RECORD_REVISION 0x20260930u
#endif
#if RE4DC_ACTOR_TRANSACTION
extern "C" {
// Called from the EXISTING successful UI archive adoption, with the same real
// byte extent. family: 1 player,2 enemy,3 weapon; key is that owner's live key.
void re4dc_actor_archive_adopt(const void* key,void* base,unsigned bytes,unsigned family);
void re4dc_actor_archive_retire(const void* key);
void re4dc_actor_archive_retire_transient();
void re4dc_actor_forget_range(const void* base,unsigned bytes);
void re4dc_actor_forget_all();
void re4dc_actor_info_adopt(cModelInfo*);
void re4dc_actor_info_retire(const void*);
void re4dc_actor_model_changed(cModel*);
void re4dc_actor_model_retire(cModel*);
void re4dc_actor_data_move(const void*); // invalidate archive before rebasing
// A tracked native conversion may change representation, not source identity.
unsigned re4dc_actor_stream_begin(const void* stream,unsigned capacity);
void re4dc_actor_stream_end(unsigned ticket,const void* stream,unsigned capacity);
int re4dc_actor_material_owner_proof(cModel*,cModelInfo*,unsigned appearance,unsigned role,unsigned revision);
int re4dc_actor_role_bindings(cModel*,unsigned appearance,cModelInfo** out,unsigned count);
#if RE4DC_NMR_POOL
int re4dc_actor_pool_bindings(cModel*,unsigned appearance,unsigned sections,cModelInfo** out,unsigned char* sec,unsigned count);
#endif
unsigned re4dc_actor_binding_revision(cModel*);
unsigned re4dc_actor_role_source_bin(cModel*,cModelInfo*,unsigned appearance,unsigned role);
}
#else
inline void re4dc_actor_archive_adopt(const void*,void*,unsigned,unsigned){}
inline void re4dc_actor_archive_retire(const void*){}
inline void re4dc_actor_archive_retire_transient(){}
inline void re4dc_actor_forget_range(const void*,unsigned){}
inline void re4dc_actor_forget_all(){}
inline void re4dc_actor_info_adopt(cModelInfo*){}
inline void re4dc_actor_info_retire(const void*){}
inline void re4dc_actor_model_changed(cModel*){}
inline void re4dc_actor_model_retire(cModel*){}
inline void re4dc_actor_data_move(const void*){}
inline unsigned re4dc_actor_stream_begin(const void*,unsigned){return 0;}
inline void re4dc_actor_stream_end(unsigned,const void*,unsigned){}
#endif
#if (defined(RE4DC_ACTOR_SPAN_MEMO31) && RE4DC_ACTOR_SPAN_MEMO31) || (defined(RE4DC_ACTOR_TINY_KEEP31) && RE4DC_ACTOR_TINY_KEEP31)
// ACTOR_SPAN_MEMO31 (K45-FIX-PLAN F3) / ACTOR_TINY_KEEP31 (F1): the source-span content memo and the kept tiny-part
// blobs (native_actor_fast.cpp) die with this epoch (model unload / move / retire, actor_lifetime.inc).
extern "C" unsigned re4dc_actor_span_epoch;
#if defined(RE4DC_K45DIAG31) && RE4DC_K45DIAG31
extern "C" void re4dc_k45d_bump(unsigned line);
#define RE4DC_SPAN_EPOCH_BUMP() re4dc_k45d_bump(__LINE__)
#else
#define RE4DC_SPAN_EPOCH_BUMP() ((void)++re4dc_actor_span_epoch)
#endif
#else
#define RE4DC_SPAN_EPOCH_BUMP() ((void)0)
#endif
#if defined(RE4DC_ACTOR_SPAN_MEMO31) && RE4DC_ACTOR_SPAN_MEMO31
// F3 also drops a stream's memo when that stream is rewritten.
extern "C" void re4dc_actor_span_forget(const void* stream,unsigned bytes);
#define RE4DC_SPAN_FORGET(p,n) re4dc_actor_span_forget(p,n)
#else
#define RE4DC_SPAN_FORGET(p,n) ((void)0)
#endif
// Covers every early return of conversion/LOD/bake while a borrowed source
// representation is being mutated. Unregistered scratch streams get ticket0.
struct Re4dcActorStreamMutation {
    const void* p;unsigned bytes,ticket;
    Re4dcActorStreamMutation(const void* q,unsigned n):p(q),bytes(n),ticket(re4dc_actor_stream_begin(q,n)){}
    ~Re4dcActorStreamMutation(){RE4DC_SPAN_FORGET(p,bytes);if(ticket)re4dc_actor_stream_end(ticket,p,bytes);}
};
