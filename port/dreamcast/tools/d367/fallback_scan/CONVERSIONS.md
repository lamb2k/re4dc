# Build 29 offline light conversion

`convert.py` changes selected **converted source ModelData streams** into the
existing FE/v3 meshlet representation with baked RGB565 records. Two independent
data options default to zero:

| Data option | Selection | Data change |
| --- | --- | --- |
| `--fold-light-scale=1` | Enabled clamp-diffuse lighting, constant ambient/material colour, a material RGB × TEV scale channel below 255 | Fold the captured material/TEV scale and lighting into each record's RGB565 colour. |
| `--bake-probe-decline=1` | Captured probe mode is enabled, but actor class/Ganado toggle, vertex-colour mode, diffuse mode, scale or probe validity declines it | Bake the explicitly captured pose/light response into the same RGB565 field. |

Without either option, including explicit `=0`, the converter copies the input
**byte for byte** and does not parse the model or context. Each output is a new
file. The input is never overwritten. If an enabled option finds no matching
trigger, the selected part stays unchanged.

The runtime adapter is separately gated by `FALLBACK_SCAN29=1`, default zero,
with `NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1 MODEL_STREAM_FIX=1 NATIVE_ACTOR_PRELIT=1`.
The Make fragment checks all four prerequisites. `MODEL_STREAM_FIX` preserves
the FE decoder even for static geometry or a lazy-skinned source view whose
arrays are refreshed after a first refusal; it also prevents cached GX plans
from consuming preencoded data. The existing `NATIVE_ACTOR` checks require
the D349 renderer stack and its PVR stream owner. The new adapter does not
require Build 25's `ACTOR_LIGHT_FAST_ONLY`. When `ACTOR_LIGHT_FAST_ONLY=1`, that
existing policy still owns lighting; Build 29 does not read its new bake fields.

## Why a stream bake, rather than a material-header edit

The native ModelData material header contains material flags, texture indices,
alpha reference and specular parameters. Material RGB, diffuse mode and TEV
scale come from the live `SourceLighting` record captured by the source bridge;
they are absent from the converted BIN. Editing a spare-looking material byte
would neither remove `build_lights`' scale test nor establish the source-selected
light state. The probe additionally depends on actor kind and live basis/probe
validity. A BIN alone cannot tell whether it is Leon or a Ganado.

This implementation reuses `native_actor_fast.cpp`'s FE/v3 `kHasBake` record and
120-byte `BakeBlock`, rather than introducing a new package, geometry renderer,
registry or per-vertex light evaluator. Build 25's runtime light-only policy and
the existing character-bake tooling are complementary: this narrower step
changes the actual converted source stream that an ordinary source ModelData
draw already owns.

`state=0x46423290`, `clamped=0xf0290000 | data_flags`, and a final float sentinel
`291.0` identify this policy inside the existing BakeBlock. Normal renderer
bakes have state zero or `palette_hash(...) | 1`, hence every populated normal
state is odd; their `clamped` word is zero or one. The even nonzero state and
nonboolean flags cannot collide with a valid existing bake. Unknown/malformed
tags do not acquire this policy.

## Admission and supported ownership

Input must be little-endian converted ModelData, with its existing big-endian
GX index stream. The source declaration must say `PS2-converted-ModelData` and
`ownership: source-model`, include the exact SHA-256 of the extracted member,
and identify the private conversion provenance. The declaration is an owner
assertion; a ModelData header does not encode whether geometry originally came
from PS2 or GC.

This step currently supports ordinary source-path BIN/ETM/SMD ModelData. It
**does not update RE4NMR, RE4CP, compiled character headers, the coarse actor
transaction proof, or GC-ASSET source certificates**. Those owners have
independent source-fact and stream-format contracts; the coarse preflight
explicitly excludes CI/bake streams. Do not graft a BIN whose bytes are inputs
to such an external proof. Running the converter on a loose extracted member
does not certify its owner. Restaging a source-only package is the useful
supported scope for this version; owners with certificates need a compatible
extension in their existing packer before they can adopt the data option.

Every selected part needs explicit captured lighting and pose context. The
converter refuses morph models, missing matrices, nonstatic vertex colours,
animated material policy, nonopaque blending, per-vertex alpha, nonzero source
material flags (including mask/specular/bump cases), zero reference colour
channels, nonfinite values, protected-array aliases, or a bake that does not
fit its original stream allocation. An input FE stream is refused: convert the
original GX stream, never repeatedly bake an already converted palette.

The special Leon and headroom markers (`normal_matrix[3]` or `[7]` equal to
`1.0e30f`) are refused both in the capture and in live admission. Their existing
normal-basis, headroom and debug-toggle policy stays with its owner. A non-Leon
`basis_valid=false` does not itself predict a probe decline: production only
inverts the part basis for the Leon marker. Ganado `ganado_mode=0` prevents
probe eligibility only when captured `ganado_lit_toggle=true` corresponds to
the compiled recipe; the mode is ignored when that toggle is absent.

