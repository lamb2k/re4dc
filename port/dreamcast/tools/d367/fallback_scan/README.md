# Build 29 offline fallback scanner

`scan.py` reads an extracted/composed **native converted disc tree**. It does
not extract a retail disc, execute game code, modify inputs, or infer which
assets the console actually drew. Python 3.10+ and the repository's existing
standard-library format tools are sufficient. No game data belongs here.

The scanner keeps three different facts separate:

* A package contains a model, material, source primitive or stored meshlet.
* Its bytes, resolved recipe and explicitly bound runtime context satisfy a
  fallback condition, or leave that condition unknown.
* A console capture actually counted the fallback. This is a separate input
  to the owner's analysis; static inventory does not establish it.

## Run on private converted data

From the repository root, use a new output directory outside the disc tree:

```sh
python3 port/dreamcast/tools/d367/fallback_scan/scan.py \
  /private/disc-tree \
  --out /private/build29-scan-before \
  --knobs /private/exact-image/resolved-knobs.txt
```

The default room selection is `r100` through `r11f`. It is a selection of room
IDs, not a claim that every ID has an active route package. Supply the actual
route when known, or begin with the reported barn case:

```sh
python3 port/dreamcast/tools/d367/fallback_scan/scan.py \
  /private/disc-tree \
  --out /private/build29-r103-before \
  --rooms r103 \
  --knobs /private/exact-image/resolved-knobs.txt \
  --strict
```

`--input /private/generated/ganado_cast_runtime.h` (repeatable) adds generated
compiled cast headers or standalone packages not carried as separate disc
files. Such input identities are `@input/<basename>`; duplicate identities
are rejected. A compiled header's exact array prefix is retained as
`source_info`. Its arrays can include alternative appearances; do not sum
them as simultaneously drawn actors.

Omitted recipe values remain `unknown`. The scanner does not execute shell
text in a knob file or silently substitute Makefile defaults. Hashes of the
resolved knob file and every recognized input are included in the report.

Exit codes: **0** report written; **1** report written but `--strict` found
incomplete coverage; **2** invalid invocation/context or an output error.
Without `--strict`, rejected packages still produce an **INCOMPLETE** report,
never a successful inventory for their contents. Inputs are never written.
Output must be a new directory, and input symlinks may not escape their
explicitly supplied tree.

## Build 36 selection and legacy inventory (default off)

Add `--scan36=1` to enable the Build 36 repairs. With the option absent or
`--scan36=0`, the existing scanner's nine reports and process results remain
unchanged, including its existing refusals. No game code or input bytes change.

```sh
python3 -B port/dreamcast/tools/d367/fallback_scan/scan.py \
  /private/composed-disc-tree \
  --out /private/build36-r103 \
  --rooms r103 \
  --knobs /private/exact-image/resolved-knobs.txt \
  --scan36=1 --strict
```

Use the **composed final disc tree** and its exact resolved recipe. A later
data set replaces the whole `dc/tex.pak` at that path. Runtime lookup then
prefers an eligible packed member over loose data. `TEX_RESIDENT` determines
the loose flat/bucket path; `QUALITY_ASSETS` can select a current room's
`texlow` path and bypass the pack. Unknown recipe or live quality state keeps
presence and palette predicates conditional. This is file availability,
not a prediction of texture-cache residency or successful upload.

If the final pack has not yet been composed, declare **only its actual pack
replacement order** explicitly. Each supplied file replaces the entire
previous pack; omitted keys are not inherited from it:

```sh
python3 -B port/dreamcast/tools/d367/fallback_scan/scan.py \
  /private/composed-loose-and-room-tree \
  --out /private/build36-explicit-pack-order \
  --rooms r103 \
  --knobs /private/exact-image/resolved-knobs.txt \
  --scan36=1 \
  --texpak-layer /private/earlier-data-set/dc/tex.pak \
  --texpak-layer /private/later-data-set/dc/tex.pak \
  --strict
```

This does not compose loose files or room assets. Arbitrary packs found by
directory discovery or `--input` have no declared destination/order and are
reported as unselected. Repeated keys **inside one pack index** remain invalid.
A malformed or unreadable final pack is rejected and its unresolved keys
remain unknown; an earlier replaced pack does not regain authority.

`report.json/texture_selection` records physical variants, definite and
conditional keys, selected/possible/shadowed sources, hashes, layer numbers,
member offsets, and predicates for all referenced keys. The headline texture
count means definitely present keys, not payload variants or resident handles.

