# Castle chapters 3-2 and 3-3 preparation

Worker branch: `codex/castle18-ch32`, isolated from the main Castle chapter 3-1 work. The coordinator's I-011/I-012 queue is the authority. The final release checks must start from the preceding chapter's real end save and use no warps or flag edits.

## Route and ownership

The source chapter-end calls establish these boundaries:

| Chapter | Required route | End event |
|---|---|---|
| 3-2 | r204, r205, r204 part 1, r209, r20a, r20b | `R20bEventS00`, `SceSetChapterEnd(CHAPTER_3_2)` |
| 3-3 | r20b, r20c, r20f, r206 | `r206_die_event`, `SceSetChapterEnd(CHAPTER_3_3)` |

The prepared original AEV tables independently connect every adjacent room. The r20a to r20c shortcut exists in the door graph but does not replace r20b's chapter-end event. Door availability, keys, switches and room-script callbacks still require actual progress checks. The source r209 salon key is obtained from its leader encounter and used at area 2; no diagnostic inventory grant qualifies that path.

Worker A owns r205/r209/r20a/r20b/r20c/r20f and the Luis death segment of r206. Main retains r204 for chapter 3-1. Worker B owns Ashley's r206 sniper-rescue/reunion and r20d/r20e chapter 3-4 work. Shared file edits require the main Castle claim even where two event segments share r206.cpp.

Private evidence: `C:/Flycast-Evidence/re4-dreamcast/castle18-20261018/workers/ch32/`. The source door audit is `source-door-and-chapter-map.json`. It is metadata evidence, not traversal acceptance.

## First current-program r205 check

The fresh entry check uses the existing full I-009 Castle program c18oimW, ELF `746a2a5feb7cf6293ea31c2738c815a3f6ce305a29c8af82b482ca8758b2136e`. Boot and every overlay match the main lane's current program selection. Existing qualified r205 PS2 Novistador packages, motion files and audio are reused; no new model conversion is needed for this check.

Flycast `cx-r205-walk-fresh02` ran 56.28 seconds. It has an entry warp, then no placement, flags, kills, god mode or input. It is a room-entry diagnostic, not a no-warp chapter check.

- Entry, no fatal error, TEX and Leon native drawing pass.
- Four Novistadors are sampled. NOT-DRAWN passes, but CAST fails: active camouflage still declines the PS2 package and draws through the GC path (0 native, 1426 GC draws). Existing semantic guards remain unchanged.
- Room residency fails with 16 uploads after entry; no evictions, allocation refusals or retries. Last VRAM: pinned 562752, dynamic 1524512, other 90112, free 390048, largest 347008 bytes.
- The existing 49152-byte squeeze remains enabled. The smallest logged KOS total is 89152 bytes.

The first private harness attempt stopped before guest execution because the worker helper path change invalidated its derivative hash. The wrapper was re-derived after asserting the sole copy-script change was the explicit existing helper root; all payload/base/hash checks remain. That refused attempt is retained and is not a game failure.

## r205 resident data candidate

The first-sight audit identifies sixteen missing keys and one already-listed early load. Every new key's actual selected package is present, and the source width/height/format is retained even where its prepared physical image differs. The source list adds only the sixteen new rows. No texture, model, audio or program bytes change.

The private set `castle18-ch32-r205-resident-20261019` is mirrored on C: with SHA256SUMS `a29cb99c8ce03e71cff8925c84917cf6397018e6a521476e14a040e55e5045f2`. Its resident image is `c16366f345830bf823e392154944de8f3fb3fbae035ca85eeee36b2b2088c607`: 5607 records, preserving all 5591 prior records and all other rooms exactly. The additive fixture is `tools/d367/castle18/ch32-r205-resident-20261019.json`.

The matched fresh Flycast gate passes for the observed entry residency. `cx-r205-walk-resident01` ran 55.94 seconds, with gameplay uploads reduced from 16 to 0 and no official VRAM failures. Both payload manifests have identical paths, and only `dc/resident.bin` differs. The program, input, textures, models, audio and all other payloads are exact. Final free VRAM is unchanged at 390048 bytes; largest block is 346112 bytes. Minimum logged KOS stays 89152 bytes with the existing 48 KiB squeeze. The source's active camouflage CAST failure remains unchanged; this is not room acceptance.

