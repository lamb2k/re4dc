# GC-ASSET diagnostic gate (I-001, gc-port23)

Incomplete integration. Current protocol is v2 with ten required consumers
(mask3ff); Motion is explicitly unwired and current runtime wired mask remains
1f6. Raw generic geometry stays unqualified because complete UV/color/weight/
shape consumption is unproved, even for a catalog-PS2 BIN. No complete room gate,
same-profile image identity, linked heap or guest acceptance is claimed. Frozen
156658987 selected SH4 receipts use the actual current5e4 profile and merged d5c
source; they do not qualify newer main/cache/raw/v2 changes. Historical v1 logs
are rejected by the current judge, not silently upgraded. See PROTOCOL-V2.md.
Root owns local integration under CODEX-TAKEOVER-20261023.md. No recipe/rr,
asset swaps, pruning, release or media changes belong to this checkpoint.

GC_ASSET_GATE defaults0. Its macros evaluate no arguments, its new translation
units are empty and excluded from the OFF object list. Full image identity
still needs qualification. ON requires PVR_STREAM=1: buffered nonstream
acceptance is unqualified and fails configuration. GC_ASSET_CATALOG_SHA256
also defaults0; an exact independently reviewed64hex pin is required at runtime.
Default0 does not constitute a catalog or gate pass.

## Identity and memory contract

The actual immutable payload SHA256 supplies identity. Names, keys, containers,
APIs and local VQ/mipmap/mesh/audio conversion do not establish PS2 or original
Dreamcast artwork. PS2 bytes may live under GC keys. Unknown stays unknown even
when an exact reviewed exception permits it. Ambiguous/mixed source aliases
must not inherit a PS2 verdict from equivalent locally converted bytes.

The runtime streams the whole immutable CD catalog hash at installation using
512B scratch, validates its fixed records/order/bounds, and retains a read-only
handle instead of a resident whole-disc array. Load/capture matches exact
kind/id/full SHA and stores a4B epoch+index token. One catalog survives room
changes; room observations reset independently. Disc/source replacement
invalidates every token. Existing relocated BINs are never rehashed to renew
an old token in a new epoch. See PROVENANCE-INDEX.md.

Seen is a2KiB record bitset. Eight exact full-identity unknown slots quarantine
unreviewed bytes; overflow is failure. No wildcard or runtime learning expands
the catalog/allowlist. First room-use flush may read one fixed record; accepted
SQ/G2 latches perform no hashing, logging, allocation or file I/O. Repeated
asset consumers each increment their own counter, but only one non-PS2 asset
row appears per room visit. Counts coalesce per asset/consumer/flush, not
physical draw calls. Load, ready, reservation and culled work never count.

## Actual coverage and open boundaries

| Consumer | Implemented accepted path | Remaining proof |
|---|---|---|
| Original source props/actors without NMRS | Original BIN capture/class association before relocation; accepted raw gateway/packet/direct/defer produces explicit serial0 failures | COMPLETE UV/color/weight/shape source/derivation proof; full BIN hash alone is insufficient |
| Weapons | All23 source archive audit: explicit held/secondary classes, exact hand infos, owner family and ambiguous casing/mine member roles; geometry and texture masks | Actual complete runtime/room qualification |
| Motion | Required ordinal9/bit200 and separate identity namespace; actual producer is UNWIRED | Committed pose/history/blend/cache/event sources through accepted visible palette/Frame use; zero counter does not assert zero use |
| Texture and UI pictures | Exact successful loose/tex.pak full member at load, accepted Entry latch and safe flush, both UI draw paths | Complete runtime/room qualification and qualified generated atlases |
| Effect pictures | Single format-aware accepted packet observer with FX context and carried header; discard/retire reset | Complete runtime/room qualification |
| Static replacement packages | Embedded PayloadProof helper and actual UI/deferred pointer+serial bridge | Shared native_static patch is a partial unapplied proposal; mixed-owner impostors, r11f/far-shell, extra R4SG interpretation and movie reload error exits remain open |
| Font glyphs | Actual glyph call graph and immutable local upload boundaries audited | Tile/palette tokens plus exact accepted cache-cell version bridge in progress; generic atlas address alone is not a proof |
| Sound banks | Exact MRAM/ARAM source parts before original transfer; actual AX/SYN ticket before key-on and queued proof after | Actual room admission close/open, shutdown, target and runtime gates |
| Disc sound streams | Exact full immutable aica_str.dat proof, source generation through deferred claim/prefill, actual channel-pair key-on | Actual room admission close/open, shutdown, target and runtime gates |
| Movie picture/audio | Exact container and texture pointer/extent/version boundary audited | Capture and actual accepted picture/audio bridge in progress |

No complete wired mask is declared. Every active/compiled-out consumer branch
needs independent actual-path and negative controls. Missing diagnostics are
failure. A static callsite or self-reported mask is not coverage evidence.

## Original BIN and deferred ownership

