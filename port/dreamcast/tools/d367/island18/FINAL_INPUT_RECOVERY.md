# Final-room input recovery, 2026-10-18

Private data only; no packaging, character-model change or gameplay promotion.
Source/runtime checkpoint: 528a155f. Fresh diagnostic i18f1mW ELF
d8b8f06fcf1eae64d29cb87170ba4d13cc23db5aed8abed848de1867a0f8d3de,
missing symbols 0, _end=8c3cf9d8. Original Island recipe, 49,152 B KOS
held; ACTOR_CAST_SHADOW_EMPTY, ACTOR_R300_FULL_SOURCE and
SADDLER_MASK_OPAQUE all 0.

## Verified private inputs

Each set is under /root/re4data/private/<set> and immediately mirrored to
C:/Game Dev/Emulators/re4-assets-private/<set>. The table pins SHA256SUMS.

| Set (all end in -20261018) | SHA256SUMS |
|---|---|
| island18-final-source | 9889001d4c6219b009d8f28d7ea4c9c2c6eeddc66ad2a08f15794b34cd3c7eb1 |
| island18-final-worlds | f23797f5d7e3e029fa29fe4404603fdd89cb8f7ecfa1a38111fbc7d19ad4def4 |
| island18-final-rooms | f9abc4f1b61e2093d2e42c7e7e6bb427e340f1eb5892df17bf754ea73ea47249 |
| island18-final-movies | 8ea6f0ef92d84d9b6f5c756abab4666f933b417ac7f32c364c97a4789c42ba37 |
| island18-saddler-motion | bca2f0849e5b2f157c338e54ff43d29ad16f0a3d2953426dd7b73eb8a3959d42 |
| island18-final-sound | 0284815224a413c86a208ed0b14c61f0d24d8aecbe6e9b84b4dc82cfd402bffa |
| island18-r333-world | a5db4b0fdbf7d3e7162c70df27d9d177ab3602290f0e9bfe2c44fe903d021560 |

Whole review Disc 2 SHA 118640eb... and PS2 USA SHA eb0874cf...
were refreshed. Exact source extraction matches existing em31 and seven
EVD dependencies; no retail-Disc-2 mixture.

Retained r331/r332 worlds passed manifest hashes, the current runtime-derived
host checker, source placement/order/IDs and all TPL GS/JL decoder checks.
r333 was absent and was converted with a private snapshot of the unchanged
existing pipeline and its pinned NumPy/Pillow environment. The recovery
workspace was never modified.

Nine of the ten audited final16 payload hashes are restored exactly: r332
world mesh/sidecar/IDs, s00/s10/s20 movie streams, room ARC/DAR, and em31 DRS.
The missing tenth item is the Saddler registry, owned by boss18. All twelve
final-room SFDs now have checked 288x192 full-range transport. s30/s40/s41
remain without GC room-code hooks; conversion adds no events.

## Bounded evidence and remaining gates

The existing incomplete opening hot audit retains 14/77 em31 clips,
255,616 B. Actual-cache host FAST_READ 0/1 tests verify all 77 clips three
times and clean unbind. Requested fixed footprint is resident body
1,452,032 + hot 255,616 + two slabs 64,192 + target metadata 1,232 =
1,773,072 B, before allocation overhead, load staging, other archives and
model/cache storage. The ample host free-memory adapter is not a guest fit,
consumer concurrency, full fight or no-play-read proof.

Sound-only conversion preserves every non-sound byte. The unchanged
1,004,192 B arena contains r332 ROOM/FOOT/em31 banks totaling 645,088 B,
leaving 359,104 B; rates 16,000 / 11,025 / 11,025 Hz. These output archives
match final16 exactly. r333's other-bank census is still pending.

Diagnostic fixtures use source door arrivals. r332 has ordinary START movie
input and god mode for observation; no forced boss state, scenario bits or
kills. Source EVD bodies are only FileExistCheck metadata while available
movie hooks bypass reads. Do not use them as qualified LE fallback events.
Actual staged boot and all selected overlays must match the fresh candidate.

Fresh guest evidence belongs under
C:/Flycast-Evidence/re4-dreamcast/island18-20261018/h-i18f1.
Entry/events, actual memory, alive-vs-drawn, resident lists, TEX/CAST/LEON,
route completion and subjective presentation remain separate gates.