The FE stream retains every ordered GX triangle, corner position/normal/UV/
colour index and degenerate triangle. It does not decimate or change vertex
positions, normals, bones, weights, bind data, material headers or source
animation. Original source arrays and every byte outside selected stream
allocations are identical. Header bounds follow the existing converter's
bind-space sphere convention, rounded outwards. Meshlets have at most 128
records and 1024 indices, and each emitted three-index strip retains the
original winding. RGB565 adds two bytes per unique record within that existing
allocation; there is no package-size or resident-byte increase.

## What the approximation changes

The bake evaluates the captured pose's normalized normals against explicit
directional lights and captured ambient/material/TEV values. The owner must
derive the directions and effective colours from the actual selected lights;
point-light attenuation may be sampled at the part centre. These values cannot
be reconstructed from the BIN or inferred from a QA counter alone.

The output differs from the old exact evaluator in these stated ways:

1. **RGB precision:** colours are quantized to RGB565, then expanded by the
   existing `pass_baked`. The axis-light synthetic fixture differs by at most
   seven channel values. Other scenes have additional approximation error.
2. **Pose and light direction:** the per-record spatial light pattern comes
   from the explicit captured pose and directions. Current animation still
   moves the original geometry using its original bones; the baked lighting
   pattern does not follow animated normal/direction/attenuation changes.
3. **Live light colour and flashes:** each draw computes a per-part RGB energy
   ratio from the current selected lights, ambient and material/TEV values.
   Clamp-diffuse directional energy uses the existing quarter-Lambert mean;
   diffuse-none uses one and signed diffuse uses zero. Signed diffuse therefore
   tracks ambient/material energy, not changing signed directional terms.
   This ratio scales the old RGB565 palette and preserves a live colour
   response, but cannot reproduce changed shadows, distance attenuation,
   spatially varying flashes, saturation recovery or directional changes.
4. **Static per-vertex RGB:** the bake uses each source colour index. The live
   gain uses the captured mean colour for vertex-sourced channels. A palette
   that can change at runtime is unsupported; do not assert it is static.
5. **Crowd/rigid flat lighting:** an admitted tagged part keeps its baked
   per-record colours instead of subsequently flattening those colours in the
   crowd/rigid approximation. Crowd distance classification stays in its
   existing path; the level-zero-only geometry tradeoff is described below.

There are two additional costs to include in a whole-view comparison. Tagged
streams contain only the unchanged original level-zero triangles; they do not
request runtime LOD generation and do not generate backface cones. A baseline
that builds or selects reduced LODs may therefore transform and submit less
geometry. Also, `model_bridge.cpp`'s existing static object batch builder
accepts only GX streams and refuses a preencoded FE member. Such groups draw
their original parts separately, so eliminating exact lighting can increase
setup/submission work relative to a cached merged group. These are reasons to
measure the complete candidate view, not to infer a frame gain from the
removed exact-light vertex count alone.

Constant alpha is taken from the **current** draw, not the bake. Source UVs,
texture selection, depth, culling and part ordering remain in their existing
paths. Admission rejects a live blend/material/alpha policy it cannot handle.
If lighting enablement, vertex-colour source or diffuse mode changes, or the
gain is invalid/out of range, the original selected lighting evaluator runs.
The tagged palette remains immutable, so a later compatible draw can use it
again. A fallback in an unsupported live state is deliberate; this is not a
claim that every possible material state has been eliminated offline.

## Private-data commands

Run from the repository root. Keep all data and receipts in a private generated
directory. The examples use a converted room DAR already produced by the
existing pipeline; raw source-endian or compressed game archives are refused.

```sh
SCAN=port/dreamcast/tools/d367/fallback_scan
PRIVATE=/absolute/private/build29
SOURCE=/absolute/private/disc/st1/r103.dar
mkdir -p "$PRIVATE"

python3 -B "$SCAN/package.py" list "$SOURCE" > "$PRIVATE/r103-members.json"
```

Choose the exact key printed by `list`, and verify that this member is actually
a source-only PS2 conversion and is not covered by an external actor/GC proof.
Keys are stable within the package and include DVD/archive/SMD or ETM identity;
they are not guessed model IDs. A common top-level key shape is
`package/DVD[0]/ARC[0x4]`; use the actual inventory value.

```sh
MEMBER_KEY='package/DVD[0]/ARC[0x4]'
python3 -B "$SCAN/package.py" extract "$SOURCE" "$PRIVATE/source.bin" \
  --key "$MEMBER_KEY" --receipt "$PRIVATE/member.json"

python3 -B "$SCAN/convert.py" "$PRIVATE/source.bin" "$PRIVATE/folded.bin" \
  --context "$PRIVATE/bake-context.json" --fold-light-scale=1 \
  --receipt "$PRIVATE/conversion.json"

python3 -B "$SCAN/package.py" graft "$SOURCE" "$PRIVATE/folded.bin" \
  "$PRIVATE/r103-folded.dar" --member-receipt "$PRIVATE/member.json" \
  --conversion-receipt "$PRIVATE/conversion.json" --receipt "$PRIVATE/graft.json"
```

