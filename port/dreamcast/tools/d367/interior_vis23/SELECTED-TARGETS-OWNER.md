# Conditional target admission: tested owner proposal

This branch contains only new tools, this document and an **unapplied** patch.
No runtime, build configuration or converter file was edited. Base:
`194fecd107fdf5211a30b47ff90011ac5754e5a6`, including material fix `86d8703ff`
and the reviewed captured-affine source receipt fix. Root must coordinate the
native_static.cpp claim with select-only23 before applying the patch.

## Minimum implementation

Apply `selected-targets-owner.patch` only after that claim is transferred. It
changes three existing files:

1. In native_static.cpp, keep both early target tests under knob-off. With new
   `PS2_PVS_SELECTED_TARGETS=1`, run both target tests immediately after the
   existing actual affine selection and `pvs_source_placement` capture. Admit
   `pvs_cur` only when `pvs_source_placement==i` and unchanged `can_cut(i)` passes.
   No second dynamic query or fresh-state substitute is introduced.
2. In t2exact.mk, declare the new knob default 0, validate exact 0/1, require
   PS2_PVS=1 when enabled, and route the value to native_static.o only.
3. In certify.py, make every newly emitted `--conditional-targets` descriptor
   fail compilation unless that knob is 1. Its research/unadmitted status,
   geometry verifier, margins and table format remain unchanged.

No certificate fields, queue fields, heap allocation, dynamic epochs, target
indexes, offsets, transforms, source observation identities or source guards
change. Numeric/material/source-prefix/all-receipt guards remain exactly the
existing bodies. Fresh target intact remains an additional conservative veto.

The pointer check authenticates what the renderer actually selected. A normal
or root-pose cached moved delta can coexist with a fresh-rest target predicate;
the selected local moved_affine nevertheless gets the sentinel and cannot use
the certificate. A captured baked matrix remains the certificate geometry even
if ownership later changes. Hidden/source-hierarchy query results skip before
the new target gate. Claimed world-owner paths can cut only their actual baked
geometry and still must pass every existing source/target check.

## Complete call-site and admission audit

The base native_static.cpp has one declaration of `can_cut`, one caller in
`pvs::hidden` (4922), and one qualified caller at the beginning of ps2_pass
(6287). The hidden-placement call is also before dynamic affine selection
(6321). There are no other game callers. The proposal preserves hidden's
redundant can_cut recheck, moves its **only caller** after selected-affine
qualification when enabled, and keeps both original positions when disabled.

`pvs_cur` feeds the existing SELECT_ONLY selector and direct MeshDraw. Both
implementations share `chunk_ok`, which refuses any nonnull `pvs_set`. Thus a
partially hidden admitted target already takes the direct cluster filter;
there is no new PVS-bearing queued context. Moved targets get null pvs_cur,
retain their existing queued picks/matrix/sentinel, and actual chunk_emit does
not re-run target PVS decisions. A source becoming qualified after target
selection cannot retroactively discard queued target picks. All three existing
identity assignments and replay restart remain unchanged.

The R4PV loader binds physical mesh/policy CRC and instance count, validates
layout/cell ranges/padding, constructs base/poff, and calls the certificate table
guard. That guard binds the exact table bytes/CRC, mesh identity, physical
policy and source panel placement/part/cluster/one-level/meshlet/corner mapping.
Neither contains a unique-ID target veto or a separate target roster. Current
target exclusion is the converter's default `~I['dyn']` predicate. Its existing
research `--conditional-targets` option removes only that veto while preserving
the continuous full-cluster/all-LOD AABB proof and independent verifier. The
same hashed package geometry/physical policy must be used at runtime; this
proposal does not authorize mutable target LOD/bounds or a new certificate
format. Source-prefix retention, at most16 source dependencies and every
committed source receipt remain mandatory.

Existing private conditional research descriptors predate the compile guard.
Do not reuse them for a target build: after owner application, regenerate and
authenticate the guarded descriptor for its exact unchanged table. No private
descriptor or table was generated, promoted or changed by this task.

## Actual-source host controls

```text
python3 port/dreamcast/tools/d367/interior_vis23/check_selected_targets.py \
  --evidence /mnt/c/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023
```

The runner creates a small mirror in `/dev/shm`, applies the exact proposal
there, checks equality against the generated proposed source, extracts the
actual bodies and compiles them with G++13.3/C++17/O2/Wall/Wextra/Werror. All
temporary compiler inputs/products are removed on exit. Source-only sparse
checkout is under1MiB; no SDK or private assets are used.

