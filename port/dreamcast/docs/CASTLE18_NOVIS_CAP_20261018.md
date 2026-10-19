# Castle I-006 cap progress, 2026-10-18

Current runtime source: codex/castle18 30234c765c38e2992c135dd71988ce042d90aa0e, including integration3830a335. Source commits402116c9/30234c76 are pushed. Earlier293/267 runtime results below are historical; current qualification is recorded first. Full Castle is incomplete. Island remains paused under I-007; boss modeling belongs Boss18. Final seven accessory/weapon variants and 1650-file data seal are reused unchanged.

## Final cap-only recipe and exact r20a data, current383

Branch source3f413152 includes CH4REC selection df60467e and the new r20a registry spec. No runtime code changed after30234c76. EVENT_SWAP_RELOAD remains off in CH4REC; the private source-event tests below do not enable it.

Literal final CH4REC builds (no phase/jump/reload extras in these arms), SOURCE_DATE_EPOCH1760000000, JOBS4 under the shared build guard:

| Arm | Full ELF SHA256 | _end | Result |
|---|---|---|---|
| c18nerP | ddda161825800e75cee37e06c0bdfebe9e04148dff500900a5241d8d6480869e | 8c456238 | missing0, actual cap1/reload0 |
| c18nfmW | 3c5afed6e761a538 (full SHA in cap-final383-builds/proof.json) | 8c464f18 | missing0, cap1/reload0, 48KiB memory twin |

The fresh canonical cap-only memory twin passes all six actual49152-byte holds; this supersedes the private cap+reload memory numbers as the final recipe gate. Every55s run exits under60s. No OOM/HALT/FAULT/MISSING, and all room activity/completion checks pass. Full room CAST/audio failures remain separate.

| Room | Normal headroom / top B | Fragmented headroom / top B |
|---|---|---|
| r224 | 50008 /49056 | 49920 /36992 |
| r226 | 37368 /36448 | 37272 /35872 |
| r227 | 34928 /33792 | 34840 /33152 |

Evidence: cap-final383-builds/proof.json and full ELFs/knobs/generated headers/build logs, cap-final383-kos-fixtures, cap-final383-kos-runs, h-c18nf-kos, kos-cap-final383-summary.json. Existing current383 knob-off Disc1 gate still matches independent frozen383 boot+10overlays11/11; subsequent source changes are recipe/spec/data/documentation only and leave T15REC unchanged.

### Missing r20a package repaired by exact reuse

3f413152 adds ps2-ch4-r20a.json. The effective chapter3 and chapter4 r20a ESLs each contain two type0 Novistadors. The existing full PS2 type0 conversion is reused without modeling. Seven arrays (positions, normals, UV, stream, weights, parents, bind) and the PS2 atlas match the sealed r205 model byte for byte. The new room-owned package is62560B, arena66656B. All model headers, source types, joints, attachments, collision, material and animation contracts are unchanged. Only two copied source/catalog metadata room lists add the source-verified r20a declaration. The original r205 data is immutable. The first package attempt correctly refused the missing room declaration; no checker or converter was changed to bypass it. Type4 r213/r21d are explicitly excluded from this reuse.

Data castle18-novis-r20a-20261018:48files, SHA256SUMS181faf73d225950296af3121cfa8cc25c7a661c35f97fba16488dd93a1ea2069, verified immediate C mirror. Evidence r20a-native-package-reuse-proof.json. Runtime r20ap now draws172 native rows (absent0), replacing the former missing-package gap. Active OT5/refraction and other source semantic refusals remain and keep full CAST FAIL.

### Exact palette path replaces the optional lossy experiment

Nine additional textures have lossless PAL4 representations: all73216 decoded16-bit pixels, including alpha, equal their original Morton-order words. This saves109536B. Combined with the earlier three exact maps, this is12maps/267824pixels and404352B saved, without changing a source texel. No geometry, atlas, material, source CRC identity or runtime code changes. Data castle18-r20a-more-exact-pal4-20261018 SHA256SUMS0ce6ef03908f3e3a57c59cb7bfbf21f972fadc80e97865e5f34975298269a866, immediate verified C mirror.

