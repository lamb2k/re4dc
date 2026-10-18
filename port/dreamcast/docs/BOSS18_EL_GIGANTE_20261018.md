# boss18 El Gigante model work, 2026-10-18

r119 g50 is a data-only candidate for user look approval. The final source-matched calibration saves **1.447 ms per drawn frame (MODELLED)**; the new r119 g70 candidate saves 0.106 ms and is skipped under the user's approximately 1 ms threshold. No gameplay default, runtime C++, release image, or room script changed. r11e calibration/gates are in progress; this is not the boss18 completion handback.

## Final r119 evidence

Evidence root: `C:\Flycast-Evidence\re4-dreamcast\boss18-20261018`.

Build **b18srT**, ELF `daac42cfdc2cbadf82166f33638b86882eeefb6b4a7d30c230c678767e7c08bb`: current T15REC + CH2REC, LOGIC_TRACE/decisions, CODEC_READY_FIXTURE=1, TEX_CHECK=2, native census, PACE_MODE=off, KOS_SQUEEZE=49152. Source appearance trigger and ordinary movie START cancel retain the source callback/spawn. Only the player/camera fixture changes placement. Timing is the visible free fight, UI frames 230..249, tracing 230/235/240/245.

| r119 level | Source positions | Triangles | Strip vertices | MODELLED SH4 ms/frame | Saving |
|---|---:|---:|---:|---:|---:|
| full | 2192 | 4244 | 6294 | 69.097 | baseline |
| g70 | 1555 | 2970 | 4496 | 68.991 | 0.106 ms: skip |
| g50 | 1093 | 2046 | 3198 | 67.650 | 1.447 ms: review |

Absolute totals include diagnostic work and are not release FPS or console timing. Exact compiled source vsync loops contribute only 0.000055 ms/frame here. The full/g50 delta corresponds to about **0.467 ms per 1000 omitted strip vertices** in this scene, versus the old census hypothesis of 1.15; it is not a universal coefficient. The normal mW off-screen and unmatched-pose windows are excluded. `r119-calibration-deterministic.json` and `hwmodel-b18-r119-deterministic-{full,g70,g50}a/proj` retain reports and raw traces.

Fresh Flycast sampler runs of this same diagnostic build/window record full **55.6 ms/frame**, g50 **54.3 ms/frame** (1000 Hz; 20 complete frames; 1115/1088 samples; zero host gaps/lost/late samples). These are sampled Flycast costs, not console timings or host FPS. `r119-pcs-deterministic-*.txt` and the actual capture LT records establish the same source state. Sampling is coarse; the accepted calibration above uses instruction traces.

| Gate | r119 evidence |
|---|---|
| A/A | STRICT, all 882 ticks 0..881, no gaps/masks |
| Timing control +3000 us | STRICT + decisions identical, 651 room ticks 0..650 |
| Full vs g70 / g50 | STRICT + decisions identical, 651 room ticks 0..650, zero drift; 118376 em-em, 13705 line queries, 2581 damage decisions |
| Hardware-trace window | Both levels STRICT + decisions identical on all 20 ticks 230..249; 3640 em-em, 380 line queries, 80 damage decisions |
| Knob-off identity | Fresh T15REC b18irP 1ST_READ plus all 10 overlays equal frozen c18irP control; `knob-off-identity.json` |
| CAST-GC | Explicit live source id2b with native registry rows, zero GC / declines; old Ganado-only alivelog is not boss absence evidence |
| VRAM / heap4 / squeeze | TEXCHK zero, allocation-failure hash zero, actual 49152-byte KOS hold; source pool and movie retire succeed |
| Death s20 | Source rocket damage path, complete 782/782 pictures, terminal1 / end callback, source resumes. Heap4 1003904 before / 639712 active / 1003904 retired; VRAM minimum523520. No AICA no-fit. One audio underrun (18556 silence bytes), so clean audio acceptance is not claimed. |

Death evidence: `h-b18s/scenarios/cx-r119-death-g50a`. This proves that memory transition, not every r119 movie/QTE/route. User look approval and coordinator room/audio acceptance remain outstanding.

## Geometry and identities

Existing boss17 full conversions were reused after all 131 inventory hashes passed. r119 and r11e are separate em2b types 0 and 2, with original 64-bone GC runtime skeletons. The reducer preserves the exact source skeleton, weights on surviving corners, parasite part63 and terminal finger-tip triangles: 594 source faces / 345 locked vertices. Collision and attachment source code is unchanged; em2b uses Yarare boxes/bone attachments, including parasite hit[9] on part63, rather than render triangles. Existing registry LOD policy selects full during source events (Status_flg[1] bit10000000), including grabs.

The first whole-head/whole-hands g50 probe retained 96.4% positions and was rejected. Final candidates use the 80 mm local collapse cap, with exact native triangle and protected-face proofs. Sampled bidirectional surface checks are not continuous Hausdorff proofs: r119 g50 full-to-candidate p95/max54.161/182.082 mm, reverse33.765/127.620 mm. The rest sheet exposes lost mouth detail; user approval is required. A no-reduction repack control reproduces all native input arrays byte-for-byte (report metadata differs only).

Review sheet: `el-gigante-r119-sheet.png`, actual deterministic held tick330 plus labelled offline face/hand crops. Full rest/source sheet: `el-gigante-r119-rest-sheet.png`. These private screenshots are not committed.

## Private data / source changes

Dataset `/root/re4data/private/boss18-gigante-20261018`, immediate C mirror `C:\Game Dev\Emulators\re4-assets-private\boss18-gigante-20261018`. Current seal: **607 files / 58365574 bytes**, SHA256SUMS `2bdee6acb5fc6472184261bd26e710bbffdc2618af24f9fb686f831567982f6b` (`gigante-mirror.json`). No game bytes or media are in Git.

| Package | SHA256 |
|---|---|
| r119 full | 534923d8381e996c89ebc66bc54b38854881d863084b075d4e682de89c1cc05e |
| r119 g70 | eba9c771d6a0442ed2fa79438f395782efe3c7ee4e54d3396457a7988d38841a |
| r119 g50 | 1751fad08333086bc6ef55b60656181391b216c21ee874028381ff943dd7955a |
| r11e full | a8e5051fc1fea29ba17881c67dbd6ee84ea3b8b25448c2430f001d0a946365bf |
| r11e g50 | c99cd11a2938494476a78453bdaa06d03ef05cd1230145611b88c6312b3065e8 |

r119 full/g70/g50 logical arenas 91208/160352/143104 B (runtime allocator cell adds32 B); r11e full/g50 90544/141248 B. Packages retain full + selected rung and share textures. Actual target host checker passes all five packages and refuses each wrong-room/hash/bone negative control (20 cases). Native host512KiB and exact triangle checks pass. Source commits add only optional explicit locked source vertices (default empty, three actual reducer tests) and five isolated data-selection specs. No new runtime knobs, gate changes, or allowlist entries.