Native `etc/emleon00.esl`–`emleon07.esl` and `etc/omake00.esl`–`omake02.esl`
can bind global ModelData archives through the current source loader tables.
The mapping retains exact list/record/hash, player and Ashley-costume
alternatives, archive path/hash, and scanner model keys. Lists may remain
selected on room revisits. All BIN members are **archive-load candidates**,
with unknown instance counts and active appearance. Missing targets, mutable
non-DLL filenames, core-object IDs, unsupported lists and ambiguous identities
stay visible in coverage. Source-less GLP1/compiled replacements still need
owner context. `room_membership` carries the full provenance and source-table
hashes; enabled `details.tsv` and `barn.tsv` add a `membership` column.

Explicit context and `--room-list` entries override automatic candidates for
the same room. The unfilled context template keeps automatic rooms in
informational `room_candidates`, outside `rooms`, so replaying it cannot turn
conditional list evidence into verified owner context.

Ordinary legacy R4IM v1/v2/v3 packages without R4PW can provide strictly
validated **geometry-only inventory**. Their material/pass/cull/texture keys,
placement counts and selected LOD remain unknown; coverage is `partial`, so
`--strict` exits 1. PS2 owner `0x50`, physical variants, unknown extensions,
and modern bundles still need their required policy. A present malformed
sidecar, directory or dangling symlink is a refusal, not an absent optional
policy. No actor fallback predicates are applied to legacy world geometry.

## Outputs and denominators

| File | Contents |
|---|---|
| `REPORT.md` | Ranked potential work, coverage and interpretation |
| `by-room.tsv` | Parts/vertices/corners/meshlets by room, reason and status |
| `by-model.tsv` | The same, retaining exact source/model identity; greatest vertex population first within each room |
| `details.tsv` | Part/material conditions, explicit unknowns, and stored meshlet inventory/unique-record conditions |
| `barn.tsv` | All `r103` probe/scale/colour/basis/fourth/exact rows, including unknowns |
| `spawns.tsv` | Native ESL enemy-list candidates, with list/index/room/ID/type/position; active state is unknown |
| `coverage.tsv` | Scanned, rejected and missing inputs/room bindings |
| `report.json` | Machine-readable rows, hashes, knobs and `model_inventory` including source member ranges, material fields, placements and meshlet metadata |
| `context-template.json` | Hash-bound identity template with empty lighting/render context |

`predicted` means the supplied condition and relevant dispatch facts are
resolved. It still describes a potential draw. `candidate` means a positive
condition has an unresolved recipe/admission/selection prerequisite. `static`
is a property of supplied bytes. `unknown` means required information is
absent. `inert` means the relevant path is disabled or bypassed by the stated
recipe/context. `clear` means this particular condition is false under the
available facts. `inventory` is a count, not a fallback prediction.

Rankings retain `predicted`, `candidate` and `static` as separate rows. They
exclude unknowns and duplicate meshlet detail rows. A meshlet inherits its
parent part/material predicates; `scope=meshlet` additionally resolves its
own record reuse where the bytes permit it. Reason totals are **not additive**:
one part can appear under several conditions.

`vertex_basis` states the denominator. Original GX ModelData counts distinct
source corner tuples; runtime conversion can duplicate these across
meshlets. FE streams count stored records. World part totals use level zero;
meshlet rows retain all LOD alternatives. Instance counts are supplied facts,
not multipliers. Source fallback and replacement packages can coexist.
Visibility, selected LOD, active appearance, repeated submissions and drawn
ticks remain runtime facts. No static total is a measured cache miss or a
whole-frame saving. The scanner itself adds **0 runtime cycles, loads, stores,
code bytes or stack bytes; MODELLED frame delta 0 ms**.

## Bind the barn capture to real sources

1. Scan the exact composed disc and build assets. Keep its image/build
   identity and resolved knobs with the report. Inspect `report.json` model
   placements and `spawns.tsv`; these locate candidates without inventing a
   “pitchfork”, “hay” or “barn prop” label.
2. Capture the same room with `FALLBACK_AUDIT29=1` and the drawing audit. Its
   `F29A`/`F29P`/`F29L` rows identify the runtime model kind/ID/type, model-info
   ordinal, source-part byte offset when valid, geometry counts, stream
   capacity, source texture selector, material/channel state and selected
   lighting path (`F29P` includes the actual exact-light `verts` total). The
   audit retains a bounded set of rows and reports spills
   and context changes. A room total is not a timestamp-matched per-part
   light vector capture.
   Actor totals are live room accumulations and can include the current
   partial tick when QA pauses; the core `FA29` totals are sealed at the last
   completed tick. Do not divide `F29P` calls/vertices by the core draw count
   or equate them with the last-drawn-tick DFA rows. Actor lifecycle serials
   separate reused runtime addresses internally; they are not source asset
   identities and are not emitted as provenance.