In actual c18narT r20ax (full native type0 package +12exact PAL4 +additive resident list, NO four-body lossy VQ), TEX0 through480, the same two source kills at103/156 after23hits each, and native172rows/absent0. Last UI free308192B versus148448B and TEX1 in r20ap with only3exact maps. At preload249, pinned2279776/dynamic0/other65536/free222112/largest20448B; later used2193696/free308192B. Logged evictions/retries remain: this is a bounded texture/admission improvement, not full traversal/no-reread/residency acceptance.

The earlier four-body VQ option remains UNADOPTED and is unnecessary for this exact solution. Its original no-native-package r20av result was TEX0, but adding the actual native package in r20aw exposes one different texture allocation failure (a757473f). Do not extrapolate the old trial to the final data. The optional user look question was withdrawn; no visible approximation was adopted.

### Exactness qualification and the released effect trace

Legacy c18narT r20ap vs r20ax passes STRICT435ticks with zero actor/player drift (3022enemy samples), but the standard decisions checker retains MUST-DIFFER at one global tick284: ep9d99ab72/145742 vs a96f7629/145742. No difference is hidden or tolerated. The old trace had LOGIC_TRACE_OWNERSHIP=0 and read an effect backing during room replacement.

A fresh matched pair uses EXISTING LOGIC_TRACE_OWNERSHIP=1 with its required TRACE_SS_MASK=0, with no source/checker edits. c18nhrT ELF e5c17ec4a0e1699fac96410e531f2fdefc89459e6557f3c59895c12b636ea499, end8c464398, missing0. Both logs show LO release at282(site2) and284(site3), ow00 through293, then original source publications for all five domains at294. Tick284 is explicitly unavailable, rather than read from released memory. The standard tools then pass STRICT477 aligned owned ticks and MUST-IDENTICAL476decision ticks,3332enemy samples, zero drift, all must rows equal. The generic frame-gap warning is retained: both logs have the same source-declared unowned intervals, not an undisclosed masking or tolerance change. This is an owned-state comparison, not every loading tick. Both runs retain the same source kills, with exact12 TEX0 and exact3 TEX1.

Evidence: owner383h-build/proof.json and full ELF/knobs/log; h-c18nhrT-r20ao/h-c18nhrT-r20az; current383-r20a-owned-exact12-vs3-{strict,decisions}.json. The initial c18ng attempt stopped at the existing build guard because TRACE_SS_MASK=1 cannot combine with ownership; preserved as setup failure before compilation. Fresh h used the allowed flag combination.

Full Castle remains WORKING. Active camouflage/refraction stays refused pending a separate renderer review, BGM1 fit and full doors/route are open. r203 source key-wave diagnostics continue on the canonical c18nfmW; nine initial source kills are proved, key callback/door acceptance is not yet proved. Boss18 supplies boss model/auxiliary source data; Castle retains room staging and route work.

## Current383 completed cap, source-event and memory gates

The CH4REC now selects existing ALIVE_CAP_NOVIS=1, as required by I-006. It does not change T15REC or enable EVENT_SWAP_RELOAD. The latter remains a private, separately qualified source-event option. New runtime knobs still default off. This source recipe update follows these matched current383 progress tests; the fresh literal recipe build is recorded separately after packaging.

| Room / fixture | Reference sampled peak | Capped sampled peak | Source progress, both modes | Queue / clear evidence |
|---|---:|---:|---|---|
| r205q, original appearance + drain + source areas | 5 | 4 | 12 source kills; all tested wave flags fbc00000 | 1 held/1 released; no take/drop/park; enemy-empty through3120/3180 |
| r20ar, chapter4 list via diagnostic jump | 2 | 2 | 2 source kills; STRICT and MUST-IDENTICAL506ticks, room anchors281/281, 3513 enemy samples, zero drift | below cap; empty300..480; no hold required |
| r213p, isolated hive break | 9 | 4 | original hive6000hp/71hits/death151, same a0000000; 7 ordinary kills + original critical pair cleanup | 5 held/5 released; empty1020/1140; no take/drop/park |
| r21da, D + both switches + final/reset waves | 10 | 4 | 25 source kills; same final07800000 | 8 held/8 released; empty through4320/4440 beyond reset delay; no take/drop/park |

