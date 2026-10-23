# Main qualification continuation, 2026-10-23

Authority: CODEX-HANDOVER-20261023.md and CLAUDE-CARRY23.md. The old actor/cache/
PVS recovery queues are not resumed. world-merge23's tested fixed-cell method
failed its geometry GO gate; source/report handoff is pushed at 516bfe3b8.

Dedup authored source e66ec61e4caca417d170a9483ed7af0f908baf47 is independently
CLEAR for target gates. All three runtime files are unchanged in main's merged
integration af09f0a2bfd32f2ecc29bda6a71a1de42bcf2b34, based on current integration
e17af64a696778198474b1053cc8a37084eb2c3b (the later delta is DreamShell disc code).
Both owned branches are pushed to origin; no production merge or recipe edit.

## Actual build

- Tree: /root/work/lanes/dedup-offline23-integration.
- Branch: wip/dedup-offline23-int-20261023.
- First launch main-build-on.sh stopped before compiler because the new worktree
  lacked its SH4ZAM submodule. Original on-k logs and out-dd23af09onrW retained.
- Initialized exact gitlink 33fa4850cacb30dd0ad35485ef035526ec4ce782 through normal
  submodule update. Source checkout remains clean before the retry.
- Actual retry main-build-on-r2.sh is running in main exec session 14952.
  Output /root/probe/lanes/route/out-dd23af09on2rW; log
  /root/work/lanes/dedup-offline23-main/on2-k/logs-build.txt and output/build.log.
  Poll the same session, never restart a live or completed attempt.
- Uses standard ch2-build and committed release recipe plus SCENERY_DEDUP=3,
  QA_MENU/WORLD_METER/warp diagnostics. JOBS=1; existing two shared build slots
  and owned tree lease are used. No new programme accepted until link completes,
  missing symbols are empty and resolved definitions are inspected.

## Required next steps

Finish actual ON build and routine fixes, preserve every failed attempt. Build
fresh OFF and prove target knob-off image identity against the same current
integration/flags. Host preprocessing is not that image gate. Derive symbols,
stack and programme hashes from actual outputs; no historical addresses transfer.

Four alternate files are pinned in alternate-pins.json under
C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023. Their paths are
r100-linear/ps2-dd3.re4mesh, r101-linear/ps2-dd3.re4mesh,
r103-linear/ps2-dd3.re4mesh and r101-linear/ps2-dd3.r4sg. Stage with four explicit
test11 --set mappings; leave standard files unchanged. No production DATA edit
is necessary. Author is preparing small staging/gate helpers while main builds.

Then KOS48, r100 s30 340/340 with heap_before, TEXCHK, VRAM no-contiguous0,
CAST-GC, GDEMU seed, cross/farm look comparison and private Off/On QA discs.
Use console-mode Flycast via trace_lock, <=60-second runs, max3 per lane and
global capacity/release priority. Evidence and finished private discs stay on C:.
Do not touch Claude-owned release trees, recipes or SD; no publishing/messages.

## Evidence limits

Six converter tests and real C++ reader tests pass, with no reader heap
allocations and identical ordered corners. Package sizes are unchanged. Camera
counts are offline: cross19069.14 ->17054.98 transforms (-10.56%); farm24864
->19985 (-19.62%). These are not measured milliseconds or console gains.
Target, runtime/memory, look and physical acceptance remain open.

MeshPackage::close retains its header: the earlier suspected movie filename bug
was withdrawn after reading the actual contract. Host close/re-adopt tests pass;
real s30 is still required. Source review is codex-lanes/dedup-offline23/REVIEW.md.