3. Match the runtime owner to an exact source model using the package/member
   provenance, model-info/part identity, counts, texture selector and placement
   or owner inspection. The template includes `source_offset`,
   `source_length`, position/normal counts, `part_offset`, `stream_bytes`,
   material bytes and `source_key_texture_bytes` for native ModelData. The
   latter are the first two bytes of the runtime source key; byte 2 can carry
   live fog state. **Model ID alone is insufficient.** A native registry can
   replace an ordinary source draw, so establish which path owns the part.
4. Copy the template to a separate context file. Add the verified label and
   `rooms`, then only the lighting/render facts actually established by the
   capture. Preserve the complete source file SHA256 and exact model `key`.
   Do not fill unavailable facts with zero or copy the latest light context
   across a row whose context changed. The scanner rejects stale hashes,
   unknown model/part keys and invalid value types.
5. Rerun with `--context /private/build29-bound-context.json` into another new
   directory. Compare `a_probe_miss`, `a_lit_scale` and `a_lit_exact` separately.
   A declined actor probe can still be serviced by generic `build_lights`.
   Bind the Ganado, attached tool, hay and nearby props independently. The
   resulting exact source keys and the measured audit populations explain
   which of them account for the barn spike; this repository contains no
   private-data verdict about those models.

The context schema is `re4dc.fallback29.context/1`. Each source has `path`,
`sha256`, `models`; each model has the exact `key`, optional `label`, `rooms`
and verified runtime `model_kind` / `model_id`, plus `parts` indexed by scanner
part index. With a kind, these are the raw captured `cModel` bytes: only kind
0 is eligible as an enemy for the Ganado probe. Without a kind, `model_id`
must mean `re4dc_actor_model_id` (enemy ID, **-1 for a non-enemy**), not an
unqualified object ID. A kind-1 accessory with ID `0x12` is not a Ganado.
Each part can supply these optional fields:

| Object | Fields |
|---|---|
| `lighting` | `enabled`, `ambient_vertex`, `material_vertex`, `diffuse` (0/1/2), `material_rgb`, `ambient_rgb`, `tev_scale`, `leon_marker`, `headroom_half`, `basis_valid`, `probe_valid`, `ganado_mode`, `leon_mode` (0/1/2/3), `significant_lights`, `keep_lights` |
| `render` | `uv_offset`, `blend`, `alpha_state`, `flat`, `cone_available`, `static_class`, `chunk_unique`, `chunk_normal_unique` |

RGB values are integer byte triples. `headroom_half` refers to the separate
normal-matrix headroom marker, not the Leon source-light marker. `basis_valid`
only establishes the generic inverse-basis rejection for a Leon-marked part
with `LEON_SOURCE_LIGHT` enabled. `significant_lights` is the count **after
distance/attenuation/significance selection**, not popcount of the raw light
mask. `keep_lights` is the actual class policy (0 means no keep cap).
`flat` means the selected constant-light pass; whether it rewrites vertices
also depends on lean/MOVCA flags and vertex alpha. Missing fields remain
unknown. Static vertex-colour storage does not prove a live channel uses it.
In `F29L.ctl`, bit 24 captures the Leon source-light marker and bit 25 captures
the headroom-half marker. `changes=0` only means the emitted material,
ambient, TEV, channel controls and light mask stayed equal. It does not prove
unchanged pose, modelview/normal matrices, light positions, directional light
vectors, per-light colours or attenuation. Those require a separate captured
conversion context; the attribution rows alone cannot establish a static bake.
With `LEON_LIGHT_TOGGLE` enabled, captured Leon modes 0/3 select a constant
pass before probe/generic dispatch; an unknown mode keeps positive light
conditions conditional. `ACTOR_LIGHT_FAST_ONLY` bypasses the flat-rewrite
counter as well as the old exact evaluator.

An optional `--room-list` supplies explicit asset membership without light
facts. Its schema is `re4dc.fallback29.rooms/1`:

