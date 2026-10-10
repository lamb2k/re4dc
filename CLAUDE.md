# RE4 Dreamcast working handoff

2026-10-09 issues 9 and 15: the crash screen adds an `asic` line (ASIC_ACK_A/B/C,
TA_OPB_INIT) to the first-failure snapshot; disc streams decode with the SND_SHD
coefficient order (battle music and radio voices no longer saturate); prebuilt
banks use an anti-alias decimator (aica_banks.py decimate_aa, same sizes; refilter
an existing disc with `aica_banks.py reconvert`). H2/bell STRICT, s30, calls, New
Game and the inventory set pass in Flycast. A GDEMU test package was built; no
release or SD write. TA_GUARD=1 was not used (it changes drawing). See
[route doc](port/dreamcast/docs/D367_THIRTY_FPS_ROUTE.md) 2026-10-09.

2026-10-08 lamp correction: source owner 0x5e now reaches the existing native
sprite filter. The matched r102 impact shows flame/smoke, with 2,795 STRICT
source records and identical required decisions. Paired drawn hardware-model
frames cost +2.137605 ms; existing particle limits remain. The combined manual
GDI passes cold Load, visible Leon, 39-second Yellow Herb Examine, exact 3 MiB
restore and movement. See [qualification](port/dreamcast/docs/D367_LAMP_FIRE_20261008.md).
Physical console, bridge timeout and herb appearance remain open; no binary
release or SD write. This supersedes the pending lamp status in older entries.

2026-10-08 inventory correction: detach the renderer's retained-storage borrow
before the inventory swap reuses room memory. The supplied-save cold-load
reproduction now passes Green and Yellow Herb examinations, visible Leon,
repeated exact 3 MiB restores and movement in Flycast. Current-recipe uncapped
village (4,079 records) and house (3,234 records) gates are STRICT with identical
required decisions and preserved house movie/radio resources. See
[the inventory qualification](port/dreamcast/docs/D367_INVENTORY_RETENTION_20261008.md).
Physical-console acceptance and the separately reported bridge timeout remain
open; this does not authorize a binary release or SD change.

2026-10-07 bug follow-up: NATIVE_LASER=1 restores the source weapon beam, while
ACTOR_GANADO_SOURCE_LIGHT=0 implements the user's request that native Ganados
share Leon's prelit lighting path. Beam and lighting each pass 2,911-record
STRICT/required decisions. The final 512-entry s30/radio gate passes at the
accepted 63,584-byte starting heap; clean final linked end/BSS/arena do not grow.
See [the exact qualification](port/dreamcast/docs/D367_BUG_QUALIFICATION_20261007.md).
No new release or SD change; console inventory/bridge/older freeze causes stay
open pending reporter saves/settings. Fog distance and baked Leon are intentional.
The separate live-Leon probe and outdoor guard below remain private/unaccepted.

2026-10-07 outdoor follow-up: all bounded candidates remain unaccepted. The
current-Trans eligibility guard saves 0.699766 modeled ms of synchronous owner
work per drawn square sample, but final exact TA/framebuffer qualification is
REVIEW_REQUIRED. STRICT Bell/H2 and route/resource checks pass; the remaining
movie hashes and 13 held-frame pixels are unexplained. No waiver or default
change was made. Guard source d865794 and diagnostic observer stay private/off;
the accepted local capacity build, public r22j and SD are unchanged. See
[final evidence](port/dreamcast/docs/D367_OUTDOOR_PERF_20261007.md).
The outdoor 30 fps gap remains open. Larger runtime/Leon/model/resource changes
remain subject to the existing architecture/source-evidence contract.

2026-10-07 ordered follow-up: the guarded r104 visibility extension was
measured and rejected; its runtime remains private. GAME_ATLIST_512=1 is now
accepted in the play recipe: cabinet balanced sample 39.832->36.338 modeled ms,
unchanged collision order/cache limits, validated large-list reuse. Static
data +1,536 bytes costs 4 KiB after arena rounding; s30 completes 340/340 at
63,584 bytes and radio backing restores fully. The play checklist records the
exact H2 preserved-memory/timing qualification, bell and checker evidence.
Ordered work is complete. Both Leon knobs remain off: the combined path fails
required allocations/H2 gameplay, and face-only has a weak net gain. Final
capacity-only automated New Game completes 1,971/2,360/1,175 and reaches live
r100 with no required allocation failures. Clean local play ELF 5ad665ec,
CUE/GDI and launcher are recorded in the checklist; its GDI boots separately.
Published r22j and SD folder154 remain unchanged; no new hardware/route acceptance.

