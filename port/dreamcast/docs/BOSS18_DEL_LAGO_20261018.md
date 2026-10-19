# Del Lago model calibration, 2026-10-18

Retain the full PS2 model in r10b. The two protected reductions tested here save only 0.182 and 0.320 ms per drawn frame, below the requested approximately 1 ms threshold. They remain private diagnostic candidates; no gameplay default changes. This completes the bounded Del Lago calibration milestone, not boss18 or route acceptance.

## Models and protected source geometry

Full has 1,588 positions, 2,877 triangles and 4,275 strip vertices on the original 35-bone GameCube runtime skeleton. The original boss17 full conversion and 75 fish/boat/mask support files were reused exactly. PS2 geometry, material and opacity identities are retained; the GC skeleton, motions, target boxes and damage code remain source-owned. Source damage uses Yarare parts rather than render triangles (harpoon 100, ordinary guns 1, explosive 1,000).

Jaw part 9, tentacles 29..34 and terminal fin/tail parts 12/15/19/22/28 protect 1,265 exact faces and 768 fixed source vertices. Native 512 KiB host conversion, exact oriented triangle agreement, contact identities and target package positive/refusal controls pass. Full/min have eight target controls; near-g70 has four additional controls. The optional source-index locks preserve the default reducer when empty.

| Diagnostic name | Achieved positions | Triangles | Strip vertices | Local cap | MODELLED ms/frame | Saving |
|---|---:|---:|---:|---:|---:|---:|
| full | 1588 (100%) | 2877 | 4275 | n/a | 75.719 | n/a |
| protected-min | 1245 (78.4%) | 2191 | 3333 | 80 mm | 75.537 | 0.182 |
| near-g70 | 1075 (67.7%) | 1851 | 2817 | 160 mm | 75.399 | 0.320 |

The nominal 50% attempts did not reach 50% at either tested cap with the protections unchanged. No g50 timing is estimated. The initial reducer's 908 locked classification is dynamic and is not proof of a permanent vertex floor. The larger cap's sampled surface errors (vertices and centroids, not continuous Hausdorff) are forward p95/max 86.863/221.768 mm and reverse 48.294/200.206 mm. At 80 mm they are 45.322/105.318 and 28.715/85.740 mm. Material/contact identities and original bone weights remain exact at protected contacts.

## Actual fight and BIN 6

The retained r10b fixture uses ordinary A boarding inputs and an ordinary START cancellation of appearance movie source id 0x10b10. Its callback and fight spawn execute. Earlier post-boarding movement reaches the timing window inside the unchanged capture deadline. No room, spawn or gameplay code was edited.

Staged emleon00.esl SHA256 ccfdb4a7a301a189259cc001fb47f518b83bd6f900289bc3ed25c2619ea39715 (8,160 B) has the same r10b rows as retained PS2 source: A0 boat id0f/type0, A1 Del Lago id2f/type0/set1, and A2/A3 type0/set2 drowning helpers. The pre-fight helper is intentionally parked below the lake, reported separately from visible fight actors. No type1/BIN6 spawn was found in those rows or the source room spawn path. A read-only model observer validates actual fight id2f/type0/35 parts; NMRS draw-order field ot is not used as type proof. BIN6 cost is not priced. PS2/GC BIN6 bytes differ, so an old same-model comment is not a semantic identity proof.

All three fight arms show native Del Lago, boat, fish and Leon with CAST-GC zero unlisted GC rows and no native declines. Sequential ordinary aim/throw inputs cause observed source HP 1,000 to 900 in all three arms. The earlier overlapping-input trial did not throw; it is retained as a timing fixture, not hit proof.

## Timing and identical-source checks

Build b18srT uses T15REC + CH2REC, LOGIC_TRACE/GAME_DECISION_TRACE, source codec readiness, pace off, 8,192 B PCS records, heap4 watermarks and actual KOS squeeze 49,152 B. ELF SHA256 daac42cfdc2cbadf82166f33638b86882eeefb6b4a7d30c230c678767e7c08bb. Full and candidates use identical boot and overlays with only their private registry data selected.