```json
{
  "schema": "re4dc.fallback29.rooms/1",
  "rooms": {
    "r103": [
      {
        "path": "em/OWNER-SUPPLIED.drs",
        "model": "EXACT-KEY-FROM-TEMPLATE",
        "sha256": "COPY-THE-ACTUAL-64-HEX-SHA256",
        "label": "OWNER-VERIFIED-LABEL",
        "instances": 1
      }
    ]
  }
}
```

This is a schema illustration, not an actual game filename or valid hash.
In the default mode, global actors remain `unassigned` until package identity
or an explicit list binds them. Build 36 adds the conditional native-list
mapping described above. An ESL ID alone never establishes archive identity
or a visible actor.

## Format coverage and refusals

`formats.py` uses the existing runtime/exporter layouts and, where available,
their owning validators:

* LE ModelData versions `0x20010801` and `0x20030818`, with BE GX primitive
  words or an existing FE/v3 stream. Native DAR/DRS/tagged archives include
  BIN, named ETM BIN members, SMD placements/local BIN tables, ESL, and native
  R4NREF/R4PREF texture references. Absolute member byte ranges support
  same-size extraction/grafting without changing archive offsets.
* RE4NMR v1/v2 registry descriptors/geometry/textures, RE4PL08 cast packages,
  GLP1 streamed Ganado levels and generated compiled cast byte-array headers.
  Array extents, FE index/strip counts and applicable CRC/FNV digests are
  checked. Source identity certificates are inventory; this is not a full
  proof of runtime source/certificate admission.
* Prelit R4IM v2/v3 and R4PW v1, append-index v3 layouts, SLI1/SDS1, v4 split
  records and SDO3 repeat records. Variant adapters use the existing strict
  scenery tools; SDO3 is decoded in memory before ordinary geometry checks.
  Physical layout and lineage stay in the report. Known runtime alternate
  names use the canonical `ps2-world.r4pw`; source CRC/extent binding is
  checked against the canonical world mesh. Missing lineage gives incomplete
  coverage. This does not qualify PVS/interior/source-group companion files,
  owner/movie gates or render selection.
* RE4DCTX v2 loose textures and `tex.pak`, palette metadata and sorted
  `dc/resident.bin` room/key records. Presence never proves a live resident
  texture handle. Native ESL has no header; the reader applies its established
  32-byte record extent and 256-entry bound.

Unknown world extensions/appended runtime tables, FE LOD/pending streams
outside these adapters, source-endian/compressed rooms and corrupted inputs
are rejected visibly. Unknown ordinary `.bin` files are ignored unless their
ModelData version identifies them; unsupported expected package suffixes are
coverage failures. Discovery does not claim every file in the tree is a
supported render asset. Missing room inventory is explicit.

The converter's independent default-off flags and stronger source-light/pose
context are documented in `CONVERSIONS.md`. A Build 29 tag plus
`FALLBACK_SCAN29=1` is only a **candidate**: live alpha, material, mask, channel
mode, TEV or gain guards can retain the old renderer. The scanner deliberately
keeps the ordinary fallback conditions in those reports.

## Synthetic proof

```sh
python3 -m unittest discover \
  -s port/dreamcast/tools/d367/fallback_scan -p 'test_scan.py' -v
```

Fixtures contain no game bytes. They use the existing registry, PL08, GLP1,
world, variant and texpack writers, plus small native ModelData/ESL/archive
records. Controls cover checksums and inner digests, corrupt offsets/indices,
mixed LE/BE fields, exact member ranges, source-lineage mismatch, recipe and
lighting unknowns, probe decline versus generic success, live bake refusal,
chunk semantics, stale-context refusal, missing coverage, symlink rejection,
deterministic reports and unchanged input hashes.

Build 36 adds 101 tests (texture selection 40, native membership 28, legacy
worlds 13, end-to-end reports 20) and an actual baseline/absent/zero CLI gate:

```sh
python3 -B -m unittest discover \
  -s port/dreamcast/tools/d367/fallback_scan -p 'test_*36.py' -v
python3 -B port/dreamcast/tests/test_texpack_index.py
python3 -B port/dreamcast/tools/cloud/build36/verify_identity.py \
  --base bb5f18e0e3b3fac4c76bd42d0c9d8107385c568c \
  --out /tmp/build36-off-identity-new.json
```

The identity checker needs Python with `hashlib.file_digest` and tarfile's
`data` extraction filter (the checked Python version is in its receipt).
It compares all nine raw report files and process results across seven
non-vacuous scenarios, checks input hashes, and refuses changes outside this
offline scanner/checker and its hand-back. Use a fresh receipt path. The
committed receipt is in `tools/cloud/build36/receipts/off-identity.json`.