`r205-resident-matched-proof.json` seals both logs, program, payload comparison, source-data proof and official gates. This candidate cannot qualify room clear, chapter traversal, save/load or an unvisited camera. At integration, merge the r205 records into the newest resident union; never overwrite newer room additions with this older complete image.

## r209 focused actors and resident candidate

The distant current-program entry was texture-clean but all enemies were crowd-skipped, so it did not qualify their visible models. The closer `cx-r209-walk-focus01` diagnostic ran 56.28 seconds with the same program and current atlas packages. Four em1a actors are sampled, nearest 844 units; em1a draws are 2380 PS2 / 0 GC and Leon 1500 / 0. NOT-DRAWN, TEX and no-fatal checks pass. These are observed roles 07q/08q, not every wave or encounter completion.

Focused play exposes 65 late texture uploads and one residency guard, with no refusals, evictions, retries or missing textures. Final free VRAM is 736000 bytes, largest 688096; minimum logged KOS is 72408 bytes with the existing 48 KiB squeeze. The first-sight audit has one already-listed key and 65 new source keys, all resolved to actual selected packages. Source width/height/format are preserved. Current atlas package differences from historical variants were proven to be only names and CRCs with identical descriptors and pixels; current atlas bytes remain untouched.

The resident-only candidate adds those 65 rows to r209. Private data `castle18-ch32-r209-resident-20261019`, mirrored on C:, has manifest `00620e55c180058945ede7ea832ea58e3f2503b41dad3bc13fa43d9ead2ba614` and resident hash `37a7074f74a90ee2b6aedf6bf74f4cc8620b9f3e4fa7de5b95ace63d1d2b6361`. All 5607 prior records, including r205, and every other room are exact; the new union has 5672 records. Compose these rows into the latest union at integration rather than overwriting later main additions.

The matched `cx-r209-walk-resident01` run passes official residency: 65 gameplay uploads become zero, guard zero, with no failures. The 56.27-second run retains native em1a 2305 / GC 0 and Leon 1500 / 0, and NOT-DRAWN passes. Only resident.bin differs between the two staged payload manifests; all program, input, texture, model and audio bytes are unchanged. Free VRAM is 736000 bytes, largest 673792; minimum KOS remains 72408 with 48 KiB held. `r209-resident-matched-proof.json` seals the comparison. This is observed focused residency and cast coverage, not all waves, the salon key, doors or a chapter route.

## r20b unchanged full PS2 wolf package

The prepared original chapter-3 enemy list has eighteen em22 type-0 rows and one em18 type-6 row in r20b. Chapter-4 reuse has a different list; generic room-name comments do not override the actual source list. The current fixture had no r20b character package. Existing `ps2cast-4-20261011` full PS2 Colmillos geometry can be reused: the current producer with the existing wide-identity option reproduces its r11b package exactly. The r20b package changes only room/header CRC bytes; every byte after the 64-byte header, including geometry, weights, materials and source identities, is identical.

The current prepared em22 BIN4 matches the exact endian-converted source. TPL5 retains the exact header and samplers but has already externalized its pixels: its R4NREF key, dimensions, format and removed size match the original source image. This is not full TPL byte equality. The actual runtime package loader passes the r20b package and refuses it under the wrong room, with address/undefined sanitizers. No admission rule or model converter was changed.

Private `castle18-ch32-r20b-wolf-v2-20261019` is mirrored with manifest `af3c59806f845820a0ff4bfd3d95cf7642b8b989d9d3786870b2660c8d1ae092`; package `bbebff57e0bb7d88ce818ff4c87c6f260f1eb226c677c490ec5067b9a51df229`. Runtime wolf drawing, original back-parasite objects, merchant, full waves and chapter-end playback remain unqualified. The initial narrow-identity producer attempt was correctly refused because today's base exceeds its old 32-source-blob capacity; it is preserved separately. Existing wide identity reproduces the original output exactly.