The effective selected chapter ESL audit finds only these four stage2 Novistador rooms. No effective Novistador/Ganado co-rows were found; mixed-ID shared-cap behavior is covered by the actual source-extracted host test. These are progress/pointer and below-cap exactness gates, not a claim that all room traces are identical under intentional population/order changes. Diagnostic initial positions, source-area gotos and normal source damage calls are explicit; this is not a natural door-route proof. Every original actor is accounted for. All processes ran under60s through trace_lock with owned-PID production snapshot continuation; repeated snapshot history is deduplicated by kill frame/hit count. Models, source callbacks, ESL and door task bodies were not bypassed.

The old r205y fixture missed the post-drain C area and reached only10kills/f9400000. It is retained as partial evidence. Fresh r205q revisits original areaC at1600 then special58 area1B at2500, reaching the12 intended source actors and fbc00000 in both modes. The earlier r21d expected27 count was an audit error: D's four sends are inside the initial15 budget, followed by10 final/reset kills, hence25. Neither discarded interpretation is accepted as a route pass.

### Existing r213 source-event reload, private only

Current na/reload0 reproduces the immutable-EVD MemorySwap refusal. Existing EVENT_SWAP_RELOAD=1 in nb and matched cap-off nd reads the unchanged original EVD and proves both normal end and ordinary START skip through the original callbacks. The1661728-byte em2d prefix is fully covered, differing0/runs0; swap-in and restore CRC f22e3ef9 match, restore ok1. Normal end uses no action/kill/prefilledRsf0; original source event ends and sets80000000 in both modes. Ordinary START90 separately restores the same CRC, resumes gameplay, releases all5held actors and clears all9 source Novistadors by1800. No movie cursor, event-code/data or RAM patch was made. This is original EVD playback, not an SFD/SEQ picture-clock acceptance claim. Source EVD SHA9b181d4c34e1dfd6b704441c310ad15f32febd0d9007b659996618bd25eff47f and EVQ31476190198c70978a393452c877fc7c4d2cc0e23f9589a7215312ba30015780 remain unchanged.

| Additional arm | ELF SHA256 | _end | Purpose |
|---|---|---|---|
| c18ndrT | 862904ee2964a150452b0689f03b9c1f302b431a7578c91a81e0ffb30d5bcfd7 | 8c464fd8 | cap-off + existing reload1, matched normal source event |
| c18ncmW | afc152599b543accbf4d3210344e8765a45b9957b1c8257b017018d1e6beddda | 8c466138 | private cap1+reload1 48KiB memory twin, no phase/jump extras |

Both missing0. Full ELFs/knobs/generated headers/compressed build logs are mirrored under current383-builds; provenance-reload-kos-supplement.json adds them without modifying the first provenance seal. Runtime source remains30234c76;43893be8 only changed documentation.

### KOS 48KiB: all six current383 allocation gates PASS

c18ncmW actually holds49152bytes in all6tests, with0OOM/HALT/FAULT/MISSING and continuing room activity. r226 uses the completed8-info variant data. Full room CAST/audio acceptance is separate.

| Room | Normal min headroom / top bytes | Fragmented min headroom / top bytes |
|---|---|---|
| r224 | 53560 /52608 | 53472 /40544 |
| r226 | 40920 /40000 | 40824 /39424 |
| r227 | 38480 /37408 | 38392 /36704 |

Each requested55s and exited under60s. Evidence: kos-current383-summary.json, current383-kos-fixtures/current383-kos-runs and h-c18nc-kos. The runner's other full-room failures are retained; they are not allocation failures.

### r20a texture residency and private look option

b383e110 adds10 measured source keys/dimensions/formats to the room resident list. Its commit title called these world textures; inspection proves the recovered images are Novistador body/detail maps. This correction does not change their exact source identities. The additive resident union preserves every other packed room record and covers all37 current Castle lists; no all116-room claim is made because newer outside-Castle lists differ.

Three I4 textures have exact PAL4 derivatives: independent decoding compares all19660816-bit source words exactly, saving294816bytes with unchanged alpha. PAL4 alone plus the completed resident list still produces3TEX failures in both r20ar runs. Nine raw texture inputs were recovered byte-exact from the verified existing ch3 set, not regenerated.

