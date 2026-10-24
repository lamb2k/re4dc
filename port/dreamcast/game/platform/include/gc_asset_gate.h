#pragma once
// Diagnostic only. The default-off expansion evaluates no arguments.
#ifndef RE4DC_GC_ASSET_GATE
#define RE4DC_GC_ASSET_GATE 0
#endif
#if RE4DC_GC_ASSET_GATE
#include <cstdint>
namespace re4dc_gcasset {
enum Consumer : unsigned {
    SourceGeometry, Texture, EffectPicture, Weapon, Font, Ui,
    SoundBank, SoundStream, Movie, Motion, ConsumerCount
};
static_assert(SourceGeometry==0 && Movie==8 && Motion==9 && ConsumerCount==10,"preserve diagnostic ordinals");
// Protocol v2 requires Motion but does not implement or advertise its hook.
constexpr unsigned ProtocolVersion=2;
enum Provenance : unsigned { Unknown, GameCube, PS2, Authored };
struct Digest { unsigned char bytes[32]; };
// Immutable-load boundary only; never call while the G2/store-queue lock is held.
Digest fingerprint(const void* bytes, unsigned count);
using Read = unsigned (*)(void* context, void* destination, unsigned bytes);
bool fingerprint_read(Digest&, Read, void* context, unsigned bytes);
// One complete read, with a second digest of the exact prefix in that same
// byte sequence. Cold source/directory binding only; 512-byte scratch.
bool fingerprint_read_prefix(Digest& full,Digest& prefix,Read,void* context,unsigned bytes,unsigned prefix_bytes);
struct CatalogRow {
    const char* kind; const char* id; Digest digest; Provenance provenance;
};
struct CheckedAsset { unsigned value=0; };
struct AssetDescription { char kind[16],id[48];Digest digest;Provenance provenance; };
using CatalogReadAt = unsigned (*)(void* context,unsigned offset,void* destination,unsigned bytes);
// One immutable read-only CD catalog per disc/source epoch. Room changes reset
// observations; persistent owners retain tokens only while their serial lives.
bool install_index(CatalogReadAt,void* context,unsigned bytes,const Digest& expected_sha);
void retire_catalog();
// Main-thread immutable load boundaries only. Default pin "0" fails closed.
// Room changes do not close the handle; disc/source replacement must retire.
bool ensure_disc_catalog();
void retire_disc_catalog();
// Current install epoch (token bits 14..31); a token from an older epoch is stale.
unsigned catalog_generation();
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
unsigned prof_disc_reads();
unsigned long long prof_disc_us();
#endif
CheckedAsset bind_checked(const char* kind,const char* id,const Digest& actual_sha);
bool checked_current(CheckedAsset); // memory only; no catalog read, hashing or logging
bool describe_checked(CheckedAsset,AssetDescription*); // safe boundaries only: may read the catalog
void emitted_checked(Consumer,CheckedAsset); // unlocked flush: first room use may read a record
// Catalog rows must be generated from reviewed payload hashes, never path names.
// The caller owns this immutable table until the next install(). Null is valid:
// every emission then has Unknown provenance, rather than silently becoming PS2.
bool install(const CatalogRow*, unsigned rows);
void begin(unsigned room, unsigned visit, unsigned wired_consumers);
// Runtime lifecycle: prepare/log with admission closed, then publish admission
// under the existing audio mutex. Startup is a named phase with no game room.
void begin_closed(unsigned room,unsigned visit,unsigned wired_consumers);
void begin_startup_closed(unsigned visit,unsigned wired_consumers);
void open_audio_admission(); // fixed state only, no logging/IO
// Publish the next identity under the same audio mutex before unlocked END /
// BEGIN logging. Future-tagged events remain queued until the matching BEGIN.
bool handoff_audio_admission(unsigned room,unsigned visit);
void begin_room_handoff(unsigned room,unsigned visit,unsigned wired_consumers);
enum TransitionReason : unsigned { InitialRoom,RoomRetire };
constexpr unsigned FromStartup=0xffffffffU;
void begin_transition_handoff(unsigned visit,unsigned wired_consumers,unsigned from_room,TransitionReason);
// digest is the hash of the actual immutable authored payload, computed at load
// before pose/colour writes; GC lookup keys and source pointer values are not it.
// Call only after vertices/sample key-on were accepted. Loads, reservations,
// wholly culled draws, rejected packets and silent unmapped voices never emit.
void emitted(Consumer, const char* kind, const char* id, const Digest&);
// Audio key-on holds the G2 lock: enqueue a copied event there, then pump on
// the main thread outside that lock. Never log, allocate or spin in key-on.
struct AudioTicket { unsigned slot, serial; };
// Capture before the accepted key-on; complete within the existing audio mutex
// critical section. A room transition closes/opens admission under that same
// mutex, then prints its checkpoint after releasing the mutex and G2 lock.
AudioTicket audio_ticket();
void close_audio_admission();
void queued_checked(AudioTicket, Consumer, CheckedAsset);
enum PendingSound : unsigned { SoundMram=1,SoundAram=2,StreamContainer=3 };
// Copies an already completed source digest, never hashes or reads a catalog.
void queued_pending(AudioTicket,Consumer,PendingSound,const Digest&);
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
void queued(AudioTicket, Consumer, const char* kind, const char* id, const Digest&);
#endif
void pump();
// An active consumer must call checked() even in a room where it emits nothing.
// For a compiled-out consumer, the integrator explicitly checks its disabled
// branch. Merely installing a catalog or beginning a room does not check hooks.
void checked(Consumer);
void unresolved(Consumer, const char* reason);
void end(unsigned frame);
#if defined(RE4DC_GC_ASSET_TEST)
void test_queue_lock(bool held);
void test_max_counters();
unsigned test_catalog_rows(unsigned);
#endif
constexpr unsigned Required = (1U << ConsumerCount) - 1;
static_assert(Required==0x3ff,"Motion is required even while its producer is unwired");
}
#define RE4DC_GCA_EMITTED(...) ::re4dc_gcasset::emitted(__VA_ARGS__)
#define RE4DC_GCA_CHECKED(...) ::re4dc_gcasset::checked(__VA_ARGS__)
#define RE4DC_GCA_QUEUED(...) ::re4dc_gcasset::queued_checked(__VA_ARGS__)
#else
#define RE4DC_GCA_EMITTED(...) ((void)0)
#define RE4DC_GCA_CHECKED(...) ((void)0)
#define RE4DC_GCA_QUEUED(...) ((void)0)
#endif