Sixteen archive bounds and128 selected BIN records retain compact tokens plus
owner generations. Indexed ARC and named ETM spans use validated complete
member bounds, nearest later member/REL ends and strict empty-alias rules.
Original bytes are hashed before modelInit/calcModelAddr or fast encoding.
Duplicate current adoption preserves the captured identity after mutation.
Conflicting overlaps revoke old proofs before failure, including capacity
failure. UI core/room/option/player/weapon/enemy bind/retire paths are wired;
ordinary enemy early returns are included. CoreDataRead retires fixed core
storage before overwrite. A retired/ambiguous/unbounded source cannot pass.

The model gateway clears caller proof before static replacement and selects an
original BIN only after replacement declines. Both deferred queues freeze its
original serial, mask and optional replacement proof pointer. Replay never
resolves current cModelInfo into a different live BIN. The integrated actual
bridge/gateway/UI controls prove old A cannot be relabeled current B; retired A
fails. Reserved serial exhaustion fails before the replay sentinel can alias.

Static PayloadProof embeds checked geometry and interpretation-sidecar tokens
in stable owner objects. The capped intrusive list adds no separately allocated
table. Accepted latches and replay verify original pointer+serial; catalog
replacement also invalidates tokens. See STATIC-PAYLOAD-BRIDGE.md and its
source-only patch; native_static.cpp itself remains root-owned and unchanged.

## Packet formats and generated textures

The accepted observer shares the TA format rules for32/64B headers/vertices,
including a real96B sprite whose cy=-0.5f tail resembles a new PCW. Carried state
persists only within the same scene; scene/retire reset rejects incomplete
continuations. One FX observer pass preserves split-header EffectPicture use.
Zero or ambiguous Entry matches fail explicitly until an exact qualified
non-Entry payload path is supplied. Filename/API/address-range exemptions are
forbidden for font/movie/native generated textures.

## Audio source and lock contract

See AUDIO-GATE.md. MRAM hashes bounded interpretation metadata; ARAM hashes
source bytes or exact AIC1 header+consumed image. SND_PAD_SKIP stale padding is
excluded. Original DVD transfers/callbacks/sizes are unchanged. Source walking
is serialized by existing DVD-step ownership, never performs catalog I/O, and
changes generation before overwrite. Main pump binds completed source digests.

The independent5ms audio thread can key on before that main publication. A
bounded fallback copies an already completed immutable digest and fixed sound
constituent tag under a metadata try-lock. The event pump resolves it outside
all audio/G2/SQ locks. No waiting/hash/log/IO occurs at key-on. Generation,
request owner, exact offsets, readiness, contention and capacity fail closed.
Disc streams add one full container read+SHA at startup, with512B scratch and
an explicit0x1fffffff byte bound; this diagnostic cost is not free or measured.

Audio tickets capture room/visit before accepted key-on and complete in the
same existing audio mutex critical section. Room transitions must close/open
admission under that mutex, then drain/log END outside it. Late/pending/contended
queues fail END. Shutdown must pump unowned faults after stopping producers.
These real lifecycle hooks remain in progress; core race controls alone do not
complete integration.

## Judge, exceptions and qualification

```
python3 judge.py run-output.txt --room 0111 --room 0113 \
  --allowlist reviewed-current.json --baseline last-accepted.json --json result.json
```

The baseline must be the last accepted list, never an original forever ceiling.
Each exact room/kind/id/full-SHA/provenance exception needs reason, owner and
evidence. Removing exceptions is allowed; readding a removed row, changing its
payload/id, or adding one from a new guest failure fails. The list grants no
PS2 classification and never suppresses diagnostic rows.

BEGIN, separate COUNTS, and END are mandatory and fit the actual256B logger.
The judge rejects missing requested rooms/checkpoints, incomplete wiring or
checks, malformed/duplicate rows, errors/overflow, unreviewed bytes, and first
consumer rows that exceed their matching accepted counters. Explicitly empty
rooms pass only with independent complete consumer coverage.

run_host_tests.sh uses only bounded RAM host fixtures and tests OFF emptiness.
Current51 tests:50 pass and one historical private-pack opt-in skips (that real
case passed independently in seed/helper review); C++ core/member/cursor pass.
The historical seed contains2324 unknown textures and5763 exact historical-load
exceptions across26 rooms. It is not current emission evidence, and other
consumer classes still need pinned reviewed catalog/allowlist seed identities.

Still required: finish consumers/lifecycles and actual negatives, merge current
integration at a clean boundary, root-scheduled target/link checks, same-profile
OFF image identity, KOS48KiB squeeze, h2 s30 340/340 with heap_before, TEXCHK,
CAST-GC, VRAM contiguous refusals0 and GDEMU seed1 (disc/DMA changes require10
per takeover). Keep measured MODELLED and CONSOLE evidence distinct. I-002,
I-003 and I-004 stay behind I-001; Later items need separate authorization.
