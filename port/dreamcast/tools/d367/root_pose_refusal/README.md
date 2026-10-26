# Root-pose refusal controls — 2026-10-26

Base: `db222fc618045fc1da2bb3c7222743f83612ed1b` (`t15/int`). This lane repairs two
conditional native scenery omissions identified while comparing Test22, Test23
and Test24. The one-root adapter already existed in Test22 and was enabled by
the Test23 release recipe. No shipped room has been proved to exhaust either
resource, and these conditions are not intrinsically console-only.

## Controls and behavior

All three `game30.mk` controls default to **0**, accept exactly one word, `0` or
`1`, and require `PS2_WORLD_ROOT_POSE=1`, `PS2_WORLD_PARTS=1`,
`PS2_WORLD_DYNAMIC=1`, and `PS2_WORLD_ROOMS=1` or `2` when enabled. No release
recipe or default changes. Only `native_static.cpp` receives their defines.

| Control | Enabled behavior |
|---|---|
| `ROOT_POSE_CAP_FALLBACK=1` | Keeps the 16-entry delta cache. A valid moved root beyond that cache returns a distinct state; the native placement path computes its current root × original bind inverse × placement affine in bounded local scratch. |
| `ROOT_POSE_WITNESS_PREFLIGHT=1` | Reserves one potential one-root witness per unique R4ID owner together with the existing slot array, before publishing dynamic owners. One-root registration performs no later allocation. |
| `ROOT_POSE_REFUSAL_DIAG=1` | Records exact 64-bit refusal and recovered-overflow totals per bound owner, with bounded periodic emission and a final report before rebind/retirement resets its counters. |

The cap control works independently of preflight. Neither repair selects missing
GameCube source geometry or uses an old baked pose when the current root is
invalid. Hidden objects, serial mismatches, unavailable witnesses and invalid
matrices remain refused. A root returning exactly to its bind matrix uses the
original placement affine. Multipart objects keep the existing source hierarchy
path and separate part allocation.

The overflow draw rechecks object flags, serial and witness validity before
touching the borrowed part. It adds no per-frame heap or VRAM allocation and no
GPU upload. Source eligibility remains false for these native one-root owners.
The existing cache remains 16 × 48 = 768 bytes.

## Witness ownership and the memory-failure edge

The preflight cell contains `[Slot array][RootWitness array]`. Each root witness
retains the existing `PartPose` followed immediately by its original 12-float
root matrix and 12-float inverse. Its slot publishes that embedded pointer only
after the original registration captures the witness. A repeated registration
cannot recapture an animated matrix; a refused first attempt stays refused until
an explicit new object bind. Serial reuse is checked before reading part data.

R4ID stores placement-to-object IDs, not source part counts. It cannot safely
identify which unique IDs will be one-root objects, so reservation covers all
unique IDs, including IDs that never bind or later bind multipart objects.
Duplicate IDs and out-of-range IDs retain the existing baked policy. The
reservation helper rejects zero, counts above 250 and arithmetic overflow.

**Enabled-only failure behavior:** if an already validated R4ID has at least one
unique owner and the required combined slot/witness cell cannot be allocated,
room admission logs `ROOTPOSE_PREFLIGHT` with room, owner count, required payload
bytes and free-heap evidence. It frees the new sidecar and retires the newly
opened native package through the existing cleanup path, without publishing any
dynamic owner. It then calls `re4dc_missing("root-pose witness preflight")`.
That existing API deliberately stops the game with a named missing-resource
failure; this is not an ordinary load fallback. The repair prevents silent
missing objects and late bind-allocation failure, but it cannot render the room
if the required reservation is unavailable. The diagnostic switch is not needed
for this one admission-failure message.

The existing prior-room retirement boundary is unchanged: a different requested
room retires the old package where it already did; an already open same-room
package returns before reservation. No movie borrower is published at the new
failure edge. The source heap's 80 KiB reserve is unchanged, and allocation uses
the existing optional far-shell reclaim policy.

Rebind and reset free separately allocated multipart cells, never an embedded
root pointer. Movie borrowing retains the combined cell; validation checks its
exact payload size and generation, and verifies that each one-root pointer is
that slot's own reserved witness. Returning the world retains the original
witness; it does not allocate or recapture it.

### Target memory accounting

