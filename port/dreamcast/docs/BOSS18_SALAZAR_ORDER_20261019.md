# Salazar retained-mask order proof — 2026-10-19

H-028 prepares a narrow, offline order correction for the two existing Salazar mask candidates. It does not establish their final source-alpha classification or make them production assets. No existing converter, runtime, guard, capacity, recipe or registry selection changes.

## Exact boundary proved

The full native position, normal and UV arrays are byte-identical to the original converter inputs. Their oriented corner multisets match the original GX triangle lists. The old mask's first-seen UV compaction is reconstructed explicitly: 1,184 Queen UV indices and 360 upper-body UV indices. Every position/normal/remapped-UV corner and duplicate multiplicity matches the old candidate. This avoids the earlier ambiguous position-only correspondence.

The same pinned subset is projected onto original GX order and emitted as consecutive three-corner strips. Body alpha keeps 508 triangles and grows from 9,184 to 9,568 bytes (+384); upper alpha keeps 213 triangles and grows from 2,752 to 3,008 bytes (+256). Opaque blobs, mask UV arrays, encoded textures, complete skeletons and skin weights are unchanged. Queen has 59 source parts and two infos; the upper humanoid has 21 parts and one info. Eye, weak point, procedural attachments and source gameplay systems remain outside this order-only change.

| Candidate | Ordered blob SHA256 | Meshlets / records / indices |
|---|---|---|
| Queen alpha | 0e3d32f41ab95cede02226f55ae662e0db2fef065b901cc61af32d04b2c7aad6 | 21 / 1304 / 1524 |
| Upper alpha | 7fb6e1c366f72f70addafa946171ddb19580962cc0cd5be02b323acce96737ca | 6 / 380 / 639 |

## Roundoff counterexample retained

The legacy seven-sample float classifier compares sampled alpha strictly below 255. Cyclically rotating an otherwise identical face changes floating arithmetic and therefore its membership. Queen selects 516 faces in original GX order versus 508 in runtime order, with 102 source-only and 94 runtime-only faces. Upper selects 213 in both orders, but 13 faces differ in each direction. Opaque samples can evaluate to 254.99999999999994 (Queen) or 254.99999999999997 (upper).

No rounding, epsilon or membership change is applied. Rounding that float result to eight bits would give 30/30 Queen and 111/111 upper faces; those counts are diagnostic only and are not accepted as authored-source alpha. Preserving the old subset isolates the order correction. It cannot be the final source-alpha contract. A separate private source-derived classifier/reference must distinguish opaque sampled footprints from actual partial alpha using authored texels and material identity, independently of cyclic ordering.

## Verification and remaining work

The actual current `coarse_actor_preflight.h` was compiled with ASan and UBSan. Both good chunks pass; invalid UV records, local indices, triangle counts and bone weights fail with their expected errors: ten controls total, no sanitizer errors. Eight helper/reproduction controls pass, including byte-identical ordered outputs, changed pins, semantically corrupted corner records, changed source UV arrays, existing output preservation and output-path escape refusal. This establishes host preflight only.

Salazar remains unpriced: no qualified current drawn fixture, exclusive draw or logic MODELLED cost, or fresh Flycast run is claimed. The 34-image source TPL versus current role capacity, eye partial alpha, original GS/material behavior, animated retarget poses, complete native admission, full/grab selection, g70/look, resident textures, 48 KiB KOS and whole-fight STRICT/decisions gates remain open. No user appearance approval is requested from this limited proof.

## Reproduction and private receipt

`tools/d367/boss18/salazar_source_mask_order.py SOURCE_SET NEW_OUTPUT` uses its adjacent hash-only contract. It refuses changed original inputs and writes only outside the immutable source root. Windows Python with NumPy and Pillow is required. Full corner/index evidence and game bytes stay private.

Private set: `boss18-salazar-order-20261019`, 112 files, 4001555 bytes; root SHA256SUMS digest `7a1b0a0ad3a0293868d4d88c86103e365456dcc5459b4eaef7851f560eacb25e`. The set is mirrored and byte-verified at `C:/Game Dev/Emulators/re4-assets-private/boss18-salazar-order-20261019`. Nested source manifests are included in the outer inventory; only the outer SHA256SUMS itself is excluded.

Original `boss18-salazar-20261018` seal remains `54322aabdac761e233bf5b99a1ae0d67cc6db1c3307860759edefd5d59f27b6f`. Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/salazar-I010-20261019/`, including the UV-bijection proof, legacy-classification diagnostic, actual target preflight, helper controls and final seal receipt.
