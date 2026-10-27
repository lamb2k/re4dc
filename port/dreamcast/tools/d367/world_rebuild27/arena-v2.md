# Whole-house arena v2 benchmark contract

This replaces the v1 simplified/baked comparison with Original / Rebuilt / Sparse.
The complete selected house uses the same resident source texture key union in
all three arms. There are no baked maps. Package budgets are Original 2,940,
Rebuilt 900–1,500 and Sparse 300–600 L0 triangles. These package counts are not
camera-visible triangle counts.

## Two builds, one existing benchmark

HOUSE_ARENA27=1 remains default off. WORLD_REBUILD27_BAKE=0 is mandatory.
SCENERY_STREAM=1 retains its existing TA_HASH=0 requirement. Do not change the
renderer path to gain a TA_HASH counter. All existing benchmark/pace/frame-tail
requirements and frame bounds remain: warmup below room frame 120, measured
[120,300), meaning frames 120 through 299. Reuse exactly matching fixture camera,
Leon pose, actor filter and room state, with bench row names Original/Rebuilt/Sparse.

HOUSE_ARENA27_COUNTS=0 is the timing build. It does not compile geometry counters,
the observer callback, aggregate storage or diagnostic logging. Its measurements
come only from the existing benchmark CPU, PACE render/registration, frame-tail,
disc, heap and native stream instruments.

HOUSE_ARENA27_COUNTS=1 is a separate diagnostic build. It must never supply the
performance claim. native_static.cpp calls the public header's
Re4dcHouseArena27Geometry callback after each actual world-pass invocation. Bench
exports re4dc_house_arena27_room_frame() so the renderer tags the actual draw
with the room frame latched by dbgwarp; an old picture is never relabeled with
the next tick. The observation contains schema, sequence, pass, UI and room frame,
verified mesh CRC/bytes, exact view/projection/viewport camera hash, actual
transformed position work split into cache and clip work, emitted corners and
triangles, result/valid flags, fallback and abort counters.

The benchmark stores each observed pass separately, deduplicates sequence/UI
frame, rejects changing mesh/camera identities and invalid/fallback/abort records,
requires a strictly positive completion result (zero-output PT/TR still returns
result=1), and accumulates sum/min/max over actual observations whose room frame lies in
[120,300). It records the latest warmup baseline and up to four measured camera
samples per pass: first in each 60-tick band and the last completed observation.
Logs are emitted at results, outside the measured window. This avoids hundreds
of per-frame log lines. Missing passes stay explicitly unobserved. A genuinely
invoked zero-output PT/TR pass has n>0 with zero geometry metrics and is valid.

Counts describe the actual instrumented renderer path; unsupported paths are
refused by the native observer's build guards. Frustum and strip-group rejection
breakdowns are not supported by this exact observer ABI and are reported as null,
not fabricated zero counts. The package budget and the camera observations answer
different questions: clipping, culling and the chosen view can change emitted
triangle counts. A renderer callback is not a PVR presentation receipt.

## Identity and report

The verified loader emits `arena27: identity schema=2 variant=0..2 mesh_crc=...
mesh_bytes=...` in both builds. Author receipts contain exactly three A/B/C arm
entries with arm, candidate_sha256, candidate_crc, candidate_bytes and l0_triangles.
The reporter pins the private receipt SHA256, matches runtime and observation
CRC/bytes against that author identity, and checks the declared package budgets.
The source/author authentication is owned by the asset generator and runtime
loader; the reporter does not replace their CRC/SHA and companion checks.

    python3 port/dreamcast/tools/d367/world_rebuild27/arena_report.py \
      original.log rebuilt.log sparse.log \
      --environment cache-model-flycast \
      --fixtures warp.txt bench2.txt bench3.txt \
      --asset-receipt PRIVATE/arena-house-v2/RECEIPT.json \
      --json timing.json --markdown timing.md

Generate a separate report for the counts build. The reporter refuses mixed
versions, build IDs, counts/timing modes, camera identities, missing or duplicate
observer metrics, impossible sum/min/max, invalid source frame ranges and missing
baseline/last-camera samples. Each log accepts footer rows only for arms armed
in that same log/run, preserving the v1 single-arm footer repair. Legacy v1
original/simplifiedR4/baked logs remain supported without v2 receipts or counters.

Use console only for physical Dreamcast logs. Cache-model Flycast GPU values are
not hardware accurate. Keep MODELLED CPU evidence separate. No hardware GPU win,
visual acceptance, route qualification or release readiness follows from the
source, host tests or instrumented observer alone.

## Explicit measurement of the frozen target misses

The frozen recognizable Rebuilt house has 1,578 triangles and Sparse has 655.
These miss the prospective upper targets by 78 and 55 triangles respectively.
The scientific decision retains black interior liners and roof undersides rather
than deleting required panels. Cuts versus the 2,940-triangle Original are 46.3%
and 77.7%. These are geometry reductions, not measured GPU gains or look approval.

Budget validation remains strict by default. The coordinator may pass
`--allow-target-miss` when measuring the pinned final packages. Only B/C target
misses can receive this explicit measurement exception. Original must remain
exactly 2,940. Every v2 row records triangle_target range, actual, target_met,
measurement_exception and reason. Reports with the exception retain
budget_qualified=false, explicit warnings and measurement-only-target-miss
eligibility. No target is relabeled as passed, and any other failure still makes
the report invalid. Malformed/mismatched package identities, invalid completion,
source frame/camera checks and every existing measurement gate remain mandatory.
The staging helper separately pins the exact final A/B/C receipt and package
identities; this option does not admit arbitrary assets or approve production.
