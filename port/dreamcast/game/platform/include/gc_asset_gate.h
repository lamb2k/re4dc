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
    SoundBank, SoundStream, Movie, ConsumerCount
};
enum Provenance : unsigned { Unknown, GameCube, PS2, Authored };
struct Digest { unsigned char bytes[32]; };
// Immutable-load boundary only; never call while the G2/store-queue lock is held.
Digest fingerprint(const void* bytes, unsigned count);
using Read = unsigned (*)(void* context, void* destination, unsigned bytes);
bool fingerprint_read(Digest&, Read, void* context, unsigned bytes);
struct CatalogRow {
    const char* kind; const char* id; Digest digest; Provenance provenance;
};
// Catalog rows must be generated from reviewed payload hashes, never path names.
// The caller owns this immutable table until the next install(). Null is valid:
// every emission then has Unknown provenance, rather than silently becoming PS2.
bool install(const CatalogRow*, unsigned rows);
void begin(unsigned room, unsigned visit, unsigned wired_consumers);
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
void queued(AudioTicket, Consumer, const char* kind, const char* id, const Digest&);
void pump();
// An active consumer must call checked() even in a room where it emits nothing.
// For a compiled-out consumer, the integrator explicitly checks its disabled
// branch. Merely installing a catalog or beginning a room does not check hooks.
void checked(Consumer);
void end(unsigned frame);
#if defined(RE4DC_GC_ASSET_TEST)
void test_queue_lock(bool held);
void test_max_counters();
#endif
constexpr unsigned Required = (1U << ConsumerCount) - 1;
}
#define RE4DC_GCA_EMITTED(...) ::re4dc_gcasset::emitted(__VA_ARGS__)
#define RE4DC_GCA_CHECKED(...) ::re4dc_gcasset::checked(__VA_ARGS__)
#define RE4DC_GCA_QUEUED(...) ::re4dc_gcasset::queued(__VA_ARGS__)
#else
#define RE4DC_GCA_EMITTED(...) ((void)0)
#define RE4DC_GCA_CHECKED(...) ((void)0)
#define RE4DC_GCA_QUEUED(...) ((void)0)
#endif
