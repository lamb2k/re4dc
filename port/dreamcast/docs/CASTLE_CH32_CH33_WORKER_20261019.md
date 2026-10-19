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
- The squeeze is compiled in but was not requested by this fixture: the exact log says held=0 requested=0. The smallest logged KOS total is 89152 bytes; this is an unsqueezed observation.

The first private harness attempt stopped before guest execution because the worker helper path change invalidated its derivative hash. The wrapper was re-derived after asserting the sole copy-script change was the explicit existing helper root; all payload/base/hash checks remain. That refused attempt is retained and is not a game failure.

## r205 resident data candidate

The first-sight audit identifies sixteen missing keys and one already-listed early load. Every new key's actual selected package is present, and the source width/height/format is retained even where its prepared physical image differs. The source list adds only the sixteen new rows. No texture, model, audio or program bytes change.

The private set `castle18-ch32-r205-resident-20261019` is mirrored on C: with SHA256SUMS `a29cb99c8ce03e71cff8925c84917cf6397018e6a521476e14a040e55e5045f2`. Its resident image is `c16366f345830bf823e392154944de8f3fb3fbae035ca85eeee36b2b2088c607`: 5607 records, preserving all 5591 prior records and all other rooms exactly. The additive fixture is `tools/d367/castle18/ch32-r205-resident-20261019.json`.

The matched fresh Flycast gate passes for the observed entry residency. `cx-r205-walk-resident01` ran 55.94 seconds, with gameplay uploads reduced from 16 to 0 and no official VRAM failures. Both payload manifests have identical paths, and only `dc/resident.bin` differs. The program, input, textures, models, audio and all other payloads are exact. Final free VRAM is unchanged at 390048 bytes; largest block is 346112 bytes. Minimum logged KOS stays 89152 bytes with squeeze held=0 requested=0. The source's active camouflage CAST failure remains unchanged; this is not room acceptance.

`r205-resident-matched-proof.json` seals both logs, program, payload comparison, source-data proof and official gates. This candidate cannot qualify room clear, chapter traversal, save/load or an unvisited camera. At integration, merge the r205 records into the newest resident union; never overwrite newer room additions with this older complete image.

## r209 focused actors and resident candidate

The distant current-program entry was texture-clean but all enemies were crowd-skipped, so it did not qualify their visible models. The closer `cx-r209-walk-focus01` diagnostic ran 56.28 seconds with the same program and current atlas packages. Four em1a actors are sampled, nearest 844 units; em1a draws are 2380 PS2 / 0 GC and Leon 1500 / 0. NOT-DRAWN, TEX and no-fatal checks pass. These are observed roles 07q/08q, not every wave or encounter completion.

Focused play exposes 65 late texture uploads and one residency guard, with no refusals, evictions, retries or missing textures. Final free VRAM is 736000 bytes, largest 688096; minimum logged KOS is 72408 bytes with squeeze held=0 requested=0. The first-sight audit has one already-listed key and 65 new source keys, all resolved to actual selected packages. Source width/height/format are preserved. Current atlas package differences from historical variants were proven to be only names and CRCs with identical descriptors and pixels; current atlas bytes remain untouched.

The resident-only candidate adds those 65 rows to r209. Private data `castle18-ch32-r209-resident-20261019`, mirrored on C:, has manifest `00620e55c180058945ede7ea832ea58e3f2503b41dad3bc13fa43d9ead2ba614` and resident hash `37a7074f74a90ee2b6aedf6bf74f4cc8620b9f3e4fa7de5b95ace63d1d2b6361`. All 5607 prior records, including r205, and every other room are exact; the new union has 5672 records. Compose these rows into the latest union at integration rather than overwriting later main additions.

The matched `cx-r209-walk-resident01` run passes official residency: 65 gameplay uploads become zero, guard zero, with no failures. The 56.27-second run retains native em1a 2305 / GC 0 and Leon 1500 / 0, and NOT-DRAWN passes. Only resident.bin differs between the two staged payload manifests; all program, input, texture, model and audio bytes are unchanged. Free VRAM is 736000 bytes, largest 673792; minimum KOS remains 72408 with squeeze held=0 requested=0. `r209-resident-matched-proof.json` seals the comparison. This is observed focused residency and cast coverage, not all waves, the salon key, doors or a chapter route.

