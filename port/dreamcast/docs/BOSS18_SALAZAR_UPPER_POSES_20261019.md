# Salazar upper: original clip pose checks — 2026-10-19 (H-039)

The retained full upper model has now been checked on **25 poses from five original GC clips**, evaluated through the existing recovered-game motion helper. This extends the earlier rest/synthetic-pose evidence. Actual native rendering, animated appearance, live transitions and source parent attachment remain unqualified.

## Narrow host-tool repairs

Current cModel::partsWorldCalc contains mutually exclusive preprocessor arms that can each open the same block. The old tools/motion/host/prepare.py counted both arms, failed to find the function's end and raised TypeError. Commit 01d84504 tracks branch depths separately, requires agreement at each #endif and retains all original conditional text. It does not guess active macros or preprocess against chosen defaults. Comments and quoted braces do not affect boundaries.

Six asset-free guards pass on Windows and WSL: ordinary extraction, nested alternative branches, quoted/comment braces, inconsistent branch refusal, incomplete function refusal and optional balanced code. All three previously extractable model functions remain byte-identical; partsWorldCalc now extracts completely. No source game file was edited.

The next compile exposed a missing host alias for current motion.cpp: u16_un. Commit 581bfccb copies the exact non-PowerPC aligned(1) declaration from include/types.h into the host stub, with size/alignment assertions. An unaligned halfword read passes ASan/UBSan. Both commits were pushed immediately. Existing compiler logs, including the memset declaration warning, remain private.

## Original clips actually evaluated

| Original em38 FCV arc | Source routine | Last frame | Sampled poses |
|---|---|---:|---:|
| 29 | Upper idle | 120 | 5 |
| 2A | Upper flinch A | 68 | 5 |
| 2B | Upper flinch B | 50 | 5 |
| 2C | Upper critical attack | 122 | 5 |
| 2E | Upper death | 250 | 5 |

All five FCVs parse and serialize byte-exact. Samples include frame 0, fractional frame 0.5, quarter-plus-0.25, midpoint and last frame. The existing helper executes the original MotionSetCore/MotionMove, IK and blend-table code in plain host floating point. There is no emulator or game build.

Original GC BIN6 remains `ac402a6b47c45d3247fbf898a1c4536adf9b6bb985ee2665fae6394f2e97fdc6`; PS2 BIN6 remains `3e4f8cd94fd8969b80853ef42a58ed17eb0c7c801a6a0c5e9ecbcf021c0da9f6`. Five retained H-029 input pins rehash exactly. Native header `788e2d6dd8f2d66fe5a70987fc4996df07a77a4e36a956393eccd38eefda3d8b` is unchanged; no model or texture was rebuilt.

## Packed corners and retained numeric difference

All 21 bone IDs and the complete 4,143-triangle source geometry are retained. The check pairs all 12,429 original oriented corners with the unchanged native position/normal arrays through the original GX references. Each of 25 source poses compares the native skinning result with the declared PS2 virtual-rest reference: 310,725 corner-pose checks.

| Measurement | Maximum |
|---|---:|
| Static position quantization error | 0 mm |
| Posed position difference | 0.000059765728 mm |
| Virtual-rest algebra difference | 0.0000000000002274 mm |
| Posed normal-vector error | 0.000050844180 |
| Error decomposition residual | 0.0000000000004108 mm |

**Native numeric weights are not bit-exact to the original PS2 weights.** A strict equality attempt refused at corner 483. Across repeated source corners, 3,155 of 12,429 differ by at most 0.000000059604645; every bone ID is exact. For example, one native residual is 0.19999998807907104 where the PS2 source stores 0.20000000298023224. The packed model is unchanged. These differences are measured in the pose result above; no tolerance or source membership was changed to call them exact.

A hypothesis that all differences came from dividing each source weight by its sum matched none of these cases and is explicitly rejected in the retained record. A separate residual-weight comparison explains only a subset; it is not an implementation audit. No unsupported explanation or bit-exact claim is substituted for the observed difference. Earlier proofs that converted arrays remain unchanged do not imply original PS2 float weights are bit-identical after native packing.

## Limits and handoff

This is a numeric check on original clip poses at a fixed root. It excludes live transition blending, floor contact, em38UpperOnBody's body-part4 parent transform, procedural updates, source camera and lighting/material/GS behavior. The host helper has its documented arithmetic/layout differences from the console. No actual game-pose parity or animated look is claimed.

H-037's complete 34-image roles, authored shift 0 for other forms, original alpha/eye handling, full backing and weak-object ownership remain P2 requirements. Full-fight draw/logic cost, native all-live/all-drawn, VRAM/residency, 48 KiB KOS, STRICT/decisions, route and knob-off gates remain open. No new lighter level or user appearance decision was made.

Private `boss18-salazar-upper-poses-20261019`: 80 files / 3608888 bytes, SHA256SUMS `1d142f24ef3e9baa442a8b1c37529237a6ef14455494919e461aac7211b8b6d1`. Immediate C mirror byte-verified. Initial extraction/type/weight failures remain alongside the successful results. Owned compiler objects, library and ABI test executable were pruned with a hash manifest; source and logs are retained.

Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/salazar-upper-poses-20261019/`. Hash-only reference: `tools/d367/boss18/salazar-upper-poses-20261019.json`. Original model/clip bytes, generated headers and media remain private.
