# Build 29 — r103 barn exit, looking outdoors

Source audit for the second console target added to the queue on 2026-10-28,
reviewed against integration base `5f104e301f328c56a07ce9f57e3fb94d758d4999`.
This appendix adds findings and proposed switches; **it does not implement or
enable any new world optimization**. The Build 29 runtime changes and their
qualified costs remain in [the main handback](build-29.md).

## Finding and limits

The current public recipe cannot use the existing interior portal cell to
reject outdoor r103 geometry. It resolves `PS2_INTERIOR_CULL=1`, but
`PS2_INTERIOR_CELLS=0` selects a compiled **r100** package identity and
`PS2_PVS=0` removes the separate visibility-table path. r103 still has ordinary
frustum, distance, pass, AREA, placement and dynamic-state selection. Those
tests do not infer occlusion by the barn walls or doorway. Outdoor pieces
inside the camera frustum can therefore reach matrix, part, meshlet,
transform and submit work even when the barn hides their pixels.

This is a source-supported opportunity, not a measured attribution of the
whole slowdown. The queue reports approximately `(-27810, 32, -16810)`,
Ganados dead, 10.8 fps / 45 ms CPU facing the far barn versus 21.1 fps / 33 ms
facing the stalls, with about 12 ms graphics-chip work and 13% busy in the
outward view. These are owner observations, not measurements made here.
The reported 12 ms CPU difference is the target to reconcile with world rows;
do not derive fps from those CPU values or combine unlike frame/tick windows.
Player position is also not the camera eye used by cell selection.

The console's ALL ON image may differ from the public recipe. Bind its exact
`resolved-knobs.txt`, package hashes, view option and image identity before
using the values below to interpret its counters. The new recipe change to
`ACTOR_LIGHT_FAST_ONLY=1` does not add world doorway culling.

## World path and current controls

Source anchors name the functions or statements to keep them useful if later
integration moves the lines. Values are the public-game profile in
[recipe-values29.json](../../../tools/d367/fallback_scan/receipts/recipe-values29.json),
not an assertion about an unseen ALL ON image.

| Stage and source anchor | Current recipe | Trigger / work that remains in r103 |
|---|---|---|
| `ps2_pass`, [native_static.cpp](../../../game/platform/native_static.cpp), lines 8244–8315 | `PS2_PVS=0`, `PS2_AREA_HIDE=1`, `PS2_PLACE_GATE=1` | Each pass walks placements. Pass masks, AREA and source placement gates can remove work; they are not a general camera-through-door visibility test. A package or gate being present is not proof it rejects this view. |
| Dynamic placement and world bounds, same file, lines 8316–8444 | `PS2_WORLD_DYNAMIC=1`, `PS2_WORLD_LEAN=23` | Hidden/moved source placements retain live policy. World-plane and placement-box frustum tests reject off-frustum/depth work; the camera still sees through opaque walls for these tests. Surviving placements form `mv`, grid transforms, absolute rows and LOD scale. |
| `pc::setup_state` / `hidden_state`, same file, lines 2415–2476; [ps2_interior_cell.inc](../../../game/platform/include/ps2_interior_cell.inc), line 8 | `PS2_INTERIOR_CULL=1`, `PS2_INTERIOR_CELLS=0` | Identity is room `0x100` plus exact mesh/policy CRCs/bytes. r103 does not adopt that cell. An active qualified cell tests exterior boxes against the eye's portal frusta; boxes meeting the house box remain visible. |
| Generic cell loader, [ps2_interior_cells.inc](../../../game/platform/include/ps2_interior_cells.inc), lines 31–85 | `PS2_INTERIOR_CELLS=0` | PCL2 already supports `/dc/native/rXXX/interior.cell`, multiple houses, package binding and draw-all on missing/stale/read/heap refusal. It needs valid r103 data and gates; changing the knob alone supplies none. |
| `ScenerySelector::chunk_ok` / `chunk_select`, [scenery_chunk_select.inc](../../../game/platform/include/scenery_chunk_select.inc), lines 3–31 and 38 onward | `SCENERY_SELECT_ONLY=1`, `SCENERY_STREAM=1`, `SCENERY_SELECT_LEAN2=0` | Chunk selection uses cluster/meshlet bounds, LOD and strip-group tests. **Active `pc_mode` or `pvs_set` declines the chunk path** (`w_chunk_cell` / `w_chunk_pvs`) and uses the older selector. Added visibility can save geometry while increasing survivor setup. Preserve this composition in the proposal and measure it. |
| Part queue and replay, [native_static.cpp](../../../game/platform/native_static.cpp), lines 8088–8228 and 8495–8545 | `SCENERY_REPLAY_LEAN=1`, `SCENERY_SUBMIT_BATCH=1` | Selection already precedes expensive emit setup where admitted; consecutive compatible parts can batch. Reordering transparent work or bypassing live source-owner checks is not an allowed cache optimization. |
| `load_screen`, same file, lines 1117–1168 | `SCENERY_SCREEN_MEMO=1`, `SCENERY_REPLAY_LEAN=1` | Last-key memo compares modelview/projection/viewport; misses rebuild the combined matrix. A camera rotation or a different placement legitimately changes the key. `w_screen_rebuild=33` means 33 matrices, not 33 expensive complete world draws. |
| `MeshDraw::meshlet` / `Emitter::clip_strip`, same file, lines 3330 onward and 1621–1760 | `MESH_CLASSIFY=0`, `MESH_CLIP_LEAN=1`, `MESH_CLIP_ACCEPT=1`; public `SCENERY_CLIP_GATHER=0`, `SCENERY_CLIP_INDEXED26=0` | Cached transforms normally accept/cull whole strips. Depth-crossing or capacity cases enter the clipper; existing lean/accept work already reuses strip corners and accepts inside triangles. Existing Build 24/26 clip switches must be checked in the actual ALL ON recipe before proposing another gather rewrite. |