## r20b unchanged full PS2 wolf package

The prepared original chapter-3 enemy list has eighteen em22 type-0 rows and one em18 type-6 row in r20b. Chapter-4 reuse has a different list; generic room-name comments do not override the actual source list. The current fixture had no r20b character package. Existing `ps2cast-4-20261011` full PS2 Colmillos geometry can be reused: the current producer with the existing wide-identity option reproduces its r11b package exactly. The r20b package changes only room/header CRC bytes; every byte after the 64-byte header, including geometry, weights, materials and source identities, is identical.

The current prepared em22 BIN4 matches the exact endian-converted source. TPL5 retains the exact header and samplers but has already externalized its pixels: its R4NREF key, dimensions, format and removed size match the original source image. This is not full TPL byte equality. The actual runtime package loader passes the r20b package and refuses it under the wrong room, with address/undefined sanitizers. No admission rule or model converter was changed.

Private `castle18-ch32-r20b-wolf-v2-20261019` is mirrored with manifest `af3c59806f845820a0ff4bfd3d95cf7642b8b989d9d3786870b2660c8d1ae092`; package `bbebff57e0bb7d88ce818ff4c87c6f260f1eb226c677c490ec5067b9a51df229`. Runtime wolf drawing, original back-parasite objects, merchant, full waves and chapter-end playback remain unqualified. The initial narrow-identity producer attempt was correctly refused because today's base exceeds its old 32-source-blob capacity; it is preserved separately. Existing wide identity reproduces the original output exactly.

## Memory-pressure evidence correction

The first six worker captures all explicitly report `kos squeeze: held=0 requested=0`. A generic `49152` check incorrectly matched the AICA stream buffer, so every previous 48 KiB-held claim is withdrawn. Exact payload-only residency comparisons and observed native drawing remain valid without the extra pressure. Both matched proofs now preserve exact squeeze receipts and mark memory-pressure qualification false; their original versions are retained as superseded evidence. Future qualifying fixtures must request `squeeze 49152 0` and match the exact held/requested receipt. Existing rooms need this coverage in the latest integrated route union; no chapter acceptance is claimed.

## r20b original wave and memory-pressure check

The original balcony entry held the explicitly requested 49152-byte reserve but had no wolves. A separate initial placement inside original AEV area6 triggered the unchanged source wave. Its 56.14-second capture drew em22 948 native / 0 GC with four wolves sampled; Leon450 / 0 and TEX pass. Merchant18 remained GC250 and is a separate blocker. The close still retains the original back-parasite objects, whose independent source/PS2 qualification remains open.

The initial official residency zero was insufficient because its last room summary was preload. A 56.44-second continuation uses the exact same disc/program and unmodified saved state. The logs share695 exact history lines; joining that overlap yields actual later tick summaries and24 late uploads. These are an observed residency failure, despite no refusal/eviction/retry and guard0. The current exact-reserve verifier passes the joined lineage with49152held/requested and minimum KOS32680bytes. Eight original effect images have no PS2 counterpart and remain explicit exceptions.

The source-observed additive candidate includes25 previously absent keys, retaining actual source dimensions/format and all5672 prior records. Its new union has5697 records. The one additional early source load accounts for why additions differ from the24 late-upload count. Actual selected package winners are sealed; no texture/model/program changes accompany this resident candidate. Fresh candidate runtime remains pending. Keep previous room additions when composing into the newest main union.

## r20c original source body intake

The original chapter3 enemy list requires em1b types7/10 plus separate em25 parasite actors. Existing full current r201 package9485af27 includes em1b07p/08p/0ag; the current producer reproduces it exactly. The new r20c package0082606f changes only room/header CRC bytes, with the entire payload after64bytes exact.

All43 source roles and23 prepared BIN entries match the original source. Existing source-only bump slots retain header/sampler facts with the already established zero-key contract; they are recorded explicitly. Eight apparent missing texture keys are virtual colour/mask tokens, resolved to four combined packages. All seven real native packages are present; current descriptor/pixel bytes match retained inputs, and only debug-name/CRC differences exist for some atlases. Current selected bytes are preserved.

