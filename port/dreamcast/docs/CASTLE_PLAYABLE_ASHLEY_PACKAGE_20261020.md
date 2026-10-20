# Playable Ashley native package, 2026-10-20

The complete PS2 pl01 appearance now has native room packages for r20d and r20e. Both preserve the original seven source infos and complete 141-joint owner. This is a data and host qualification checkpoint; actual target drawing, texture residency, KOS and the chapter play-through remain open.

## Source contract and conversion

The inputs and aliases remain those in `CASTLE_PLAYABLE_ASHLEY_MODEL_SOURCE_20261019.md`. The preparation uses the existing `ps2_ashley.py` conversion with an owned wrapper that supplies the audited playable ordinals and model id 0. It does not substitute the partner's model id or archive.

| Role | Source BIN / TPL |
|---|---|
| Body | 4 / 5 |
| Face | 7 / 9 |
| Hair | 6 / B |
| Skirt, second pass | 8 / 5 |
| Extra | A / 5 |
| Normal right hand | 11 / 5 |
| r20e special right hand | A7 / A8 |
| Open or closed left hand | 14 or 15 / 5 |

The source archive keeps its geometry, skeleton, morph data, motions, bust joints, cloth solvers and attachments. The PS2 render meshes use 68 draw slots from that owner. No cloth links are folded. As in the established partner conversion, PS2 cloth influence is transferred to the original GC skirt surface; 83 corners reduce barycentric mixtures to three weights. This is a render approximation requiring the target moving/look check. It does not replace or reduce the source solvers. The existing runtime draws the PS2 rest face while the original ShapeMove still runs; playable setFace itself has no expression variants.

The normal variants contain 4,925 / 4,951 triangles for the open / closed left hand. The r20e variants contain 5,029 / 5,055, including both materials of the 355-triangle special right hand. Head, hair and skirt retain separate PS2-alpha mask runs. The five shared native texture files are two 512-square VQ atlases and three 128-square ARGB4444 pairs. Identical pair content with different package labels uses one selected file; native metadata and texels were checked identical.

## Prepared packages and qualification

| Room | File bytes | Skin arena | Combined bytes | SHA256 |
|---|---:|---:|---:|---|
| r20d | 210,176 | 9,328 | 219,504 | c52993fcb050c31babdb907df16b4b8be249ee32c2700cd0085ebaa82285c818 |
| r20e | 212,288 | 9,304 | 221,592 | c9aecc2b57b13264704344a369c148cbfa7806d897a0abf5fadc2cad62e8b216 |

Each package has two seven-section descriptors for the source left-hand states. The actual target native converter passes all four appearances, with zero host draw failures, and its strip check preserves every converted oriented triangle. The actual target package reader admits both packages. It refuses all sixteen malformed slot, source-parent, source-count and inverse-bind cases. It also admits each existing room registry followed by the corresponding Ashley package, including r20e's four armour appearances. Host tests establish package compatibility, not live current-pose appearance or hardware performance.

Stage as `dc/native/r20d/partner.re4nmr` and `dc/native/r20e/partner.re4nmr` through the existing two-package loader, preserving each room's primary registry. The complete additive fragment also selects the already-qualified source-texture pl01 archive. The native files add 656,656 bytes before disc packing/alignment. Four native preload keys per room are supplied as separate TSV fragments; the chapter owner merges them into the current resident union and validates actual residency.

The current Test 21 c21amW build already resolves `PS2_ASHLEY=2`, `NATIVE_MODEL_REGISTRY_PL_ASHLEY=1`, `NATIVE_MODEL_REGISTRY_BONES=96`, pool/ROLES5 and partner=2. Source-only wrapper generation uses the same four-material capacity already provided by PS2_ASHLEY. No shared converter or runtime changes were made.

## Handoff

Data: `/root/re4data/private/castle21-playable-ashley-20261020`, mirrored at `C:/Game Dev/Emulators/re4-assets-private/castle21-playable-ashley-20261020`. Use `fixture-additive.json`, `files/`, `native-preload-r20d.tsv`, `native-preload-r20e.tsv`, `PROVENANCE.json`, `pack-host/results.json` and `SHA256SUMS`.

Private reproduction wrappers are under `C:/Game Dev/Emulators/codex-lanes/castle18/workers/ashley21/`. Owned gate fixtures are under `C:/Flycast-Evidence/re4-dreamcast/castle18-20261018/workers/ashley21/fixtures/`; all 23 program files match the current c21amW build proof. The save observer makes no placement, inventory or flag changes. A separate diagnostic invokes r206's original developer task, which calls PlSelect(1) and the original exit into r20d. That diagnostic cannot qualify chapter progression.

Next: coordinated Disc 2 staging, actual CAST-GC / NOT-DRAWN, face/skirt/hand decline census, still and moving-cloth check, the original r20e hand transition, per-room residency/VRAM, KOS 48 KiB and the original chapter 3-3 save through chapter 3-4 end. No emulator, no-warp, console or performance result is claimed here.

## Current pack winner correction

The current Castle/release `tex.pak` already contains 26 of the 30 texture keys in the original additive fragment. Seventeen have different package bytes. The correction retains all 26 current winners, adds only the four absent keys and keeps both native packages and the original prepared pl01 archive unchanged. No packed texture is overwritten.

The native body atlas `2353f21e-bfc44079` has identical VQ metadata and payload; only its package label/CRC differs. Source key `9264be9a-41e48d57` has identical texels; the current pack also retains its established wrap-safe header bit 30. The remaining fifteen conflicts are the same dimensions, format, flags and source keys encoded as existing VQ instead of newly supplied twiddled texels. The existing decoder reports RGB mean absolute differences of 0.10 to 4.46 on a 0..255 scale. The native skirt pair `2c9c252a-51c59944` is among those existing VQ winners: RGB mean difference 2.42, with alpha threshold differences at 229 of 16,384 texels. Retaining the already-selected encoding preserves current actor appearance and residency. This is offline package/source compatibility evidence; target appearance remains pending.

Corrected fragment: `/root/re4data/private/castle21-playable-ashley-winners-20261020/fixture-additive.json`, mirrored under the same set name on C:. It has seven replacements: pl01, two room secondary packages and four absent texture files. `winner-decisions.tsv` gives the exact seventeen-key decisions; `winner-decisions.json` records current pack SHA256, source image carriers, dimensions/formats, decoded statistics and effective selection of all thirty keys. The original sealed package set remains unchanged. The chapter owner assembles the pack and uses this correction in the current runtime fixtures.