The earlier barn DFA values use distinct units from
[draw_fallback_world.def](../../../game/platform/include/draw_fallback_world.def):
`w_clip_depth=43` counts **strips** entering the depth fallback,
`w_clip_rebuild=277` counts **rebuilt corners**, and
`w_screen_rebuild=33` counts **matrices**, per retained drawn tick. The depth
counter is selected when strip capacity is sufficient; it is not a separate
near-only/far-only diagnosis. `w_clip_project`, `w_clip_capacity`, DSA clip
time and transformed inputs help distinguish true crossing triangles from
setup/reconstruction overhead. None of the three counts alone explains 12 ms.

### Draw distance and the PS2 camera comparison

The world renderer derives near/far from the **live game's projection**
(`native_static.cpp:7914`), then limits selection by the requested view cut,
room/lake cap and active fog (`7927–7945`). The public recipe has
`FOG_FAR=25000`, `FOG_FAR_CAP=0`, `LAKE_FAR=45000`,
`VIEW_DIST_OPTION=1`, `FAR_SHELL=1`; the lake-specific value is not evidence
of a 45 m r103 view. The ordinary cap remains 25 m outside the lake override.
`native_ps2_world.cpp:766–782` separates the opaque view cut from the far
shell and the PT/TR far. `WORLD_METER` can override the three independently.

The source-world callback obtains the game camera with
`re4dc_coarse_source_camera` (`native_static.cpp:9490`); the coarse path passes
`View._zfar` through the current View option (`coarse.cpp:900–907`).
`CameraSetProjection` loads `pG->Cam.ProjMat` (`src/game/camera.cpp:60`).
Converted PS2 geometry is not evidence that the port has selected the same
PS2 camera, frustum, occluders or visibility set. The owner must capture the
matched PS2 location, camera eye/target or view matrix, FOV, near/far, fog and
which far structures are visible. Shortening far until the DC is faster is an
approximation; it cannot be called PS2-equivalent from source inspection.

## Ranked next changes — proposals, all default off

Rank is expected eliminated work/cache traffic, subject to the meter result.
These names are proposed interfaces, not accepted Make assignments in this
build. Do not put them on the owner's build command yet.

