# Salazar authored diffuse-alpha reference — 2026-10-19

H-029 establishes an exact source-texel coverage reference and a separate private geometry candidate. It repairs neither the shared converter nor runtime admission yet. The H-028 508/213-face isolation candidates and their source sets stay unchanged.

## Result

| Source role | Parts / infos | Source triangles | Exact seven samples: partial | Full bilinear footprint: partial / opaque |
|---|---|---:|---:|---:|
| Queen body, BIN4/TPL8 | 59 / 2 with eye | 12958 | 30 | 33 / 12925 |
| Queen eye, BIN9/TPLA | same 59-part owner / info1 | 120 | 120 | 120 / 0 |
| Upper humanoid, BIN6/TPL8 | 21 / 1 | 4143 | 111 | 114 / 4029 |
| Tentacle types1/2, BIN5/TPL8 | 19 / 1 | 1567 | 0 | 0 / 1567 |
| Roots, BIN7/TPL8 | 21 / 1 | 3240 | 0 | 0 / 3240 |
| Weak object, BIN51/TPL52 | 1 / 1 | 112 | 0 | 0 / 112 |

The legacy float subset contains 478 false positives for the Queen and 102 for the upper humanoid. It also misses three actually partial faces in each. Rounding removes the float false positives but still misses those six interior footprints. No tolerance or rounding is introduced. The old roundoff counterexample remains recorded in H-028.

## Source contract and reference

All 22,140 nondegenerate source faces retain their original PS2 material index and triangle order. Every source-to-mesh UV is exact; every native UV word equals the original packer's quantization. Authored diffuse images decode byte-identically with the two independent GS/JADERLINK swizzle paths and match original atlas interiors and filtering gutters. Character orientation remains explicit. Separate opacity indices17 (Queen),27 (upper) and1 (eye) are retained as their own images and material records.

The pinned format viewer binds the diffuse image as RGB and alpha; its shader reads that alpha. This supports a diffuse-alpha reference, while original GS ALPHA/TEST equations remain unqualified. Partial diffuse images have source TEX0 TCC=1 and TFX=0. The reference does not substitute the opacity-index image. Sources: [actor material loader](https://github.com/JADERLINK/JADERLINK_MODEL_VIEWER/blob/ecd32acd1c62cf34ce4a6e958d8ea1ddafbd7dec/ALL_VIEWER/RE4_PS2_MODEL_VIEWER/src/LoadPs2BinModel.cs#L291-L301), [fragment shader](https://github.com/JADERLINK/JADERLINK_MODEL_VIEWER/blob/ecd32acd1c62cf34ce4a6e958d8ea1ddafbd7dec/ALL_VIEWER/Resources/ObjShaderFrag.frag#L28-L42).

A face is partial if any authored diffuse-alpha texel below255 has a strictly positive bilinear weight anywhere on its complete UV triangle. Texel-centre coordinates come directly from integer PS2 UVs/256. A closed triangle intersects the texel's open support rectangle exactly when strict integer separating-axis checks pass. An independent Fraction polygon clip supplies a point whose exact sampled alpha is below255. Zero-weight neighbours are excluded; arbitrarily small positive weights are retained. Every partial source face has such a witness. This is continuous footprint coverage, independent of screen resolution or a seven-point heuristic.

All three cyclic orders of all source faces agree: 66,420 face-order checks. All four clamp/repeat combinations also agree on this data, so the classification does not depend on assuming a PS2 CLAMP state. Exact seven-sample classification agrees with native quantized atlas UVs here; this is a measured correspondence, not a general quantization guarantee.

## Private candidate and checks

The separate candidate partitions every original oriented position/normal/UV corner into disjoint alpha and opaque subsequences in source order, preserving duplicate multiplicity. Their union exactly equals the complete original source multiset. Original converted position, normal, UV and palette-weight arrays stay exact. The public reference reproduces every prototype candidate byte-for-byte. Original skeletons, motion/cloth/attachments, weak zones and source gameplay systems remain unchanged.

Ten asset-free reference tests pass, including a partial texel between all seven samples, zero-weight boundary contact, a positive weight smaller than float precision, clamp/repeat behavior and unsupported-input refusal. Integer SAT agrees with independent rational clipping on 5,850 synthetic geometries, including UV points and lines. Eight nonempty candidate streams pass the actual current target header with ASan and UBSan;32 corrupt-record/index/count/weight controls fail as expected. All40 controls retain clean sanitizer stderr. Empty partitions are recorded rather than submitted as chunks. Two private script implementation refusals are preserved; the final builder's complete-partition proof and serialized original weights resolve them without modifying the H-028 helper.

These are geometry/reference checks. The candidate is not a final encoded mask pair or an admitted registry package. The complete source TPL34 role proof, original GS/material behavior, eye mask-only handling, source retarget poses/look, native draw, full grab/cutscene selection, resident textures,48 KiB fight hold and whole-fight STRICT/decisions remain open. No fresh Flycast, exclusive draw/logic MODELLED cost, LOD or user appearance acceptance is claimed.

## Reproduction and receipt

`tools/d367/boss18/salazar_source_alpha_reference.py` exposes the exact sample, footprint and independent witness routines; `test_salazar_source_alpha_reference.py` runs with Windows Python, NumPy and no game assets. The private set retains the complete source intake, original material records/texels, face/UV correspondence, exact witnesses, candidate/reproduction, target-host source/results and scripts. No original game data is committed.

Private set `boss18-salazar-source-alpha-20261019`: 200 files, 29240205 bytes; root SHA256SUMS `58c23195a586b45016ceff8b2b057ef87eb026e7a9d208095a90652a6a8bd58f`. Mirrored and byte-verified at `C:/Game Dev/Emulators/re4-assets-private/boss18-salazar-source-alpha-20261019`. Original source54322aab and H-0287a1b0a0a seals remain unchanged. Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/salazar-I010-20261019/`, including authored-alpha summary, legacy membership comparison, actual target preflight and final seal.
