# Bounded sound-bank diagnostic boundary

This is I-001 provenance instrumentation, not I-004 asset conversion or a sound
swap. The recovered DVD transfer statements, callbacks, sizes, queues and ARAM
layout remain unchanged. Every addition is behind GC_ASSET_GATE=1.

src/game/dvd.cpp::readMain resolves exact bank slot t in its original type1
(MRAM) and type2 (ARAM) setup cases. Begin retires the prior bank proof before
the next original transfer. After the original read-complete/error/in-flight
checks succeed, piece hashes exactly the current DVD_BUFF span before the
original transfer callback. Completion occurs only after original transfer
completion and before SndBlkInit. The existing cDvdQueue::ReadProc native-step
ownership serializes this shared-buffer walker across source scheduling. The
new helper never opens files or takes the audio mutex from that source step.

MRAM hashes its declared complete source part, including sample/loop/pitch and
instrument interpretation metadata. ARAM hashes its complete source part for
runtime conversion. Prebuilt AIC1 hashes exactly its96-byte header plus declared
consumed AICA image, bounded by the original part size; wholly skipped GC-sized
padding is excluded. SND_PAD_SKIP passes stale DVD_BUFF for padding-only chunks,
and those bytes are deliberately never read by the hasher. Both constituent
full SHA256 identities must be independently reviewed. Conversion to AIC1 does
not establish PS2 or original-authored provenance.

One bounded incremental hasher serves the serialized source part. Fourteen
bank records retain two32-byte pending digests each; actual catalog binding is
deferred to bank_pump at the unlocked main-frame boundary. No catalog fs I/O is
performed from the DVD transfer callback or while g_lock/G2/SQ is held. Begin
changes a monotonic generation for every part, completion must match its owner,
part, exact offsets and bounds, and publication rechecks generation after I/O.
Contention, gaps, duplicate callbacks, cancellation/reload and overflow fail
closed. There is no auto-learning or filename-based origin rule.

audio_aica::blk_begin records the actual source generation under the existing
audio g_lock. Actual AX and SYN dirty-start blocks capture tickets before
ch_start, then queue checked tokens after accepted key-on in the same existing
critical section. Tickets never hash, log, read files, allocate or spin. Missing
or stale generations queue invalid tokens and become explicit errors in the
unlocked pump. Key-off, readiness, mapping, silent unmapped voices and mix-only
updates do not count as key-on. Existing per-room admission/outstanding-ticket
race handling remains mandatory for final room checkpoints.

The production queue normally retains compact checked tokens. The independent
5ms audio thread can key on after a source hash completes but before the next
main-frame catalog publication. That case copies the completed immutable
digest and a fixed sound-constituent tag into its event under a nonblocking
metadata try-lock. The unlocked pump resolves it afterward. A load that is
incomplete, stale or contended still fails; there is no lookup/hash/I/O or wait
under G2. The old arbitrary string/digest adapter remains test-only.
This fallback adds36 bytes per bounded queue entry (1152 B for32 entries) over
the checked-only queue, plus bounded AudioUse stack copies. It remains smaller
than the original identity-string queue. Actual target repricing remains open.

Disc streaming uses one conservative exact full aica_str.dat container SHA,
including AIS1 metadata and all intro/loop payloads. The reader computes it
once before any stream claim or g_lock; main bank_pump binds its checked token.
The claimed stream saves that source generation through existing s.gen prefill
checks. Actual ready+want playback captures one ticket only after all required
channels have been acquired, then completes it after the accepted key-ons.
Ready-only, stopped/missing work and a rejected channel pair do not emit.
Reread/source replacement changes generation and rejects stale prepared work;
catalog replacement also invalidates every old checked token. A mixed-source
container must remain unknown until its complete exact contents are proved.

Cost is explicit: diagnostic builds add one full file read and SHA256 pass at
stream-reader startup, with512-byte scratch; files above0x1fffffff bytes are
rejected by this bounded identity helper. Stream pending metadata adds64 host
BSS bytes and the live Stream gains one gated generation word. No runtime
timing or actual SH4/link/memory gate is claimed for that additional load cost.

Current evidence is bounded host source/helper controls. Movie audio, audio admission close/open under actual g_lock, shutdown
pump, room BEGIN/END, target syntax/size, full image and guest gates remain open.
No complete I-001 pass follows from these bank controls.
