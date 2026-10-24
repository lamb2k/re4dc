# Build 12: local vertices and sequential strip inputs

Date: 2026-10-24. Branch: `codex/scenery-data-variants-20261024`.
Publication base: `4efca35b98cdcdd845122c279321b848b621e029` (`origin/t15/int`).
Validation base: `057e00a248c9ed473d0b3377a0ce14b0b2f5186d`, including Build 10.
The upstream difference is only the coordinator's queue answers; all target
and builder inputs are identical, as recorded in the publication-base receipt.
Candidate knobs: `SCENERY_LOCAL_INDEXED=1` or
`SCENERY_DIRECT_STRIPS=1`; both default to zero and are mutually exclusive.

This implements the two representation experiments in the
[2 ms plan](WORLD_2MS_PLAN_20261024.md). It does not reduce geometry, change
the release recipe, or establish a console speedup. The local-vertex arm
removes the shared-pool gather. The sequential arm removes transformed-cache
traffic on eligible whole meshlets, at the cost of repeated transforms and
per-corner kernel setup. The measured trade is reported below.

## Representation and ownership

The existing R4IM v3 plain representation already expresses both candidates:
12-byte prelit local vertices and local u8 strip indices. No new runtime
assembly, linker change, vertex quantization, LOD simplification, or format
version is needed. The new helper headers leave `MeshPackage`'s ABI and
definition unchanged in every translation unit.

| Arm | Offline work | Runtime work |
| --- | --- | --- |
| Current | Shared vertex pools and local gather tables | Gather, transform to the existing cache, walk strips, submit |
| Local (`SLI1`) | Materialize each exact local gather in dense order | Existing plain transform/cache/strip path; no shared-pool gather |
| Sequential (`SDS1`) | Materialize every strip corner in its existing order | Whole, conservatively inside picks transform directly into the current store-queue slot and flush it; other cases use the existing cache/clip path |

`ps2-sli1.re4mesh` and `ps2-sds1.re4mesh` are alternate files alongside the
unchanged `ps2-world.re4mesh` and policy. Reserved header words hold the
`SLI1`/`SDS1` marker and original file extent/body CRC. Admission checks those
against the actual standard-file header, validates the candidate's own
body CRC and ordinary package ranges, and proves local continuity, bounds
enclosure and (for SDS1) exact sequential strip indices. The marker is not a
substitute for the candidate's physical CRC.

Converter and reader reject more than 65,536 global meshlets because queued
picks carry 16-bit absolute IDs. They also prove that the sum of each cluster's
maximum selected LOD count fits its part's reserved pick count. Individual
range checks alone would allow overlapping cluster levels to overflow that
reservation. Subtracting each maximum from the remaining budget avoids an
overflow in the validation itself. The existing 320-pick/48-part queues flush
at capacity; a larger expanded part takes ordinary drawing rather than being
truncated. That possible path change is part of the measured layout trade.

SDS1 splits only between existing whole strips when the 256-local-vertex
capacity requires it. It preserves their order, winding, restart positions,
parent bounds, part ownership, and every LOD's ordered corner bytes. No
triangle-equivalence relaxation was needed by the synthetic fixtures.

The converter preserves model/UV tables, texture keys, colors, R4PW placements,
pass/cull policy and source identities. A supplied R4SG is validated against
the original package and remapped with the original selection bounds and
group membership. Without a matching candidate R4SG the existing whole-meshlet
fallback applies. The 262,144-byte group-file limit is unchanged; the converter
rejects an oversized remap. Check the `PS2SG` admission row as well as `SCNVAR`.
If groups are absent or rejected, use a matched whole-meshlet control; otherwise
selection work and output populations are no longer the paired group experiment.
Unknown appended tables, unsupported color representations
and unrecognized data are rejected rather than discarded.

The 3,072-byte gather reserve remains allocated to keep existing ownership and
retirement behavior. Its avoidance by an arm is not a 3 KB heap saving. The
transformed-cache capacity is also retained for fallback. Report candidate
package residency and sidecar growth separately from accessed working set.

## Eligibility and certificate boundaries

Direct submission requires an admitted SDS1 world, the ordinary direct SQ
owner, a full pick, the scheduled/lean transform configuration, and a bound
fully inside the supported camera's frustum and near/far planes. All strip
sizes are checked before the first irreversible SQ burst. Partial or empty
picks, clipping, oversized strips, unsupported kernels, TA-hash and CPU
back-face diagnostics retain the established path.