Actual executed bodies include query/intact; both placement target gate
locations and the actual dynamic/owner selection; pvs hidden/cluster-bit
filters; chunk_ok/restart/emit; the complete current proof runtime including
table/frame/numeric/receipt/source/target guards; source observe/commit and
MeshDraw source observation/finish; and all three captured-identity assignments.
The full current proof header is included unmodified.

Mocks are synthetic object/root/package/vertex storage, translation inverse
and concat boundaries, source scene/material API results, target emit_pick
vertex/packet boundary, and an explicit FPSCR-reader boundary. No numeric,
table, intact, query, source receipt or target cut result is stubbed. The
synthetic certificate intentionally permits knob-off fixture compilation to
demonstrate the old path; separate controls execute the proposed converter's
actual emitted guard and reject conditional descriptors with knob absent/0.

Eight knob/lean/root configurations pass1,558 assertions:

| Selected targets | Lean | Root pose | Assertions |
| --- | --- | --- | --- |
| 0 | 0/1 | 0 | 149 each |
| 0 | 0/1 | 1 | 182 each |
| 1 | 0/1 | 0 | 188 each |
| 1 | 0/1 | 1 | 260 each |

Normal and root moved-to-rest controls first show actual fresh intact and
can_cut both accept while actual query retains movement. With the new gate,
all moved clusters remain visible, including queued selection followed by
rebind/cache reset, late source receipt and reuse across moved/baked/empty
contexts. Actual chunk_emit emits every captured pick. Stable baked hidden
targets cut; partially hidden baked targets take direct fallback and retain
the other cluster. Hidden/hierarchy/area/gate owners, invalid binding and
claimed-owner mismatches retain their existing behavior.

Negative controls exercise actual wrong mesh/policy/source-LOD/missing-LOD
table admission; no source receipts; failed source intact; frame/scene/package
epoch changes; opaque-source API refusal; no active cell; source-prefix
retention; and actual numeric/FPSCR/projection/viewport/camera rejection.
Restoring the old early fresh-state target gate, or removing only the new
selected-affine check, compiles and fails the moved-target visibility assertion.

Eight bounded source-preprocessing comparisons across PVS on/off, dynamic
on/off and lean on/off match the base when the new knob is0. SDK includes are
removed identically and unspecified RE4DC features are defaulted off for these
host text comparisons. Make-variable tests verify object-flag routing and
reject enabled-without-PVS, invalid/list/empty values. Six emitted-descriptor
tests preserve ordinary descriptors and reject conditional descriptors unless
selected-target support is1.

Evidence: `selected-targets-host.json` and `selected-targets-excerpts.json` in
`C:\Flycast-Evidence\re4-dreamcast\interior-vis23-20261023`.
Tested proposal SHA256:
`1e8a542a9692d87f7acf9dce091dff4bec0781a5f01fa2a7c8ca10fbadcb93b3`.

## Current real-data applicability and remaining gates

Existing primary-lane research was read back without modifying its inputs:
r102 mesh CRCa4ccc78d, physical policy CRCcf4936c0; seven camera-derived cell
domains, one conditional source panel at placement0/prefix0. Continuous proof
clears one target instance91 in each of cells48/49/70,24L0corners per cell;
that target is placement16/field16/part89/cluster91 and conditional. Its table
hash is `0e6e860eba6d4347fcb56fefb36e9a3fc7e5e49b59dc2fef791198f26da3ac03`.
The research record explicitly says `runtime_admitted=false` and
`actual_runtime_cuts=0`. These are continuous-proof data counts, not runtime
selected vertices, observed cuts or a speed claim. Primary's current43-view
r102 window averages7,634pre-SG opaque corners/139meshlets with static-target
ceiling0; this proposal unlocks a necessary eligibility class, not a measured
performance result. r109 conditional-target research currently proves0bits.

Owner application must wait for the shared-file handoff, independent review
and an exact patch/context check. Required later gates include target knob-off
program-image identity, target compile/link and arithmetic/material/table
qualification, useful admitted cuts with source/runtime-state evidence,
corresponding-buffer/pixel or approved look checks, memory/KOS/s30/TEXCHK/GDEMU
checks as applicable, and console measurement before any speed claim. No full
target build, staging, media/guest run, new private data, sampling proof,
conditional-table promotion, recipe, SD or release change occurred here.
