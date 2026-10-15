# Lane ps2cast

Rules: port/dreamcast/docs/D367_WORKSTREAMS.md. Branch lane/ps2cast, tree /root/work/lanes/ps2cast, evidence
/root/probe/lanes/ps2cast, private assets `re4-assets-private/ps2cast-20260930/`.

## Goal

The user (2026-09-30): "we need to build the remaining character models and world sourced from PS2". This lane
converts PS2 character models (a converter, like the PS2 world converter; no hand modelling) into the cast bundle
format that `cast_bundle.py` / `coarse_ganado_cast.cpp` consume, compares them with the external cast's v4-fit
Ganados on cost and look, then converts the stage-1 characters the external cast does not cover, in route order.
The external cast delivery (cast-20260925, play-actor-bundle-20260928) is not modified.

## State and next step

- Done: the converter (tools below), reproducible end to end; the first PS2 Ganado (em15 type 00, r101) converted,
  bound to the GC skeleton, packed through the cast's own packer / host check / strip builder, bundled by
  cast_bundle.py unchanged; cost numbers and a look sheet against v4-fit.
- Done: the stage-1 character inventory (below; `tools/ps2_cast_inventory.py`).
- Done: the Ganado models the cast lacks, in route order: **em17 / em16 type 0xc** (female villager; r108 r118
  r111 r113 r11d) converted, host check + strip verify PASS, bundled with em15-00 by cast_bundle.py
  (`bundle-em15-00+em17-0c`, 2 appearances, 13 signatures): 1242 tris, records 1171 (0.943/t), strip vertices
  1894 (1.525/t), 109 palettes, 142 runs, skin stream 3384 B; modelled 0.25x1171 + 0.30x142 + 0.93x109 +
  0.07x1894 = 568 us per drawn Ganado. Rest PS2 -> GC surface p95 body 19.3 / head 4.0 / hands 5.7 mm; over the
  GC poses p95 21.0 (median) : binding correct. **em13 type 6** (r104 r11c r10f): a 61-bone special model whose
  Em13Set type 6 uses nine more model slots (mot 16..20: 0x1f0, 0x1f1, 0x1ed..0x1ef) and whose mot 6 / 11 are
  legs, not hands; converted as a 4-section test (1837 tris, 34 palettes, host check PASS; PS2 matches GC to
  p95 2.3 mm at rest) but it cannot enter the 34-bone Ganado bundle (cast_bundle.py: bone_count != 34): it needs
  the non-Ganado format below and its full model set.
- Sheets: `ps2cast-20260930/sheets/em15-00-look.png` (GC / v4-fit / PS2) and `missing-ganados-look.png`
  (em17-0c, em13-06 partial).
- Next (route order): the non-Ganado characters (em2a traps from r100 on; em29 bats, em2e crawlers in r106;
  then em18, em27, em24, em2f + pl0f, em22, em2b, em3b, em11-07, pl11 Ashley, pl14 Luis, em35) wait on the
  runtime format proposal below (the converter itself only needs per-character model lists and the
  generic pack path); em15 / em16 type 0xb converts with a 2.1 mm bone tolerance if the crowd lane wants the
  PS2 variant of every appearance.
- Trap hit (recorded for the skill): `wsl -- sed -i 's/\r$//' file` typed on the Git Bash command line reaches
  sed as `s/r$//` and deletes a trailing "r" from every line (it cost `return r` and a comment in two tools;
  repaired and verified). Strip CRs only inside script files, or not at all: the Write tool writes LF.

## Stage-1 character inventory (2026-09-30)

`python3 port/dreamcast/tools/ps2_cast_inventory.py /root/probe/lanes/ps2cast/inventory` (WSL): every required
room in route order (plus the alternates r10c/r10e, r11e) through `assets.sh discover` (enemy list entries with
model type, script loads / spawns, event actors). Ganado appearances resolve through each module's EmXXSet
(src/emXX/emXX_set.cpp: TPL / body / head arcs per model type); the key is archive:body/head/tpl. "External cast"
= the GC body and head signatures match a cast Ganado's (what coarse_ganado_cast.cpp matches, so identical
models in other archives are covered automatically), or the cast's animal packs, or leon4k. "PS2 source" = the
PS2 archive has BINs at the same arcs with bone tables equal to the GC's (the converter's precondition). ESL
ids map to archives through read.cpp EmFileTbl (0x03 -> pl11, 0x04 -> pl14, 0x0f -> pl0f). Event rows are evd
actor groups (their models load from the event files, not the enemy archive). Output: inventory.json / .md.