| Rank | Proposed switch / data flag | Concrete change and admission | Expected benefit and risk |
|---|---|---|---|
| 1 | `WORLD_PORTAL29=0`; `--barn-portals29=0` | Produce a package-bound r103 barn cell from the actual PS2 opaque, static wall geometry, all openings and near-plane margin. Reuse PCL2 storage/lifecycle. Reject wholly hidden placements before part setup; extend chunk selection to carry conservative portal rejects for surviving clusters/meshlets under its own new block. Preserve old `pc_mode` behavior when off. | Removes bounds walks, material work, transformed inputs and submission for hidden outdoor geometry. This has greater potential than making their transforms cheaper. Requires aperture/near/LOD/source-state proof; an open exit, windows or camera outside the safe inset may leave little to reject. |
| 2 | `WORLD_VIS_TABLE29=0`; `--visibility-table29=0` | For qualified static eye cells, store a conservative placement/cluster visible superset in sequential bitsets or run lists. Bind to mesh, physical policy, placement/LOD identities and all occluders; invalidate on camera/projection/viewport/depth, package and live-state changes. Reuse the existing PVS admission contract instead of bypassing it; draw all on doubt. Keep dynamic objects visible unless separately proven. | Avoids repeatedly testing known hidden outdoor pieces. A placement-only table can be applied early; cluster tables offer finer cuts at added memory cost. A sampled camera path or equal CRC alone is insufficient. Existing PVS may have survivor batching costs too. |
| 3 | `WORLD_PART_PLAN29=0` | Compile immutable per-pass part metadata/texture keys and placement-independent records once at package admission, then stream compact records. Cache only qualified same-frame placement products across passes; key live affine, camera, package generation, source binding and material/UV state. Preserve submission order and every live policy gate. | Targets selection/setup if meter/census shows many small surviving pieces with modest vertex work. Avoids re-reading bulky records and repeated matrix/part initialization. A larger random-access cache could lose to current streaming; report bytes and misses, not only arithmetic saved. |
| 4 | `WORLD_CLIP_REUSE29=0` | Only if clip time remains material with landed clip fixes enabled: retain the already transformed clip inputs/attributes across an individual depth-crossing strip, preserving winding, alpha, exact operation order and capacity/partial-submit behavior. Price cache storage and serial reads first. | Saves repeated corner reconstruction. The existing three-corner ring and Build 24/26 work may already leave little; do not rank it above visibility from the three DFA counts. Synthetic exact TA-word comparison is required before the console pair. |
| 5 | `WORLD_ROOM_FAR29=0`; `--room-far29=0` | A separately authored r103 opaque/PT/TR distance policy, optionally with a source-backed far shell, selected only after the matched PS2/view-distance sweep. No hard-coded barn player-position shortcut. | Deliberately reduces visible distance; may remove whole sets of outdoor pieces. State which structures disappear, fog/shell seams and camera-transition pops. Keep this approximation separate from conservative occlusion. |

For proposal 1 the existing builder
[build_cell.py](../../../tools/d367/ps2world/interior/build_cell.py) is a useful
starting point, not a certificate. Its header explicitly says dense ray
sampling can miss cracks. Build the r103 hull/eye boxes from private geometry;
do not reuse the r100 box or invent them from the player's reported position.
Exclude dynamic doors, boards and breakable windows from occluders. Ensure
every aperture has a conservative bound, retain uncertainty as an opening,
test all supported LODs, and cover the entire eye cell and near-plane envelope.
The magenta hidden-geometry check is a valuable walk-through gate; a clean
finite camera walk is not proof for every possible camera.

Keep the PCL2 refusal conditions and test missing, stale, malformed and
heap-short files, eye outside the cell, doorway/near-plane crossing, changed
FOV, room reload, movie lending/restore, moved/hidden source pieces and each
transparent pass. The existing runtime caps each cell at 24 portal frusta and
draws normally outside the safe inset. Do not suppress those refusals to make
the target coordinate activate. Record surviving `w_chunk_cell`,
`w_chunk_pvs` and `w_select_old` alongside saved transforms.

The PVS alternative should start from the explicit proof/lifecycle rules in
[pvs23/README.md](../../../tools/d367/pvs23/README.md): geometric cell membership
does not authorize hiding; the existing contract also verifies the qualified
opaque source panels and successful current-frame source submission. A portal
proposal needs equivalent live-occluder reasoning for the policy it uses.

### Cost model for deciding which prototype to build

For a rejected meshlet with `V` stored inputs and `S` strip-index bytes, the
ordinary 12-byte input stream accounts for `12V` bytes before metadata,
indices, palette and setup. The projected cache reserves `32V` bytes plus
`V` outcodes. These are layout quantities, **not measured transactions**;
cache-line touches depend on alignment, overlap and actual access paths.
Rejecting a whole placement additionally avoids its part/meshlet metadata
walk and all those streams. A visibility row over `N` placements occupies
`ceil(N/8)` bytes before headers; a sequential cold read costs approximately
`ceil((alignment + ceil(N/8))/32)` distinct 32-byte lines. Charge its proof,
selection and survivor costs as well as its saved work.