The actual runtime loader host check accepts20c and rejects the same package for201. Private castle18-ch32-r20c-em1b-v2-20261019 is mirrored with manifest1878d4a44ed91569ba08c9717a4215d010122aafcbcdcc7f97ab2ccf8677792f. This establishes source-compatible package preparation, not current r20c runtime, parasites, encounter progress or chapter acceptance.

## r20b full Merchant composition and corrected residency

The existing full wolf package is composed with both closed/open Merchant18 appearances from the qualified standalone r102 archive. The original wolf sections remain prefix-exact, all geometry arrays remain exact, and all fourteen Merchant source roles are checked against the original source. The actual loader accepts the combined package. Its SHA256 is `c5b4f44956f7a3629c285c0551f416c64484aad9084b0991a7300ff0cf9a2620`; mirrored private set `castle18-ch32-r20b-wolf-merchant-20261019` has manifest `17b1271d8006047ebbf913e58c0d6d24b377ea8b7ffdb36d5b9ca863b13f5de9`. This is unchanged source-compatible package composition, with no modeling, converter, runtime or source-event edit.

Every selected Merchant texture is byte-identical to the current main r200 nativeL/Shop fixture winner. Existing optimized VQ images are preserved; canonical raw images are not falsely called encoded-equal. Decoded alpha differences from those raw inputs are recorded, including the existing c0/o0 mask differences. No new re-encoding occurs. The public model fragment replaces only `dc/native/r20b/registry.re4nmr`.

Current746 `castres03` ran55.92seconds and its exact unmodified saved-state tail ran56.22seconds. The histories share681 exact lines, with one leading partial ring line excluded. At frame2222, actual cumulative native draws are wolf1061, closed Merchant1445 and Leon1800; each has zero declines. These are final counters, not sums of repeated census snapshots. Merchant was initially crowd-skipped but later draws; the Shop-open appearance and full encounter remain untested. TEX and NOT-DRAWN pass. The exact49152-byte reserve passes with minimum logged headroom33480bytes. Only the composed registry and resident image differ from the earlier wolf control; this is not a resident-only A/B.

Actual post-play tick summaries throughframe1967 still expose3late uploads, versus24 in the older wolf control. They are the three native Merchant keys newly reached by this composition. Official residency therefore remains a failure. Eight established source-only effect exceptions remain explicit; there are no allocation refusals, evictions or retries. Proof is `r20b-castres-current-proof.json` with exact joined-history provenance.

The next candidate adds those three source-observed rows to the newest main V11 union, preserving all5707 records and every other room exactly. Source dimensions/formats and actual package winners are verified; current image bytes stay unchanged. Private `castle18-ch32-r20b-merchant-resident-v12-20261019` has5710records, resident `07c984d704b079d0dcf179c939cd1f4bfd1c32fd2ac6a021ab4d5b3879396c40` and mirrored manifest `8965eb6186afd6b2306e58238298edb938bf7b62ad99f391db99723c4b93a66f`. Fresh runtime qualification is pending. Compose any newer additions instead of overwriting a later union.

## r20c current source-door entry

The current746 original-door diagnostic ran56.50seconds with the explicit49152-byte reserve and minimum KOS44680bytes. Leon3150native/GC0, TEX, world and official residency pass, including an actual post-preload tick atframe767. No enemies activate at that doorway, so this is entry/data coverage only. The original cage-trigger preparation retains unmodified source camera, actor waves and player movement; its focused runtime check is next. No chapter progress or parasite-model acceptance is claimed.

## r20b V12 matched observed residency result

The fresh `merchantv12` run completed56.34seconds, followed by56.22seconds from its exact unmodified saved state. The histories share682 exact lines. Only `dc/resident.bin` differs from `castres03`; program, input, model, texture and audio payloads are exact. Actual post-preload summaries throughframe1967 now have0late uploads, versus3 in that control, with guard0 and no official VRAM failures. FreeVRAM1267744/largest1196032 and minimum KOS33480bytes are unchanged; the exact49152-byte reserve passes. The final frame2222 census retains wolf1061, closed Merchant1445 and Leon1800 native submissions with zero declines. Source-only effect exceptions remain explicit.

