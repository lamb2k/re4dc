# Playable Ashley: model source correspondence, 2026-10-19

The original PS2 pl01 geometry can reuse much of the partner Ashley source mapping **after explicit archive remapping**. This audit does not establish a full-quality converted model: cloth weight transfer and the native contract for the original face/skirt remain open. No converter, runtime, source skeleton or guard changes were made.

The isolated branch is `codex/castle18-playable-ashley`, starting from 335cced0430d3e523dbc02a747f78df61376dfb0. The parent owns the chapter 3-4 route and prepared source textures; this specialist owns only this bounded model audit. Playable Ashley is player model id 0 / type 1, created as cPlAshley, while the existing `ps2_ashley.py` targets partner model id 3 / pl11.

## Original input identities

| Archive | Bytes | SHA256 |
|---|---:|---|
| Original PS2 pl01.dat |909152|6799931bf25a9e53321bef1bcce737c156cb396d29fd7fc4c3436edb59725427|
| Original GC pl01.drs |1527424|7dbffe5a7111f53dd20b491308bdaaca15cf7aab483e3a4866af8824020bb529|
| Original PS2 pl11.dat, comparison only |943392|e244cd783f852350baea1daf2c1161f407a7311020d275add17f19ab69fa723f|
| Original GC pl11.drs, comparison only |1388640|f6fd174c7a02949c467f792eb08ecbd0529034a66189766dd7fd87e0ee991c58|

The original GC pl01 bytes match the chapter worker's retained original exactly. Its recovered endian-converted archive and source-texture preparation are qualified separately in `CASTLE_CH34_WORKER_20261019.md`; neither establishes a PS2 model conversion.

## Exact GC source aliases

All numbers in this table are hexadecimal archive ordinals. There are five base infos and two currently selected hand infos; the alternate hands are separate original identities, not additional simultaneous actors.

| Playable role | pl01 BIN/TPL | Byte-identical original pl11 BIN/TPL |
|---|---|---|
| Body |4/5|4/5|
| Face |7/9|7/B|
| Hair |6/B|6/8|
| Skirt |8/5|9/5|
| Extra |A/5|A/5|
| Default right hand |11/5|C/5|
| Open left hand |14/5|F/5|
| Closed left hand |15/5|10/5|
| r20e right hand |A7/A8|No exact GC partner BIN or TPL alias|

All nine original role attachment tables are retained. Their weighted IDs are inside the complete 141-joint source owner and the attachment IDs are unique and in range. The body owner is byte-identical to partner Ashley's body. The full skirt has matching IDs/parents with a maximum local-rest difference of 7.994e-12 mm from the body; those original bytes are retained, not normalized. A generic local-tree check was initially refused for an attachment naming global owner parents, and the discarded assumption is recorded in the private evidence.

## PS2 correspondence and attachment rests

The PS2 body has 81 joints. Its first 64 match the original GC IDs/parents, with maximum local-rest difference 2.274e-13 mm. All seven original PS2 BINs parse; their non-cloth attachment world rests align with the GC owner within 6.289e-6 mm. These are source precision checks, not animated-pose or cloth equivalence.

| PS2 source | pl01 BIN/TPL | Exact pl11 source payload alias | Raw triangles |
|---|---|---|---:|
| Combined body/head/detail |4/5|4/5|3459|
| Hair/skirt cards |8/B|9/8|963|
| Default right hand |11/A7|C/11|251|
| Open left hand |14/A7|F/11|253|
| Closed left hand |15/A7|10/11|279|
| r20e special right hand |A8/A9|12/13|355|

The PS2 special-hand pair is established by exact payload aliases and material/image compatibility. Its material references image1, so the one-image TPLA7 cannot supply it; TPLA9 contains two images. The original PS2 setup call has not separately been disassembled, so this correspondence is not labelled a direct source-call proof. The extra original PS2 BIN12 (337 triangles), identical to partner BIND, is retained in the inventory without inventing a live role.

## Concrete contracts still required

**Cloth.** GC 141 retains 77 solver outputs: hair 64..84, sweater 85..92 and skirt 93..140. PS2 joints 64..80 are its own 17 cloth outputs, not the GC joints with the same numbers. The existing partner exporter transfers cloth influence from a nearest GC donor surface, truncates mixtures to three weights and may fold links to fit its default 64-slot budget (`ps2_ashley.py:215-281`). For playable Ashley the exact donor alias is skirt BIN 8. Running that exporter unchanged would introduce an unqualified render approximation. No weight transfer, link folding, skeleton replacement or geometry reduction was performed. A full output must preserve the 141-joint runtime owner and qualify its cloth mapping and actual draw-slot count independently.

**Face and skirt.** `pl_ashley.cpp:84` retains the original shape-capable face in Body->pShape; `player.cpp:355` calls ShapeMove. The playable `setFace` is a no-op, so active expressions are not established by this audit. The original skirt explicitly has be_flag 0x40. The current `coarse_actor_owner_registry.inc:1076` face nomination is for partner model 3 only, and `coarse_actor_material.inc:268-310` has no explicit playable-Ashley contract for these face/skirt flags. A renderer owner must establish the actual source-state semantics before native admission. Reusing model 3 identity, deleting the shape or 0x40 flag, removing source arrays, or relaxing the certificate is not a source-compatible fix.

**Actual chapter.** No full pl01 conversion, native pose roundtrip, current target drawing, live alternate-hand transition, STRICT/decisions, KOS 48 KiB, resident texture or no-warp chapter gate ran here. The parent retains the original transition, lantern/crank/puzzle, reunion and save checks. All source motions, bust joints 1D/1E/1A, cloth solvers, collisions and attachments remain untouched. No performance or look claim is made.

## Durable handoff

Private set `/root/re4data/private/castle18-playable-ashley-source-20261019` is immediately mirrored under `C:/Game Dev/Emulators/re4-assets-private/`: 8 files / 5,097,567 B, SHA256SUMS 2d901f993ec49ff4e3ff04ad2b0a629d60969b2c3617ef46e29dec8458f31519.
Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/playable-ashley-20261019/`, including the correspondence census, complete source contracts, ten byte-pinned source ranges and final seal. Reproduction scripts stay under `codex-lanes/castle18/workers/playable-ashley/`. No game bytes or media are tracked in Git. Shared-file claims remain free.

This finishes the requested source audit with the specific cloth and renderer boundaries above. It does not qualify playable Ashley or chapter 3-4. The modeling slot returns to the standing Salazar/guardian/statue boss queue while those boundaries are routed.
