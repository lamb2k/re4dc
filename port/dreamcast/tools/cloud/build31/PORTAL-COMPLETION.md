# EF08 queued portal completion, first slice

`WORLD_PORTAL_COMPLETION=1` extends the existing WORLD_PORTAL29 receipt path.
Its default is0; absent/explicit0 preserve the existing portal-only behavior,
ABI, source branches and early PVS/batch refusal. The enabled composition is
listed exactly in `portal_completion_profiles.json`; it is a validation arm,
not a release recipe. No ALL ON promotion is authorized.

The existing ScenerySelector/MeshDraw selection records a ticket with pass
serial, witness index, placement and part in ChunkPart. It does not commit.
The actual chunk_emit runs normally. After e.end_direct and batch_close,
Completion distinguishes Submitted, Culled, Refused, Partial and Aborted;
a default Queued result cannot witness. Only Submitted with whole coverage
may commit. Ordinary source rendering and draw order remain unchanged.

First supported coverage requires every stored part meshlet in encounter
order, nr255 (all strip groups), positive published geometry, input==output
and unchanged strip clip/cull counters. This deliberately declines subset
selection, unproved multi-LOD coverage and legacy immediate witness grants
in completion1. Those paths still draw. This is a bounded consumed correction,
not complete EF08 coverage or evidence that current private walls qualify.

At flush, exact ticket part/placement/serial, current image/view, package
storage/metadata/placement pointers, room and cell generation must still match.
All witness material keys are snapshotted at begin and compared at flush and
activation. Existing source placement-intact/dynamic exclusions and opaque
readiness checks remain. Observed source/view/material changes revoke old
receipts; restoring a value later cannot revive them. Ticket serial exhaustion
permanently fails open. Immutable package geometry still relies on the existing
validated package/cell lifetime and source-placement authority; no new mutable
geometry certificate is invented.

Only the precise portal+PS2_PVS_BATCH_COMPOSE+submit-batch early guard exception
is admitted. All existing PVS compose requirements remain. SCENERY_STREAM,
SCENERY_CLIP_GATHER and SCENERY_CLIP_INDEXED26 are explicitly0 in this slice.
WORLD_SCRATCH/TA_GUARD and all existing owner/diagnostic exclusions remain.
Four required facts formerly absent/late in native_static (TA_DIRECT,
PS2_WORLD_HDR_CACHE, MESH_FASTPATH, PVR_STREAM) are propagated from their exact
validated Make values only for completion1. Guard predicates are retained.

## Synthetic gate

```bash
python3 port/dreamcast/tools/cloud/build31/portal_runtime_host.py
python3 port/dreamcast/tools/cloud/build31/portal_completion_host.py --output "$OUT/host"
python3 port/dreamcast/tools/cloud/build31/portal_completion_host.py --sanitize --output "$OUT/sanitized"
```

Use fresh output directories. The completion gate retains the original388
loader/runtime checks, then tests actual production runtime, literal chunk_emit
and the literal end_direct/batch_close/finish block:628 total checks. emit_pick,
Package and PVR edges are controlled. Cases include queued and clipped-away
work, partial emission, refusals, aborted work, exact part/placement, stale
serial/exhaustion, target-before-last-witness, frame/scene/view/projection/
viewport, cell generation/storage/metadata pointers and material mutation.
Fifteen additional actual Make/source guard cases verify supported composition
and retained refusals. ASan+UBSan inspect host memory; leak inspection is disabled.
This does not test retail geometry, full selection/emission mathematics, GPU
fences, real movie playback, gameplay/STRICT, look or console performance.

The fixed completion key array is256x6 uint32 words (6,144 bytes), plus source
context/serial. Queue tickets add four words per48 bounded contexts. These are
storage costs, not runtime headroom, whole-stack or hardware acceptance results.

## Missing private acceptance inputs

Use the existing Build31 private-data commands with PKG equal to the exact
staged room-package directory and CFG equal to geometry-authored safe eye/hull
boxes from actual opaque walls. The three package files are
ps2-world.re4mesh, ps2-world.r4pw and ps2-world.ids. The builder must produce a
matching interior.cell and portal-proof.json and identify witnesses that precede
targets. No such geometry/config/proof is supplied by these synthetic fixtures.
Their absence holds real occlusion/magenta/look acceptance, not source work.
Current-data reset/reentry/movie loan, gameplay/STRICT, memory and full physical
CPU/GPU cost remain separate gates. Existing failed or incomplete evidence stays.

## 2026-10-29 target result

Runtime source is `ec1855b42` plus scoped Make propagation repair `f5383c0dc`,
based on77461a84. Fresh full release absent/explicit0 and the explicit ON
validation composition pass actual rc0, nonempty ELF and existing empty
missing.txt. The original failed ON at ec1855 is retained separately; it was
not overwritten or counted as target validated.

Baseline==absent==zero for raw programme3,372,036 bytes
(SHA256 fbf2d3c94dfc02e109f5901b2aedfbb91106cabd3cb7b77d16d283e3662302c1),
all15 overlay payloads and all11 allocated ELF sections including zero-fill
metadata. Whole debug ELF hashes differ. Complete native_static -E -P and
-g0 objects also match baseline/absent/zero in both release and the existing
solo-portal source composition. That additional TU profile uses explicit
PS2_PVS_DEFAULT0; it is a source-composition check, not a separate full game link.

The actual enabled Make command's -dM readback confirms20 required1 facts and
three stream/clip0 facts. Four previously missing early facts match their
resolved Make values. All source guards remain; this is no hardcoded bypass.
ON ELF SHA256 and all source/recipe/toolchain bindings are in
[the target receipt](receipts/portal-completion-target.json).

Actual completion symbols total6,165 B of BSS plus8 B initialized data, before
section alignment. The fixed key array accounts for6,144 B. Queue tickets are
16 B each at48 contexts. In the exact target configurations the local ps2_pass
frame is9,008 B release,9,476 B old solo-portal and10,256 B new queued completion.
The ON composition also enables batching/PVS/portal prerequisites, so these
frame differences are not an isolated optimization cost. They are local frames,
not whole-call-chain bounds, measured headroom or hardware duration. No speed
or real geometry admission result is claimed.

Receipts: [host](receipts/portal-completion-host.json),
[sanitizer](receipts/portal-completion-sanitized.json),
[full OFF identity](receipts/portal-completion-disabled.json),
[TU identity and actual macro readback](receipts/portal-completion-tu.json).
Raw build outputs are /root/probe/lanes/route/out-ef08oct29v1{absent,zero}rP
and out-ef08oct29v2onrP; baseline is out-enginewave1oct29rP. Detailed logs and
TU artifacts are under /root/probe/engine-ef08-20261029/{release1,release2,tu2}.
Exact serialized local scripts are codex-lanes/engine-wave1/ef08-build.sh,
ef08-build-v2.sh and ef08-tu.py in the Windows workspace. They use the unchanged
rr recipe and ch2-build.sh rP chain; outputs are unique, preflight-checked and
the route registry is isolated/disabled. All recorded runners exited; no SDK,
emulator, publication or media job remains active.