GCC 15.2.0 SH-4 layout: `Slot=76`, `PartPose=40`, `RootWitness=136` bytes,
4-byte alignment. `Slot.parts` is at byte 56 and `root_matrix_offset` at byte 72.
The witness's two matrices start at byte 40 and byte 88 of its 136-byte record.
With diagnostics, `RootDiag=24`, `Slot=100`, and the diagnostic field starts at
byte 76. Host pointer sizes differ; target layout was checked separately.

For **N** unique R4ID owners and **R** owners that actually become one-root:

| Item | Existing path | Preflight |
|---|---:|---:|
| Slot payload, diagnostics off | `76N` | `76N` |
| Root witness payload | `136R`, separate cells | `136N`, inside slot cell |
| Maximum extra reserved payload compared with slot-only admission | — | `136 × 250 = 34,000` bytes |
| Maximum combined payload, diagnostics off | — | `212 × 250 = 53,000` bytes |
| Maximum combined payload, diagnostics on | — | `236 × 250 = 59,000` bytes |

The ordinary high-allocation charge is
`round_up_32(payload + 32-byte Room4Cell) + 64-byte OS/MAD overhead`.
An existing separate 136-byte witness therefore normally costs 256 heap bytes.
For N=250, the combined cell normally costs 53,120 bytes, versus a 19,104-byte
slot cell plus `256R` bytes for the original separate root cells. If all 250
owners are roots, combining their cells normally saves 29,984 heap bytes; if
none are roots, it normally costs 34,016 extra heap bytes. These are allocator
layout calculations, not room census measurements. A too-small remaining free
cell tail can also be absorbed by the allocator. Multipart allocations and the
existing R4ID/package cells are common to both paths.

## Diagnostic interpretation

Example format:

```text
ROOTPOSE room=104 id=10 serial=27 object=0x... when=periodic refused=3 spill=8 reasons=30 frame=120
```

Room, R4ID owner ID, original bound serial and object address identify the owner.
`refused` counts **new refusal decisions** at registration, an uncached query, or
the overflow draw's revalidation. It is not a count of every attempted draw:
repeated same-frame queries reuse their result and do not count again.
Registration and subsequent query refusals are separate decisions. `spill`
counts valid overflowing-root evaluations accepted for scratch recomputation;
it does not count geometry submissions. Both are 64-bit cumulative counters.

`reasons` is a cumulative hexadecimal bitmask:

| Bit | Meaning |
|---|---|
| `01` | Owner flags deliberately hide/disable the root |
| `02` | Missing object or owner serial mismatch |
| `04` | Missing original witness |
| `08` | Invalid root transform or offset |
| `10` | Fixed delta-cache capacity |
| `20` | Part allocation refusal |
| `40` | Short original part chain |

Up to four dirty owners are emitted per 120 native frames, at native-pass entry
before direct/chunk/SQ ownership. Emission clears only the dirty marker, not the
totals. Retirement reports all remaining dirty owners (at most 250), and rebind
reports that owner's dirty totals before reset. `when=retire` / `when=rebind`
distinguish these final reports. Deliberate hiding and successful spills are
distinguishable from missing or invalid data; the log is not itself proof of a
rendering regression.

## Verification and measured costs

`validation.json` is the compact receipt. Full command logs and generated
translation units are reproducible with the commands below.

- Eight host ASan/UBSan arms cover all combinations of the three controls.
  They extract the actual affine helpers, dynamic adapter, bind/source functions,
  placement decision branch, R4ID admission block, movie validator and retirement
  body. The heap, filesystem, object records and frame clock are synthetic.
- Controls cover 17 moved roots, exact transformed points, bind return, changed
  owner flags/serial between eligibility and draw, missing/invalid witnesses,
  refusal without late bind recapture, multipart behavior, 250 unique IDs and
  234 simultaneous overflows, same-room retention, room transition, failed
  admission cleanup/no publication, movie generation/size/interior-pointer
  rejection, exact 64-bit diagnostic totals and balanced allocation/free.
- Admission-failure tests use both a throwing failure adapter and a deliberately
  returning one: one named failure is recorded, ownership is unwound, and the
  admission function cannot publish a normal owner. The real failure API never
  returns. LeakSanitizer is disabled because its `/proc` thread scan is unavailable
  in this runner; the fixture's exact allocation ledger must end empty.
- Complete SH-4 `native_static.cpp` builds use the **current selected public
  release plus every ordered rr CH2 assignment**, including `SCENERY_STREAM=1`,
  and the current `build-public.sh` missing-asset overrides. Baseline, absent
  controls, and all-zero controls have byte-identical `-E -P` output and raw
  objects. All seven enabled combinations compile. Twenty-one negative Make
  controls reject blank/multiple/invalid values or a missing root prerequisite.