The unattended original wolves kill Leon, and both tail stills show the original Continue menu. This qualifies the observed encounter/death-path residency and actual native submissions only; it is not a visual Merchant shop review, survival, wave clear, door, save or chapter acceptance. No god mode, kills, injected flags or extra input were used. `r20b-v12-current-proof.json` seals the payload-only comparison and exact history. Joined log SHA256 is `6a3c562d355097807dd5a3515c84cb6444e1604b79cb8813bebad7d8a4414ca6`.

## r20f existing source models and texture limits

The higher-thinking source audit `2ca70cbf` establishes that em14 type6 is an authored Merchant alias on both original platforms:44 exact BIN/TPL comparisons and all8 retained source-to-mesh-to-header roles pass. It preserves3265 oriented triangles, UVs, normals, weights and the61-part owner with zero source-to-mesh position delta. The source-provenance blocker is cleared; no model reconstruction is needed. Its mirrored private seal is `castle18-em14-type6-source-20261019`, manifest `90637dae72ddd3403f8862d043004af445f94967e600fb1d20f956ed1c2fcedb`.

The current producer exactly reproduces retained full r227 package `0aba2397008ed22c64589875166b4646e44000c9685623aba42fcbd44efb2f8d`. Selecting original r20f types6/7/8 and omitting unused type9 makes every one of the12 package sections a byte-exact prefix of that control. There are no geometry or material edits. All50 original source roles and30 prepared BIN entries pass; original ESL attachment flags require no extra flag2 acc32-b variant. The actual96-bone-capacity loader accepts20f and refuses the wrong room. The first attempt correctly refused the default48-bone producer budget; the retry uses existing `--pack-bones96`, matching current746 resolved controls, without increasing runtime capacity.

All17 native texture tokens resolve to existing selected packages. Type7/8 images retain exact pixels. Type6's old same-key atlas e7735a39 differs from current2af4bac7 in200920 decoded pixels; encoded or decoded equality is expressly not claimed. The original source RGB atlas/layout is the same according to the specialist, but these are different compressed derivatives. The current fixture already selects the exact main nativeL/Shop Merchant winner; it remains unchanged, as do the existing VQ mask winners. Actual r20f type6 material/alpha/look qualification remains open. Independent source/model proof does not certify those current compressed pixels in this room.

Private `castle18-ch32-r20f-em14-v2-20261019` is mirrored with manifest `10d464f97fb793839c90bc5bc75e4b2f79139b0a3ae01dea05b69a426b3a684f`; package `d034c033b2e7796c5f260fdc51fdb31b77ec3e6dbccff4728b7f1fa8a218b3bc`. Its public fragment changes only the r20f model package. Runtime actors, separate em25 parasites, residency, waves, keys and chapter route remain unqualified.

## r206 original chapter-end source preparation

Existing r206 em11-07p/08g package `98d513a7a7ce04f03087b98f6dc3ad26a82197cc8db3352d8226537b06f4e81c` passes42 original source roles,22 prepared BINs, the actual loader and all10 native texture tokens against the current selected images. The original chapter3 ESL has12 type7 and one type8 row; no row requires flag2 alternate acc32-b. The later08h descriptor adds that exact extra source role; source flags do not justify blindly replacing08g here. Dynamic source changes and actual current enemies remain untested.

The prepared original r20f door leads to r206 at(-10704.958984375,8000.00390625,-4144.39404296875), angle1.5029754638671875. Current746 program, original chapter2 Ashley partner and allthree S00/S10/S20 movies are retained. No Rsf5 injection or event skip is used. Original `r206_snipe` invokes the101.101-second Luis S00 movie and `CHAPTER_3_3`; any resulting end save must preserve diagnostic origin. The actual event/save gate is pending and cannot substitute for the final no-warp chapter3-3 route.


## r20b original full chapter movie, save and cold load

The original area2 trigger runs R20bEventS00 without injected room flags, kills, god mode or skip input. Original20b00 shows all2289frames, with dropped0/late0, skip_func0/end_func1, then enters SceSetChapterEnd(CHAPTER_3_2). The56.17-second start and56.39-second unmodified-state continuation share775 exact history lines; joined log77a956d4 preserves the full source completion.

