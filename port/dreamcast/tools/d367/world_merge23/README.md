# World placement merge estimate

Source-only offline investigation from integration `451bed6f` (2026-10-23).
No game code, room format, recipe, binary or private assets are changed here.
Use `placement_estimate.py` for the whole-placement/material estimate.
`estimate.py` also retains the preliminary meshlet probe for reproducibility;
its one-meshlet context cap is not the placement-merging design.

## Reproduce

1. In WSL, run `inputs.py --resolve /path/to/new-inputs.json`. It resolves the
   existing release recipe DATA order using the existing test11 stager maps.
   The returned manifest pins the actual room file bytes. It is private evidence.
2. With Python and NumPy, run:

   ```text
   python placement_estimate.py --inputs INPUTS.json --room r101 --camera CROSS.log --full-detail --bake-uv --output NEW-REPORT.json
   python placement_estimate.py --inputs INPUTS.json --room r103 --camera FARM.log --full-detail --bake-uv --output NEW-REPORT.json
   python test_placement_estimate.py --inputs INPUTS.json --cross-camera CROSS.log --farm-camera FARM.log
   ```

   Windows Python can consume the Linux manifest through WSL UNC paths.
   Reports use exclusive creation; earlier attempts are preserved.

The actual cross/farm camera frames are 500 through 794, stride 7: exactly 43
views per room. Missing frames are refused. Source-policy CRC and ID count bind
the original ownership table; placement records must remain identical after the
current texture-key remap. Strip groups must bind the original source policy.

## What is estimated

Whole eligible original parts are grouped by a fixed world-space area cell and
compatible final material. A new context must include at least two placements.
It may contain many native meshlets, each capped at 256 corners. Small source
meshlets are packed together within it. Every original part is either replaced
in full or remains on the original path.

Repeated actual mesh instances, unique live-owned props, sky, alpha and
transparent parts remain unchanged. Numeric BIN/common/owner values can restart
in appended source namespaces; they are not unique mesh identities.

The default estimate keeps only single-LOD parts. `--full-detail` separately
tests replacing eligible multi-LOD parts with complete level-zero geometry and
counts the added vertices and triangles. It does not claim pixel identity.
`--bake-uv` estimates baking final UVs into a common float representation rather
than requiring original UV quantization to match. Material keys still include
texture CRC/FNV, dimensions, pass, cull and alpha/flags. The copy bound uses a
24-byte aligned vertex (22-byte payload) for that arm, plus strips/descriptors.
This is a conservative coexistence bound, not a proved replacement-package size.

Reports separately count selected meshlets, nonzero transform meshlets,
emitting meshlets, placement+part contexts, placements, transformed corners and
submitted strip triangles. A lower meshlet count is not automatically fewer
part contexts or fewer milliseconds.

## Decision and limits

GO requires at least 40% fewer selected part contexts at the cross, at most 10%
vertex growth, and a separately proved memory fit. No tested arm currently
meets that geometry gate. Current best context reduction in the full-detail,
baked-UV 2/4/8/16 m cross sweep is approximately 4.43%, with 62.92% vertex growth.
This result applies to the specified ownership-safe fixed-cell packing method;
it does not rule out every future world batching design.

The static reference reuses the established `worldlean/sgprice.py` geometry
model and agrees with its transform totals in every sampled view. That model
omits placement-level world_out, sky-far overrides and live dynamic/gameplay
gates. It is neither a fresh Flycast replay nor console timing. Regrouped opaque
submission order, target rounding, vertex encoding, memory and look acceptance
remain untested. No runtime implementation is admitted by these reports.

r100 assets are outside the merge scope and unchanged. Since no runtime code
has been built, this does not claim a new s30 heap or movie result. A future
implementation still needs default-off image identity, KOS48, s30 340/340 with
heap_before, TEXCHK, VRAM, CAST-GC, GDEMU and look checks before console QA discs.
