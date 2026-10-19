# Castle em14 type6 source mapping — 2026-10-19

The retained type6 geometry is an authored Merchant alias, not an accidental replacement by a wrong PS2 subtype. This conclusion comes from original-disc bytes and complete retained-corner correspondence. It does not rely on native drawing or a shared atlas key. No reconstruction or new conversion is needed to resolve this source-provenance question.

## Original source identity

Original `src/em14/em14_set.cpp` case6 selects BIN1E7/TPL1E8, head1E9/TPL1EA, robe1F0/TPL1F1, hands1F4/1F8, cloth1ED/1EE and goods1EF. Lines252–256 explicitly assign type6 to Ganado class0; other types get class1. All eight source roles remain distinct and use the original61-part runtime owner.

All eight BIN payloads and all three TPL payloads are byte-identical across original em14 and em13 Merchant entries, and the mapped standalone em18 entries, on both PS2 and GC:44 exact comparisons. This includes material records, positions/normals/UV/weights and complete texture tables, not just skeleton counts. Both archives were read directly from the original ISOs; retained source metadata matches their full hashes.

| Role | em14 / em13 arc | em18 arc |
|---|---:|---:|
| Body | 1E7 | 5 |
| Head | 1E9 | 7 |
| Robe | 1F0 | E |
| Right / left hands | 1F4 /1F8 | 12 /13 |
| Open / closed cloth | 1ED /1EE | B /C |
| Goods | 1EF | D |
| Body / head / robe TPL | 1E8 /1EA /1F1 | 6 /8 /F |

PS2 em14.dat:3942464B, `4fa1403865738ac7db01fa69b366a7dc4a541de5b85ff894569a81172c362f1c`. GC em14.drs:6599872B, `e082de1eb74fd0d15b1c7a5a87f7585b559e336456affb2fc64a5e65133f195c`. The unrelated type7 source BIN1FC is different; no generic subtype alias is inferred.

## Retained geometry and source pixels

The retained `zealot-em14-06p` runtime header is `2d7029e155ba7efc241bf2b6d8b2a42491c92bd141ffcce439206a539fcf1eb6`. All eight sections match original PS2 source through the exchange mesh and native header, including oriented corner multiplicities, original material/TPL/UV identity, normals and weights at the existing native quantization. Original position/normal/UV input arrays are byte-identical to the retained header. The complete61-part hierarchy, rest/capture matrices and original GC section bindings match. No weight/skeleton/geometry tolerance changes or nearest-surface inference.

Nondegenerate triangles per role are1080/323/655/217/217/100/104/569:3265 total. The raw goods BIN has one zero-area triangle that the existing converter already drops. Maximum original-to-mesh float position delta is 0.0mm; all positions match exactly at the original1/16mm native quantization.

All original TPL images decode identically through GS and JADERLINK paths. Used source RGB pixels match the retained512x512 atlas exactly. Independent original em18 closed/open selections reconstruct the same source atlas pixels and key61519868-9ee3f93f. Separate alpha/material behavior is not newly qualified by that RGB correspondence.

## Encoded texture distinction retained

The retained type6 package is67728B, SHA`e7735a398b908f7f3c3c214b8468f6c9d29c557df51cd1082287f8ad83b93139`, matching its manifest. The preserved Merchant library file under the same source key is SHA`2af4bac78227dc4008ffc79c86877a0d62cd56b24aed05b45cdbf8ec247bb3a4`. Their VQ payloads and decoded pixels differ:200920 of262144 pixels, mean absolute RGB difference5.206/4.546/5.000, maximum173/158/148. This failed byte/pixel-equality check is explicit; a shared content key is not a compressed-byte proof. Original source RGB identity is proved separately. Use exact selected package hashes for staging; no texture was replaced or re-encoded here, and no compression-quality choice is made.

The provenance question is resolved. Existing alpha/material, live part composition, cloth/animation, visibility, room residency, textures and route gates remain with Castle. Types7/8 and source em25 parasites still need Castle's unchanged composition. No new runtime, source selector, model conversion, look choice, Flycast or hardware gate is claimed.

## Private receipt

`castle18-em14-type6-source-20261019`: 60 files/24830265B, root SHA256SUMS `90637dae72ddd3403f8862d043004af445f94967e600fb1d20f956ed1c2fcedb`. The set is mirrored and byte-verified at `C:/Game Dev/Emulators/re4-assets-private/castle18-em14-type6-source-20261019`. It retains original PS2/GC em14/em13/em18 inputs, full alias and corner proofs, necessary converted inputs/header, source pixels, both encoded variants and the negative readback observations. Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/em14-type6-source-20261019/`. No game bytes or media are committed.