| Character | Name | Model types | Rooms (route order) | External cast | PS2 source | GC tris | PS2 tris |
|---|---|---|---|---|---|---|---|
| event:pl00 | Leon | - | r120 r100 r101 r106 r104 r105 r102 r10b r11b r119 r117 r11c r11f | leon4k (cl lane) | event model (evd files) |  |  |
| event:pl07 | pl07 (event actor) | - | r120 r100 r10b | **missing** | event model (evd files) |  |  |
| em12:0x1bc/0x1be/0x1bd | Ganado (em12 set) | 0x0 | r100 r103 r106 r107 r10a r11a r10c | ganado-em15-00 | yes, skeleton identical | 3013 | 1243 |
| em12:0x1d8/0x1da/0x1d9 | Ganado (em12 set) | 0x1 | r100 r103 r106 r107 r10a r11a r10c | ganado-em12-01 | yes, skeleton identical | 3057 | 1234 |
| em12:0x1dc/0x1de/0x1dd | Ganado (em12 set) | 0x3 | r100 r103 r106 r107 r10a r11a r10c | ganado-em15-03 | yes, skeleton identical | 2829 | 1003 |
| em12:0x1e0/0x1e2/0x1e1 | Ganado (em12 set) | 0x4 | r100 r103 r106 r107 r10a r11a r10c | ganado-em15-04 | yes, skeleton identical | 3014 | 1237 |
| em21 | dog | 0x0,0x1 | r100 r103 r119 | dog-00/01 | em21.dat (1 BINs) |  |  |
| em23 | crow | 0x0 | r100 r105 r108 r109 | crow-folded/spread | em23.dat (3 BINs) |  |  |
| em2a | traps (bear trap, tripwire bombs) | 0x0,0x2 | r100 r106 r107 r105 r10a r111 r113 | **missing** | em2a.dat (3 BINs) |  |  |
| event:em10 | Ganado (em10 set) | - | r100 r101 r106 r104 r119 r11c | **missing** | event model (evd files) |  |  |
| em15:0x1bc/0x1be/0x1bd | Ganado (em15 set, r101 village) | 0x0 | r101 r105 | ganado-em15-00 | yes, skeleton identical | 3013 | 1243 |
| em15:0x1c9/0x1cb/0x1ca | Ganado (em15 set) | 0xb | r101 r105 | ganado-em15-0b | yes, a section rest differs 2.0 mm | 2925 | 1241 |
| em15:0x1dc/0x1de/0x1dd | Ganado (em15 set) | 0x3 | r101 r105 | ganado-em15-03 | yes, skeleton identical | 2829 | 1003 |
| em15:0x1e0/0x1e2/0x1e1 | Ganado (em15 set) | 0x4 | r101 r105 | ganado-em15-04 | yes, skeleton identical | 3014 | 1237 |
| em26 | cow | 0x0,0x1 | r101 r103 | cow-00/01 | em26.dat (1 BINs) |  |  |
| em28 | chicken | 0x0,0x1 | r101 r103 | chicken-00/01 | em28.dat (2 BINs) |  |  |
| event:em13 / em15 / em16 | Ganados in events | - | r101 r106 r119 | **missing** | event model (evd files) |  |  |
| em29 | bats | 0x0 | r106 r10e | **missing** | em29.dat (1 BINs) |  |  |
| em2e | small crawler | - | r106 | **missing** | em2e.dat (1 BINs) |  |  |
| event:em34 | em34/em37/em33 large biter | - | r106 r105 r11f | **missing** | event model (evd files) |  |  |
| event:pl04 | pl04 (event actor) | - | r106 r104 r11c | **missing** | event model (evd files) |  |  |
| em13:0x1bc / 0x1d8 / 0x1dc / 0x1e0 | Ganado (em13 set) | 0x0,0x1,0x3,0x4 | r104 r11c r10f | the em15-00/em12-01/em15-03/em15-04 casts | yes, skeleton identical | 3013 / 3057 / 2829 / 3014 | 1243 / 1234 / 1003 / 1237 |
| em13:0x1e7/0x1e9/0x1e8 | Ganado (em13 set) | 0x6 | r104 r11c r10f | **missing** | yes, skeleton identical | 2055 | 1837 |
| event:em18 | merchant | - | r104 r102 | **missing** | event model (evd files) |  |  |
| event:em30 | large stationary parasite enemy | - | r104 r117 | **missing** | event model (evd files) |  |  |
| em27 | lake fish | 0x0,0x1 | r107 r11b r10e | **missing** | em27.dat (1 BINs) |  |  |
| event:pl02 / pl82 | event actors | - | r105 | **missing** | event model (evd files) |  |  |
| em18 | merchant | 0x0,0x1 | r102 r10e r112 | **missing** | em18.dat (8 BINs) |  |  |
| em17:0x1bc / 0x1d8 / 0x1dc | Ganado (em17 set) | 0x0,0x1,0x3 | r108 r118 r111 r113 | the em15-00/em12-01/em15-03 casts | yes, skeleton identical | 3013 / 3057 / 2829 | 1243 / 1234 / 1003 |
| em17:0x1cd/0x1cf/0x1ce | Ganado (em17 set) | 0xc | r108 r118 r111 r113 | **missing** | yes, skeleton identical | 2981 | 1242 |
| em24 | small box / coil enemy | 0x0 | r10a | **missing** | em24.dat (2 BINs) |  |  |
| em2f (+ event) | lake monster (boss) | 0x0 | r10b | **missing** | em2f.dat (3 BINs) |  |  |
| pl0f (+ event) | lake boat (Del Lago fight) | 0x0,0x2..0x5 | r10b r11b r10e | **missing** | pl0f.dat (5 BINs) |  |  |
| em22 | dog (parasite dog) | 0x0 | r11b r118 | **missing** | em22.dat (3 BINs) |  |  |
| em2b (+ event) | giant | 0x0,0x2 | r119 r11e | **missing** | em2b.dat (14 BINs) |  |  |
| event:em21 | dog | - | r119 | dog-00/01 | event model (evd files) |  |  |
| em3b | truck / mine carts | 0x1,0x2 | r118 r11d | **missing** | em3b.dat (2 BINs) |  |  |
| em11:0x1fc/0x1fe/0x1fd | Ganado (em11 set, 37 bones) | 0x7 | r117 | **missing** | bone tables differ: 0x1fe 13 vs 37, 0x204 4 vs 41, 0x208 4 vs 41 | 2758 | 1065 |
| event:pl01 | pl01 (event actor) | - | r117 r11c r11f | **missing** | event model (evd files) |  |  |
| pl11 | Ashley (partner archive pl11) | - | r117 r11c | **missing** | pl11.dat (8 BINs) |  |  |
| pl14 | Luis (partner, cabin fight r11c) | - | r11c | **missing** | pl14.dat (5 BINs) |  |  |
| em16:0x1c9 / 0x1dc / 0x1e0 | Ganado (em16 set) | 0xb,0x3,0x4 | r11d | the em15-0b/em15-03/em15-04 casts | yes (0x1c9: a section rest differs 2.0 mm) | 2925 / 2829 / 3014 | 1241 / 1003 / 1237 |
| em16:0x1cd/0x1cf/0x1ce | Ganado (em16 set) | 0xc | r11d | **missing** (same models as em17 type 0xc) | yes, skeleton identical | 2981 | 1242 |
| em35 (+ event) | beam hall boss | 0x0,0x1,0x2 | r11f | **missing** | em35.dat (5 BINs) |  |  |

Readings:
- Ganados: the external cast's five appearances cover every Ganado model in the stage except three: em13
  type 6 (r104, r11c, r10f), the type 0xc model shared by em17 / em16 (r108, r118, r111, r113, r11d) and em11
  type 7 (r117; a 37-bone skeleton whose PS2 head / hands carry reduced bone tables: needs an id-based bone map
  in the converter and a runtime that is not fixed at 34 bones). The first two convert with ps2_cast.py as is.
- em15 / em16 type 0xb: the PS2 head BIN's rest differs from the GC head by 2.0 mm (the GC head itself is
  ~1.6 mm off the body; cast_bundle.py reports this spread): converting it needs --bone-tol 2.1 and moves face
  vertices by up to ~2 mm.
- Everything else missing is a non-Ganado character (traps, bats, crawler, fish, merchant, boss, boat, giant,
  parasite dog, carts, Ashley, Luis) or an event actor. The PS2 disc has every one of their archives.
- Leon (pl00) is the cl lane's leon4k; Ashley (pl11) and Luis (pl14) are partner archives with their own sets.

## Proposal: a runtime format for non-Ganado characters (for the coordinator / crowd lane)

