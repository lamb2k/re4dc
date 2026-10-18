# r333 original transport checkpoint (2026-10-18)

The final escape room stopped at DLL_Link because module57 (pl0e, the jet ski) was absent. Existing default-off ROUTE_FINAL now links its source overlay after em31, with an explicit module57 row, overlay slot and matching converter/config identity checks. Earlier overlays keep their order. T15REC and all source ride controls, rails, collisions, routines and event callbacks are unchanged.

The texture-only pl0e preparation retains every FCV, including motions lent simultaneously to Leon and Ashley. It externalizes only the reviewed top-level model TPLs; ARC4 effects retain their own bytes. This is a transport checkpoint, not a PS2 ski/ride model qualification.

## Source and data

Correct review GC Disc2 SHA256 118640eb02953d5a8234d3f9e27ea535e75b0346b9cf22aa764b65c3d76f1b12. pl0e source SHA256 b036657fc666acf3fccb4841b0609d59a67a15e4b61cdb9597c2dc4cec9e2b80 matches the retained dependency exactly. Native resident body 577568 bytes (original static body 965984), all motion payloads resident, no cache/slabs.

Original r333s00 and s10 prepared EVD/EVQ pairs are reused only after exact current converter/certificate comparison. Their source event durations independently agree between BE source and LE prepared data: s00 430 frames / 6 cuts, s10 2328 / 20. Generic RouteMoviePlay uses a zeroed Event; it cannot replace s00 without preserving MaxTotalFrame, which the source callback subtracts from the escape timer. No movie replacement is implemented here.

Private sets, mirrored immediately to the matching C:/Game Dev/Emulators/re4-assets-private folder:

- island18-r333-transport-20261018 SHA256SUMS e3162053e50b97f30d57b39b1a7f99fe3f3a6f3b64ce41ae820450924bd84319 (source, resident archive,19 texture packages,original EVD/EVQ).
- island18-r333-sound-20261018 SHA256SUMS f2bd15e1f6237d4866f1f7c564a2fb2debeb3ce9a77e5f482365c1196727e92a. Existing AICA converter changes only sound payload ranges; all other bytes exact, layout unchanged. Ski bank 86948 bytes/11025Hz, ADPCM SNR22.2dB; room275968+ski86976+Ashley68064 aligned =431008 of1004192 arena,573184 left. Subjective sound quality remains unaccepted.

## Validation (Flycast only)

Target i18f3mW ELF51842d429a17a2534fad35b19a60545ceeb4fcd63ce219244e5058c161ba426c, _end8c3cfcb8/missing0. Actual staged boot and all22 overlays verified before capture. World-room-modules0/1 x final0/1 preprocessing matrix confirms exactly one module57/slot with final on and none off; converter registry/config checks PASS. Existing 32-bit native binder hosttest fails to compile bits/libc-header-start.h on both pristine7d and draft; recorded environment limitation.

Fresh T15REC i18d9rP: 1ST_READ 9dbb243431064e5b65c875f44ae4b75a14047a9c20f309d7c41b2b6c83d80c23 and all10 overlays byte-identical to frozen origin/t15/int7d7c05ab. _end8c400eb8/missing0. T15REC never changed.

r333/ski1 (59.02s process lifecycle) enters and links pl0e16200B/111relocations/prolog, no HALT/FAULT/MISSING, ski sound prebuilt and snd_fail0. Its fixture omitted standalone ski textures: retained as a failed TEX diagnostic.

r333/ski2 (59.14s) adds the18 absent standalone source keys. Entry/world/no_fatal/TEX/Leon checks PASS; shortwalk and character provenance UNPROVEN. Static arrival only, no ride/event completion or full-room acceptance. Source effect loader logs PL0E:NULL; original effect data needs further audit. Live/drawn ski and borrowed rider model contracts still need explicit validation rather than relying on drawn-character checker PASS.

At tick767: VRAM315168 pinned/1846304 dynamic/315840 free/288768 largest,152 loads stable after startup,0eviction/retry/refusal. Heap4 minimum/largest2467168; actual49152B KOS held, minimum total KOS43656/top42784. These are sampled entry figures, not ride residency proof.

