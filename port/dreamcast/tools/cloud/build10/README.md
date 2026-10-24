# Build 10: world census controls

`WORLD_CENSUS24=1` is the diagnostic implementation of Gate 0 in
[the world programme](../../../docs/cloud/WORLD_2MS_PLAN_20261024.md).
It defaults to zero and changes no production recipe. See the
[hand-back report](../../../docs/cloud/BUILD10_WORLD_CENSUS24_20261024.md)
for the accounting contract, evidence and target-cost limitations.

## Collect a window

Use the accepted QA recipe and its existing assets, with:

```text
WORLD_CENSUS24=1 WORLD_CENSUS24_WINDOW=300 QA_MENU=1
PS2_WORLD_DRAW=1 PS2_WORLD_MESH=1 PVR_STREAM=1 MESH_DIRECT=1 TA_DIRECT=1
```

The window must be between 300 and 600 **drawn ticks**. Keep all other
recipe, logging, display, camera and world settings fixed. `WORLD_METER`
may remain enabled for comparison, but is not required. Duplicate-work
comparison modes (`MESH_VP_SCHED`, `MESH_STRIP_LEAN`, `MESH_CLIP_ACCEPT`,
`PS2_INTERIOR_CULL` or `SG_SELECT_LEAN` set to 2, or
`SCENERY_DEDUP_CHECK=1`) are rejected.

The serial log emits one bounded `WC24` line per complete window. Timing
fields are integer microseconds per drawn tick. `t` and `d` are the actual
logic-tick and drawn-tick denominators. `phase` is selection, transform,
clip, header/material, submit, other, in that order. `pick` is indexed,
plain and empty-strip-group (`nr == 0`) picks. `v` counts transform inputs;
`c` counts emitted strip corners, not triangles. `flip` counts observed
page flips, not submitted scenes or present requests. `gap` counts flip
intervals longer than two observed fields. `err` must be zero for a
qualified window. `summary_overflow=1 full=QA` means the compact log row
did not fit; the sealed snapshot and QA rows remain available.

Open the in-game QA menu and choose **WORLD CENSUS (LAST COMPLETE WINDOW)**.
A/Right and Left change pages; B returns. The page displays the sealed
near/far × OP/PT/TR matrix, both overall denominators, explicit waits,
residual and presentation cadence. Opening the menu pauses collection;
resuming starts a fresh window. Room, view, relevant world-option and
package-residency changes invalidate a mixed window. Wait for a new
complete window after each change.

Raw totals are available through `re4dc::wc24::snapshot(Snapshot*)`.
For any phase or count, divide the **same window total** by `ticks` for
the per-tick mean and by `drawn` for the amortized per-drawn mean. The
display uses integer division; reconcile the raw totals, not rounded
display rows. Scene completion, drawing intent, present requests and
actual flips deliberately have independent counters.

## Public, reproducible controls

All fixtures generate synthetic data. They require no game files.
Run from the repository root, using a fresh output directory each time:

```sh
python3 port/dreamcast/tools/cloud/build10/run_controls.py --output /tmp/wc24-core
python3 port/dreamcast/tools/cloud/build10/run_controls.py --output /tmp/wc24-core-asan --sanitize
python3 port/dreamcast/tools/cloud/build10/check_geometry.py --help
python3 port/dreamcast/tools/cloud/build10/build_controls.py --help
python3 port/dreamcast/tools/d367/world_census24/target_cost.py --help
```

`run_controls.py` links the actual census core against a deterministic
clock, thread identity and PVR-event oracle. It checks 600 logic ticks /
300 drawn ticks, exclusive nested phases/waits, a second window, logging
cost attribution, non-owner calls, pause/resume, partial ticks, identity
changes, overflow, stale scopes and actual-flip cadence. The sanitizer
mode enables address/undefined checks. Leak detection is disabled there
because the managed validation environment cannot inspect `/proc` task
state under ptrace; this is recorded in the receipt.

The geometry control extracts the current production emitter and its
successful output-accounting helpers. It compares ordered TA words,
vertex/header accounting and SQ ownership traces with instrumentation
explicitly zero/on. It also reconciles the on-census counters with an
independent packet parser. Selection and the far-shell loader are outside
that emitter fixture; the hand-back names their separate coverage.

Target controls compare absent/zero/on builds using the repository's Make-derived recipes, generated
public headers, pinned KOS/SH4ZAM headers and SH-4 compiler. Do not replace
their full preprocessing/object comparison with a text-only guard check.
Cycle modelling is instruction/pipeline evidence; it does not model the
console's operand-cache miss latency or PVR/SDRAM contention.

## Local acceptance still required

Collect matched cross and farm windows, verify zero census errors, and
retain raw totals plus the resolved build/asset identity. Measure the
instrumented-versus-uninstrumented perturbation on the console. Check
actual presentation cadence, visual output, room transitions and STRICT
gameplay equivalence with the normal local harness. An instrumented
world time is not an uninstrumented production cost and is not proof of
the 2 ms target.
