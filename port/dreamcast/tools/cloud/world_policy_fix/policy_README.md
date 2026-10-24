# Original-policy control preparation and R4SG diagnostics

This is a tools-only correction for a policy-lineage mismatch. It does not
change a renderer, runtime admission rule, certificate table, texture mapping
table, or the result of the Build12 experiment. The owner's current old-data
control has `WC24 err=0`; SLI1 was a wash and SDS1 was rejected. This work does
not reopen either variant or claim a speedup.

## Why the converter and runtime could disagree

The ordinary Build12 converter requires the R4SG policy field at byte 24 to
equal the actual R4PW body CRC stored at byte 20. Runtime can instead compare
that group field to the original policy CRC returned by the committed
`WORLD_RECT21` provenance helper. That helper accepts only a full, known
policy/mesh tuple, including the whole-policy FNV and genuine body CRC.

The error `R4SG identity/CRC` combines several checks. Without the actual input
bytes, it does not identify which check failed. These tools provide the fields
and a safe original-policy preparation path; they do not assume that every
refusal is a texture-key remap.

Simply admitting an original CRC while keeping the remapped policy would be
insufficient. The current Build12 recipe requires `WORLD_RECT21=0`, whereas
the remapped texture keys require matching runtime support. Normal Build12
parsing therefore remains strict. Its sole code change is the default-off
`--policy-diagnostics [0|1]` option, which adds exact field values to an error.
Successful package, group, JSON and checksum outputs remain byte-identical.

## Read-only inspection

From the repository root:

```sh
python3 port/dreamcast/tools/world_policy_provenance.py \
  /private/r101/ps2-world.re4mesh /private/r101/ps2-world.r4pw \
  --room r101 --source-groups /private/r101/ps2-world.r4sg
```

Inspection writes no files. Omitting `--prepare-original-policy` and setting
it to `0` have identical behavior. The report contains the physical policy
CRC/FNV, mesh identity, exact certificate mismatches, authenticated source
policy CRC when available, and separate group checks against the physical and
reconstructed original policy. A successful inspection command is not an
admission or preparation PASS; inspect the report's explicit status fields.

The converter's independent diagnosis option is:

```sh
python3 port/dreamcast/tools/scenery_data_variants.py \
  /private/r101/ps2-world.re4mesh /private/r101/ps2-world.r4pw \
  --source-groups /private/r101/ps2-world.r4sg \
  --scenery-local-indexed --policy-diagnostics=1 --out /private/new-layout
```

That command keeps the existing conversion/refusal behavior; the option only
explains the failing header field. It is not a recommendation to rerun the
closed performance experiment.

| R4SG offset | Meaning | Ordinary converter comparison |
|---:|---|---|
| 0 | Magic | `R4SG` |
| 4 | Version | `1` |
| 8 | Meshlet count | Actual input R4IM count |
| 12 | Groups per meshlet | `1..8` |
| 16 | Mesh body CRC | Actual input R4IM body CRC |
| 20 | Mesh file bytes | Actual input R4IM total bytes |
| 24 | Policy body CRC | Actual input R4PW body CRC |
| 28 | Group record CRC | Calculated CRC32 of R4SG bytes after the 32-byte header |

The exact group-file length must also be `32 + 16 * meshlets * groups`.
Diagnostics also identify R4PW magic, version, counts, reserved fields, extent
and body CRC. Group strip boundaries, local ranges, corner enclosure and
coverage still use the existing complete validation.

## Explicit original-policy preparation

```sh
python3 port/dreamcast/tools/world_policy_provenance.py \
  /private/r101/ps2-world.re4mesh /private/r101/ps2-world.r4pw \
  --room r101 --source-groups /private/r101/ps2-world.r4sg \
  --prepare-original-policy=1 --out /private/original-policy-control
```

The new directory receives `ps2-world.r4pw`, the supplied `ps2-world.r4sg`
when valid, `policy-report.json` and `SHA256SUMS`. The mesh remains at its
original path; its identity is recorded. Existing output directories and
source files are never overwritten. Failed validation occurs before output
creation. No input certificate, origin map or sidecar binding is modified.

