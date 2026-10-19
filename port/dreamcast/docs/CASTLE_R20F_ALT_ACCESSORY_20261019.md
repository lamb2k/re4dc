# r20f em14 original alternate accessory

The original E0/type8 actor can bind BIN 0x217 with TPL 0x219. The retained r20f package covers the same geometry with TPL 0x218, so its last live info declines. This preparation adds the missing source role without repacking the accepted atlas or changing existing geometry. It is offline data preparation; actual room and look gates remain with Castle.

## Original selection and material

`src/em14/em14_set.cpp:154-156` sets mot38 to BIN 0x217, mot39 to TPL 0x218 and mot40 to TPL 0x219. `src/em10/em10.cpp:18412-18416` first selects 0x218 for flag 0x200000; flag 0x4000 selects 0x219 only if that accessory slot is still empty. These are mutually exclusive material alternatives, not two simultaneous accessories. Existing per-BIN material accounting already supports that relationship.

The PS2 mesh has 241 triangles, 13 partial bones and one material: flags 0, diffuse 0, opacity 255 and no bump texture. Its retained runtime owner has 37 bones. The 128x128 PS2 images differ at all 16,384 RGB pixels (maximum component difference 161). The GC 64x128 color images differ at 5,665 pixels and masks differ at 3,386 pixels. Reusing the 0x218 pixels or mask would be wrong.

## Proven retained reuse

The original PS2 and GC BIN 0x217, TPL 0x218 and TPL 0x219 entries in em14 are each byte-identical to the corresponding retained em1c inputs. The existing em1c/type9 section22 already provides the source-derived 0x219 pair. Complete oriented position/weight/masked-UV triangle sequences match all 241 faces; positions, normals, weight records and the masked UV chart are exact. Raw atlas UVs differ because the old pools use different cells.

The donor stream has flags 8; the current lit em14 stream has flags 12. The donor stream is not copied. New section21 aliases current em14 section20 arrays and retains the current lit stream, normals, weights and mask UVs. Only the proven original 0x219 color/mask pair is reused. All 21 old chunk records and array literals remain exact. No mesh reduction, new color bake or material-flag change is made.

This preserves the existing GC-pair correspondence and ARGB4444 quantization. It does not establish PS2 pixel equality. The retained closest-surface mapping has median distance 1.696 mm and maximum 6.811923 mm; its prior mapping/quantization limits remain explicit. No new appearance acceptance is inferred. Rebuilding the whole pool was rejected because it moves three existing atlas cells.

## Package result

| Item | Existing | Additive |
|---|---:|---:|
| Registry bytes | 273728 | 273952 |
| Skin arena bytes | 19648 | 19648 |
| Registry plus skin bytes | 293376 | 293600 |
| Unchanged capacity | 425984 | 425984 |
| Source roles | 50 | 51 |
| Type8 sections | 21 | 22 |
| New pair VRAM | 0 | 16384 |

Geometry, the complete 252128-byte blob, parents, inverse binds, model/part facts and source blobs are byte-identical. Existing reference/texture/texture-fact/role records are exact prefixes. The only changed old descriptor byte is its type8 section count. New role21 names BIN 0x217/TPL 0x219 and reuses the existing geometry. All existing texture package files remain exact; one pair is added.

Baseline registry SHA256: `d034c033b2e7796c5f260fdc51fdb31b77ec3e6dbccff4728b7f1fa8a218b3bc`.
Candidate registry SHA256: `da42932a6c2b029cbc3d26d7e0105a0b2885738564c0b41a73813fa125e35d7d`.
Pair `7a5e30d0-89b5ef09.re4tex` SHA256: `edc35f81c1e2958137856a3699ad0e0fa02b380c19bff75dc297d30ab92b0ac0`.

The private root is `/root/re4data/private/boss18-r20f-alt-material-20261019`, mirrored immediately under `C:/Game Dev/Emulators/re4-assets-private/` with the same leaf name. Its 255 files / 31172850 bytes are hash-verified; SHA256SUMS SHA256 is `3241811c86caf45fb63346dfb325eaae72c0b516a2c27086ddfaf17c0390787f`.

## Reproduce and stage

The owned `tools/d367/boss18/prepare_r20f_alt_accessory.py` pins original inputs, baseline registry/headers and retained pair, proves raw source and complete oriented masked-chart correspondence, then creates a fresh private additive set. Its companion asset-free tests cover eight append/refusal cases. The new `tools/d367/model-registry/boss18-r20f-alt-material.json` is the exact emitted spec. Use existing `model_registry.py` with `--package-room 20f --pack-bones 96 --wide-identity --pool --roles5`. No shared converter/helper or runtime source is changed.

For the current A fixture, replace only `candidate/package/r20f/registry.re4nmr` and add `candidate/tex/7a5e30d0-89b5ef09.re4tex` from that private root. Preserve the current room-census package precedence and every existing atlas winner. Do not substitute the candidate's entire texture directory or an earlier package for the current merged chapter set.

Verification: eight asset-free tests pass; standard generator preflight, capacity and self-check pass; the control generator reproduces A's exact baseline; binary section and texture preservation checks pass. Private `source-material-audit.json`, `retained-alternate-correspondence.json`, `additive/additive-proof.json` and `package-preservation-proof.json` record exact source and output details. No new target build, live capture, speed or complete-fight gate was run. Castle still owns original E0/DF adoption/drawing, TEX/CAST/VRAM, 48 KiB KOS, materials/look and route checks. Existing bump drops on unrelated retained sections are unchanged and are not qualified by this addition.