Current publication, 2026-10-07: [r22j](https://github.com/lamb2k/re4dc/releases/tag/play-r22j-audio-performance-20261007) includes the validated room music,
PS2_INTERIOR_ACTORS=2 and GAME_ATLIST_OVERFLOW=1 changes plus all r22i fixes.
All four packages and checksums are published and verified. See the play
checklist for build provenance and bounded validation; issue #2 remains open.
Earlier publication/candidate status below is historical.

Current publication, 2026-10-06: r22i packages the validated c36a08cc runtime
with the herb texture additions, pickup ordering, source part animations and
movie staging fix. See the play checklist's r22i section for exact scope and
validation. Issue #2 is still unresolved; the new music, indoor culling and CPU
optimization below are follow-up work outside that release. All existing release caveats still apply.


2026-10-07 follow-up accepted: PS2_INTERIOR_ACTORS=2 and GAME_ATLIST_OVERFLOW=1
are in the play recipe, with the corrected chapter 1-3 bank-9 music asset staged
separately. The play checklist records the measured stair-ascent/cabinet gains,
shared-record STRICT/decision comparisons, s30/radio and final New Game gates.
Published r22i remains unchanged; this does not resolve issue #2 or establish
physical-console or 30 fps acceptance.

Updated 2026-10-05. Project rules: [AGENTS.md](AGENTS.md).

2026-10-07 audio candidate (not in published r22i): r104/r107 select music bank 9; `ROOM_BGM0` now prepares it
in the existing BGM0 slot (236,640 / 264,576 bytes, no layout/reserve growth).
Regenerate and stage the chapter 1-3 `bgm/bio4midi.dat` overlay explicitly using
the play checklist's "room music bank preparation" command; the base stage
route omits these rooms. Driver/sample validation is not console listening.

2026-10-05 (pushed 3f4b599d; test disc r22, not released; fight 73% is a projection): the perf lanes sk / fx / cl / wd / logic are integrated and their 12 knobs
are in build-r21.sh with LINK_ORDER link-order/r21z-perf-c3-8k.ld (route doc "2026-10-05: integrated perf lanes"):
hw ms drawn house 47.80 -> 43.61, fight 66.03 -> 59.10, square 78.03 -> 72.39; console projection fight 66.6% 10.0 fps
-> 73.2% 11.0, house 100% 15.0. Logic STRICT (H2, bell, PACE_FORCE=2 pair). PS2_FOLIAGE_FAR stays off (user look call).
Later 2026-10-05: GAME_ROT_FSCA=1 adopted (user) with LINK_ORDER link-order/r22-fsca-c3-8k.ld: hw ms drawn / skipped
house 42.50 / 21.95, fight 57.54 / 21.96, square 70.75 / 25.08; decisions identical (decision_cmp, H2 / bell / fight;
last-bit maths, so H2 is DISCRETE float drift, not STRICT); console playtest with the next test disc.
2026-10-06 later: lane pc in the recipe: PS2_INTERIOR_CULL=1 + PS2_INTERIOR_ACTORS=1 with the cell as the disc file dc/native/r100/interior.cell (play fixtures must stage it: pack-fixture.sh / interior/add_cell.py), an r100-only heap-4 block lent to every route movie; r100 s30 340/340 at the knob-off heap_before; stair foot -8.6 hw ms (route doc lane pc).
Earlier 2026-10-06: lane pc landed DEFAULT OFF (PS2_INTERIOR_CULL / PS2_INTERIOR_ACTORS, r100 house interior cull, stair foot -7.56 hw ms): not in the recipe because the cell's 47 KB static cost in heap 4 made the r100 s30 movie fail (0/340); being moved to an r100-only disc-loaded allocation. Heap-4 gate (coordinator 2026-10-06): every landing that grows .text, .rodata or .bss, or uses more heap 4, runs H2 through r100 s30 with its knobs on, confirms s30 plays 340/340 and reports heap_before at s30; the New Game gate stops before s30 and does not count.
Later 2026-10-05: lanes el / iv / ph landed default off; CROWD_INVIS_SKIP=1 + EFFECT_FADE_CLAMP=1 (the white window-glare fix) in the recipe (user), fight 54.37 / 22.13 hw ms, logic STRICT; PS2 haze waits for the user's r22h console look (route doc lane ph).

**Active (D367, user-directed).** Goals:
- 30 fps at full game speed (33.3 ms a tick: gameplay G <= 24 + render R <= 6 + a margin) on a real NTSC Dreamcast via GDEMU + VMU, per the 2026-09-25 rethink (a coarse complete square first). This is the acceptance target; 20 fps and a 15 fps fight fallback were the earlier targets (historical).
- The recovered game playing r100 -> r101 -> r103 with PS2-FMV cutscenes, music, inventory and retry.

Resume with the shared skill `re4-dreamcast-d367` (Claude and Codex): it covers the procedure, harness, commit recipe and standing decisions. Then read [D367_THIRTY_FPS_ROUTE.md](port/dreamcast/docs/D367_THIRTY_FPS_ROUTE.md):
- its "30 fps rethink" status (the older "Work plan: serialized perf lane" table and the 20 fps budget are history);
- every user decision.

Build recipes are in [tools/d367/README.md](port/dreamcast/tools/d367/README.md). The current recipe is port/dreamcast/tools/d367/build-r21.sh plus the play overrides in the checklist; quote its `resolved-knobs.txt` (make's resolved values, since 8f34aa63), not the make line (README "Current effective recipe"). LH (83 ms Flycast, 120.3 hw) is a dated 2026-09-23 snapshot.

2026-09-25: the r101 square (30 fps rethink) follows [D367_SQUARE_PERF_PLAN.md](port/dreamcast/docs/D367_SQUARE_PERF_PLAN.md), section "Current order and status". Frame pacing and the coarse renderer landed default off (f4da5fd); R headroom and code placement (LINK_ORDER) landed default off (801d72d); the em-em candidate cache GAME_ATCHK_CACHE (aeefd26), the workAt inline GAME_WORKAT_INLINE (3eaa868) and the line queries' leaf and block walk kernels GAME_LINE_LEAF (cf46edc) and GAME_LINE_WALK (ba73027) and the pieces' transforms GAME_LINE_PIECE (4e394ea) and the skeleton kernels GAME_PWC_KERNEL / GAME_PMC_KERNEL / GAME_HERMITE_FAST (ddea9bf) landed default off: G_q 29.55 (fx9, after the effect pools GAME_FX_SCAN + GAME_FX_MOVE, 1d3dc4d; sq97 30.66 before); the collision stack (7caa2f7) 29.03 alone (gc13); on the landed stack together (sq99) G_q 28.29, with the skeleton lane and the object scans (sq100) G_q 26.34, with collision batch 7 and the object batch 2 (sq103) G_q 25.22, and with the area lists rev 2, the object batch 3 and the skeleton batch 3 GAME_VEC_NORM_INLINE / GAME_MTXINV_SCHED (4f81bbd) (sq104) **G_q 24.57** (under the 24.97 target; superseded: a stride-8 trace, G is not closed, see 2026-09-26 night below); the skeleton lane (ee7d080) 29.14 alone (sk10); the vertex kernel ACTOR_VTX_KERNEL (42afaa1, rev 2 7726caa, rev 3 d938501, rev 4 + 5 e4fb8e8) takes the reduced characters 15.84 -> 8.65 ms (vl26; version C R 12.70, ~21 fps paced on sq104's G: superseded with that G); collision batch 7 (ca229cf), the area lists rev 2 (ff32da9) and the object batches 2 and 3 GAME_OB_MAT / GAME_OB_PATH (9f66533), GAME_OB_NEAR / GAME_OB_DECODE (97874b5) landed default off; the coarse world's ground takes the source's lit tones from v10 (05e402a, private header); the coarse world COARSE_WORLD (6f4c91c: houses, ground, sky, trees; R +0.68) and the object scans GAME_OB_SCAN (0862e7c) landed default off; R 4.05 with coarse stick figures (cl22), 26.47 with the reduced characters (version C, cl21), 19.89 after the cl lane's fitted meshes and FTRV adapters (cl42; landed 9df764b default off). Since the evening of 2026-09-25 the work runs in parallel, non-overlapping agent lanes (cl characters, vl vertex loop, gc collision, fx effects, sk skeleton, wd world, bg route bugs; lane map in that section; by return, user 2026-09-26: gc / ob / vl park after their current batches, sk / cl / bg carry on): per change one cost arm and one STRICT gate, and the main session lands every patch via warp/tree7. An external, user-launched agent builds the first level's cast models (integrated by COARSE_GANADO_CAST, 08d2216); a second external agent will rebuild the r101 world's assets (the user rejected the coarse world's look on 2026-09-26; prompt in re4-assets-private/world-agent-20260926/); no in-session agent builds models. 2026-09-26 evening: version C on the landed stack measures G_std 24.84, G_fight 29.30, R_fight 11.77 (sq105-sq107: ~10 fps paced in the kite fight); COARSE_PREGATE + CHAR_DATA_BLOCK landed default off (c6edb6f); the user: the environments are not compromised (the budget is made to fit them), work backwards from the original world (route doc, user decisions 2026-09-26 evening). 2026-09-26 night: those G figures were sampled on one Frame_cnt residue; over all ticks G_std ~25.92 and G_fight ~29.61, so G is not closed (trace stride 7 from now on; R arms had run at 18 m fog); the original GameCube world was never fully drawn by the game (route doc, progress 2026-09-26 night); world runtime rev 2 + COARSE_NO_STD_SCENERY landed default off (e69737e); route fixes 7f1533d..c999bea (SE random tables, post-house call, createBack, s20 movie claim). The user's world picks (C1b, "Go with recommendations"): look A, ground R14, PS2 tree geometry, fog F0; d1 authorized (route doc, user decisions 2026-09-26 night). The full original set draws in-game (R 94.74 hw ms in F, ~8 fps); its look gaps against Dolphin (ground, Filter00, sky fog, fires) are being diagnosed. Measured re-baseline (G0, 25 m, stride 7): G_std 25.75, G_fight 29.23, R 12.47 / 11.44 / peak 13.49 (version C, knobs off); COARSE_ONE_SUBMIT landed default off (e874a66: R -0.54 / -0.85 / peak -1.06). Open: the landed recipe is DISCRETE against tr56 / tr42 (float drift from t=182; bisect running). Route: `room_smd.py release` (66b8edd) frees r100 heap 4 for the s20 movie and the full ambush (A1 +1.09 MB); its private data reaches user discs after the audit's proofs.

2026-09-28: r19 -> r21 landed on dreamcast-port (4fb68a8..36e28e0; route doc "Progress 2026-09-28"): the Codex
playability integration, the PS2 r101 world through R4IM + MeshDraw (PS2_WORLD_MESH) and coarse_finite. Recipe:
port/dreamcast/tools/d367/build-r21.sh. Release kite fight 93.3 hw ms: G ~29.0, R ~64 (characters ~35, world 21.9).
The remote is lamb2k/re4dc (the account was renamed from stevedamnvan on 2026-09-29; old URLs redirect).

2026-10-02: hardware readiness (route doc "Hardware readiness"): Flycast hides SH-4 misaligned faults; r21m would
crash early in r100 on a console. Fixed (cCtrl work 0x14, `u16_un`), CRASH_SCREEN=1 in every play build (asks for a
ticket), tools in port/dreamcast/tools/d367/hwready. Any new room gets an align run before a console disc.

2026-10-02 (user r21n play): calls released ~2.3 MB of room textures and reloaded them for 5-6 s; SS_PACK=1 packs
the sub screen area into TA bank 1 instead (0 released). The r100 s30 cliff cutscene failed for heap 4;
MOVIE_HEAP_EVICT=1 evicts motion keys for it. Both in build-r21.sh (route doc "Radio calls and the cliff cutscene").

2026-10-03 (user r21o play): skewed wall textures came from mesh_lod's geometry-only collapses (UVs clamped across
seams), not the PS2 data; PS2 world packages are now built with --lod-uv-guard 0.002 (fixture title-c13). The
"native closed pass requested" halt is caught by CLOSED_PASS_KEEP=1 (build-r21.sh); its caller is still unknown.
CLOSED_PASS_KEEP is a crash-avoidance fallback (ordering / alpha / depth unresolved), not proof of correct rendering.
Loading: PS2_PRELOAD_LEAN=1 (build-r21.sh) preloads the PS2 world package's textures instead of the replaced GameCube
scenery's (r100 route preload 16.3 -> 7.2 s); TEX_PACK=1 (build-r21.sh) + dc/tex.pak (tools/d367/route/pack-fixture.sh)
loads every texture package from one file (room entry 7.2 -> 3.1 s, east walk 6.5 -> 2.7 s).

2026-10-03 (architect review, doc corrections; details in the route doc, square plan, checklist and README):
- ACT_CAP: the r101 approval is historical, the r100 H2 cap arm a diagnostic; capped results never back
  ACT_CAP=0 preservation claims.
- Logic tick vs drawn image; capacity 30G + F x R; old quiet / coarse / fight estimates do not transfer to H / H2.
- TA banks are 2 MiB x 2 (SS_PACK owns bank 1 while a sub screen is open).
- Movies: blocking movies own the frame; stepped / QTE movies do not. The cache loan is owned by ui_bridge.cpp
  (f845b301) and logs the restored bytes. The stepped case is not reproduced in Flycast.
- Pack failures: absent vs read error vs INVALID (766a5fa5); verified content-addressed packs (13eaccec).
- House fixtures: H (unguarded, 2,512-entry pack) vs H2 (guarded, title-c14 pack; diagnostic, same-binary late
  activation).
- Discs: the GDEMU raw 2352-byte image vs the 2048-byte CUE image Flycast boots.
- WP2 (H2, hwsim): Leon by the 4K cast saves 7.09 ms a tick vs the per-part source path. CROWD_READOPT=2 (with
  CROWD_CULL=1 CROWD_FOGSKIP=1) joined the play recipe the same day (user; 7cbea8e7), and MESH_CLIP_LEAN=1 too
  (ce39455f, H2 -2.18).

2026-10-04 (inventory fix, r21t, review; route doc "2026-10-04: review of 2026-10-03/04"):
- 6819f3a2: PS2_WORLD_ROOMS=2 took the inventory's rigid models for room scenery (since ad0c59d0, 2026-09-29; very
  likely in the public r21k-r21m too). r21t is a public prerelease (tag play-r21t-inventory-fix-20261004); its GDEMU
  image boots in Flycast (HLE BIOS) to the title and r100 gameplay, GDEMU / console untested. Play discs now run an
  inventory open/close check (checklist "Play build rules").
- LANDED (local session, gates in docs/lanes/review-fixes.md "Landing"): lane/review-fixes-20261004.
  - TEX_PACK retry spacing, plus a follow-up that re-runs the room preload after the pack recovers. The gate found a
    single read error skipping the whole preload.
  - The TA_HASH whole-meshlet hook and the native_static #error guard.
  - build-r21.sh fails on dead knobs; route-build.sh requires resolved-knobs.txt and now really reports missing
    symbols (link.sh writes the tree's game/obj/missing.txt).
  - H2 STRICT: `om` differs across builds only while the radio-call sub screen has the parts' memory swapped out
    (ticks 741..1217).
- Play disc r21u (b730bf1a; checklist step 6): C:/RE4DC-Play-Discs/r21u-title + r21u-gdemu, launcher
  D:/RE4DC-Play/Play-r21u-Review-Fixes.cmd; GDI boot, New Game, chapter end, inventory r100/r104 all pass. Not released.
- r21v (fe50a85a; route doc "r21v"): the supervisor performance knobs are now IN the play recipe (build-r21.sh);
  r100 24.3 -> 25.9 fps, r101 bell steady 27.1 -> 24.8 ms (Flycast). Disc needs registry/pl08 packages + tex.pak
  (fixtures-v/title-v-pak.json). Released play-r21v-performance-20261004 (page removed 2026-10-04); console test pending.
  H2 STRICT across the radio call needs equal frame times (compare against a LOGIC_TRACE_DELAY_US control).
- LANDED default-off (route doc "supervisor code landed default-off"): experiment/supervisor-20261004's code (r101
  square 90.08 -> 82.65 ms modeled with its knob set, SUPERVISOR_BASELINE_20261004.md). 038d1c59 is split into
  one commit per feature. MESH_STRIP_LEAN now feeds TA_HASH. Not in the play recipe (a separate user decision).
- r21x (a0618068; route doc "r21x"): the first console fixes + the VMU speed page, the main build from now on (user).
  Trans skips the room list walks while the sub screen window is swapped (r21v console fault 0xE0 after the radio
  call / on Y; a strong hook + a link.sh check when SUBSCREEN=1); COARSE_SAT_SCENERY_ONLY=1 (bridge blocker),
  SS_BG_BLACK=1 (tan frame), PACE_VMU=1 (VMU page) in build-r21.sh; the disc needs the call voices in
  bgm/aica_str.dat (aica_banks.py --call-voices). Released play-r21x-vmu-20261004 (page removed 2026-10-04).
- Console calibration 2026-10-04 (route doc "r21x"): the hw model stands; logic x1.07, drawn render x0.95-1.06. On
  the console G is 12.7-20.3 ms (fits 24) and a drawn frame ~53 ms quiet / 90-95 ms with Ganados: the work is
  drawing (user: performance work on the drawing problem next; logic unparked later the same day).
- r21y (564f5168; route doc "r21y"): r21x + the camera fix (cCamera destructors memset(this, 9, 0x200) and four
  end* paths left `extra` set -> the next `delete extra` faulted on the console at the r100 window jump; Flycast resets
  silently: treat "log head decreased: reset" as a possible console fault) + the VMU CPU line as %. Released play-r21y-camera-fix-20261004 (the only release page now).
- r10b (2026-10-10, route doc "r10b", ROUTE_CH13): chapter 1-3 ends at r10b; pl0f / em2f are heap-4 room overlays
  (ROUTE_OVL: tools/link.sh multi-overlay, platform/modules.cpp loader); play discs must stage dc/pl0f.ovl +
  dc/em2f.ovl (checklist 2026-10-10).
- r11b (2026-10-10, route doc "r11b", ROUTE_CH21 needs ROUTE_OVL): chapter 2-1 starts in r11b after the r10b save;
  em22 is a room overlay (stage dc/em22.ovl); stage the le_mirror'd etc/emleon01.esl (raw on the disc: R11bInit hang).
- r119 (2026-10-10, route doc "r119"): El Gigante under ROUTE_CH21; em2b is a room overlay (stage dc/em2b.ovl) and
  must be staged prepared (textures + motion leases, dc/mot keys): the GC body does not fit r119's heap 4.
- LINK_TIGHT / LINK_OVL_HELPERS (2026-10-10, route doc "LINK_TIGHT", default 1 with ROUTE_CH21): no KOS .sub
  padding; helpers only one room overlay reaches live in that overlay (obj/ovlh/moves.tsv), so the overlays must
  come from the same build as the image. MOVIE_FENCE_RETRY: a not-ready fence no longer ends a route movie.
- r11a (2026-10-10, route doc "r11a"): data only. A room counts as built when dc/native/<room>/ps2-world.r4pw is
  staged. aica_banks ROOMS r11a reads em24 at room entry.
- WATER42_GRID_SKIP (2026-10-10, route doc "WATER42_GRID_SKIP", default 1 in the ROUTE_CH13 block): espgen42 (the
  r10a / r11a lake water) keeps only its plane; the GX-only grid update was ~18 hw ms of r11a logic. Logic reads only
  the plane; init RNG draws kept. Find a generator's rooms with a le_mirror SEQUENCE_OBSERVER scan (Kind 1, Espgen_id).
- WATER45_NATIVE (2026-10-10, route doc "r10b lake water", default 1 in the ROUTE_CH13 block): the r10b lake surface
  as a native PVR multiply queued in OT 0x10 (coarse images too), and the PS2 r10b sprite set (GC mist / backdrop
  sheets dropped, PS2 haze). Lake view 61.1 -> 51.6 hw ms drawn. Logic STRICT (H2, bell, r10b).
- Material pair 18d0fd82-2c9a9309 (2026-10-10, route doc "material pair 18d0fd82"): r10b / r11b room model TPL
  (#27 / #28) color + mask; built by pairs_from_log.py --file st1/r11b.das + VQ, staged by lane r11b mkfix r11b().
  pack-fixture.sh replaces an existing dc/tex.pak with a pack of the loose files only: merge the catalog pack first.
- Disc streams (2026-10-10, route doc "stream 1:148"): `aica_banks.py streams --streams ch21` is the chapter 2-1
  play list (CH21_STREAMS); append new streams at the end so earlier entries stay byte-identical. 0:29 (chapter 1-3
  results music) is still not in it.
- Chapter 1-3 (c4ec84e9; route doc "chapter 1-3"): ROUTE_CH13=1, default off; resident-track music in r108/r10a;
  "Coming Soon" at doors into rooms not on the disc. Test disc r21z-c13 awaits the user's console play.
- User 2026-10-04 "Pursue All": logic speed-ups are unparked (exact, STRICT), alongside the drawing lanes, cheaper
  Ganados (gameplay-gated: the AI reads visibility) and PACE_CAP=2. Route doc "chapter 1-3 ... fight plan".
- 2026-10-05 console r22g: fight 70% / 10.4 fps (projected 73%); CPU limits every slow moment; GPU 43-55 ms outdoors,
  11-15 indoors; slowest = inside before the window jump (67%), no preset yet (lane ms). Lane fm: GAME_ROT_FSCA
  (last-bit FSCA local matrices, -1.18 hw ms per tick in the fight) landed default off; adoption awaits the user +
  a console playtest. GAME_TRIG_FSCA failed its decision gate.
- 2026-10-05 lane ln: LEON_NATIVE_PIPE + LEON_FACE_LAZY landed default off (exact, -2.19 hw ms per drawn fight tick,
  28% of Leon's cost: FAIL against the 40% rewrite bar, so no Ganado rewrite). The r21z-c13 disc lacks most textures
  (pack-fixture.sh replaced tex.pak): compare pack keys with the last good disc and boot the real disc before the SD.
- 2026-10-06 WEAPON_HEAP4=1 in the recipe (issue #1 option 3): rifle / TMP / rocket launcher load into heap 4 (+0.3 s per door
  while held, equip reverts when heap 4 is short); r107 has ~100-109 KB heap 4 left with one held (scoped rifle reverts there).
- 2026-10-06 PRIM_CAP_R107=327680 WEAPON_HEAP4_TOP=1 in the recipe: scoped rifle fits in r107 with 360-367 KB heap 4 left (no revert);
  em2a fails in the r100 ambush with the scoped rifle held (warp/cheat only, accepted); r22e fixture uses the prepared em13.
- 2026-10-06 r22f = the play build (a64cef05 + ROUTE_CH13=1): r22e + issue #2 crash screen (all threads, tasks row,
  backtraces) + issue #3 (PS2_WORLD_DYNAMIC=1 with ps2-world.ids fixture files; r105_markOpenCk uninitialised translation
  fixed, the puzzle door opens). pc2 owner-path cull waits for MOVIE_STAGE_ORDER (all three fail s30). Checklist "r22f".
- 2026-10-06 r22e = the play build candidate (d3a36242 + ROUTE_CH13=1): r22d + WEAPON_HEAP4, PRIM_CAP_R107 /
  WEAPON_HEAP4_TOP, prepared em13, PS2_INTERIOR_CULL, EFFECT_PS2_HAZE=1 EFFECT_PS2_STREAK=2, prebuilt weapon sound
  banks (AICA_WEAPONS=1 fixture files); all gates and the issue #1 exact steps pass; checklist "r22e". Known: no
  r104 / r107 room music. Next: r22f (issue #2 crash screen, issue #3 PS2_WORLD_DYNAMIC, owner-path interior cull).
- 2026-10-06 r22d (console test disc, not released): issue #1 fix landed (89035a54 + d72fd6a4, WEAPON_RESIDENT_BYTES=275424
  WEAPON_MODULES=1): shotgun / Punisher / grenades equip without halting; merchant rifle / rocket / TMP still halt, non-handgun weapons silent.
- 2026-10-05 r22c = the play build (user released play-r22c-chapter-1-3-20261005): 2bb24730 + ROUTE_CH13=1 on the
  play flags, fixture lanes-20261005/r22c/fixtures/title-r22c-pak.json; Flycast checks pass, console play pending; GD
  97% full. ROUTE_CH13=1 goes into build-r21.sh after the running lanes land (H2 STRICT on the new base).
- 2026-10-05: PACE_VMU_GPU=1 (test knob) adds `GPU <mean>/<max>` PVR render ms to the VMU page (console disc r22g).
  Round-2 experiments fm (logic maths, bounded, automated decision checks + playtests) and ln (native Leon renderer
  PoC) run with pass/fail thresholds (route doc "r22 test disc, the VMU GPU line and the round-2 experiments").
- 2026-10-05: LINK_ORDER in build-r21.sh is link-order/r21y-house-fight-square-c3-8k.ld (~-1 hw ms drawn, -0.2
  skipped; STRICT). Run tools/d367/ordcheck.py before each release; regenerate when the placed share drops.
- 2026-10-05 lane crowd: no logic reads the Ganados' render side (CROWD_DRAW_MAX=2 and ENC_SKIP_GANADO=1 STRICT);
  REPORT.md's "logic changed" was a LOGIC-bucket attribution shift (compare functions.tsv). PACE_FORCE=T and
  PACE_CAP2_SPEED (default off) landed; PACE_CAP=2 in the recipe awaits the user (fight 66% 9.9 fps -> 78% 7.8).
- lamb2k/re4dc is public: every push publishes (AGENTS.md).
- User decisions 2026-10-04: the supervisor branch's code lands default-off, after the cleanup above and after r21u
  (local session; turning any of it on in play builds stays a separate decision). Gameplay-logic cost (G, ~29 ms in
  fights against 24) is parked behind render work until the console calibration (disc c8), then re-planned.

State at the 2026-09-23 update (HEAD 5285bc7; history, superseded by the paragraph above):
- **Perf lane:**
  - Step 0 (FRONT_NATIVE, RELEASE_FLAGS) landed.
  - Step 2 (logic, 12.0 hw ms/tick) landed.
  - Step 1 (texture preload/O(1) handles; r101 slots; ~93 hw ms reload whenever a Ganado is in view) is in progress.
  - Steps 3-5 are queued. Patches are ready in /root/probe/d367-agents/{actors30,actcap,safecuts,frontend,w9,scenery-trials,ps2-blender}.
- **Route blockers, in order:**
  1. Stream waits: fixed, 5285bc7.
  2. W11 SUBSCREEN (transceiver): pending commit.
  3. Codec data `op/op01.das` missing from the disc.
  4. Image/heap regression: the ELF grew 2.06 -> 2.35 MB; source heap free at r100 s40 fell from 310 KB to 48 KB, so movies fail.
  5. The real r100 -> door -> r101 fixture.
  6. The r101 fight to the bell, then r103.
  Also: a room re-entry takes ~15 s (motion-key per-sector reads plus an unprofiled remainder).
- **Agent state:** each area has `/root/probe/d367-agents/<area>/STATE.md`. Read it before resuming that area.

Evidence goes on D:\Flycast-Evidence\re4-dreamcast (new dirs from the C: harness template). The per-agent Flycast cap was lifted on 2026-09-25 (keep flycast.exe at 10 or fewer machine-wide; builds use make -j4); delete disc images after each run.

The sections below (D366 pause, the four-owner "beat D349" sequence, Sol/Max assignment) are historical context; where they conflict, D367 wins. The [D366 pause handover](port/dreamcast/docs/R4_D366_CLAUDE_HANDOFF.md) still describes the inherited dirty overlay (~75 files; never stage, reset or clean it).

- **Play build (2026-09-29): follow [the checklist](port/dreamcast/docs/D367_PLAY_BUILD_CHECKLIST.md) step by step; update it with each step.**

## Historical (pre-D367): persistent goal and model handoff

North star: **beat D349, do not merely recreate it**. The recovered game drives
a cheaper native visual workload while retaining its real source state systems.
Complete [the r100 native static cutover](port/dreamcast/docs/R100_NATIVE_CUTOVER_GOAL.md)
in `re4dc-game.elf`. The app goal was reset to this milestone on 2026-09-22.
The broader normal-menu -> r100 -> r101 -> r103 playable objective remains open.

**Implementation assignee: GPT-6 Sol / Max.** Continue the accepted four-owner bounded
[D349 slice/source-block qualification](port/dreamcast/docs/R4_R100_SOURCE_BLOCK_BUDGET.md).
The 14,577,304-byte all-block conversion is not the target representation or proof
of architectural failure. Reuse existing selection/partition and source block
ownership; continue implementation if bounded native packages fit that lifetime.
Follow the [escalation rule](port/dreamcast/docs/R100_NATIVE_CUTOVER_GOAL.md#astramax-escalation-rule)
only on demonstrated contract/budget failure or a need for different architecture.
D364 completed v4's first layout qualification. AoS20 is frozen as the leading
layout unless integrated evidence disproves it; D349 math stays default. Do not
repeat Split24/SH4ZAM layout tuning. Keep the accepted four owners and GCC15.2/KOS.
Continue AoS20 integration/reader qualification -> source-backing accounting ->
FILE_01 PS2/DC reduction -> complete static cutover -> residual CPU/PVR measurement
-> native actors -> broader visual reductions -> SH-4 tuning. The goal document
owns the detailed roadmap and historical comparison thresholds.
The persistent goal is paused at the operator's request; it is not complete.
Passing an isolated adapter or host test does not complete it.

Recovered GameCube source is the simulation/state authority. Productionize the
existing D349 preparation/converter -> `.re4room` -> native renderer pipeline.
The live GX/ModelPart bridge is only a fallback. GC and PS2 assets are first-class
offline visual inputs; the final runtime representation is Dreamcast-native.
Replace qualified source render-only backing, preserve source owner/state
contracts, and measure the complete candidate. D362 ended lossless scavenging.
No further bridge-cache/admission campaign or second room converter is planned.

The goal document owns the detailed contract and anti-reinvention rule. Older
next-task instructions in historical checkpoints are evidence, not active orders.
The PS2/native static phase is active; there is no prerequisite to finish a
perfect GC-oriented bridge or a perfect GC-derived asset first.

## Retained baseline and current work

Primary reference: D362 `62414dc39feccc949af4b3ed29053be9fde4d5fc` on
`dreamcast-port`. Preserve newer work and the inherited dirty source overlay;
HEAD alone does not reproduce the accepted executable.

| Reference | Verified result / role |
|---|---|
| D361 `1039667` | 128 KiB retained preparation improved matched render p50 from ~1,563 to ~1,368 ms. Keep as control, not a prompt to continue cache tuning. |
| D362 `62414dc` | Exact UV sharing recovered 34,016 source-heap bytes; free/largest 116,704 bytes. Render p50/p95 1,368.093/1,370.801 ms; page-flip p50/p95 1,389.602/1,406.282 ms. No material CPU saving. |
| D349 `5f42caa634c0e6124c48842e21570033738adfda` | Preserved native room architecture and presentation reference. Its ~49-58 ms CPU cost belongs to the smaller historical workload, not the recovered game's budget. |
| D353 `d928ad6` | Existing GC-derived static RGB bake and native modulation path. Direct PS2-authored RGB transfer is not yet qualified. |

[D361/D362 evidence](port/dreamcast/docs/R4_NATIVE_PREPARATION_CHECKPOINT.md)
records exact limits. Settled scripted presentation is not manual combat/audio,
transition/retry, real-time or hardware acceptance. Disabled audit counters are
unmeasured, not zero.

The cutover has not yet run on target. The uncommitted embedded-native-BIN draft
was rejected: it bypassed `.re4room` and expanded loaded geometry. Its scripts and
patch remain in `/root/probe/d363-rejected-embedded-format`; do not resume it.
The untracked `tools/bake_room_prelit.py` adaptation is not accepted runtime work.
Reuse the pinned D353 bake in the existing package chain and qualify any changes.

Continue from the existing source-object/owner mapping and package contract.
Historical `r100-source-cell-4.re4room` is an encounter-radius subset, not complete
r100 coverage. Full source-authored OBJ inputs already exist (paths below).
Extend existing SourceGroup identity for source instance/owner state; adapt the
proven native room submission and actual backing retirement together. Keep an
explicit dynamic/unconverted fallback list. Static cutover acceptance comes
before native actor-package integration, then r101/r103.

## Latest bounded checkpoint: D364

[Package-v4/SH4ZAM qualification](port/dreamcast/docs/R4_ROOM_PACKAGE_V4_CHECKPOINT.md)
now exists for the exact four accepted owner packages. AoS20 totals 1,299,298
bytes versus v3 1,992,824; Split24 is 1,478,690. Flycast CPU fixture p50 totals:
v3 prelit 35.293 ms; AoS/D349 47.486 ms; Split/D349 47.935 ms. SH4ZAM's
transform/reciprocal did not win; it remains optional, default math stays D349.
These are preparation/packet fixture times, not game FPS or a whole-frame win.

The leading storage candidate is AoS20, pending moving visual/source binding
acceptance. No v4 package has been activated in re4dc-game.elf or source backing
reclaimed. The [four-owner budget](port/dreamcast/docs/R4_R100_SOURCE_BLOCK_BUDGET.md)
prices a modeled 746,816-byte shortfall. This activates FILE_01 asset reduction
now: compare GC v4, qualified PS2 and custom DC input through the same package.
Target roughly 900 KB-1 MB gross reduction/headroom if feasible, including the
net allocator and loading-overlap accounting. Do not grow budgets or equate file
savings with source-heap savings. Preserve source readers,
generation/rebase/retire boundaries and the single frame owner. Continue the
cutover; do not return to cache tuning or treat this fixture as room acceptance.

The source-range reader now qualifies all four unchanged AoS20 packages against
owner/work/BIN/common identity (58 source instances / 1,093 child groups), with
no extra registry/allocation. The game hooks are still pending. FILE_01's exact
cost and material coverage are in the budget's latest decomposition; private
evidence is `/root/probe/d365-r100-cutover`. Four combined texture/mask identities
remain unqualified in the selected folder. Preserve their fallback explicitly.
Continue actual source binding/backing replacement and the authorized FILE_01
candidate, not layout/math tuning; no whole-game saving is claimed yet.

## Working paths and reproduction

| Purpose | Path |
|---|---|
| Primary repository | `/root/work/re4-dreamcast` (WSL Ubuntu-24.04) |
| Windows repository access | `\\wsl.localhost\Ubuntu-24.04\root\work\re4-dreamcast` |
| Target | `port/dreamcast/game/re4dc-game.elf` |
| Reusable renderer/packages | `port/dreamcast/room`, `port/dreamcast/tools` |
| D349 reference worktree | `/root/work/re4-r100-reference-5f42caa` |
| D353 prelighting worktree | `/root/work/re4-r100-prelit-d353` |
| Source OBJ inputs | `orig/G4BE08/rooms/r100/stream/r100_full_export/R100.allparts.obj` and companion metadata |
| Selected UV-shared private mirror | `/root/probe/d362-mirror` |
| Source assets | `/root/re4data` |
| Current fixture/native textures | `/root/probe/d354v7-fixtures` and its `tex/` |
| Pinned KOS / compiler | `/root/work/kos-re4dc-d336`; `/opt/toolchains/dc/sh-elf` GCC 15.2 |
| Matched build recipe | `/root/probe/d361-build.sh` (inspect inherited source identity before reuse) |
| Baseline evidence | `C:/Flycast-Evidence/re4-dreamcast/d361-retained-model` and `d362-shared-uv` |
| Private scratch | `/root/probe`; `C:/Game Dev/Emulators/re4-session-scripts` |
| Inherited-work snapshot | `/root/probe/d363-before` |

Set `RE4DC_KOS_BASE=/root/work/kos-re4dc-d336` before sourcing `kos-env.sh`.
Adapt the saved matched build recipe to a fresh destination; do not run it
unchanged because it writes the preserved D361 output. Use current mirror/fixture
identities; the old D305 generic build recipe is not the current control. Separate generated
candidate outputs and capture windows. Check disk space before full disc builds;
preserved disc deltas need their named, hash-verified base. Keep video audio.

Remote: `https://github.com/lamb2k/re4dc.git`. Keep assets/evidence private;
commit only reviewed owned code/docs. Preserve uncommitted event/source work;
its presence is not permission to stage it with this cutover.

## Existing backlogs and completed side work

- [PLAYABLE_PATH.md](port/dreamcast/docs/PLAYABLE_PATH.md): normal menu/three-room
  acceptance, source/event/audio/inventory/transition dependencies and debug tools.
- [REALTIME_PATH.md](port/dreamcast/docs/REALTIME_PATH.md): matched timing and
  acceptance, not another renderer roadmap.
- [R4_ASSET_RESIDENCY_PLAN.md](port/dreamcast/docs/R4_ASSET_RESIDENCY_PLAN.md):
  source ownership, native textures, warm motion and transition overlap.
- [PS2_INSPIRED_DREAMCAST_PROFILE.md](port/dreamcast/docs/PS2_INSPIRED_DREAMCAST_PROFILE.md):
  authorized visual candidates and quality/cost qualification.
- [D349 recovery](port/dreamcast/docs/R4_R100_REFERENCE_RECOVERY_CHECKPOINT.md):
  matching historical assets/builds and proven mechanisms to reuse.
- [First-stage audit](port/dreamcast/docs/R4_FIRST_STAGE_GAP_AUDIT.md): source/data
  route r100 -> r101 -> r103 and remaining dependencies across all 29 stage rooms.
  Converter fix `961c51e` and private r101 DAR exist; native r101 loading remains
  unproved. Use its latest addenda, not superseded missing-file lists.
- Isolated movie, water, PS2 and Blender work retain their own branches/checkpoints.
  Inspect current deliverables before reuse; do not relaunch finished experiments
  or assume an old running-agent report is live. Stove `14dd633` remains rejected.

Full historical handoff and build identities remain in
[the D362 snapshot](https://github.com/stevedamnvan/re4dc/blob/62414dc39feccc949af4b3ed29053be9fde4d5fc/CLAUDE.md) and the named checkpoints.
This concise handoff replaces their stale execution instructions, not their evidence.
