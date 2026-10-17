# batch17: lossless batching of a room's PS2 world (lane batch17, 2026-10-16)

Fewer, bigger meshlets for the unreduced world (no vertex ladder), loaded as WORLD_VERT=1 WORLD_VERT_LEVEL=5.

- `batch17_world.sh <src> <out> [cell mm=4000] [groups=4] [--spatial]` (WSL): ps2_world_batch.py (merge consecutive
  meshlets of one part / cluster / level in one cell, up to 256 corners, strips copied byte for byte), then
  ps2_strip_groups.py, then verify_groups.py (every level's strips and vertex records equal the source's). `--spatial`
  adds ps2_world_spatial_batch.py (32 m room-space parts; requantizes to <= 2 mm, so it is NOT lossless; six-file set).
  Then run tools/d367/lostpart/lostpart_gate.sh: t11-fix.py refuses ps2-wv* files without a LOSTPART PASS stamp.
- t11-fix.py `DATA['bat17r101']`: the r101 candidate b17v4 (env BAT17 = its dir). Not in any release data set.
- `bench17-build.sh` / `bench17-package.sh` (WSL): the console A/B disc. Test 16 program + bench knobs + WORLD_VERT=1;
  scene 1 `wvlevel 0` (test 16 world), scene 2 `wvlevel 5` (batched), the same r101 cross, 30 s each. The `wvlevel <n>`
  warp line (dbgwarp_bridge.cpp, DBG_WARP + WORLD_VERT builds) sets the level read at the next world open.

Result for r101 (b17v4, 1830 -> 1424 meshlets): MODELLED -0.12 ms per picture at the cross and the worst view; the
spatial option -0.73 / -0.49 ms. Per-meshlet costs fall about 1 ms but transform work rises about 0.9 ms because
coarser boxes cull less. Below the 1.5 ms bar, so the other rooms were not done. Console A/B pending.
Full notes: BATCH17-20261016.md in the workspace (not in git).