coarse_ganado_cast.cpp (and cast_bundle.py) express exactly one kind of model: a 34-bone Ganado appearance of four
sections (body, head, right hand, left hand) matched by GC signatures, one texture. The PS2 conversion itself is
general (the cast packer takes any bone count and section list; the external cast's animal packs already use
that pack layout), so the converter can write the same per-model pack (native arrays, strip blob, runtime
header, texture package, GC signatures) for any character. What the runtime lacks is an adapter that draws a
pack for a non-Ganado model: proposal, not implemented here (runtime code belongs to crowd / coordinator):
- a generic coarse model table keyed by the GC ModelData signature (positions, normals, palettes, vertex FNV)
  per section instead of the fixed role order, with the pack's own bone count (kBones per pack, not a
  static_assert on 34) and parents / inverse bind per pack;
- sections optional (a bat, a trap: one section), several textures per pack (a boss); the skin, pregate and
  one-submit paths already work per chunk;
- the bundle maker (cast_bundle.py) generalised the same way (per pack: bone count, chunk list, signatures).
Until then, non-Ganado characters keep the source renderer path.

## The converter

| Tool | Runs on | Does |
|---|---|---|
| `tools/ps2_bin.py` | any Python | PS2 disc reader: ISO9660 -> BIO4DAT.AFS -> emXX.dat entry table; PS2 skinned model BIN decoder (JADERLINK RE4-PS2-BIN-TOOL layout: bones, materials, VIF nodes, weight maps, strips) |
| `tools/ps2_cast.py convert <preset> <out>` | Windows Python (numpy, PIL) | GC skeleton + signatures from the GC debug disc, PS2 mesh + weights + TPL atlas, validation, then the cast's packer (`character-prototype-20260925/tools/pack_coarse_actor.py`, unchanged) and the host fixture |
| `tools/ps2_cast_native.sh <out>` | WSL | host check (the cast's test_cast_dynamic.cpp built against THIS tree's native_actor_fast.cpp), fastpath build_blob / verify_blob / patch_header -> runtime header, pvrtex VQ + vq_export.py -> `<key>.re4tex` |
| `tools/ps2_cast.py finish / castdir` | Windows Python | manifest (counts from the runtime header), cast dir layout for cast_bundle.py (manifest, source-bindings with GC signatures, source.json, header, texture, em15-hand-N hand-pose signatures) |
| `tools/ps2_cast_run.sh <store> <preset>...` | Git Bash | all stages + the bundle (`<store>/bundle-<tag>`) |
| `tools/ps2_cast_sheet.py <spec> <png>` | Windows Python | look sheet: models side by side, same views and GC pose, runtime look (texture only) + geometry |

Presets: ganado-em15-00 / -0b / -03 / -04 (arcs from Em15Set), ganado-em12-01. Disc extracts are cached on ext4
(`/root/probe/lanes/ps2cast/inputs`, PS2CAST_INPUTS), sha256 in validation.json.

### Binding to the GC skeleton (the mapping)

- The PS2 em15.dat has the same entry slots as the GC em15.drs (arc = entry + 4; body 0x1bc, head 0x1be, hands
  0x1c0 / 0x1c5, TPL 0x1bd). Every section's PS2 bone table equals the GC BIN's: 34 bones, PS2 (id, parent) ==
  GC (partsNo/attach, parent) for all 34, rest translations equal to 5.5e-12 mm (body / head) and 1.1e-4 mm
  (hands). The converter asserts this (tolerance 0.001 mm).
- GC attach == index for all 34 parts, so a PS2 weight's bone id IS the GC part index (identity map, checked).
  Positions: PS2 s16 x the segment factor (1/16 for all 47 segments here) = GC millimetres, same axes (Y up).
  The packer's 1/16 quantization is then exact (max position quantization 0.0 mm).
- Weights: PS2 weight maps (up to 3 bones, float weights summing to 1 +- 3e-8); the packer keeps the last influence
  as the remainder as MakeWeightPalette does. UV = PS2 s16 / 256 (the world converter's rule), placed in its
  TPL image's 256 cell of the atlas. Winding as read agrees with the GC convention (face vs vertex normal
  agreement: PS2 99.8-100 %, GC 99.9-100 %), so no flip. One zero PS2 normal -> the face normal. No degenerate
  strip triangles.
- The runtime identifies the loaded GC model by the GC source signatures (counts + vertex FNV), so the
  appearance keeps the GC signatures and draws the PS2 mesh in its place; no format change was needed.

## Numbers (image, build, evidence)

Ganado em15 type 00 (r101 square), conservative level; counts from cast_bundle.py blob_stats on each runtime
header (the same tool for both). Unit costs: the cl lane's (D367_SQUARE_PERF_PLAN.md): 0.25 us per transformed
vertex (record), 0.30 us per palette switch (run), 0.93 us per palette entry, 0.07 us per emitted strip vertex.

| em15-00 | tris | records (/tri) | strip verts (/tri) | palettes | runs | meshlets | skin stream | modelled us / Ganado |
|---|---|---|---|---|---|---|---|---|
| GC source | 3013 | - | - | 111 (source) | - | - | - | - |
| v4-fit conservative (play build) | 898 | 821 (0.914) | 1402 (1.561) | 151 | 181 | 8 | 4552 B | 498 |
| v4-fit lean | 628 | 628 (1.000) | 1024 (1.631) | 112 | 122 | 7 | 3600 B | 369 |
| **PS2 ps2-v1 (no reduction)** | **1243** | **1148 (0.924)** | **1925 (1.549)** | **93** | **126** | 11 | 3016 B | **546** |

- The PS2 Ganado is NOT cheaper at equal look: +48 us per drawn Ganado vs v4-fit conservative (+9.6 %): 38 % more
  triangles outweigh 38 % fewer palette entries (93 vs 151; the most expensive unit) and fewer runs. Also +345
  triangles for the PVR per Ganado.
- Its look is closer to the GC source than v4-fit (sheet): the PS2 mesh is Capcom's own reduction (41 % of the GC
  triangles) with the source's weights; v4-fit is a Blender reduction to 30 %.
