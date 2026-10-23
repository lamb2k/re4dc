# D367: queued world UV snapshot — 2026-10-23

Base: `28da09802ed9ff6756529bab02978230983453be` (`origin/t15/int`).
Option: **`SCENERY_UV_SNAPSHOT=1`**, default **0**, requires `SCENERY_CHUNK=1`.
This is the separate Build 2 correctness fix. It carries a small setup cost.

## Behavior

`PS2_WORLD_TRANSITION_OWNER` prepares `part.uv_offset` for the current placement
and part. Queue replay previously read that shared field later, after another
owner could replace it or an `R11fUvScope` could reset it. A capacity drain can
also happen after the next owner's offset has already been prepared.

Both SELECT_ONLY and ordinary queue admission now snapshot the two components
**after any capacity drain**. Replay applies the row's UV before emission. A
flush-local scope saves and restores the pending owner's UV on normal and abort
returns. It encloses the existing submit scope, preserving its lock lifetime.
Owner predicates, cull/sky handling, material setup and accounting stay on their
existing paths. Static offsets produce identical output; differing dynamic
owners now match immediate per-owner emission.

The copies use explicit component moves. Test22's `-Os` compiled even an 8-byte
`memcpy` into a library call; replacing those new calls reduced modeled replay
overhead from about 49–58 to **6–13 cycles per row**. SH4 assembly saves/restores
UV through `fmov`, with no UV arithmetic. Target controls preserve signed zero,
quiet-NaN and signaling-NaN payloads exactly.

## Footprint and compiled cost

Actual Make-derived public Test22 flags, SH GCC 15.2.0. `native_static` executable
and allocated sections grow by the same amount; BSS and `native_ui` stay identical.
S = SELECT_ONLY, R = REPLAY_LEAN, B = SUBMIT_BATCH.

| R / B | Code delta, S=0 | Code delta, S=1 | `chunk_flush` stack |
|---|---:|---:|---:|
| 0 / 0 | +100 B | +100 B | 848 → 864 B |
| 0 / 1 | +100 B | +100 B | 852 → 868 B |
| 1 / 0 | +88 B | +88 B | 884 → 900 B |
| 1 / 1 | +96 B | +88 B | 896 → 912 B |

The SH4 queue row grows **96 → 104 B**: **+384 B** for 48 rows, or twelve 32-byte
lines of additional queue storage. `ps2_pass` grows 8988 → 9372 B with S=0 and
8992 → 9376 B with S=1. Its nested flush adds another 16 B: **+400 B on that
call path**. `MeshDraw` remains 776 B. These are object/stack results, not a
linked-disc or room-memory result.

The following are replay-only **model estimates per piece**, amortized over 48
pieces. The target fixture uses S=1 and already-selected records. The interpreter
runs the real compiled replay/setup bodies with an observed geometry edge. Warm I assumes residency; cold I starts with an empty
8 KB I-cache once for the complete batch. Both assume perfect D-cache.

| R / B | Warm cycles, off → on | Cold-I cycles, off → on | Load / store instruction delta | Read / write byte delta | Repeated 32 B line-touch delta |
|---|---:|---:|---:|---:|---:|
| 0 / 0 | 867.58 → 876.35 | 879.17 → 888.52 | +3.65 / +2.08 | +14.58 / +8.33 | +1.06 |
| 0 / 1 | 903.79 → 914.48 | 915.21 → 926.56 | +3.65 / +3.08 | +14.58 / +12.33 | +1.06 |
| 1 / 0 | 269.73 → 275.94 | 282.42 → 288.62 | +1.12 / +2.08 | +4.50 / +8.33 | -0.17 |
| 1 / 1 | 288.33 → 301.04 | 300.56 → 313.58 | +1.65 / +1.56 | +6.58 / +6.25 | -0.17 |