**Whole-view sensitivity, MODELLED:** hold the owner's 33 ms inward CPU work
fixed and treat the reported extra 12 ms as removable outdoor work. Removing
25%, 50% or 75% of that difference gives 42, 39 or 36 ms CPU respectively,
before added visibility/setup overhead. At 200 MHz the entire 12 ms is 2.4
million cycles. This is an arithmetic budget, not a benchmark or fps promise.
Warm/cold-I cycles, executed loads/stores, data lines, code and stack for the
proposed switches are unmeasured because no prototype is implemented here;
they must be reported with its eventual handback.

## Owner capture that distinguishes the causes

Use the **exact ALL ON image recipe**, with unchanged world packages and
lighting, then add a world-focused observer. Variables have the meaning given
in the main handback. This is a separate owner build command; it is not a
claim that a private image was built here.

```sh
RELEASE_KNOBS="$IMAGE_RECIPE" ASSETS="$BUILD_ASSETS" OUT="$PRIVATE/world-observer" \
  bash port/dreamcast/build-public.sh \
  DBG_WARP=1 WARP_AFTER_RESET=1 QA_MENU=1 BENCHMARK=0 PMC_ROW=0 \
  WORLD_METER=1 GAME_TICK_LOG=60 FAR_SHELL=1 VRAM_PAGES=1 \
  DRAW_FALLBACK_AUDIT=1 DRAW_SETUP_AUDIT=0 WORLD_CENSUS24=0 \
  FALLBACK_AUDIT29=0 FALLBACK_SCAN29=0 QA_LINK=1 QA_LINK_REVIEW28=1

ql() {
  python3 port/dreamcast/tools/qalink/qalink.py \
    --pi "$QALINK_PI" --review28 --out "$PRIVATE/barn-world" "$@"
}
ql send MENU
ql send QA WOPQ GAME
ql send QA WXLU GAME
ql send QA WSHELL GAME
ql capture start barn-out-game
ql send RESUME
# Hold the outward camera; let at least one complete 60-tick window seal.
ql send MENU
ql send DIAG
ql capture stop barn-out-game
```

Before capturing, reach the owner-established position with the same dead
enemies, camera angle and Options View; do not assume an unverified teleport
label. Repeat complete stable windows facing the stalls (`barn-in-game`), then
outward again. Pause/resume after changing camera so the prior meter window is
invalidated. Keep several complete windows, the full multipart T/D snapshots,
tick/draw counts, image/package hashes and screen pairs.

At the outward camera repeat the same capture sequence with the following
commands issued while paused. Restore all GAME rows between arms. Numeric
values are metres; `WOPQ FULL` and `WXLU 10` are not accepted row values.

| Arm | Change from GAME | What it separates |
|---|---|---|
| `barn-out-opq125` | `ql send QA WOPQ 12.5` | Opaque-distance sensitivity, with shell and translucent policy held at GAME. |
| `barn-out-xlu125` | `ql send QA WXLU 12.5` | PT/TR-distance sensitivity; keep WOPQ at GAME. |
| `barn-out-shelloff` | `ql send QA WSHELL OFF` | Far-shell contribution only; keep both distance rows at GAME. |

The rows intentionally change rendered output for diagnosis. Record what
disappears; an apparent speedup is not approval for that policy. `WORLD_METER`
times and transformed/inside counts are **means per logic tick**, including
skipped ticks. DFA is the **last completed drawn tick**. Do not divide one by
the other. Compare world-window identities and obtain a matched drawn-frame
denominator before reconciling CPU/fps. A low inside/transform ratio suggests
wasted candidate work, but crossing triangles can have zero corners inside
and still cover pixels; it is not a visibility proof.

If OPQ/PT/TR timings do not distinguish selection/setup from transform/clip,
take a separate `WORLD_CENSUS24=1` observer with its normal complete drawn-frame
window and inspect selection, matrix, material/header, transform, clip and
submit phases. Keep the observer configuration constant within every A/B.
Request `PS2MESH` placements/culled/parts/native/fallback/aborts and effective
near/far/cull_far, the world rows and exact DFA units together. These results
determine whether the first prototype should remove invisible outdoor pieces,
stream survivor setup more cheaply, or concentrate on a measured clip phase.