Normal owned-window A/LEFT/A saves into empty FILE01. Original cCard reaches state8/10 with status1; RE4DCS01A writes5799compressed bytes in14blocks, inplace0/rc0, and system write returns0. The11.38-second capture exits normally. Private before/after VMUs are retained, and extracted VMS CRC passes. Saved VMU SHA256 is `277d7e8ab7910bf90b82e373f86a7857b776cea80cd78f7279f9cf0b49d94b23`; neither production profiles nor save bytes were edited.

A fresh56.73-second boot loads this exact VMU with AutoLoadState=no and a squeeze-only fixture containing no room/position/flag/inventory directives. Ordinary title/CardLoad buttons read FILE01 with ok1 and digest5431889e, matching the save digest. Its56.42-second unmodified-state continuation provides252 valid read-only samples of chapter8/room20b/gameplay phase3/Stop0/Leon1440, plus a viewed still showing normal gameplay. The observer correctly refuses further process queries after the owned emulator exits. The two cold-load histories share824 exact lines; joined log SHA256 is `922bcc7dcbd3833609c1b87d16d9926714cc0544523f71cb97d37f25c5d90981`.

The exact49152-byte reserve passes with minimum logged headroom32112bytes. Finalframe2564 has1500 native submissions each for Leon and Merchant18 with0GC; TEX has0failures. No active warp census exists, so NOT-DRAWN is unproven. This loaded view exposes16 late uploads/guard3, so official residency remains FAIL. Eight source-only effects remain explicit. This proves the original full movie/save/cold-load mechanism from diagnostic origin; it does not prove a complete chapter route.

The approved additive candidate records precisely those16 post-final-preload source keys, preserving all5713 records of the newest r222 union and all current image/model/audio bytes. Two other first-sight keys occur before the final room preload and are not added. Source dimensions/formats remain distinct from smaller physical package dimensions. Private `castle18-ch32-r20b-coldload-resident-v14-20261019` contains5729records, resident `8a26f3661131756d65d8d7fc9fa5fc18e41c161bb662fea3216d0882b1eb9017`, mirrored manifest `f802a9a7634dacfe933a7fe7e8a9795a20bfd1fd013a3aeae51a31aa9836e4e7`. A fresh matched cold-load gate is pending.


## r20b V14 matched cold-load residency gate

The fresh V14 cold boot runs56.66seconds and its exact unmodified-state continuation56.39seconds, sharing787 exact history lines. Only resident.bin differs from the control payload. Official post-play summaries now report0late uploads and guard0, versus16/3, with no official VRAM failures. Minimum KOS remains32112bytes with exact49152held/requested. FinalfreeVRAM1226304bytes is unchanged; largest1145856bytes. Eight source-only effect exceptions remain explicit.

The identical source VMU loads digest5431889e again. All306 valid observer samples show chapter8/r20b/phase3/Stop0/Leon1440, with no observer errors, and the viewed still shows normal gameplay. Atframe2564 Leon and Merchant each have1500 native submissions and0declines. Source images, full models, audio, input and program are byte-identical. The joined log SHA256 is `3689fbc42b135165b3f19d7dc81d20d3cb798f0f0d90440134a2772009e8d473`; `r20b-coldresident14-matched-proof.json` seals the comparison. This is observed save/load-view residency acceptance, with diagnostic origin; full chapter traversal, unseen actors and a no-warp census remain unproven. No timing benefit is claimed.


### Original r20c cage, held source rows and additive preload (2026-10-19)

The original cage trigger ran on frozen c18oimW ELF `746a2a5f` with the full source-compatible r20c body package. Two bounded captures (56.58 and 55.95 seconds) share exact disc `527bceb6` and an unmodified saved state; 693 ring-history lines overlap exactly. The final original-room summary at frame 2567 records 17 late uploads, guard 0, no refusal/eviction/retry or sound failure. Exact KOS reserve is held=requested=49152, minimum logged headroom 38560. The final frame2581 census has Leon2351 and ordinary type7 body counters2278/74/130 native, all zero declines. The latter are cumulative shape-specific counters, not four separate actor totals.

