# Early PS2 water coverage: source checkpoint

The user's scope is all three early landmarks: opening bridge/ravine/pond r100, lake-house/fish basin r107 and boulder/shallow stream r10a. Later r10c/r10d/r10e water and r10c rain remain separate existing work. This checkpoint proves source correspondence and adds default-off diagnostics; it does not claim repaired appearance or runtime acceptance.

## Authenticated original paths

- r100 uses a material/refraction path, not Esp08. Actual PS2 st1_0.rel (92,760 bytes, SHA256 01718aa3fdb13d69bc00d4b577a09231d33cf612eee79a1c489c86813c496f5f) R100Init calls the unnamed material setup at 0x6500. That routine applies texture247, blend255, alpha240, shader2, refraction power30/ratio128 and64x64 target to object IDs0/1. Actual SLUS_211.34 (SHA256 465d144f526603d0dcc35ad1fdb4e82cc3a1481c22289f321482cc910fb9f1ad) SmdSetup stores objects by SMD byte51; SmdGetObjPtr indexes the same table. r100 has unique IDs0/1 at placements0/1, BIN129/130. This mapping is authenticated from PS2 code and data, replacing the earlier GC-only hypothesis. The two authored meshes contain94/147 triangles and are not horizontal planes.
- r107 has two authored PS2 water rows. r10a has four. `bind_early_tables.py` regenerated their row strings in memory from the actual original room EFF and proved exact agreement with the existing `water_ps2_table.inc`. These are already covered by WATER_PS2; adding duplicate planes would be wrong. Existing base-table lifetime uses the current effect area or recovered generator; texture and native acceptance remain runtime questions.
- `inspect_source.py` proved each room's input SMD byte-identical to actual original DAT member4; every embedded BIN agrees with its existing extracted BIN, and the standalone TPL agrees with the embedded SMD TPL. Totals: r100283placements/148BINs, r10771/69, r10a228/201. OBJ group identity agrees with source placement/BIN/ID/status. OBJ geometry is reported as evidence; this is not a full converter geometry or current consumed-package certificate.

## Default-off runtime witness

`RE4DC_EARLY_WATER_DIAG=1`, defined only for espgen45.cpp by root's later target build, reports existing base rows seen, quality-skipped, inactive, missing registered texture, native-rejected and emitted. Table-index bitmasks identify rows; reports occur on mask/room changes or every300pictures. No row, area, generator, texture, draw activation or gameplay decision changes. Native acceptance is submission acceptance, not visible pixels.

`test_diag.py` checks exact default-OFF preprocessed token identity with original source base140a699f8 (includes omitted equally), and compiles the actual diagnostic helper for nine host controls. Target object/ELF/payload identity is still root's gate; preprocessing does not replace it. No SDK, Make, target build or guest runs here.

## Concrete remaining material plan

r100 must preserve the two authenticated authored meshes and current source visibility/lifetime. The default-off material path should bind the exact consumed package/placement/ID/generation, carry alpha240 and shader2/refraction128, and use the live64x64 source TexRender target. Existing R4PW material records and Re4dcModelPart do not carry this state. A source-owned native RTT identity and source-to-current-package binding must be added by or coordinated with root/native_ui and the geometry owner. Do not apply an arbitrary scrolling texture, synthesize a plane, or claim the whole issue fixed by diagnostics.

r107/r10a should first use the new existing-path reason witness in root's exact programme. Close texture ancestry and working set against actual consumed PS2 payloads, then repair only the demonstrated failure. Source table equality alone cannot prove generator lifetime, effects-area correspondence, residency or look. The current source shows several distinct possible skip reasons, so no unobserved one is designated the cause.

## Private reproducibility

Scripts accept explicit original private paths and refuse existing outputs. Every scan uses a256MiB address-space cap and120second alarm. Original ELF/REL and complete correspondence/record metadata stay outside Git. Private files and reports live under C:/Game Dev/Emulators/codex-lanes/water-coverage24 and re4-assets-private/water-coverage24-20261024. Root owns SDK/staging/guests/actual programme/PS2 package ancestry/stills/memory/progression/console gates. No recipe, data option, defaults, broad regeneration, deletion or publication was performed.
