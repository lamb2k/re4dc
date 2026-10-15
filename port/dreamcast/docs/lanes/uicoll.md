# Lane uicoll (2026-10-15): B3 UI OT cache + B2 collision broadphase cache

Branch lane/uicoll (worktree /root/probe/lanes-20261015/uicoll), base dreamcast-port 1c79d543 (test 13). Local
commits only. Backlog rows B3 and B2 of PERF-BACKLOG-CH1-2-20261015.md (user OK 10-15 evening). Both are exact
levers: B3 must keep the TA output identical, B2 must keep every query result identical.

## Step 0: ceilings first (coordinator 10-15: measure before building; report anything under ~0.7 ms)

Image: arm t2crW (lane t2exact's c0 control = the test 13 rW recipe at 1c79d543 + PACE_MODE=off
PC_SAMPLER_BYTES=8192; ELF sha 7075c866...). Scene t2-r101cross (benchmark-r101 cross without the bench line, cap 6,
data T13 set), global frames 500:799, 10 traced frames (stride 30). MODELLED 57.32 ms/frame, identical to
t2exact's hwmodel-c0-cross. Evidence C:\Flycast-Evidence\re4-dreamcast\uicoll-20261015\hwmodel-u0-cross (traces
kept for the analysis below).

Method: inclusive cost per function from the kept traces (`_private_tools\uicoll\incl.py`): per-PC average cycles
from proj/nominal.pcs.tsv charged along a call stack rebuilt from the trace (jsr/bsr/bsrf push, rts pops to the
matching return address, vector entry / rte save and restore stacks, tail jumps). The rebuilt total is 57.32
ms/frame (= the model); 70 unmatched returns in 45k calls per frame.

### B3: what the HUD actually costs (MODELLED ms per frame)

| part | ms | note |
|---|---:|---|
| IDSystem::trans (queues units into the OT) | 0.124 | GAME_ID_LISTS=1 already in the recipe |
| IdGeneralTrans callbacks (ExecOt in Render) | 0.518 | 35 calls; re4dc_draw_id_quad 0.454 for 25 quads |
| - draw_id_quad self (TexWk lookup, concat, 4 projections) | 0.172 | UI_QUAD_LEAN=1 already |
| - re4dc_ui_submit (resolve 0.107) | 0.140 | |
| - re4dc_ui_hud_mask_submit | 0.069 | |
| ui_draw_quad at present (header, 4 vertices, stream_send) | 0.238 | 20 quads |
| Draw_cinesco + FadeControl + DrawOTag | 0.012 | letterbox is off in gameplay |
| **ceiling (everything the HUD build and draw do)** | **~0.89** | x1.15 = ~1.03 corrected |
| not cacheable: IDSystem::move (UI state, animation) | 0.457 | |

The hV6 "ui 4.29" area is file attribution (everything in native_ui.cpp: model packet reserve/begin,
ps2_world_direct_begin, effect sprites, texture lookups), not the HUD. A cache still compares each unit's
inputs and still sends the same TA bytes, so the realistic saving is ~0.4-0.5 MODELLED.

### B2: scenery collision (MODELLED ms per frame)

Total scenery collision (cSatMgr / blk* / spw* / re4dc_line_*) 1.83 (+0.11 collision_sphere_hexahedron, the OT
view test, not scenery). By actor: Ganados (cEm10, 5.3 updates per frame) 1.19 = 0.22 per Ganado update; Leon
0.39; camera 0.11; crows (cEm28) 0.11.

Inside: hitCheck2 1.40 (40.5 per frame) = piece walk re4dc_line_piece2 0.44 (210 per frame) + leaf polygon tests
re4dc_line_leaf2 0.53 + blkPolyLineCkCore / tail 0.15 + self 0.23; sphere walk spwRun 0.21 (6.7 per frame),
blkPolySphereCkCore 0.10.

An exact broadphase cache can remove the walk (piece walk 0.44 + the sphere walk share ~0.1): ceiling ~0.5
MODELLED (~0.08 per Ganado). The leaf tests stay (same leaves, same order). Lane el (10-05) priced an AABB
prefilter at < 0.15 real. LINE_WALK(+PF) asm, SPHERE_WALK, COL_PREFETCH and LQ_MEMO are already in the recipe.
Net after validation cost ~0.2-0.35.