Read-only exact-symbol observations cover 100+ samples at difficulty4: four actual type7 actors CB/CC/D2/D5, with seven original sends D6/D7/D8/D9/DA/EE/EF still in the held queue. All held source records remain byte-identical throughout observation; D6 is the original em1b/typeA/set15 claw body confirmed independently in boss H035 (`202e0222`). No release occurs in this no-kill window, so claw-body drawing, refill, and the whole fight remain unproven. The original low-rank substitution does not apply at difficulty4. Source `R20cExecCageEmResetSub` requests `setFlag(1)` while held, whereas `cEmWrap::setFlag` only writes a live actor; possible loss of that activation needs an actual release diagnostic before a shared runtime claim. No runtime change is made.

The source-observed candidate adds only those17 post-preload keys to r20c.tsv and the latest5738-record union, preserving every existing record and every other room. Dataset `castle18-ch32-r20c-cage-resident-v16-20261019` has5755 records, resident SHA256 `2ccc55c0776a061af8d33dd1316d054f997368417f7dba1a8a4fccd87426aaa2`, manifest `a43765f62bc2a6c87e45bcaebd511ea93c6545f17dca42243fa599e317cc7a83`. Actual package winners and source width/height/format are retained, including source48x48 and64x48 descriptors whose selected physical package dimensions differ. No texture/model/audio/program bytes change; fresh matched candidate gate is pending.

Evidence: worker `r20c-cage-source-queue-proof.json`, `r20c-cage-continuation-provenance.json`, `r20c-cage-first-sight-winners.json`, and `r20c-cage-resident-host-proof.json`. Initial placement remains diagnostic; this is neither full-fight nor no-warp chapter acceptance.


Matched V16 cage residency now passes: captures56.22/55.86 seconds, exact679-line saved-state history overlap, candidate disc `3495ba1f`, joined log `13b93daa3461640b4238779e0e546ae040c66e56f38cf76c58de76384adcbbac`. Actual staged payload sets are identical and only resident.bin differs. Official late uploads17→0, guard0, no failures; exact49152 reserve and minimum38560 unchanged. Frame2581 native census is2351/2279/75/130 with zero declines, versus control2351/2278/74/130; these draw counters do not establish frame-identical gameplay. FreeVRAM1225856, largest1185792, peak pinned1251456. Read-only samples again show difficulty4, four original type7 actors and the same seven held source sends; this proves neither their release nor claw-body drawing. Evidence `r20c-cageres16-matched-proof.json`. No hardware FPS saving is claimed.


### Reproduced deferred activation loss, separate decisions/progress diagnostic

The original cage fixture plus the existing bounded damage rig (four em1b targets; no direct HP/flag/ACTIVE/room edits) reproduced the queue concern on the same746 program. Captures55.78/56.16 seconds have692 exact overlapping history lines; joined log SHA `ec5fb900a9e045d0a13e236673ea6c726a4d6de06c8f1ca838406e1dd2607601`. D6 leaves the held queue atframe1571, creates original typeA/HP4000 at source height10490, and remains routine1/4/1 with flag0 through the final observed sample. No claw native admission/body draw occurs. EE also releases but remains in HideJump without its release flag. Source calls setFlag(1) while held; the live-only wrapper drops it; set15/HideJump then waits for that bit. All seven source sends eventually leave the queue rather than being deleted. This establishes an activation blocker, not a full fight pass. The tail observer retains143 valid samples and refuses its final ownership query after orderly owned process exit; that terminal observer refusal is not a game crash. Cap-off runtime comparison remains pending.

The death/release path additionally has3 late packaged textures, guard0/no refusal, minimumKOS38080 with exact49152 reserve. They are separately source/WHF/winner-audited in `r20c-release-first-sight-winners.json`. Dataset `castle18-ch32-r20c-release-resident-v17-20261019` adds only these3 over Worker B's5765-record r219 union, preserving every old record;5768 total, resident `e2513c50c96836b8a457281ff8a34a602507bc90ecae37a3d80d37182d21f392`, manifest `3f259a025040750c690efa957379e64a6f0751d443743c13c6f87e80b5f0193d`. No image/model/audio changes; matched runtime gate is pending the narrowly scoped activation correction. Evidence `r20c-deferred-activation-reproduction.json`.

## Current AP1 r20f entry: missing original accessory material variant