The candidate does not rewrite or impersonate existing mesh-bound proofs.
PVS, interior-cell, SCCN/SCPS/dedup and `WORLD_RECT21` combinations are rejected.
The current release recipe therefore needs the same three adjustments in
**both** control and candidate:

```text
PS2_INTERIOR_CULL=0 WORLD_RECT21=0 FOLIAGE_MIP24=0
```

Use corresponding unremapped original-policy assets. Existing texture-remapped
release assets are outside this experiment's accepted input contract.
Production OFF identity is checked separately against the unmodified recipe.

The unchanged OCCL enemy-visibility path uses source placement indices and
R4PW identity, not meshlet/corner indices or the replaced R4IM fingerprint.
Its source-placement semantics survive because placements, source IDs and
the ordered surfaces are unchanged. No certificate is newly issued here.
Hard-pinned movie/owner packages in the guarded r100/r11f/r200 paths retain
their base representation. `SCNVAR` logs report the requested and actually
admitted representation and physical/source CRCs separately; a base fallback
must not be timed or reported as candidate admission.

## Census composition

Build 10 is already in this branch's integration base. SDS1 eligibility is
charged to Selection. Its inseparable transform-and-SQ loop is one exclusive
Transform interval, including direct submission work. It is **not** a pure
transform measurement comparable to the cached arm's Transform column alone;
compare total world cost and the relevant combined phases. There is no
per-corner timer instrumentation or invented split of the fused interval.

Successful fused work contributes actual transformed inputs and walked strip
inputs once. The existing central direct-account path counts emitted corners
and headers once. Refused fast paths keep the existing census behavior.

## Validation and cost evidence

The [reproducibility README](../../tools/cloud/build12/README.md) gives commands
and the final compact receipts. All fixtures are public synthetic geometry.
No private world, disc, gameplay trace, emulator frame or physical console was
used. Target compilation uses GCC 15.2.0 (KOS thread model), binutils 2.45.1,
newlib 4.6.0, KOS `804b3195ebd1a06a27cc2b3a5eacf7a2429040a3` and SH4ZAM
`33fa4850cacb30dd0ad35485ef035526ec4ce782`.

The temporary compiler from Build 10 was lost. This build uses a separately
verified prebuilt compiler with the same component versions, from
`maishuji/dc-kos-image@sha256:aed8f106bccd705a554acf19ab224ef4d05f7d66f669ab8031872e458a9132fe`.
Its host ELF loader/RPATH were relocated into an isolated temporary SDK; all
executable instruction sections were checked unchanged. Actual compiler and
tool hashes are recorded. This is not a claim of binary identity with the
lost Build 10 host installation, nor a change to the game's linker/runtime.

| Gate | Result and scope |
| --- | --- |
| Default-off target identity | 16 complete `.ii`/`.o` byte comparisons: 2 existing TUs × production/matched recipes × absent/explicit-zero knobs × preprocessed/object output. |
| Enabled target builds | Six profiles compile: local, direct, their existing-stack compositions, eager direct, and census-enabled direct. Four comparisons prove the unaffected UI TU remains identical with A/B enabled. |
| Configuration rejection | 20 invalid Make configurations refuse the build. |
| Census target composition | Real renderer/UI/core objects partially link with every new hook resolved; the compiled census core contains zero FPU instructions. External KOS/libc and the final game link are outside this gate. |
| Converter and builder | Seven test groups, 16 ordered-corner cases, 18 strip-group cases; actual builder primary mesh/policy and normalized report identity with absent options, and unchanged primary files when alternates are requested. |
| Actual emitter | Each census-off, census-on and census-on ASan/UBSan run passes 480 converted A/B comparisons, 156 unmarked compatibility comparisons and seven malformed-reader controls. Ordered TA words, external accounting and SQ ownership agree. |
| Active census | 720 variant observations per enabled run; 72 fully fused cases require actual transformed inputs = strip inputs = emitted corners. Independent output parsing and the exclusive phase/residual partition agree. |
| Final reader bounds | Normal and ASan/UBSan runs admit eight ordinary candidates and the 65,536-ID boundary, reject 65,537 specifically, admit a safe 160-pick/161-slot overlap, and reject the unsafe 322-pick overlap. |