Private r20av additionally stages four historical c42 body/detail keys 1cd605d4/2bf09d1d/99ce795e/f911150f with existing VQ codec derivatives. These save450560bytes, preserve alpha/dimensions/names/format, and actual decoded RGBA PSNR is33.27/37.23/32.69/33.97dB. This matches rounded historical quality figures, not lost-output byte identity. Both55.88s current383 runs have TEX0/no allocation failure through480, versus TEX3 on exact PAL4+resident. Both still kill the same2enemies; STRICT/MUST-IDENTICAL512ticks,3569enemy samples, zero drift. Their remaining native model absence/camouflage failures are retained. The variants' model geometry, native atlas/material and source refraction contracts are unchanged. The four compressed body textures are NOT adopted pending the user's still-pair choice; two other generated maps in the sheet were not staged. No new3D modeling was performed.

Evidence/data seals:
- current383-r20a-texture-codec-benefit.json, current383-r20ar-{strict,decisions}.json and current383-r20av-{strict,decisions}.json.
- r20a exact PAL4 SHA256SUMS8c0df865daef03003a6d444c45171f6f33bb27bae87d20e3d529304501a1d90e.
- r20a additive resident SHA256SUMS53c2bb6893e64c081e1228badf2902dff34e7c764a238053226d8f82c83636e2.
- r20a private VQ SHA256SUMSe46e1a06fd035183de55059781bac2693028af2e9f16300c10bc99699de21429.
- All three sets verified under C:/Game Dev/Emulators/re4-assets-private and /root/re4data/private, with dated Castle names. Look sheet: castle18-r20a-vq-candidate-20261018/r20a-vq-look-sheet.png.

Full Castle remains incomplete: active Novistador camouflage/refraction remains refused, r20a native absence is not repaired by texture compression, BGM1 fixed-slot fit remains open, and full wave/door/event/cast/residency route acceptance continues. No release/hardware claim is made.

## Current383 hive gate and provenance

402116c9 merged31 incoming paths from integration3830a335. The only conflict was the r205 registry JSON: incoming partial_sections=true for both descriptors was obsolete. Retained the already qualified full Castle descriptors; all other JSON fields were identical. Atlas sampler4/locked-vertex3 host tests pass. All seven Castle variant presets/data remain unchanged.

30234c76 changes only knob-on r213 send order and adds the correct st2_2/r213 object macro. C5/C8 initialize against intact source hive collision before the regular seven; four real slots are used and five regular sends are held. The original R213SuBreakModel and enemy AI remain unchanged. With the knob off the original nine-send order is preserved; when Rsf2 is already set the original seven-only branch is preserved. The source-extracted regression compiles actual R213EmSet and SuBreakModel in both modes and reproduces missing critical pointers against the pre-fix negative control.

The prior cap1 phase guest gate is a real rejected candidate: C5/C8 had hp0 but remained alive in routines1/28 and1/2 through room2580. The read-only owned-process observer and source em2d set4 branch establish the collision-dependent initialization cause. No generic hp/death/routine injection was added.

Current383 programs, SOURCE_DATE_EPOCH1760000000, JOBS4 under the shared build guard:

| Arm | ELF SHA256 prefix | _end | Purpose |
|---|---|---|---|
| c18b383arP | c641e2ae47e1ff39 | 8c4061d8 | independent detached frozen383 T15REC control |
| c18n9rP | a824f1a9ca0d5821 | 8c4061d8 | own knob-off T15REC |
| c18n9rT | f10014474ca8af93 | 8c463d98 | current CH4, cap off, common phase/jump rig |
| c18narT | d190417995f8b19f | 8c463f78 | matched cap on |
| c18nbrT | 1056b075c71cee0f | 8c465198 | cap on plus existing EVENT_SWAP_RELOAD=1, private S00 trial |

All missing0. Actual scrambled Disc1 boot a64f194480afa44a19ea7d8d9960e2593b1e21a38bc4773b64bfa31888396e0e and all10overlays equal frozen383 (11/11). ELF debug/path differences are not payload differences. Compile command checks prove the cap flag on all four intended objects; cabin-source.h and actual dvd.o strings prove reload code only in nb. Full ELFs, resolved knobs, generated headers, compressed build logs and private enemy include hashes are mirrored on C. The initial frozen control build stopped before compilation because its new worktree lacked the pinned submodule; it is retained as a setup failure, not a runtime gate.