A fresh current `2c0e3dc0` / upstream `f2555097` entry used `c32gtbmW`, ACTOR_PLAN=1 and the qualified deferred-flag fix. All 23 selected programs were verified; the ELF is `6f081a5699c793d49adb435227b8bdef6aec37ff1a1222cea34e513ea39d22da`, staged disc `c2f73b656029f372ad57bb83198b2890dd62d89ab91af74c330468d731a83feb`. Only programs and latest V18 residency changed from the source-prepared r20f fixture; original room/model/image/audio bytes were retained. The original incoming door and 49,152-byte reserve were used without flags, god mode, kills, event skips or injected input.

The 56.25-second capture exited cleanly with no capture, TEX or audio-fit errors. Exact reserve held/requested is 49,152; minimum logged headroom is 35,144. Original em14 types6/7/8 all have actual native admissions and draws. However, CAST-GC **fails**: aggregate census reports 2,814 native draws and 900 source-path draws for em14. These are census totals, not unique actors or a timing measurement. The unresolved actor has 37 parts/eight infos and repeatedly fails role binding. Official VRAM has no reported failures but only preload samples through frame180; this is **not** full gameplay residency acceptance. No close appearance, combat, wave, lever, platform, stream or whole-room pass is claimed.

A read-only decode of the exact saved state located 16 MiB main RAM with three unique 256-byte signatures from that ELF. It pinned the failed actor to original ESL E0, type8, pointer `8cbe4460`. Seven current infos have exact package roles and adopted ownership. Its final accessory is original BIN `0x217` with TPL `0x219`; the package has no such role, and the info is unadopted. Native comparator DF uses the same BIN with TPL `0x218`, matching pool role20. Original `em10SetAccesory` at `src/em10/em10.cpp:18412` selects mot38/mot39 for flag `0x200000`; its later flag `0x4000` fallback uses mot38/mot40. `Em14Set` maps these to BIN217, TPL218 and TPL219. Thus the earlier flag2-only attachment audit was insufficient: it correctly excluded acc32-b but missed this different original material variant. No runtime semantic relaxation or model reduction is proposed.

The 93 retained conv4 source records plus 36 Castle variant and 13 Castle room records contain no BIN217/TPL219 info. The higher-thinking model specialist owns original PS2 texture/UV/alpha and additive-material preparation; fresh geometry is not presumed necessary. Existing masked section20, archive identity, full geometry and current texture winners must be preserved. Runtime qualification of that future candidate remains open.

Private receipts under the worker evidence root:

- `r20f-current-ap1-runtime.json`: `a9ff3b28ea549789b9dc09e49d527065b8e53ac73bc0c69231ac6d64037dccde`.
- `r20f-current-ap1-cast-gc.json`: `9ade6e1b1e45bf6de0f3d7fa2fedcacb939e033cc2e39e95ad8d86706b393454`.
- `r20f-original-actor-role-audit.json`: `863ef553fc0fcb6ec3b39d931c71ce7808227d1023c0abc4a082144ed2de2c0e`.
- Saved-state decoder: worker scratch `audit-r20f-saved-actor-roles.py`; read-only, no save or process writes.

The completed disc's two owned links and sole exact cache link were hash-verified and retired through the existing guarded deletion journal. All logs, source proof, programs, stills and original snapshot remain. This recovered 1,421,133,824 physical disc bytes and does not touch any main-route image.

## Current r206 chapter-end preparation

`r206-current-ap1-death.json` now selects the same fresh 23 current programs and V18 5,791-record resident union. All nonprogram/nonresident payloads are byte-identical to the audited source-prepared r206 fixture, including original chapter2 Ashley, em11 package, audio and all S00/S10/S20 movies. Preparation proof is `r206-current-ap1-preparation.json` (`521bb543566e523c9bdc7bc8bc47da7372f51020fa6b31236494448b2d90a157`). The unskipped original Luis movie, CHAPTER_3_3 save and genuine cold-load gate have not run yet. Any resulting save keeps its diagnostic-entry origin and cannot replace the final no-warp chapter route.

## r20f original alternate role and residency candidate

Boss H043/H045 provides the missing original BIN217/TPL219 role without
changing geometry or existing material winners. The current same-key texture
29480f18 and donor edc35f81 have identical complete texels and decoded RGBA;
only header name/CRC differ. The candidate therefore stages only registry
`da42932a6c2b029cbc3d26d7e0105a0b2885738564c0b41a73813fa125e35d7d`.
All other 6,601 staged payloads, including all programs/images, remain exact.
The actual selected pair remains the existing loose 29480f18 file.