Reported to the coordinator before building (both realistic savings under 0.7).

r103 farm (same image, scene t2-r103farm, 500:799, 10 traced frames, 87.98 MODELLED): HUD path IDSystem::trans 0.125,
IdGeneralTrans 0.526, ui_draw_quad 0.229 (same as the cross); scenery collision 2.98 (Ganado route line tests 0.89,
cEm10 2.01 in total, crows 0.30, Leon 0.38, camera 0.10); walk-only part (piece walk + sphere walk) ~0.6.

Coordinator decision (10-15 evening): **B2 dropped** (backlog row annotated: measured ceiling ~0.5 MODELLED, net
0.2-0.35, not built). **B3 go, small**: the exact per-unit memo in re4dc_draw_id_quad plus the TA bytes path of
ui_draw_quad, behind UI_OT_CACHE, runtime-toggleable for lane poc101 (POC layer bit 0x08).

## B3 design (UI_OT_CACHE)

Where the HUD's time goes (pcprof, MODELLED): draw_id_quad's own 0.172 is compute (dmiss 0.009, imiss 0.009: the
concat, four projections and eight divides per quad); ui_draw_quad's 0.107 is mostly loads plus 8 divides, and its
store-queue lock / unlock per quad is 0.059 of stream_send's 0.082. resolve() is already a handle cache (UI_HANDLES)
whose hit touches the LRU (RE4DC_TOUCH): it stays, as do UI_HEADERS (already caches the header per handle) and the
TA submission itself.

- Part 1, ui_bridge.cpp: a 32-slot direct-mapped memo by unit address (4.3 KB .bss) keyed by every input word of the
  corners (scrn matrix, projection, viewport: numbered environment; unit mat and vtx). A hit copies the stored
  corners; everything else of the quad runs as before (texture, uv, colour, blend, PAD_PROMPTS / HUD mask branches,
  letterbox note, CameraCurrentProjection). =2: every hit also computes and compares ("UOC id" lines).
- Part 2, native_ui.cpp: "cached TA bytes per quad" as a full-input key would cost what rebuilding the 160 bytes
  costs (the key needs the same header / cover / dims loads), so the TA side keeps the per-quad build and instead
  batches 8 quads per stream_send (one store-queue lock per batch, 1.3 KB .bss). The TA receives the same words in
  the same order; the batch is flushed when full, before a glyph run and the door picture, and at the end of both
  drawing loops.
- POC101: with BENCH_POC=1 both parts act only while POC layer 0x08 is on (RE4DC_POC_UIOT, game30.mk).

### First measurement (memo + batch, arm uc1rW, hwmodel-u1-cross; MODELLED, same window)

| function (inclusive) | off (u0) | memo + batch (u1) | delta |
|---|---:|---:|---:|
| re4dc_draw_id_quad (25 per frame) | 0.454 | 0.491 | **+0.037** (memo: self +0.011, memcpy +0.027; concat -0.019) |
| ui_draw_quad (20 per frame) + uoc_flush | 0.238 | 0.149 | **-0.089** (stream_send 0.081 -> 0.016 in uoc_flush) |

The memo hit on every quad (the concat disappears) but its key work costs more than the concat and four projections
it replaces: **memo removed**. The batch stays: UI_OT_CACHE=1 is now the batch alone (native_ui.cpp; ui_bridge.cpp
unchanged). Whole frame 57.30 -> 58.46 (+1.16): world submit +1.0, i.e. code placement drift (LINK_ORDER is a fixed
order file; the edited object moves what follows it), not work. Re-measured below with the batch alone.

Item pickup fixture: r101 ITA record 2 (green herb, item 0x6 at 11284 1753 13763), Leon at its trigger (12400 1753
14210, ang -1.953), A every 40 frames: the take / examine screen opens (o-pickup2 shot t0030). The first attempt
(record 3, item 0x1001) faced a barrel (the item is inside a breakable).