The two admission-only capacity fixes were added after the full geometry
matrix. Their bounded final controls and final complete target builds are
separate evidence; the matrix was not rerun under a new full-source hash.
The host receipt proves that all 28 census-off and 31 census-on extracted
production bodies used by that matrix remained unchanged. The converter also
rejects a valid source whose SDS1 expansion would exceed the new reservation.
ASan/UBSan passed with leak detection disabled because managed process
inspection is unavailable; no leak-sanitizer result is claimed.

Raw `native_static.o` section sizes, before final link garbage collection:

| Matched arm | Executable bytes | Allocated bytes | BSS bytes | Executable / allocated delta |
| --- | ---: | ---: | ---: | ---: |
| Control | 62,510 | 91,358 | 17,067 | 0 / 0 |
| Local A | 63,530 | 92,922 | 17,067 | +1,020 / +1,564 |
| Direct B | 65,128 | 94,586 | 17,067 | +2,618 / +3,228 |

The load-time function's local stack grows from 592 to 704 bytes. The new direct
function uses 100 bytes locally (104 with census); `chunk_emit` is 128 bytes
for control/A and 136 for B. Selector local stack remains 260 bytes. The largest
individual compiler stack record in the TU remains 8,880 bytes for all three
arms; this is not a proof of maximum integrated call-chain usage. No new BSS
or target assembly is introduced by either representation.

### Resident data

These are complete synthetic package sizes, not selected-frame populations.
The unchanged R4PW and other original companions are additional; the optional
R4SG column shows the sidecar that actually changes with splitting.

| Fixture | Original / local / sequential mesh bytes | Stored vertices, original / local / sequential | Meshlets, original / local / sequential | R4SG bytes, original / local / sequential |
| --- | ---: | ---: | ---: | ---: |
| Compact | 1,248 / 1,504 / 1,664 | 24 / 48 / 60 | 6 / 6 / 6 | 416 / 416 / 416 |
| Reused corners | 5,120 / 7,040 / 21,472 | 192 / 384 / 1,572 | 6 / 6 / 12 | 416 / 416 / 800 |
| Local-capacity boundary | 13,152 / 20,832 / 21,152 | 768 / 1,536 / 1,548 | 6 / 6 / 12 | 416 / 416 / 800 |
| Unused local vertices | 1,600 / 2,080 / 1,664 | 48 / 96 / 60 | 6 / 6 / 6 | 416 / 416 / 416 |

The direct arm can avoid transforming unused inputs, but it expands every
reused strip corner. In the reuse fixture its mesh package is over four times
the original size. Neither arm is presumed to fit the private room's peak
memory budget.

### Compiled kernel cycles and traffic

The target harness executes actual SH4 opcodes from the established scheduled
transform/strip walker and the new direct helper. It checks committed output
words for a deliberately bounded FP domain: identity FTRV and reciprocal-square-
root input 1. Broad geometry equivalence comes from the separate actual-emitter
host fixtures; this microkernel interpreter is not a complete SH4 FP emulator.

The indexed control includes its gather; local uses the same cache/strip kernel
without that gather. Direct includes conservative bound classification and
strip prechecking. Bind/selection/header/lock/wait/clip costs outside those
functions, D-cache misses, memory contention and SQ/PVR service time are
unpriced. Counter/census diagnostics are off for these performance comparisons.

Each cycle entry below is **warm I-cache / cold I-cache, MODELLED**. `P` means
the cached arm's cache setup is included in that call; otherwise its cache
state is already prepared. Scattered source controls use the same gathering
work with deliberately separated source vertices.

| Unique inputs / submitted corners | Source / cache setup | Shared control | Local A | Direct B |
| --- | --- | ---: | ---: | ---: |
| 8 / 8 | contiguous, P | 1,054 / 1,448 | 677 / 1,002 | 1,255 / 1,625 |
| 32 / 32 | scattered, P | 3,598 / 3,992 | 2,093 / 2,418 | 3,631 / 4,001 |
| 64 / 64 | scattered, prepared | 6,792 / 7,188 | 3,780 / 4,095 | 6,799 / 7,169 |
| 64 / 256 | scattered, prepared | 10,116 / 10,512 | 7,104 / 7,419 | 25,927 / 26,297 |
| 32 / 128 | scattered, P | 5,290 / 5,684 | 3,785 / 4,110 | 13,255 / 13,625 |

Architectural cached-RAM demand traffic for the two 64-input cases:

