# Water/rain24 read-only selector and coverage tools

This is a tools-only unit, based on fb254e82. It changes no runtime, converter, recipe, resident TSV or private asset. `waterres24-private-off` is a required audit-option label, not a new enabled data set. No overlay is emitted. Historical guard11 is an unresolved old observation, not a proven water cause. The first-stage river room remains unknown.

Run the host controls from the repository:

```
PYTHONDONTWRITEBYTECODE=1 python3 port/dreamcast/tools/d367/water_rain24/test_audit.py
```

C++ fixtures/executables and synthetic texture/record inputs live only in a unique `/dev/shm` directory. The test extracts the actual `WaterPs2Pattern` function, mocks only its input storage, and compiles FLIP1/8/16 with host g++. It compares13,326 vectors across duration boundaries, zero/sparse tables, clamped Frames, null animation, rates0/1/32/36/42/128/255, ptn0 and u32 multiplication wrap. Exact reachable-pattern witnesses cover all u32 ticks by modular arithmetic; short exhaustive and deterministic random ticks supplement that proof. Removing FLIP or widening the product must fail. Host arithmetic/storage tests do not qualify SH4 execution or target layout.

`audit.py` takes a private JSON manifest and creates a **new** JSON report:

```
PYTHONDONTWRITEBYTECODE=1 python3 port/dreamcast/tools/d367/water_rain24/audit.py /private/manifest.json --output /dev/shm/new-report.json
```

Manifest schema1 requires `option="waterres24-private-off"`, `selector_sha256` (exact extracted function), `source_contract` (the six full-source hashes returned by `source_contract()`), `rooms` (a nonempty subset of0x10c/10d/10e), `renderer_level` (the actual renderer's0/1/2 value, not the UI FX_LEVEL setting), `flip` (>0), `row_scope`, and `entries`. Scope must include every textured actual ext-table row in those rooms with row.level>=renderer_level, regardless of current area/SST activation. Missing rows are refused; f7 is untextured and contributes no package. This union covers the declared quality level's possible areas/display states, not only the sampled view. The caller must separately establish which renderer value the actual build uses.

Each entry supplies actual `row_index`, `source_eff`, `ps2_eff`, `converter`, `conversion_receipt`, and `packages` (source key to file reference). Each reference is `{file,sha256,span_sha256,offset?,length?}`: the full original file and exact borrowed span are hashed. Input files are read once per audit. Source EFF must be original big-endian GC layout; PS2 EFF must be little-endian v0xB. Counts, offsets and descriptor/animation/payload bounds are checked. The established source TPL parser and actual `image_identity` function determine source keys. PS2 descriptor, texel and CLUT hashes are recorded separately; animation header/pattern/duration bytes are pinned too. No frame/key is inferred from a filename or log difference.

The private conversion receipt is schema1 with profile `fx_ps2_pack.py:frame-mod-v1`, `source_eff_sha256`, `ps2_eff_sha256`, `converter_sha256`, and `bindings`. Each binding has `source_key`, numeric `texture`, `ps2_frame`, exact `ps2_picture` record returned by `eff_texture(...,ps2=True)`, and `package_sha256`. The converter reference must match the pinned existing fx_ps2_pack.py source. Every selected frame must map to its existing converter rule (source frame modulo PS2 descriptor count), and its exact supplied package must match the receipt and existing native-header CRC/bounds convention. No conversion is executed or reproduced. Missing packages or changed PS2 descriptor/texel/CLUT pins fail. Existing library metadata alone is insufficient input.

The report always says source owner binding UNPROVEN, conversion not replayed, origin not admitted, current loaded payload binding false and resident memory not qualified. A self-consistent receipt does not prove that a room loader actually selects these EFF files, that the converter produced those bytes, or that their origin has been independently reviewed. Parent/archive membership and exact loader/pack selection still need separate authenticated evidence. This unit does not grant GC-ASSET or PS2 provenance acceptance. Without that evidence, private real-data inventory results remain provisional even if all consistency checks pass.

The computed `required_resident_records` use **source descriptor** width/height/format, not packed format or a VRAM cost estimate. Optional `resident` references (`before`, `candidate`, `remap_before`, `remap_candidate`) check a separately prepared candidate. They never create one. Every old record must survive byte-for-byte, all selected required records must exist, no unrequested additions/conflicting keys are accepted, records remain sorted/deduplicated, remap bytes remain identical, and zero padding is terminal and512-byte aligned. Without a candidate, coverage is NOT_RUN; with one it can only be RECORD_COVERAGE_ONLY. Neither proves actual preload admission, working-set completeness, no rereads, palette/slot/contiguous availability or memory benefit.

Controls include25 manifest/ancestry/package/missing-required-key negatives and9 independent record/remap/padding/order negatives. All inputs are synthetic; no private real texture, overlay or TSV was generated or promoted. A future root-owned data trial still needs original-source ancestry, actual selector/loader binding, complete working set, exact current programme/profile, zero refusal/guard/no-contiguous/rereads, KOS/H2/TEXCHK/census, progression and matched water stills before any recipe or appearance decision. Rain-controller tracing remains a separate read-only task.