These are **net compiled-code differences**, including spills, literals and
helpers. The complete-batch distinct line unions are 197→212, 201→215, 199→201
and 202→204 for the table's four rows. A union is not divided by occupancy and
called a per-piece working set. Negative net repeated touches in two rows come
from compiled layout/access changes; the additional queue storage still exists.

Admission separately copies **8 read + 8 written bytes per piece**. Its cycles
and address-generation/spill effects are outside the replay trace. No cache-miss
penalty is inferred from line counts or from the console's +8.2 ms half-cache
experiment.

**500-piece frame model subtotal:** with ten 48-piece runs plus one 20-piece run
at 200 MHz, added replay cost is **0.0156–0.0318 ms** across R/B settings;
**+0.0318 ms** with R=B=1. Admission adds another **4,000 read + 4,000 written
payload bytes**. This subtotal excludes admission cycles and real cache misses;
it is not a measured or complete frame-time prediction.

## Qualification

Off-identity comparisons consistently omit preprocessor line markers and debug
line records, as in the preceding replay controls; complete executable objects
and line-marker-free preprocessed TUs are compared byte for byte.

| Control | Result |
|---|---|
| Complete `native_static` / `native_ui`, all eight S/B/R combinations | 64 exact baseline-versus-absent/zero `.ii` and `.o` comparisons; 16 enabled-UI identities |
| Real Make recipes, default/zero/on/value/dependency/owner cases | 24 configurations × 2 TUs passed |
| Actual production material + portable geometry, zero/static offsets | 1,056 exact TA-word and semantic-state comparisons |
| Dynamic rows versus independent immediate per-owner baseline replay | 528 exact TA-word and semantic-state comparisons |
| Old queued dynamic path, negative control | Different TA output in 34 of 66 cases in each of eight combinations |
| Both actual admission branches, capacity drains, ordinary fallbacks, early/late aborts, PVS-valid combinations | 85,536 static event comparisons; 128,304 dynamic/special-word cases; pending UV asserted around every flush |
| Actual SH4 compiled replay setup | 15 scenarios × 8 arms; two special-word pairs × 8 arms, exact row and pending UV bits |

Geometry controls cover validated synthetic R4IM v1/v3 meshes, indexed gather,
UV scales, cull/sky/alpha/material changes, clipping/rejection, empty selections,
and second-part packet pressure. They compare every word, not just hashes. The
host geometry uses the repository's portable transform plus the existing C
adapter for the SH4 SQ walker. No game assets, FTRV/FSRRA execution, full-frame
capture, Flycast run or console run is claimed. Console measurement and the
room-memory gate remain with the integration lane.

Source hashes, object hashes, stack values, model inputs and receipt hashes are
in [D367_WORLD_UV_SNAPSHOT_20261023.json](D367_WORLD_UV_SNAPSHOT_20261023.json).

## Reproduction

From the repository root, set `SH4_CXX`, `KOS_ROOT`, `SDK_ROOT` to the public
cross-compiler, KOS source and SDK-header roots. Each output directory must be new.
The tools reuse the already-qualified setup/submit/replay helpers on this base.

```sh
python3 port/dreamcast/tools/d367/world_uv_snapshot/build_controls.py --output /tmp/uv-build --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SDK_ROOT"
python3 port/dreamcast/tools/d367/world_uv_snapshot/verify_knobs.py --profile /tmp/uv-build/build-controls.json --output /tmp/uv-knobs
python3 port/dreamcast/tools/d367/world_uv_snapshot/check_geometry.py --output /tmp/uv-geometry
python3 port/dreamcast/tools/d367/world_uv_snapshot/check_admission.py --output /tmp/uv-admission
python3 port/dreamcast/tools/d367/world_uv_snapshot/target_build.py --output /tmp/uv-target --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" --sdk-root "$SDK_ROOT"
python3 port/dreamcast/tools/d367/world_uv_snapshot/target_run.py --build /tmp/uv-target/target-build-controls.json --output /tmp/uv-price
```