For the independent probe candidate, use `--bake-probe-decline=1` and different
new output/receipt paths. Both flags can be supplied for one conversion. Verify
the candidate with the scanner and its matching context, then let the existing
disc staging process install the new DAR at the same relative disc path. Do
not publish private models, contexts or output packages to Git.

The extraction receipt binds the whole package hash, member key, exact member
offset/extent and member hash. The conversion receipt binds both member hashes,
context hash and selected stream hashes. Grafting checks every receipt,
restricts differences to the selected original stream ranges, rediscovers all
member boundaries and retains the hashes of every other model. It reuses
`ps2_objects.remap_native_tables` to check the unchanged NTR texture-identity
and ESQ effect tables, their CRCs, payload lengths and referenced bytes. Since
no layout changes, offsets and sidecars remain byte-identical. A sidecar that
points into a changed stream is refused. This tool does not rebuild transport
or source certificates that live outside the DAR/DRS.

### Required capture context

`bake-context.json` uses a different schema from the scanner's partly known
context template because a bake requires complete lighting/pose inputs. The
following is the **synthetic test fixture's** context, not a suggested barn
capture. Replace the hash with `member.json`'s member hash only after collecting
and verifying the actual values. Do not fill missing data with these examples.

```json
{
  "schema": "re4dc.fallback29.bake/1",
  "source_sha256": "EXACT_EXTRACTED_MEMBER_SHA256",
  "source_kind": "PS2-converted-ModelData",
  "ownership": "source-model",
  "provenance": "owner's existing PS2 conversion receipt and source member identity",
  "pose_space": "source-normal-space",
  "parts": [{
    "index": 0,
    "static_vertex_colors": true,
    "normal_matrices": [[1,0,0,0,1,0,0,0,1]],
    "render": {"blend": 0, "alpha_state": 73, "material_animation": false},
    "lighting": {
      "enabled": true, "ambient_vertex": false, "material_vertex": false,
      "diffuse": 2, "ambient_rgb": [64,64,64], "material_rgb": [128,128,128],
      "tev_scale": 1, "actor_probe_mode": 2, "model_id": 18,
      "leon_marker": false, "headroom_half": false,
      "ganado_lit_toggle": false, "ganado_mode": 0,
      "basis_valid": true, "probe_valid": true,
      "directional_lights": [{"direction": [0,0,1], "color_rgb": [64,64,64]}]
    }
  }]
}
```

Matrices are row-major 3×3 transforms from each source normal palette entry to
the space of the supplied light directions, one per referenced weight/palette
entry. The converter validates each referenced normal's palette index. The
capture must describe the pose chosen for the lighting approximation; it is
not a replacement pose for rendering. `directional_lights` has at most eight
entries. No executable snippets, dynamic expressions or arbitrary offsets are
accepted in the context.

## Reproducible fixture proof

```sh
python3 -B port/dreamcast/tools/d367/fallback_scan/test_convert.py -v
python3 -B port/dreamcast/tools/d367/fallback_scan/test_package.py -v
python3 -B port/dreamcast/tools/d367/fallback_scan/test_runtime.py -v
env ASAN_OPTIONS=detect_leaks=0 \
  python3 -B port/dreamcast/tests/test_model_stream_dispatch.py -v
env SCAN29_SANITIZE=1 ASAN_OPTIONS=detect_leaks=0 \
  python3 -B port/dreamcast/tools/d367/fallback_scan/test_runtime.py -v
```

The runtime fixture includes the **actual complete** `native_actor_fast.cpp`,
links the real source-light evaluator and geometry clipper, calls production
qualification and FE detection, and submits full packets through the real
meshlet decoder and emitter. Only platform/packet owners are host fixtures.
It covers new knob off/on, FAST_ONLY off/on, MEMSET_LEAN off/on and NO_CLEAR
off/on. It proves old scale/probe decline plus exact lighting, the admitted
baked path's removal of those operations, exact emitted geometry/UV/alpha,
bounded fixture RGB565 error, flash response, vertex-colour baking and fallback
without offline-palette mutation. FAST_ONLY on gives paired identical packet
outputs and never reads Build 29's new dispatch fields.
An additional `LEON_LIGHT_HEADROOM=1` composition proves both special markers
retain their existing evaluator and do not overwrite the offline palette.

Conversion tests prove independent options, absent/zero byte identity,
topology/array preservation (triangles, quads, odd/even strips, degenerates and
meshlet splits), constant and varying CI layouts, signed/unsigned UV layouts,
tag noncollision and unsafe-input refusals.
Package tests cover top-level DAR BIN, DRS SMD and ETM members, NTR/ESQ
integrity, refusal of changed sidecar targets, stale receipts, nonstream
changes and overwrite attempts. Leak checking is disabled in the ASan command
because this environment prevents LeakSanitizer from reading `/proc` under its
trace wrapper; address and undefined-behaviour instrumentation remain enabled.

These are synthetic implementation and target-build gates. They establish no
private barn model counts, visual acceptance or console milliseconds. The
owner must run the scanner, capture real source context, compare the selected
views and moving light/animation cases, then return DFA/QA and console timing
for the candidate data flags before any default changes.