Current r213 isolated post-s00 hive gate (same sealed input/data, source damage calls only):

| Metric | c18n9rT cap off | c18narT cap on |
|---|---|---|
| Sampled combined peak | 9 | 4 |
| Hive 4D6000hp death | room151 after71 normal damage updates | room151 after71 normal damage updates |
| Original SuBreak persistent state | a0000000 (initial bit0 plus actual bit2) | same |
| Ordinary Novistador kills | 7 | 7 |
| Critical pair | original callback; both gone | original callback; both gone |
| Held sends / successful releases | 0/0 | 5/5 |
| Empty enemy census | room1020 | room1140 |
| take/drop/park logs | 0 | 0 |

Warm actual45.11/45.01s and exact production snapshot continuations50.69/51.08s. Each process exits under60s via owned-PID close and trace_lock. No input/RAM/instruction/state patch, no actor deleted to enforce cap. Source order/timing/population changes are intentional cap policy; this is a matched progress/pointer gate, not a MUST-IDENTICAL full-trace claim. Snapshot history repeats: unique kill frames plus fresh tails are used. Teardown head0 is not evidence of guest failure or a complete no-fatal gate.

Historical note at43893be8: this closed the isolated source hive-break/capped-clear regression. It is NOT full r213 route acceptance. Active Novistador camouflage remains refused, original S00/source door/bridge progress remains open, and the recipe still does not enable ALIVE_CAP_NOVIS. Current r205 all-wave, r21d combined switches/reset and r20a active2+recovered texture gates continue.

Historical swap-in-only checkpoint at43893be8: original r213 S00 on na still halts at immutable-EVD MemorySwap. Separate existing reload option nb reaches exact1661728-byte archive-prefix compare, all covered/differing0/runs0, and installs EVD with CRC f22e3ef9. Playback, exact restore CRC and event completion are not yet proved; do not enable from swap-in alone. No new event code or assets were generated.

C evidence root: C:/Flycast-Evidence/re4-dreamcast/castle18-20261018.
- current383-build-proof.json, current383-actual-object-proof.json, current383-builds/provenance.json.
- current383-cap-fixtures/fixture-proof.json:11 immutable fixtures, all off/on nonprogram/input hashes equal.
- h-c18n9rT-r213p and h-c18narT-r213p, scenarios warm + resevta; state-seed/before-a bind exact disc/program/exe/input.
- current383-cap-progress.json: explicit source kill events, sampled populations, original flags and queue logs.
- h-c18narT-r213e (expected immutable backing refusal), h-c18nbrT-r213e (private reload trial).
- bgm1-source-duplicate-audit.json and bgm1-exact-sample-audit.json reject unsafe BGM0/BGM1 alias: source members3/7 share wavetable metadata but all eight decoded PCM sample images differ. Prior fixed-layout budget blocker remains.

## Historical293/267 source and runtime evidence

## Source changes

b5869b45 adds default-off ALIVE_CAP_NOVIS. With ALIVE_CAP enabled, stage2 id2D uses the same budget as Ganados10..20 for initial creation, deferred sends and fresh-not-yet-active work. Existing held ESL entries still count in SceCountEmAlive. Existing Castle no-parking exclusions and Ganado-only park selector remain intact: no live Novistador is destroyed to enforce this cap. Existing raw-pointer take exceptions remain visible. r21d's original delayed reset task waits while the combined cap is full; its setReset sets ACTIVE synchronously before another reset task can run.

ea31a7a5 adds narrow source-room repairs behind the same knob. r205 sends69/6F wait for a slot before committing their source wave flag and immediately using the real actor position to open a door. Its actor-hit-list probe skips held wrappers rather than materializing a getPtr exception; a held actor cannot be in that hit list. r213's original statue-broken persistent Rsf2 state is restored after actual release initialization: all C2..CA receive flag20000000; C5/C8 received raw hp0. The actual hive-break gate later proved that this alone is insufficient after the hive SAT is removed; 30234c76 fixes their initialization order (see current section). They are never silently dropped from the queue. r205 held58 also receives its original alert flag1 on release. There is no generic wrapper change, new queue layout, ESL mutation, renderer exception or new model work.