Preparation performs these checks in order:

1. Strictly validate the input source mesh and R4PW, including their actual
   body CRCs, lengths, counts, records and supported source representation.
2. Match the input against the current committed `provenance_certificates.inc`
   using the runtime helper's exact room/extent/count/mesh/CRC/full-file-FNV
   contract. Unknown or ambiguous certificates refuse. There is no caller
   certificate, trusted-CRC or hash-override option.
3. Reverse only the first eight key bytes of each material record through
   the unchanged current `scoped_origins.inc`. This is the runtime's one-step
   original-key lookup; unknown keys remain unchanged.
4. Compute the restored body CRC and require it to equal the certificate's
   original policy CRC. Then write that calculated CRC into the new header.
   Verify every other header byte, all non-key material bytes and every
   placement byte remain exact. A missing or incorrect mapping cannot be
   repaired by stamping the expected CRC.
5. Where an existing historical record matches the complete source-policy
   lineage, also require its pinned original-policy SHA256 and mesh SHA256.
   Current matching records cover r100 and r103. Historical candidate hashes
   are not authority for current physical files. Conflicting matching records
   refuse.
6. If an R4SG was supplied, validate it fully against the unchanged geometry
   and restored policy, then preserve its complete bytes. A group file bound
   only to the remapped physical policy refuses. No secondary rebind is
   performed, and no R4ID/R4TC/PVS/cell proof is changed or transferred.

For r101 and other certificates without a matching historical original SHA,
the report states **“runtime certificate + exact inverse-map restoration;
original archive SHA unavailable.”** It does not claim archived-source byte
identity. An optional `--original-policy /private/known-original.r4pw` requires
full byte equality with the restored result; those caller bytes never authorize
an otherwise unknown certificate. This optional comparison is recorded
separately from a committed archive SHA.

## Using the prepared policy

Both a control and any layout candidate must use the same prepared original
policy and corresponding original textures. The ordinary converter can consume
the prepared policy and preserved source-bound groups with the unchanged mesh:

```sh
python3 port/dreamcast/tools/scenery_data_variants.py \
  /private/r101/ps2-world.re4mesh \
  /private/original-policy-control/ps2-world.r4pw \
  --source-groups /private/original-policy-control/ps2-world.r4sg \
  --scenery-local-indexed --out /private/new-layout
```

Any resulting candidate R4SG binds the **actual restored policy CRC** through
the existing converter. No remapped-key policy is advertised as valid under
the off recipe, and no layout-changing candidate inherits a physical mesh
certificate. The runtime `WORLD_RECT21=0` gate remains unchanged.

**The output is a policy control, not a recreated `ctl-olddata` disc.** Original
texture availability, texture package layout and the matching complete
DATA/pack/resident configuration remain owner staging checks. The tool neither
reconstructs textures nor proves that removing mip22/mip22b/fol24/sg109/res22c
matches the owner's qualified old-data package. All private files and generated
controls remain local and outside Git.

## Public verification

```sh
python3 port/dreamcast/tools/cloud/world_policy_fix/policy_controls.py \
  --out /tmp/world-policy-controls-new \
  --receipt port/dreamcast/tools/cloud/world_policy_fix/policy-receipt.json
```

The controls use existing public Build12 fixtures. They compare complete
converter returns and CLI outputs with the committed pre-fix implementation;
check exact default errors and detailed refusal fields; verify exact key-only
restoration, optional/pinned SHA behavior, stale and physical-bound group
refusals, complete group enclosure validation and unchanged source bytes.

The existing C++ provenance probe is compiled against the real committed
helper/table for public-data refusal controls. Positive unit cases use a
separate explicitly synthetic table under `/tmp`, with the helper header
byte-identical to production. The production CLI has no table override. The
actual committed C++ original-key helper is also checked against every current
mapping and unknown keys. No synthetic positive is reported as a real private
certificate or r101 recovery PASS.

The committed JSON receipt records counts, source/table hashes, compiler and
scope. This lane changes host tools only: it introduces no runtime code, target
cycles or target traffic. No hardware, Flycast or private asset qualification
is claimed.