- The source-extracted SH-4 fixture executes actual compiled decisions and
  affine math, checks target layout, and prices recorded instructions with the
  existing pipeline model. XOR immediate controls cover 1,280 inputs; retained
  ROTR behavior covers 80. Existing memory-observer controls also pass. No shared
  interpreter, SDK or runtime assembly was changed.

Compiler: `sh-elf-g++ (GCC) 15.2.0`; KOS pin
`804b3195ebd1a06a27cc2b3a5eacf7a2429040a3`. Debug records were omitted consistently
for object identity. Only a local copy of pinned PVR header declarations was
patched for compilation; no KOS library or complete game was built.

### Complete-TU section and stack deltas

| Enabled controls | Executable bytes added | Allocated-section bytes added | Static BSS added |
|---|---:|---:|---:|
| Cap only | 472 | 472 | 0 |
| Preflight only | 344 | 442 | 0 |
| Both repairs | 816 | 914 | 0 |
| Both repairs + diagnostics | 1,530 | 1,762 | 4 |

Diagnostics also add one initialized 4-byte scheduling word and 24 bytes per
heap slot. These are object-section figures, not final linked-image sizes.
GCC's complete-TU stack report changes `ps2_pass` from 9,000 to 9,008 bytes and
registration from 68 to 72 bytes with both repairs. Query remains 120 bytes;
room open remains 596 bytes. The compiler reuses placement scratch; these stack
figures are distinct from the smaller standalone timing fixture's stack.

### Synthetic overflow cost — not a console timing

Both timing arms enable witness preflight and disable diagnostics. The measured
sequence fills the first 16 entries, then queries and draws one additional moved
root. The draw fixture stops after choosing/copying its affine, before geometry.

| Operation | Cap off: cycles warm / cold I-cache | Cap on: cycles warm / cold I-cache |
|---|---:|---:|
| Overflow query | 1,493 / 1,870 | 1,488 / 1,867 |
| Native placement decision + affine | 168 / 354 (hidden) | 1,963 / 2,400 (drawn) |

The enabled overflow draw observes 1,496 data-load bytes, 428 data-store bytes
and 39 distinct 32-byte data lines; the off draw observes 163, 108 and 18.
These include stack and literal accesses. Line sets are touches, not cache misses
or bus traffic. Warm figures use perfect instruction/data caches; the cold
sensitivity starts an 8 KiB I-cache cold with the fixture ELF layout. Neither
models data-cache stalls, DMA/IRQ contention, SQ/PVR backpressure or GPU work.

The additional warm transform/decision cost is 1,790 cycles for one native pass,
about **0.00895 ms at nominal 200 MHz**. If the same overflow root reaches all
three passes, the projection is `-5 + 3 × 1,795 = 5,380` cycles, or **0.0269 ms**.
This is a **MODELLED transform-only projection**, not a measured whole frame or
speedup: the previously missing object's geometry and GPU work must also run.
Normal-path fixture differences and all other cases remain in the receipt.

### Existing legacy test blocker

The unchanged command
`python3 port/dreamcast/tests/test_movie_world_arena.py`
stops in `contracts()` at the assertion
`body.index('ps2_movie_blocked()') < body.index('#endif')` for
`re4dc_ps2_mesh_camera`. Extracting that function from base `db222fc6` reproduces
the same assertion. This lane does not change that unrelated extractor or claim
its full suite passed. The new ownership/lifetime tests above passed separately.

No private assets, complete-game link, Flycast route, gameplay STRICT comparison
or physical Dreamcast run was performed. These are conditional correctness
repairs and diagnostic controls, not confirmation of the reported hardware
regression or approval to enable them in a release.

## Reproduce

Run from the repository root; each output directory must be new. `SDK` is the
initialized `port/dreamcast/game/third_party/sh4zam` checkout. `CXX` is the selected
SH-4 compiler, and `KOS` is the pinned SDK source root.

```sh
python3 port/dreamcast/tools/d367/root_pose_refusal/test_host.py --output /tmp/root-pose-host
python3 port/dreamcast/tools/d367/root_pose_refusal/build_controls.py \
  --output /tmp/root-pose-target --sh4-cxx "$CXX" --kos-root "$KOS" --sdk-root "$SDK"
python3 port/dreamcast/tools/d367/root_pose_refusal/target_cost.py \
  --output /tmp/root-pose-cost --build-controls /tmp/root-pose-target/build-controls.json
```
