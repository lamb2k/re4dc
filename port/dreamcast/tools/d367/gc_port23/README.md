# GC-ASSET diagnostic gate (I-001, gc-port23)

This is an incomplete integration checkpoint. Host fixtures pass; no target,
room, release-ready or image-identity gate has run. Do not add this to the
release recipe until the consumer integration and room proof below pass.

The texture hook unit now hashes each successful immutable loose/packed member,
latches accepted UI/effect/model texture use, and flushes outside the SQ lock.
Source-extracted controls exercise actual MeshDraw end/direct/batched methods,
header-only versus split vertex packets, effects, and loaded-but-unused keys.
Source geometry, weapon, font, audio/movie and room-close hooks remain incomplete.
No complete consumer wired mask is declared by this checkpoint.
The diagnostic currently requires `PVR_STREAM=1`; an unqualified buffered
nonstream build fails configuration instead of counting a reservation as use.
An accepted textured packet without exactly one cache Entry fails explicitly.
Font/movie/native generated atlases need their own complete payload hooks before
they can qualify such a non-Entry texture; an API/address is not origin proof.

The new source-member helper is a separate incomplete capture unit: sixteen
live archive bounds and128 selected BIN digest records, with actual source
`calcModelAddr` capture before mutation. It hashes only complete, bounded BINs
selected for model construction, preserving the digest through relocation/FE.
Named ETM records and indexed ARC members use the existing source format and
actor-lifetime alias/REL bounds. Duplicate current adoption preserves saved
bytes; retirement revokes the owner generation. Unknown/ambiguous/out-of-bounds
members and capacity failures are coverage errors. Bind/retire and accepted
emitter wiring await the UI file handoff, so this is not source draw coverage.
Host fixtures include normal TPL records among named BINs and assert preparation
never emits a GC-ASSET use row.

`gc_asset_packet_cursor.h` supplies the UI observer's format-aware 32/64-byte
TA continuation handling. The actual observer controls include a real 96-byte
sprite with cy=-0.5f, split 64-byte vertices and 64-byte headers whose tails
resemble PCWs. Reset with an unfinished continuation fails diagnostics rather
than silently accepting an incomplete stream.

`run_host_tests.sh` builds only small host fixtures in `/dev/shm`, deletes its
own outputs and prints the core's text/data/BSS. `GC_ASSET_GATE=0` defaults to
an empty translation unit and argument-free diagnostic macros. The `.mk`
filters that empty object out when included, but full target identity still
needs proof. No asset swap, data prune, recipe or rr production edit is made.

## Provenance and identities

`CatalogRow` matches all of kind, stable id and the **actual immutable payload
SHA256**. A key/path/container/API is a locator and cannot determine origin.
Unknown stays unknown even if its exact exception is allowed. PS2 content
under a GC texture key is PS2 only after matching the reviewed payload digest.
`Authored` means documented original Dreamcast artwork; converting GC pictures
to VQ/PAL/mips does not make them authored. The caller lends a bounded catalog;
the gate does not compile or retain a whole-disc catalog. Its resident bytes
and the emitted lookup/digest metadata must be included in final memory costs.

The core logs one non-PS2/unknown row per kind/id/digest per room visit. It
counts accepted emissions separately for all consumer classes. Its Seen table
uses the first 128 bits of SHA256(kind NUL, id NUL, full payload SHA256) solely
for compact per-room de-duplication; provenance compares the full digest.
Overflow is a failed checkpoint. Repeated consumers of one asset still each
increment their own counter. Load, ready, reservation and wholly culled work
are not emissions. Bind/reuse pointers cannot survive source retirement.
Texture consumer counts acknowledge accepted use once per Entry/consumer/flush;
multiple draws before that safe flush coalesce. They establish asset use, not
physical draw-call totals or performance. Packet header state resets on scene
open and Entry retirement; only a same-scene header/vertex split can join.

## Shared-file integration audit (claims cleared by root)