- For the crowd lane: the PS2 mesh has fewer palette entries than the GC source (93 vs 111) and than v4-fit
  (151). A reduction of the PS2 mesh to ~900 triangles at its own palettes would model at ~425 us (-73 us vs
  v4-fit) if records / strips per triangle hold; that is a hypothesis, not built (model reduction is not this
  lane's converter work).
- Texture: PS2 TPL 0x1bd = 3 x 256x256 4-bit CLUT (decoded, GS-unswizzled) -> one 512x512 atlas VQ, 67,584 B VRAM
  per appearance (v4-fit shares one 1024x512 human atlas across its 5 appearances).
- Validation (validation.json): PS2 -> GC surface distance at rest, median / p95 / max mm: body 0.0 / 11.9 /
  88.2, head 0.0 / 2.0 / 6.3, hands 1.9 / 5.7 / 7.1; over 114 GC poses (pose-samples.json, every 4th of 456) the
  p95 stays 18.3 / 2.6 / 9.1 at worst (binding correct: posed error ~ rest error). Host check PASS (1243
  triangles, 3 frames, 0 failures); strip verify PASS (triangle multisets SAME in all 4 infos); the pipeline is
  deterministic (rerun: identical mesh.json a9acd796.., header 74bae93b.., texture package 5f6e64e3..).
- Look sheet: `re4-assets-private/ps2cast-20260930/sheets/em15-00-look.png` (GC source / v4-fit / PS2, front,
  side, back, posed 3/4, geometry).
- Bundle: `re4-assets-private/ps2cast-20260930/bundle-em15-00` (cast_bundle.py, 1 appearance, 11 signatures).
  v4-fit comparison bundles (stats only): /root/probe/lanes/ps2cast/v4fit-bundle{,-lean}.
- No Flycast / hwproject run yet: these are modelled costs from the unit costs, not hardware ms.

## Lane ps2cast-2 (2026-10-10/11): boss lighting, PS2 Del Lago, em17-0c, flat normals

Tree /root/probe/lanes-20261010/ps2cast-2 (from 3cf55917), evidence D:/Flycast-Evidence/re4-dreamcast/ps2cast-2-20261010,
sheets and scripts C:/Game Dev/Emulators/ps2cast-2-20261010, assets re4-assets-private/ps2cast-2-20261010. Arms: play
flags (ROUTE_CH13 ROUTE_CH21 SBB_STUB ...) as lane ps2cast-all; trace arms add LOGIC_TRACE GAME_DECISION_TRACE
PACE_MODE=off. Frame-matched stills use trace arms (PACE off: every tick presented) and the warp `freeze`.

- **El Gigante shading (PS2_GIGANTE).** Cause: the registry owner path drew every non-Leon plan with the constant
  `light` record (the approved flat Ganado look); only ACTOR_GANADO_SOURCE_LIGHT=1 (off in the play recipe) lit
  registry plans, so the PS2 giant drew unlit (lighter, flat). Fix: NATIVE_MODEL_REGISTRY_SOURCE_LIGHT (bit 0 em2b,
  set by PS2_GIGANTE): the giant's registry plan takes actor_source_lighting (LightSetModel's lights, channel,
  ambient, material colour, nrm = part.mv^-T, TEV scale), and the lit kernel folds the torch lights exactly as for
  the source giant (GIGANTE_LIGHTS reads base.model's id: "gigante lights: folds=3502 / 2558" per 600 frames).
  Census: planned 1075, admitted 1075, declined 0. Stills (trace arms, tick 900, gigante-lit-sheet-T.png; play
  arms at 860 / 900 / 940 with the unlit "before", gigante-lit-sheet.png): the light falls the same way; what still
  differs is the PS2 atlas itself (greyer, less contrast than the GC textures).
  hw ms (hb 900:979, drawn / skipped): control 74.30 / 12.45, PS2 lit 76.68 / 11.63; the giant's own buckets
  (RENDER actors + models) 27.62 -> 24.56 (unlit 24.37: lighting costs ~0.2 ms); the +2.4 total is outside the
  giant (kos/irq +2.5, deferred source draws +2.3, IdSys +1.2: frame-mix noise). hb 820:899: control drawn mean
  92.1, PS2 lit 85.0 (6 drawn ticks; the first-view tick 827 is a 181 ms upload frame in the PS2 arm, the window
  phase moved by one frame). Flycast PACE draw ms (300-tick windows 900..3000, hb): control p50 53.5 / max 66.0,
  PS2 lit p50 54.2 / max 62.8.
- **Del Lago bump: today's port draws none.** trans.cpp shaderSetup -> bumpSetup (flags & 1) loads part->bumpTex and
  sets GXSetIndTexOrder / GXSetTevIndBumpXYZ on the specular stage (on GC the bump map offsets the specular / env
  lookup); all of it reaches the GX stubs (gx_stub.cpp). The bridge (materialSetup -> re4dc_model_material,
  model_bridge.cpp re4dc_draw_model_part) binds the colour texture (texId) and the alpha mask only; nothing reads
  bumpTex, and the specular stage is dropped too. No switch exists because there is nothing to switch. So the PS2
  Del Lago without bump changes nothing visible.
- **PS2_DELLAGO=1** (em2f type 0: 2,877 PS2 tris vs 5,820 GC, 35 bones, shift 2; one section, one 116-palette
  chunk). Runtime: NATIVE_MODEL_REGISTRY_SHIFT=1, source lighting (bit 1) and NATIVE_MODEL_REGISTRY_DROP_BUMP: the
  certificate counts the bump need as met for em2f's registry plan (the source draws no bump either), and a role
  texture row with key 0-0 (model_registry.py "source_drops": ["bump"] marks bump-only textures) is proved by its
  exact header and sampler. Data: the r10b room package (dc/native/r10b/registry.re4nmr, 54,528 B; arena 58,096)
  and its atlas, plus a texture-only em2f archive: the r10b disc's em2f.drs had never been through the texture
  pipeline (0 R4NREF references, so no texture row could be proved: registry_declined for every frame, ATX_INFO
  why=6). prepare_enemy_motions.py gains an em2f texture-only contract (--keep-motion-resident; 7 images
  externalized, body 1,624,256 -> 1,280,576 B; the DMY sub-files and the unstripped REL stay as today), then
  aica_banks build as r119 does: only em/em2f.drs changes. Census (k3Dd): planned 1956, admitted 1956, declined 0.
  STRICT: the knob is render-only (fb fixture, both arms on the texture-only archive: frame 0..6911 and room 010b
  STRICT, MUST-IDENTICAL). The archive itself is a load-timing change: its read takes 363 ms instead of 413, so the
  next reads (em27, pl0f) complete three ticks earlier and the r10b trace moves from tick 184 (e 6 -> 11 at 184
  instead of 187); the same door-frame IO class as the r101 VQ fixture (D367_PLAY_BUILD_CHECKLIST 2b); no
  equaliser exists for mid-room reads (dvdhold covers door cycles only).
  Cost (fb fixture, both arms on the texture-only archive; play arms, so the timelines are not frame-locked):
  hw ms without PACE/WAIT, hb 2340:2419 control 47.37 / PS2 40.99 (RENDER 24.32 -> 15.09), hb 4100:4179 control
  43.21 / PS2 45.97 (RENDER 10.58 -> 8.92; kos/irq +4.6 is outside the boss). Flycast PACE draw ms (300-tick windows
  1500..9600): control p50 35.7 / p99 38.8 / max 38.8, 26.9 fps; PS2 p50 19.7 / p99 41.1 / max 41.1, 28.8 fps.
  **Open defect (why it stays default off):** frame-matched trace stills (dellago-sheet-T.png, ticks 2410 / 2440 /
  2470, logic STRICT) agree at 2410 and 2470 (same arm, same light; the PS2 texture is smoother), but at 2440 the PS2
  arm fills the screen with a close furry surface where GC shows the distant legs: some PS2 part is drawn at the
  camera where the source draws nothing or something else (suspect: a part the source hides per frame, or a
  part-to-bone mapping the shift-2 conversion got wrong). Not diagnosed yet.
- **em17-0c (female Ganado, r108 / r118): stopped, needs a decision.** Converted again (1,242 tris) and a registry
  spec written (r108 + r118 packages), but the GC head (BIN 463) materials need mask/alpha pass + source pass (the
  hair), which no flat owner path implements; the PS2 TPL for it is fully opaque (PSMT4, alpha 128 everywhere), so
  the PS2 model has no hair mask to draw. Options: a mask contract on the registry path, or accept the PS2 opaque
  hair (a "source_drops"-style rule for the mask, which changes today's hair edges).
- **PS2_GANADO house cost with flat normals.** r100 house (h2 1450:1569): the reported "+3.2 ms skip ticks" is a frame
  mix, not cost: the window's light frames (PACE-skipped, ~22 ms) are 5 of 17 in the control and 2 of 17 in both
  PS2 arms; the heavy frames average control 41.32 / flat normals 40.85 (full normals, lane ps2cast-all: 41.18 /
  40.79). Flat vs full normals pixel check (trace arms, r101 square, frozen tick 1370, ganado-flatn-T.png): one
  pixel differs (max 8 of 255): identical, as expected for the unlit cast.
- **Gates** (both knobs). Knob-off identity: play flags and the default recipe vs 3cf55917 byte-identical images,
  overlays identical, missing.txt empty. H2 (ACT_CAP=0) STRICT 1450..1569, 0..740, 1218..; decision_cmp
  MUST-IDENTICAL; s30 340/340 heap_before 61,600 = control. r101 bell STRICT (7,496 / 7,483 ticks) MUST-IDENTICAL.
  r119 g3 STRICT 2,705 MUST-IDENTICAL (PS2_GIGANTE). New Game 1971 / 2360, s40 1175. MISALIGN 0, HALT 0 (the
  freeze runs end in the 30 s hang screen by design).

## Lane ps2cast-3 (2026-10-11): Del Lago 2440 fixed, female Ganado with hair mask, GC texture bakes

Evidence: D:/Flycast-Evidence/re4-dreamcast/ps2cast-3-20261011 (sheets dl-fight-1/2, f17-r108, f17-head, gig-gctex-900,
dl-gctex in C:/Game Dev/Emulators/ps2cast-3-20261011). Assets: re4-assets-private/ps2cast-3-20261011 (store f3bf6e7).

- **Del Lago tick 2440: fixed (PS2_DELLAGO now sets RE4DC_NMR_SOURCE_CULL=2).** Cause: at 2440 the camera is inside the
  body (vertices 7.1 m behind it, same em2f state in both arms, DLDIAG dump). The source path culls back faces
  (model_bridge.cpp re4dc_model_cull of CullMode 0), so from inside it shows only the legs; every owner path draws with
  cull none, so the registry Del Lago showed the body's inside over the whole screen. The registry draw of em2f now takes
  the source cull (coarse_actor_transaction.inc). The PS2 mesh keeps the GC winding (an offline render culls the same
  faces in both meshes). Frame-matched stills (same prepared em2f archive in both arms, logic STRICT) at 1600, 2425,
  2440, 2470, 3500, 5000, 6500, 8000: all agree (2440 shows the claw and legs as GC; the PS2 leg strands are thinner).
  On this fixture the boss is in view only from ~1600 to ~2470; later ticks show water and fog in both arms.
- **PS2_GANADO_F=1 (new, default off): em17 / em16 type 0xc through the registry owner path with the PS2 mesh and the GC
  hair mask.** NATIVE_MODEL_REGISTRY_MASK=1: a package section may carry two runs (ref word 12: opaque geometry, hair
  geometry, colour texture, mask texture); the hair run draws with the Leon hair material (TR, blended, no depth write,
  same-UV I4 mask, ARGB4444 pair keyed as model_mask_key). tools/ps2_mask_runs.py classifies the head's hair triangles
  (35 of 386, distance to the GC hair cards median 1.8 mm, max 6.2), bakes the GC colour + mask onto UV islands packed
  into a 64x128 pair (16 KiB VRAM, the size of today's GC hair pair), writes the run blobs; model_registry.py
  "mask_runs" packages them (r108 / r118 packages 42,976 B). Coincident cross-material triangles: 0. Run geometries
  decode on demand from the package (no static per-geometry table). r108 (Leon at 51300, 8624, -6071, the live entry
  147): admitted 600/600, declined 0; sheet f17-r108.png / f17-head.png (hair draws masked, no notches; the PS2 body
  reads darker than the GC source). hwproject r108 900..979 (drawn frames): 49.25 -> 46.74 ms (registry draw 1.63 ms);
  per-tick p50 / p99 / max 47.0 / 50.3 / 50.3 -> 46.6 / 47.1 / 47.1. **Heap gate: fails alone** (s30 heap_before
  57,504 < control 61,600; layout-sensitive: the smaller image after the table removal measured the same 57,504);
  with UI_OS=1 both knobs give 65,696 (UI_OS=1 control 69,792). Needs a decision: stack PS2_GANADO_F with UI_OS=1, or
  find room elsewhere.
- **PS2_GIGANTE_GCTEX (data only, no knob):** the GC TPL baked onto the PS2 UVs (tools/ps2_gctex_bake.py; closest
  surface median 3.7 mm, p95 23 mm), same 1024x512 VQ atlas (133,120 B VRAM, delta 0), package 82,400 B (header and
  mesh bytes unchanged), so hw ms is unchanged by construction. Sheet gig-gctex-900.png: sharper detail (wound, eye,
  folds); the warmer GC hue is not the texture (both atlases mean RGB 60/51/44 vs 59/51/45) but the source material
  colour, so the bake does not close the colour gap.
- **Del Lago GC texture bake:** same loss (the PS2 atlas uses the top 512x256 of 512x512); baked at the same size and
  format (67,728 B, VRAM delta 0), package 54,528 B. Sheet dl-gctex.png (2470): more GC contrast pattern, modest. A UV
  rescale to the full 512x512 would recover the GC resolution (changes the uv words; not done).
- **Del Lago hw ms (cull fix), r10b 2340..2419 drawn frames:** control 71.35 ms (3 drawn) vs PS2_DELLAGO 67.87 ms (11
  drawn); the pacing mix differs (control skips 9 of 12), so compare drawn frames.
- **Gates** (knobs PS2_DELLAGO=1 PS2_GANADO_F=1, final code): knob-off identity (play knobs and default recipe vs
  e8fa2b54, images and overlays identical, missing.txt empty); H2 ACT_CAP=0 STRICT 1450..1569, 0..740, 1218..,
  decision_cmp MUST-IDENTICAL; r101 bell STRICT 7,483 MUST-IDENTICAL; r10b fight STRICT 6,914 (same-archive control);
  r108 STRICT 1,100 (em17 on screen); New Game 1971 / 2360, s40 1175; MISALIGN 0; HALT 0 outside the freeze screens;
  s30 340/340 with heap 61,600 for PS2_DELLAGO alone (= control), 57,504 with PS2_GANADO_F (see above).

## Lane ps2cast-4 (2026-10-11): PS2 animals, PS2 parasite dog, Ashley and crow findings

Evidence D:/Flycast-Evidence/re4-dreamcast/ps2cast-4-20261011, scripts / sheets C:/Game Dev/Emulators/ps2cast-4-20261011,
assets re4-assets-private/ps2cast-4-20261011 (store 3452312). Asset recipe: PS2 mesh; texture = PS2 TPL where it is not
weaker (the GC bakes of every family below showed seam streaks and no gain at equal resolution); VQ RGB565 as today.

- **PS2_ANIMALS=1** (data knob, image byte-identical to knob off): dog em21 (699 -> 1,059 tris), cow em26 (700 -> 652),
  chicken em28 (149 -> 408) from the PS2 meshes (ps2_cast.py presets dog-00/01, cow-00/01, chicken-00/01;
  PS2CAST_FLAT_NORMALS=1: the animals draw with the constant actor light, normals never read). Packages r100 / r101 / r103
  from tools/d367/model-registry/ps2-animals.json (same descriptor names and rooms as today's packages): arena r100
  26,248 -> 24,144, r101 28,872 -> 23,936, r103 57,936 -> 50,896 B. VRAM unchanged (dog / chicken 128x128 VQ 6,144 B, cow
  256x256 VQ 18,432 B each, as today). Runs (PS2): dog 203, cow 109, chicken 46. Census: admitted / declined identical to
  today (r100 dog 5,803/0; r103 cow-00 16,797/3, cow-01 4,199/1, chickens 12,600 / 4,200 / 0). hw ms (drawn, 600:679):
  r100 dog view 44.76 -> 44.52, r103 62.98 -> 62.49.
  Gates: knob-off identity (play + default recipe); H2 STRICT 1450..1569, 0..740, 1218.., room, decision_cmp
  MUST-IDENTICAL; r101 bell STRICT 7,496; r103 STRICT 3,836; s30 340/340 heap_before 63,712 >= 61,600 (the first full-normal
  packages gave 58,880: rejected); New Game 1971 / 2360 / 1175; MISALIGN / HALT / MISSING 0.
- **PS2_WOLF=1** (em22, r11b r118): 3,978 -> 1,735 tris, 177 palettes, 264 runs; registry owner path with the source
  lighting record (NMR_SOURCE_LIGHT bit 4) and source cull (NMR_SOURCE_CULL bit 4), as the source path draws it today. Atlas
  512x256 VQ (pack_atlas now takes a 2:1 atlas of a single wide image). Needs the texture-prepared em/em22.drs
  (prepare_enemy_motions.py em22 texture contract, then aica_banks; body 903,776 -> 822,112 B): on today's archive every
  plan is registry-declined (ATX_INFO why=6, the Del Lago case). The archive is a load-timing change of the same class as
  em2f's. Packages r11b / r118 36,768 B (arena 42,168). r118 with PS2_GANADO_F needs one combined package (not built).
  Census r11b: admitted 1,449 / declined 0 by frame 788. hw ms r11b 900:979 drawn 75.64 -> 64.86 (frame mix differs).
  Image +640 B (_end); s30 heap_before 61,600 = control (no IMAGE_PAD needed). Gates: H2 windows STRICT, decision_cmp
  MUST-IDENTICAL (whole-room align: field om differs on 476 ticks from 741, run-to-run movie timing, unverified); r11b
  STRICT 3,700 (both arms on the prepared archive); New Game 1971 / 2360 / 1175; MISALIGN / HALT / MISSING 0.
- **Crow em23: not converted, needs a decision.** PS2 750 / 668 tris (folded / spread; the PS2 wing BINs have reduced bone
  tables, ps2_cast.py subset_bones handles them). Today it draws on the source path; on the registry path its GC materials
  are a contract: body flag 0x83 (bump + specularSetup2: both GX-only on the DC source path, so a source_drops rule is
  justified) and the folded wings' I4 mask (the PS2 wing is opaque: mask runs, or accept the PS2 opaque wing).
- **Ashley pl11: PS2 differs, not converted, needs a decision.** Body 3,819 GC / 3,459 PS2 tris; the PS2 skeleton has 81
  bones, the GC 141: bones 64..80 (skirt / cloth) differ in parent and rest, so PS2 weights cannot bind the GC cloth
  skeleton without re-weighting; 141 bones also exceed the registry cap (128) and pl11 is a partner, not an em model.
- The objects survey (om / etc / set pieces): C:/Game Dev/Emulators/ps2cast-4-20261011/OBJECTS.md (every loose object is
  still GC source).

## PS2_ASHLEY at run time (lane ps2cast, 2026-10-15; test 13, default off)

PS2_ASHLEY (778e4674) was offline-checked only. The first Flycast census (r117 follow warp) showed Ashley
registry-declined on every frame, so she stayed on her GameCube model. 33014c75 fixes four things, all behind the knob:

1. Four owner materials. Her plan has the atlas plus three mask pairs (head, hair, extra 9). The owner capacity was three,
   so the plan declined at the third mask run. RE4DC_ACTOR_MATERIALS=4 now applies in every object under the knob.
2. TEV group 1. The partner Ashley uses group 1, like Leon and Luis. Before the fix, the certificate declined her as a
   LiveModifier.
3. The head shape bit and the Morph / Bump needs, accepted in the certificate under =2 (rest face; Bump is dropped as for
   Del Lago).
4. The slot palettes' bind. A draw-slot descriptor's bind run has one inverse per SOURCE joint, so slot b must use
   bind[source_parents[source_bones + b]]. Before the fix she drew with large spikes on the cloth / hair slots.

Results (MODELLED, Flycast; build lane/ps2cast3 33014c75, test 11 recipe + PS2_ASHLEY=2, disc data
ps2lib cast/r117/ashley-pl11):
- Census r117 follow warp, 120 s: admitted 2400/2400 drawn frames, declines 0. A walk run with 4 Leon gotos, so she
  runs after him: 2530 admitted, 0 declines. TEX_CHECK 0 fails. No HALT / FAULT / MISSING.
- H2 STRICT 4702 ticks MUST-IDENTICAL, s30 340/340, heap_before 126,688. r117 follow STRICT 2402 MUST-IDENTICAL
  (knob-off control padded to the same _end, PAD_T=1088).
- Knob off: bin 217b1110 and overlays 9cbc854b, identical to before the fix.
- Heap 4: the r117 package uses 239,688 B. Look sheet (GC on DC | PS2 on DC back / front | PCSX2):
  C:/Flycast-Evidence/re4-dreamcast/ps2cast-20261014/ashley-sheet/ASHLEY-SHEET.png. On DC she draws flat-lit and
  slightly brighter than PS2, like the merchant without PS2_CAST_MERCHANT_LIT.
- Not covered: cutscenes s00 / s10, because the ch21 padscript stalls in the Files menu (a harness limit). Rooms after
  r117 (r11c / r11f / r112) have no packages yet. Face expressions still need the user's look decision (=2 shows the
  rest face).

## PS2_ASHLEY_ROOMS: Ashley in the chapter 2-2 / 2-3 rooms (lane ps2cast, 2026-10-15; test 13, default off)

Ashley follows Leon through r117, r118, r112, r111, r113, r11c and r11f. Six of those rooms already have a registry package
for other PS2 actors (r111 / r113 crows, r112 merchant, r118 em17 + wolf, r11c Luis, r11f Mendez). One merged package per
room did not fit (r112: 35 chunks against 32; r11f: 366,432 + 229,952 B against the 256 KiB ceiling), and the coordinator
chose a second package per room (10-15). Heap 4 is the same either way (both files are resident while the room is open).

- Disc data: the room keeps its own `dc/native/r<room>/registry.re4nmr`; Ashley's package is
  `dc/native/r<room>/partner.re4nmr` (229,952 B, heap-4 cell 229,984 B; the r112 / r118 / r11f payloads are identical to
  r111's apart from the header room). r117 has no room package, so her package stays `registry.re4nmr` there.
- Loader (coarse_actor_registry_pack.inc, RE4DC_NMR_PARTNER): both files are read and validated before anything is
  published. pack_validate takes a PackBase (the room package's counts) and places the partner's records after the room
  package's; indices inside a file stay file-relative (format unchanged), and the run-time cross references are made
  absolute (descriptor appearance / first chunk, chunk texture / geometry / mask runs, role appearance). Texture keys stay
  unique across both files. One view; two heap-4 cells (the room cell holds both skin arenas, one contiguous arena);
  registry_gview reads a geometry from its own package. A room without registry.re4nmr publishes the partner alone; a
  partner that fails validation is refused alone ("NMRPACK partner refuse"), the room package stays published.
- Capacities under the knob: chunks 48 (r112: 14 + 21), fact models 20 (r112: 8 + 10). Everything else fits.
- Certificate fix (route builds): ROUTE_CH22's TEV-group rule named only Luis (id 4), so Ashley (id 3, group 1) failed
  semantics clause 28 on every chapter 2 build. With PS2_ASHLEY both partners take group 1 (coarse_actor_material.inc).
- Host check: `tools/d367/ps2cast/partner_pack_test.py <game> <out> <room> <room package|-> <partner>` builds the target
  validator with the partner flags; all seven rooms pass (r111 r112 r113 r117 r118 r11c r11f, route flags CH22 + CH23,
  bones 96, immutable alias).
- Specs: model-registry/ps2-ashley-r112.json, -r118.json, -r11f.json (ashley_rooms.py).

Run time (Flycast, MODELLED; test-only tree test/ps2cast-ch2 = test/alivecap-ch2-1015 eb6413b6 + this lane; route recipe
of the ch22 lane's cxac1 + PS2_CAST_MERCHANT=1 PS2_ASHLEY=2 PS2_ASHLEY_ROOMS=1 ACTOR_TRANSACTION_DIAG=1; data ch22
route-v6 + ps2lib Ashley packages + the texture-prepared em18.drs; one 55 s warp run per room, status 3 0x04000000):
- r112: room package + partner open (heap 4 7,569,152 -> 7,215,968: both cells 352,968 B); Ashley AND the merchant
  admitted on every drawn frame (ATX ev 16/18 only; NMRS no declines), TEX_CHECK 0, LEON-GC 0, no HALT / FAULT. The
  merchant needed the texture-prepared em18.drs (route-v6 carries the untreated one: ATX_INFO why=6) and
  PS2_CAST_MERCHANT=1 (in the test 12 recipe already).
- r117: Ashley admitted (her package alone). TEX_CHECK shows 3 lines for e1cd6919-a1b4d41c (missing from the route data);
  the knob-off control on the same data shows the same key plus 78 VRAM-budget / upload lines, so this is route data,
  not this change (owner: chapter 2 route data / VRAM).
- All seven rooms (disc d2pa4: every route overlay, route-v6's bounded texture-prepared pl11.drs, no pl11 override):
  Ashley admitted on every drawn frame (ATX ev 16 / 18; 0 declines) in r117 r118 r112 r111 r113 r11c r11f; TEX_CHECK 0
  in all but r117 (the pre-existing e1cd6919 above); LEON-GC 0; HALT / FAULT / MISSING 0. Heap 4 at room entry (room +
  partner cells): r111 / r113 264,800 B, r112 353,184, r118 328,064, r11c 384,768, r11f 624,512 (both drawn in r11f with
  MOTION_BOUNDED_R11F's bounded pl11). Not this change (pre-existing, other owners): em17 GC in r111 / r113 / r118
  (ATX_INFO why=5 / 2), em13 GC in r11c, em11 GC in r117.
- An earlier disc (d2pa3) lacked em35 / em3b / pl14 overlays (route data tree older than the arm): r118 HALTed "route
  overlay missing". master.sh now copies every overlay the arm links.
- STRICT per room (trace arms cxtk1 knob on vs cxta3 off, IMAGE_PAD_BYTES=2944, _end 8c430ddc both; same disc data; stop
  tick 600 or the 60 s cap): r117 0..453, r118 0..571, r112 0..601, r111 0..412, r113 0..467, r11c 0..355, r11f 0..553:
  STRICT, decisions MUST-IDENTICAL, 0 overruns, 0 HALT. (A warp start is not continued play: these prove the knob
  changes no logic in each room's first ~6-10 s, not whole-room play.)
- The r112 merchant: route-v7 (ch22 lane fix/route-v7.json) = route-v6 + the texture-prepared em18.drs.
- Knob-off identity (test 11 recipe, play arm): image 412198a0, all overlays identical to 80f2f58b; with PS2_ASHLEY=2 and
  the rooms knob off, image eafa01ab identical too.

## Ready to land

- lane ps2cast-4: PS2_ANIMALS (data knob), PS2_WOLF (default off; disc needs the prepared em22.drs + r11b/r118 packages),
  ps2_cast.py presets / subset_bones / 2:1 atlas / animal flat normals, prepare_enemy_motions em22 contract, specs
  ps2-animals.json / ps2-wolf.json.
- lane ps2cast-3: RE4DC_NMR_SOURCE_CULL under PS2_DELLAGO (the 2440 fix; PS2_DELLAGO's open defect is closed),
  NATIVE_MODEL_REGISTRY_MASK + PS2_GANADO_F (default off; heap gate needs UI_OS=1 or a decision), tools/ps2_mask_runs.py,
  tools/ps2_gctex_bake.py, model_registry.py mask_runs. Discs: r108 / r118 packages + pair in tex.pak
  (re4-assets-private/ps2cast-3-20261011 em17-0c-mask2); gctex atlases are data swaps of the PS2 packages.
- lane ps2cast-2: NATIVE_MODEL_REGISTRY_SOURCE_LIGHT (PS2_GIGANTE lit), PS2_DELLAGO (default off, open tick-2440 defect; its disc needs the
  r10b package, the atlas and the texture-only em2f.drs from re4-assets-private/ps2cast-2-20261010), the em2f
  texture-only contract, model_registry.py source_drops. See the section above.

## Test 12: PS2 Ganado accessories (cObj12), data set acc12all (2026-10-15)

What: em10SetAccesory hangs a cObj12 on a Ganado's head joint (SetObj12 + setParent(em, 4, 1)) from the Ganado
archive's ARC 0x25F..0x269: caps (Cap_type 1/2: BIN 0x25F, TPL 0x260 / 0x261), kinds 3/4 (BIN 0x262, TPL 0x263 /
0x264), hats (kinds 5/6: BIN 0x265, TPL 0x266 / 0x267), glasses (pGlasses: BIN 0x268, TPL 0x269, 2 images). Every disc
drew the GameCube data (crowd12 census: 2,786 of 7,943 actor-path triangles at 12 alive in the village).

How (disc data only, the executable is unchanged; tools/d367/ps2cast/ps2_accessories.py): each BIN is rebuilt with the
PS2 BIN of the same ARC (ps2_objects.rebuild: GC header, joints, part headers kept; le_mirror form) and each TPL
record gets the key of the PS2 picture of the same image (decoded from the PS2 TPL, encoded as a dc/tex package: 64x64,
32x64 and 128x128 opaque VQ; the glasses' two 32x32 images ARGB4444 with the PS2 lens alpha). The span ARC 0x25F..0x268
is re-laid out in place: the archive keeps its size and every byte outside the span; the moved TPL records' NTR rows
are rebased and the NTR crc refreshed; empty alias slots (em17 0x262..0x264) follow their entry. Every output must
pass a port of SourceIdentityTable::adopt (read.cpp halts "invalid prepared enemy texture identities" otherwise: the
first em15 candidate wrote the NTR crc one word off and halted at r101 entry; the check now runs in build and census).
GC triangles = PS2 triangles (104 / 116 / 102 / 112): the PS2 meshes are the same models, so no CPU or TA saving.
Texture VRAM: the 8 GC packages (16-bit, 94,208 B) become 27,648 B (VQ), -66,560 B when all are resident.
The GC and PS2 accessory entries are byte-identical in em12 (r100, r11a), em13 (r104), em15 (r101) and em17 (r108,
without 0x262..0x264); em11 (r117) has a different layout (not converted). Outputs: re4-assets-private
ps2lib/cast/common/acc12/{em12,em13,em15,em17}.drs + tex/ (8 packages) + per-archive reports. Data sets (t11-fix.py):
acc12 = em15 only, acc12all = all four. ACC_CROWD_TIER (crowd12) is unaffected: object id, kind and parenting are the
source's.

Gates (Flycast, MODELLED; arms acctT / accmW / acctW from lane/acc12 = lane/t11 20a3b047 code; control = T11_DATA,
test = T11_DATA + acc12 / acc12all; evidence C:/Flycast-Evidence/re4-dreamcast/ps2cast-20261014/acc12):
| Gate | Result |
|---|---|
| Knob-off identity | by construction: no code change (the arms are the lane/t11 images) |
| r101 square STRICT (sq101c vs sq101a2, stop 2400) | STRICT 2402 ticks, 0 masked, decisions MUST-IDENTICAL |
| H2 + s30 (h2c vs h2a2 em15; h2c vs h2all em12 r100) | STRICT 4702 ticks, MUST-IDENTICAL; s30 340/340, heap_before 126,688 in all three |
| r104 (em13), r108 (em17), r11a (em12) warps, stop 1800 | STRICT 1802 ticks each, MUST-IDENTICAL |
| TEX_CHECK=2, r101 village view 150 s (v101c / v101a) | acc12 0 fails; control fails the known 9fe00ef7 256x256 fragmentation twice |
| GC-fallback count, offline (census) | 0 GC accessory BIN / image in each converted archive (test 11: 12 in em15) |
| GC-fallback count, runtime (accessory texture loads by key) | r101 v101 12 GC -> 0 GC / 13 PS2; sq101 11 -> 0 / 11; r100 (H2) 16 -> 0 / 16; r104 8 -> 0 / 8; r108 3 -> 0 / 6; r11a 8 -> 0 / 8 |
| Faults / HALT / MISSING / LEON-GC | 0 in every run above |
Look sheet: acc12/sheets/ACC12-HAT-SHEET.png (hat Ganado: GC data on DC | PS2 data on DC | PS2): the PS2 hat has the
darker straw and the dark band the PS2 shows. Release: stage acc12all and merge the 8 packages into tex.pak.