Evidence root C:/Flycast-Evidence/re4-dreamcast/island18-20261018: h-i18f3/scenarios/cx-r333-walk-ski{1,2}; identity/r333-module-off-identity.json; r333-module-matrix.json; r333-source-event-durations.json; r333-original-trigger-areas.json. Source draft pins in r333-module-draft. Per-disc packaging and boss models remain separate owners.


## Real boarding exposed a constructor trap (H-013)

Source area0xE interior plus ordinary A input opens the key screen, uses the source-granted key and calls ride(). Static entry did not exercise this path. On i18f3mW ride1 (59.25s), this produced NULL motion/effect owners, no-parts warnings and a model.cpp1907 alignment HALT at frame368. Exact target compilation shows implicit derived value-initialisation emitted memset(em,0,3552) before cEm's constructor, erasing EmMgr's already-assigned subArc/id. The existing pl0f route fix uses default-initialisation on Dreamcast; pl0e now uses the same guarded pattern. PPC construction remains unchanged. No controls, clocks, rail, collision, crash or motion logic changed.

Exact before/after SH4 assembly in C evidence pl0e-constructor-draft confirms the3552-byte memset is removed while the base constructor and vtable installation remain. Fresh target i18f4mW ELF3114395e23b6bf1d3d49e4a415d4d02e2427120c7e62d78bf8d29429dea1d2ee, _end8c3cfcb8/missing0. Fresh T15REC i18d10rP program+10overlays remain byte-identical7d7c05ab, evidence identity/pl0e-constructor-off-identity.json.

Same physical key-use rig ride2 (59.03s) now has no HALT/FAULT/MISSING, no NULL-motion/no-parts/PL0E-owner warnings. Ski class0e identity/hp1000 survives; source routine1/0 waiting ->1/1 boarding ->1/2 rail run. Position moves from(-674136,-26663,-551098) to(-517234,-26663,-607975), then ordinary forward input hits a wall and source routine1/4 sets player life0. That crash is preserved, not bypassed. Boarding+rail progress is observed; ride completion is not.

Whole room FAIL: missing material pair263e8f16-1edc3127 (source ski color e8820dbc-32602af6 +mask4302026e-320c9985,256x128),23texture evictions by frame960; no ski/borrowed-rider PS2 contract acceptance. Tick767 VRAM1489568 pinned/946464 dynamic/41280free/6080largest; minfree33120/minlargest3072. Heap4minimum2433792; KOSminimum41496. These are diagnostic pressure figures, not stable-play residency.

New source ride/failure streams1:116/56/57/114 were absent from retained containers. The45-entry private island18-r333-streams-20261018 reuses all41 previous final records exactly, adds4 using the unchanged converter and verified GC stream headers, and remains under the existing56-entry cap. Mirrored SHA256SUMS8e2933290e00384db59b83758274bdc0c92f0248f8322fce06dab16a614dfa2e,68634624bytes. Actual ride2 starts1:116 and crash1:56 without bank refusal. Initial room stream0:49/offset5b18000 is another newly exposed missing profile entry; not a clean-audio gate. No shared packaging or movie hook added.

## Physical first event and production snapshot continuation (H-014)

Private production Flycast64491c00 uses supported AutoSave/LoadState with exact sealed disc/program/executable and source data-file SHA checks, no interpreter substitution or guest edits. Warm4/resume4/resume4b process lifecycles45.08/56.25/56.27s, all owned processes exited. Same ELF3114395e and disc6edf7c1e throughout; actual staged boot and22overlays checked before each capture. Snapshots are emulator test tooling, not DISC_SET/VMU/hardware proof. Evidence r333-production-state-progress.json and h-i18f4-state4{,b}.

The31 ordinary input actions clear3 obstacles, jump, and physically trigger area1. Original r333s00 installs1682432B successfully, Rsf0 sets, and the unchanged event returns to second rail with player1920 and ski1/2 alive source1230..1380. Unsteered next wall crashes1410 and sets player0. No escape/door-route completion. A later ordinary A restarts after death: resume4b checker entry PASS refers to that restart, not full-route acceptance. Saved serial history repeats: do not add duplicate rows as separate samples. Numerical runtime countdown not logged;430frames remains a separately proven source fact.