The same-6f081 AP1 comparison and unchanged saved-state continuation ran
55.94 and 55.97 seconds, both owned processes exited with no capture errors.
The original E0 info now binds role21/global146 for BIN217/TPL219; DF retains
its original TPL218 role20. Actual native draws occur for all selected 6/7/8
families. Combined census totals are em14 native24,486/GC0 and Leon
native5,400/GC0; these are repeated census totals, not unique frames or speed.
CAST-GC and NOT-DRAWN pass. TEX and audio-fit failures are zero. Exact KOS
reserve is49,152 and minimum logged headroom36,424 bytes.

The later official room ticks at f767/f1367 establish a separate residency
FAIL:41 post-preload uploads, guard/refusal/eviction0. At the last tick pinned
933,344/dynamic562,304/other90,112/free981,664/largest948,224 bytes. This is not
accepted room residency. The first capture's preload-only report was not used
as a passing gate. Stills do not provide a close actor look; movement, combat,
whole-wave/platform/lever/door and no-warp chapter gates remain open.

The new data set `castle18-ch33-r20f-resident-20261019` adds exactly those41
source-observed keys over all5,801 V20 records, preserving every original row
and all other rooms. Source dimensions/formats and actual package winners are
recorded; no texture, model, program or audio bytes change. New total5,842,
resident SHA256 `49a48c29eabdc24bd69070e6fb241002b70acb077814599ed00ca6c698d7017b`,
manifest `63b99b15a3e95ebc1ae6aa98cfc1febe03b5d1e36a114a286ff22b378c37125f`.
The WSL set is hash-verified and mirrored to the same private leaf on C:.
Its fixture fragment is `tools/d367/castle18/ch33-r20f-resident-20261019.json`.
Compose these additions into newer unions; never replace later room records.
Matched runtime residency remains pending.

Private evidence: `workers/ch32/r20f-alt-material-complete-runtime.json`,
`r20f-alt-material-actor-role-audit.json`,
`r20f-alt-material-first-sight-winners.json`,
`r20f-alt-material-continuation-provenance.json` and
`r20f-resident-host-proof.json`. The continuation joins718 exact ring-history
lines; the original state is unchanged. The old default first-pass checker
path was missing; the current source checker was run explicitly and retains
walk/provenance scope as unproven. Finished disc links/cache were hash-checked,
journaled and retired; all logs, states, stills, programs and source inputs stay.


## r20f matched residency gate, 2026-10-19

The registry-only accessory correction now also passes the matched room-residency gate. Only `dc/resident.bin` changes across all 6,602 staged payloads; the exact 6f081 program, original E0 BIN217/TPL219 role21 and DF TPL218 role20 remain unchanged. The source-observed 41 additions preserve all 5,801 prior records, giving 5,842 records.

The original entry and unchanged-disc continuation exited after 55.81 and 56.16 seconds. Their exact saved-state lineage joins 713 equal log lines. Official frame767/1367 samples retain preload201 loads: 41 late gameplay uploads fall to zero, with no guard/refusal/eviction/retry/TEX/audio-fit failure. Minimum free VRAM is981,664 bytes, largest contiguous946,176 bytes; the exact49,152-byte KOS reservation holds with36,424 minimum logged headroom. The draw census contains30,892 native em14 counts and6,750 native Leon counts, both GC0; these are cumulative diagnostic counts, not performance measurements. Original E0 role21 and DF role20 are independently verified in the saved state, and the visible em14 alivelist maximum remains4.

This is a matched asset/residency diagnostic on the frozen program, not close-up appearance, whole-fight, no-warp chapter or current-upstream acceptance. The no-input short-walk check remains unproven, and the generic provenance checker remains unproven; the separate source/package identity receipts are retained. Runtime proof: `workers/ch32/r20f-resident5842-complete-runtime.json`, SHA256 e1ad055d7cab7afaddbd2b8cee56b784f055a7136e8d85ce03c13b9a9eb19c2c. Combined log SHA2568064c856c200fa0b57aaf52c1a049dc3750c7ce9a21cd4d4fd9baf3c022e97f3. Both owned capture processes exited; finished disc retirement retains all logs, states, images, program and source receipts.