| Inputs / corners | Arm | Load / store instructions | Read / written bytes | Distinct 32-byte data lines | Actual transforms |
| --- | --- | ---: | ---: | ---: | ---: |
| 64 / 64 | Shared | 1,096 / 679 | 4,699 / 2,524 | 198 | 64 |
| 64 / 64 | Local A | 837 / 487 | 3,791 / 1,756 | 113 | 64 |
| 64 / 64 | Direct B | 2,048 / 747 | 8,056 / 2,988 | 53 | 64 |
| 64 / 256 | Shared | 2,443 / 679 | 11,422 / 2,524 | 204 | 64 |
| 64 / 256 | Local A | 2,184 / 487 | 10,514 / 1,756 | 119 | 64 |
| 64 / 256 | Direct B | 7,859 / 2,868 | 30,898 / 11,472 | 128 | 256 |

These line counts include stack, constants and data-literal accesses. They are
distinct lines touched, not observed fills or bus transactions. The receipts
separate data regions, repeated visits, prefetch requests, uncached accesses
and SQ writes. SQ reads are zero. At 64 corners the cached arms issue 257 SQ
store instructions / 2,052 architectural bytes and direct issues 512 / 2,048;
at 256 corners they issue 1,028 / 8,208 versus 2,048 / 8,192. The cached walker
rewrites the EOL word before the burst; these extra stores do not create extra
committed TA packet bytes. The logical output remains exactly identical.

Local A is the stronger scalar result in these fixtures. Direct B has a smaller
distinct working set in the low-reuse case, but its per-corner kernel setup
spills and repeats work. With fourfold corner reuse, its extra transforms and
input expansion dominate even the perfect-D-cache model. The data-line result
is the reason to retain the bounded console comparison; no universal winner
or console cache benefit is claimed.

The isolated kernel object is 2,112 executable bytes / 2,192 allocated bytes,
with zero BSS. Interpreted maximum call-chain stack is 120 bytes for the cached
arms and 156 for direct in these controls. Those are fixture-chain numbers,
not the full renderer's peak stack.

### Explicit MODELLED whole-frame scenario

Assume **100 calls per drawn frame** of the scattered 64-input/64-corner case,
**200 MHz**, and **30.0 ms for every other part of the frame**. The arithmetic
is `30 + 100 * kernel_cycles / 200000`:

| Arm | MODELLED frame, warm I | MODELLED frame, cold I before every call |
| --- | ---: | ---: |
| Shared control | 33.396 ms | 33.594 ms |
| Local A | 31.890 ms | 32.0475 ms |
| Direct B | 33.3995 ms | 33.5845 ms |

This supplies the requested whole-frame arithmetic with explicit assumptions.
Neither the 100-call population nor the 30 ms remainder is a measured r101
value. The cold column pessimistically resets the isolated instruction cache
for each call. These figures do not predict the supplied 49.3 ms console frame,
establish 30 fps, or prove the 2 ms complete-world budget.

The coordinator's newly published [Build 10 answers](CLOUD_AGENT_QUEUE.md)
report two zero-error steady cross windows at 14.097 / 14.145 ms world time
per drawn tick in Flycast, **MODELLED**, with 11,248 transformed inputs,
8,672 emitted corners and indexed/plain/empty-pick counts of 25/309/61.
Those are owner-reported workload shape, not console results or a workload
run executed by this build. In particular, plain picks already avoid the
gather eliminated by A; the synthetic all-indexed calls cannot be multiplied
by the total pick count. Per-meshlet sizes, reuse and clipping distributions
are still needed for a valid projection. The geometry-reduction work in the
2 ms plan remains necessary.

## Local-owner acceptance

Stage a hash-bound original package and each alternate with its matching
optional R4SG. Verify the actual `SCNVAR` admission row. Compare the paired
recipe above with identical camera, actors, effects, near/far policy, assets
and build toolchain, first at the cross and then over traversal/clip/room
transition cases. Keep the existing look, STRICT gameplay, source-placement,
memory-pressure and retirement gates.

Collect world census populations, actual transforms/corners, package and peak
resident memory, cache-miss phase diagnostics when qualified, console frame
time and presentation cadence. The public host/target fixtures cannot prove
real D-cache benefit, PVR behavior, gameplay equivalence or a 1–2 ms world.
Select a representation only after the combined console cost and memory
result is favorable.