Whole room remains FAIL: ski pair263e8f16 and original EVD512x512 key792f940a missing, ski/borrowed-rider PS2 provenance UNPROVEN, late96textureevictions/3retries. The18.26s EVD install coincides with one audio underrun; original event stream1:131 is absent. PS2 movie hooks remain next work, with original EVD fallback preserved. Failed135-action course3 is retained as INVALID INPUT RIG (source cap32); corrected private runner refuses overcapacity before staging. Current-tree supplemental checks cover warm4/resume4 after the inherited default checker referenced a wiped old tree.

The48-entry r333 route stream profile preserves45existing records, adds3initial/wind/result source keys,76568576B, mirrored SHA256SUMSc7dba764183db1d560d8b7a8e8dff27616aebc4d14abb5b42f656237e15e8b2d. Initial/ride/crash starts were observed without underrun before the EVD load; clean whole-route audio is not claimed.

## PS2 S00 movie with the original timer and skip cut state (H-015)

The existing ROUTE_FINAL per-object movie flags now include r333. Only its S00 preload/playback is replaced when the PS2 movie is available; the original EVD fallback, physical trigger, stopEngine, set2ndRail and prompt remain. S10/result/ending are unchanged. No new knob. An error after partial playback blocks secondrail/prompt instead of inventing progress or retrying the EVD. The generic movie bridge is unchanged.

Independent original PS2 companion EVD vs GC/prepared camera lengths match every cut: S00[35,124,117,38,21,95],total430; S10all20,total2328. Source Event::RunEvtCancel suppresses mode1 during fast-forward: START retains its current-cut lasting flags. The local S00 tick records the last presented picture; its adapter supplies430 to the unchanged end callback and applies only that cut's lasting flags. The backend never drops the final decoded picture at EOF, so natural completion receives429. Source/PS2 sndFlag0 independently confirms event sound init/end. Actual callback source-extracted ASan/UBSan matrix27552 comparisons PASS: all430pictures, normal/cancel cleanup,8initial flag seeds,4timer values, dropped/zero-picture cases. This is lasting-state transport, not event-model or target arithmetic proof.

Fresh i18f5mW ELF5586faf1a6ee3e12c91eb3d8908d5a06a1c0a4e290bc2a15a457d26254918d6d,missing0/_end8c3cfcb8. Only st3_3.ovl differs from i18f4mW. Fresh7d T15REC i18d11rP boot9dbb2434+all10overlays exact frozen7d7c05ab; sourceT15REC unchanged. Live origin advanced to293aefcd at the16:30 fetch: this is historical7d identity, and a new literal293 T15REC baseline/candidate pair is required after merging. Both build outputs mirrored in gated-r333-movie-builds; source pins in r333-movie-refined-draft.

Natural production continuation56.25s physically triggers S00:430/430 terminal1, lastpicture429, actual saved2893-subtract430=2463, original secondrail alive source780..990. Early START uses existing movie-state padscript (no desktop input): skip picture16 at0.731s,lastpresented14,terminal2/skip_func1/end_func1, same2893-430=2463; source900 Status1bit800 remains set for the early cut, clear naturally. A warp-act START trial fired after the movie because native playback has noPADRead; it is NOT skip proof. Every capture bounded<60s, exact staged boot/22overlays and snapshot disc/program/exe sealed. Saved serial history repeats; laterA restarts after normalwall death, so entrycheckerPASS does not establish fullroute.

Movie quality/audio remain FAIL: natural313presented/117dropped,14.523s; both normal/skip have1underrun18556silencebytes. Source ski pair263e8f16 and PS2ski/rider provenance remain unresolved,25late textureevictions in current window; no residency/wholeescape acceptance. Original49152B KOS held throughout; sampled game-frame minimum40816/top37888, no total minimum inside paused movie claimed. The old original-EVD512x512 key792f940a is not read on the PS2S00 path. Evidence r333-s00-ps2-movie-gate.json, h-i18f5-state1/resume1 and state3/skip2. Source review pending at drafting.

Independent next-boundary audit finds cSofdec still stubbed for gameResult's movie/ending.sfd. OriginalGCending raw6475pictures/~216s versus PS2r333s20 raw7295/~243s does not qualify replacement. No ending mapping inferred from filenames or duration; r333-ending-source-index.json and r333-ending-duration-audit.json preserve the findings.