Authoritative hwproject runs are hwmodel-b18-r10b-fast-{full,min,g70}a, source frames 390:409 and traces 390/395/400/405, tail 4. HWM_SECONDS=52; source collection completes through frame413 within about40.4 s, wrapper about56 s. Values above are MODELLED SH-4 at200 MHz, not console measurements or host FPS. The exact compiled vsync loop contributes 0.000055 ms to each arm; no other costs are removed. An earlier requested690:709 window reached only473 by its deadline and yields no timing.

Actual hardware-window full/min, full/near-g70 and normal/full versus hardware/full each pass 20/20 source ticks STRICT plus MUST-IDENTICAL decisions. Harpoon full/min and full/near-g70 each pass 601 room ticks STRICT plus decisions, with zero drift, masked ticks, gaps or allocation failures. Original boarding full/min also pass601 ticks. Dedicated r10b A/A and delay controls were not repeated; the same b18srT build's El Gigante controls are documented separately.

Fresh Flycast sampling in the same390:409 window yields full62.6/min62.2/near-g70 61.9 ms from1,255/1,247/1,242 samples at1 kHz across20 complete frames. No lost, late or host-gap records; actual sampled source pairs pass20/20 STRICT plus decisions. These are diagnostic sampled guest costs, too coarse to certify a sub-ms saving; the hardware model supplies the rung decision.

## Memory, transport and scope

Lowest observed heap4 free/largest B: full543136/530432, min496896/484192, near-g70503232/490528. All three at source tick600: VRAM pinned356768, dynamic1321120, other90112, free799424, largest764864 B; zero refusals, no-contiguous, evictions or retries. TEXCHK fails0, allocation failures0, KOS held49152 B. Dynamic loads are not a blanket proof of no disc re-reads.

Appearance movie s10 is intentionally skipped normally after2/1077 frames; callback resumes the fight. Heap4 returns from active movie to pre-movie free bytes (full906336->542144->906336; min860096->495904->860096; near-g70866432->502240->866432). Each records one audio underrun/18,556 silence bytes. Full movie playback, clean audio, death/rope QTE, doors and route acceptance are not claimed. A pre-room source OSCheckHeap(-1) warning is retained in the gate report; subsequent heap checks succeed. No GC character fallback or gate weakening was added.

Fresh T15REC knob-off identity is the existing b18irP boot plus10 overlays, byte-identical to frozen c18irP. Boot SHA256 9dbb243431064e5b65c875f44ae4b75a14047a9c20f309d7c41b2b6c83d80c23. Source commits only add isolated specs and the previously verified default-empty reducer option; no runtime, converter, recipe or harness source changes.

## Private outputs and review

Data /root/re4data/private/boss18-dellago-20261018 and immediate C mirror C:/Game Dev/Emulators/re4-assets-private/boss18-dellago-20261018:496 files,25,473,570 B. SHA256SUMS SHA256 18a5ca3aabd476d38ed7f28ee6f78b4d0c155af81f12fff8c7e11a30057d1f80.

| Package | Registry SHA256 | Logical arena B |
|---|---|---:|
| full | 2dc497bdf84e3b3a7640f6529c893cbe4bb11039435f9120015dcdad91988c73 | 95944 |
| protected-min | a84d3ac445fcf69a0c298fd0b800fd468894c581333de5cc27e921269cacfb7d | 142200 |
| near-g70 | de92735f0f7ee27b32082524d96b4522cdee0b0de8fb02aafbacf9e5bd41b31e | 135848 |

Allocator cell overhead is32 B. Source geometry and textures remain private; no game bytes or media are in Git.

Evidence root C:/Flycast-Evidence/re4-dreamcast/boss18-20261018. Inspected del-lago-sheet.png has actual body hold697/LT696, proven before/after read-only VRAM capture for every arm; full/candidate source traces and decisions match697/697 ticks. Offline source/full/reduced matched cameras and lighting are in del-lago-rest-sheet.png. The body still fixture and earlier timing fixture are explicitly distinct. No look choice is required for skipped rungs; retain full. Main reports: r10b-calibration-fast.json, r10b-model-gates.json, r10b-{shots,hw,pcs,held}*-{strict,decisions}.json, dellago-esl-audit.json and per-capture source-hold-proof.json.