| Consumer | Actual call graph and required accepted boundary | Remaining work |
|---|---|---|
| Source props / source actors without NMRS | `src/game/trans.cpp` source object loop -> model bridge -> `native_model.cpp::re4dc_model_submit` -> native actor or generic builder -> packet commit / direct end | Bind immutable source BIN identity before preparation; count only output. Do not use SOURCE_OBJECTS calls as draws. |
| Weapons | Same model emission graph, with weapon archive ownership from `native_ui.cpp::re4dc_ui_bind_weapon` | Carry that owner through fast/direct, fallback and deferred paths; hash authored payload at load, not transformed pose arrays. |
| Texture keys | `native_ui.cpp::load` opens exact loose or tex.pak member; accepted model/effect/UI emission uses its Entry | Hash exact member at immutable load, carry Entry identity through eviction/reuse; binding/load alone is not use. No disk access per draw. |
| Effect pictures | `re4dc_effect_sprite`, strip/mesh, haze/stage1 batch -> immediate sends or copied deferred tags -> `re4dc_model_finish_source_draws` | Store copied picture identity with deferred packets; report only the final send; discarded queue is not an emission. |
| Fonts | Source glyph -> glyph cache cell -> `glyph_draw_run` -> final strip flush | Carry immutable sheet/palette identity through cached cells; key/font filename alone is insufficient. |
| UI pictures | `re4dc_ui_submit` -> quad handles -> `ui_draw_quad`; source subscreen/tr packet alternatives | Report textured quad only at accepted final send. Untextured native geometry is not GC picture use. |
| Sample banks | `AXSetVoiceState` resolves voice -> `flush` AX key-on; SYN note -> `flush` note key-on | Capture immutable bank/sample identity before G2. Include both AX and SYN. A mapped/ready voice is not playback. |
| Streams | stream claim -> prep/ready -> `str_flush` actual AICA ring key-on | Identity includes stream entry and actual converted content. Ready or refill alone is not playback. |
| Movies | PS2 seq and movie audio -> picture/key-on emission | Verify PS2 sequence/audio provenance; do not mark clean solely because movie API is used. |

`native_static.cpp` remains root-owned. Its replacement package can draw PS2
geometry under source object ownership; the diagnostic must use the payload
that reached the emitter, not label it GC because the source caller was GC.
Direct, batched SQ, ordinary packet and deferred paths need separate exercise.
Static callsite existence and a declared wired mask are not coverage proof.

## Audio lock / room lifecycle contract

Audio must never log, hash, open files, allocate or spin while holding G2. Copy
an `audio_ticket()` before accepted key-on, and complete `queued(ticket,...)`
inside that same existing audio mutex critical section. The ticket captures
the admitted room/visit; a late delivery cannot read and adopt a newer room.
The bounded queue uses try-lock only, and any contention/drop is a gate error.
The main thread pumps/logs outside the audio/G2 locks. Close admission while
holding the existing audio mutex during a room transition, then release it
before draining/logging END. A crossing outstanding ticket fails END. New room
publication must likewise be serialized against audio key-on. Drain unowned
faults after stopping audio, including shutdown; never kill the producer and
claim a final clean audio checkpoint from an earlier interval.

Host tests deterministically pause a ticket over END/new BEGIN, hold the queue
lock during END, overrun the queue and deliver after END. These are synthetic
contract tests; source integration still needs real room-transition negatives.

## Judge and only-shrinking exceptions

```
python3 judge.py run-output.txt --room 0111 --room 0113 \
  --allowlist reviewed-current.json --baseline last-accepted.json --json result.json
```

The baseline must be the **last accepted** list. An original forever ceiling
would allow previously removed exceptions to return and is invalid policy.
The release integrator owns that pinned previous-list input and should compare
the proposed list with the last accepted Git/release revision. Do not generate
new exceptions from a failing run. Every exact room/kind/id/digest/provenance
entry needs reason, owner and evidence; patterns are rejected. Removing a row
is allowed. Changing a payload/id or restoring a previously removed row fails.
The list does not classify content as PS2 and never suppresses diagnostic rows.

The judge rejects absent begin/end checkpoints in **each** input log, unwired
or unchecked consumers, malformed/duplicate rows, overflow/errors, mismatched
summary/consumer counts, unreviewed bytes, and requested rooms without coverage.
Per-room zero draws are allowed only with complete checked coverage from the
actual active/compiled-out consumer paths.
Consumer counts and END are separate mandatory rows to fit the production
256-byte logger. Host fixtures use that same limit and test maximum-width
numeric fields plus the longest accepted kind/id/consumer combination.

## Qualification still required

1. Finish every runtime hook and exact audit seed. Confirm current room/source
   hashes, rather than treating the audit's load census as new draw evidence.
2. Exercise actual consumer branches, plus targeted negative payload/unknown,
   missing hook and final-checkpoint tests. r111/r113 traps must be observed.
3. Clean checkpoint, merge current integration, then obtain root's build slot.
4. Same-profile knob-off image identity, KOS 48 KiB squeeze, r100 s30 340/340
   with heap_before, TEXCHK, CAST-GC, VRAM contiguous refusals 0, GDEMU seed 1.
5. Hand back the patch and evidence. Claude owns production rr/recipe wiring.

I-002, I-003 and I-004 stay behind this gate. No Later items are authorized here.