Source-extracted host tests compile old and combined modes. They exercise all256IDs in stages1..4, mixed4 fresh admissions, duplicate-held sends, held-alive counts, paused/full release guards and release order. Real r205 wave functions keep the door send owed while full and issue it once free; held zone wrappers never call getPtr. The actual source-room restore helper changes only the selected source context and checks raw hp/flag writes only. That host model did not prove the actual late-initialized enemy AI enters a death routine; the failing guest hive gate exposed this limitation.

## Initial b5869b45 runtime evidence

Every emulator requested55s, actual55.89..56.44s, trace_lock/release priority/owned processes. After the first pair, Castle captures were serialized under an owned guard because foreign release/model jobs were active. No foreign process was stopped.

- r205 off/on: actual boot plus all22overlays match selected program; zero extra overlays. Reference sampled5 combined enemies, candidate4. Both logs contain5 completed source hp<=0 kills and room census through600. Candidate held70 at4, then released it after a source death, with no take/park/drop. CAST still fails active camouflage; source wave/door completion not proved.
- r213 off/on diagnostic: reference9, candidate4; candidate holds5 and releases3 in the bounded window. Source kills5/7 at different maxroomticks, so no equal-clear claim. Both recovered fixtures retained unused st2_4/em3e overlays from an old build: INVALID for full staged-identity gate, even though boot/all22 selected overlays match. Fresh clean repeats are required.
- r21d off/on diagnostic: reference8, candidate4; both8 completed source kills. Candidate releases all4 deferred1B..1E. Same two unused-overlay issue: INVALID for full staged-identity gate. Original reset/final-switch waves remain pending.
- r20a off/on: zero Novistadors observed, zero holds. Actual program/overlay-set identity passes. STRICT/decisions MUST-IDENTICAL1060ticks (room anchors178/178), zero position drift,535029 em-em checks/37038line queries/1057area/32779damage checks. This is below-cap regression evidence, not Novistador combat coverage.

C evidence root: C:/Flycast-Evidence/re4-dreamcast/castle18-20261018.
- novis-cap-build-proof.json: c18n0rP T15REC off identity11/11 against independent current293 control, actual boota64f1944; c18n0rT53355630/end8c463578 and c18n1rTa31065af/end8c463698. All missing0; source flags independently found in em_set+r21d compile commands. Full ELFs and knobs C-mirrored.
- novis-cap-initial-summary.json, novis-cap-r20a-initial-decisions.json.
- h-c18n0 / h-c18n1, scenarios cx-r{205,213,21d,20a}-walk-capn{0,1}b. setup attempts suffixa failed before stage/capture due an ordinary-runner trace0 assertion; retained as invalid setup logs. The private runner now explicitly accepts trace1 diagnostics.
- novis-cap-esl-inventory.json: exact prepared ESL rows identify r20512, r20a2 (both chapter lists), r2139 and r21d13. No other stage2 Novistador room found in all three selected chapter lists.

## Next

All ea31a7a5 builds complete missing0: c18n2rP ee66d375/end8c4061d8, c18n2rT d4423144/end8c463578, c18n3rT faa3eb4f/end8c463758. Full ELFs/knobs mirrored. novis-cap-v2-build-proof.json proves all3 object macros and off11/11identity against current293 control (boota64f1944). New clean fixtures must remove all overlays absent from the selected program and assert the entire actual staged overlay set before capture. Use earlier bounded kills, then supported production save-state continuation for queued tails/reset waves if the one-minute window is insufficient. Do not mark queue/room/route progress complete from entry or a peak alone. Keep CH4REC unchanged until these source contracts pass.

Remaining full lane work: camouflage/refraction renderer review (retain refusal), room CAST/residency/audio/clear/wave/door gates, all Castle route rooms in order. Current existing task1 Ashley/chapter2 identity/STRICT and six48KiB KOS gates remain recorded; no repeat of the fixed archive admission. Revisit KOS on any final new runtime recipe. Boss models remain current while Boss18 owns changes.
