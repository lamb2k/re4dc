# boss18 El Gigante model work, 2026-10-18

r119 g50 is a data-only candidate for user look approval. The final source-matched calibration saves **1.447 ms per drawn frame (MODELLED)**; the new r119 g70 candidate saves 0.106 ms and is skipped under the user's approximately 1 ms threshold. No gameplay default, runtime C++, release image, or room script changed. r11e g50 saves **1.577 ms per drawn frame (MODELLED)**. Both forms now have reviewed source-held sheets; the user still chooses each level. This is the El Gigante milestone, not the boss18 completion handback.

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

## Final r11e evidence

The same **b18srT** ELF and diagnostic controls are used. The ordinary source appearance event receives START after registration; its original callback spawns the giant. Free-fight hardware samples are UI ticks 290/295/300/305, counted window 290..309. The first event-bound trial and early pictures are excluded.

| r11e level | Source positions | Triangles | Strip vertices | MODELLED SH4 ms/frame | Saving |
|---|---:|---:|---:|---:|---:|
| full | 2202 | 4296 | 6328 | 71.502 | baseline |
| shipped g70 | existing fallback | 2982 | 4528 | 70.844 | 0.658 ms: do not add a new rung |
| g50 | 1086 (49.32%) | 2064 | 3202 | 69.925 | 1.577 ms: review |

The shipped, already approved g70 package remains available unchanged; the threshold does not remove that fallback. Exact source vsync waits contribute approximately 0.00005 ms/frame to each arm. The g50 delta is about 0.504 ms per 1000 omitted strip vertices in this scene. Together with r119's 0.467, this calibrates these two scenes only. `r11e-calibration-deterministic.json` and `hwmodel-b18-r11e-deterministic-{full,g70,g50}a` retain raw evidence.

Fresh 1000 Hz Flycast sampling records full **57.4**, g50 **56.0 ms/frame** for the same 20 complete frames 290..309 (1150/1123 kept samples, zero host gaps/lost/late records). Actual sampled-run source trace and decisions match 20/20 ticks. These sampled diagnostic costs are not console timing or host FPS; hardware traces remain the primary calibration.

| Gate | r11e evidence |
|---|---|
| Full A/A | STRICT 889 ticks; decisions identical for the 888 complete decision records |
| Full vs shipped g70 / g50 | STRICT + MUST-IDENTICAL, 601 room ticks 0..600, no gaps, masks, allocation failures or drift; 116325 em-em, 10673 line queries, 6834 damage tests |
| Timing control +3000 us | Same 601 room ticks STRICT + decisions identical, b18drT ELF1967f9d0 |
| Hardware window | Both reduced arms STRICT + decisions identical, all 20 actual trace-run ticks 290..309 |
| CAST-GC / presence | Source boss id2b admitted and native-drawn. g50 report: Leon1300 / Ashley805 / em2b1496 native rows, all GC0. No native decline; Ganado-only alivelog is not used as boss presence evidence. |
| TEX / memory / KOS | TEXCHK fails0; actual KOS hold49152. Lowest observed heap4 free/largest: full444576/444256, g70376704/376384, g50393856/393536. g50 tick600 VRAM pinned873024 / dynamic724576 / other90112 / free879712 / largest856064 B; refusals, no-contiguous, evictions and retries0. Later preload discoveries are not a blanket no-disc-read proof. |
| Source grab | Separate close fixture, source hold500 / LT499; full vs both reduced settings STRICT + decisions identical for all500 ticks. Both reduced arms reselect original full `gigante-em2b-02` at source event tick386; all three grab pictures are pixel-identical. |
| Knob-off identity | Same fresh b18irP T15REC control, 1ST_READ plus10 overlays byte-identical; source changes contain no runtime behaviour edits. |

Review `el-gigante-r11e-sheet.png` with source/rest comparison `el-gigante-r11e-rest-sheet.png`. Each picture's JSON proves the source freeze sentinel and completed LT tick before and after the read-only VRAM capture. Free fight is hold330, grab hold500. Full/g70/g50 source trace + decisions match330 ticks at the body still, and500 at the grab. g50 loses mouth detail in the rest view. Full source collision, original skeleton/attachments and source event policy remain unchanged. r11e g50 sampled surface p95/max error is56.245/182.082 mm forward and33.677/127.620 mm reverse; this is not a continuous Hausdorff guarantee.

`r11e-model-gates.json`, `r11e-{strict,decisions}-*.json`, `r11e-{lookheld,grabheld}-*.json`, the sampler reports and per-capture `source-hold-proof.json` retain evidence. Entry/fight/grab checks do not establish doors, full chapter route or all r11e movies.

## Review capture correction

The original 24-second screenshots preceded the requested hold (r119 LT281..284, r11e LT258..259). Their earlier same-pose caption was incorrect; that image is preserved only as `el-gigante-r119-early-unmatched-WITHDRAWN.png` and is excluded from review. The current r119 sheet was replaced with all three source hold330 captures, each proving completed LT329 before/after capture and330/330 STRICT plus identical decisions. Timing and long behaviour evidence were independent and remain unchanged. The current r11e sheet uses the same verified capture method. No pixels were retouched.

## Geometry and identities

Existing boss17 full conversions were reused after all 131 inventory hashes passed. r119 and r11e are separate em2b types 0 and 2, with original 64-bone GC runtime skeletons. The reducer preserves the exact source skeleton, weights on surviving corners, parasite part63 and terminal finger-tip triangles: 594 source faces / 345 locked vertices. Collision and attachment source code is unchanged; em2b uses Yarare boxes/bone attachments, including parasite hit[9] on part63, rather than render triangles. Existing registry LOD policy selects full during source events (Status_flg[1] bit10000000), including grabs.

The first whole-head/whole-hands g50 probe retained 96.4% positions and was rejected. Final candidates use the 80 mm local collapse cap, with exact native triangle and protected-face proofs. Sampled bidirectional surface checks are not continuous Hausdorff proofs: r119 g50 full-to-candidate p95/max54.161/182.082 mm, reverse33.765/127.620 mm. The rest sheet exposes lost mouth detail; user approval is required. A no-reduction repack control reproduces all native input arrays byte-for-byte (report metadata differs only).

Review sheet: `el-gigante-r119-sheet.png`, corrected source-verified hold330 / LT329 plus labelled offline face/hand crops. Full rest/source sheet: `el-gigante-r119-rest-sheet.png`. These private screenshots are not committed.

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
## I008 retained r119 native presentation attribution (2026-10-19)

This is a read-only audit of the original b18srT/ELFdaac42cf calibration
captures. Those captures used skin slots1. This is not a fresh slots2/current
program qualification, new emulator test, current boss logic price or console
measurement. Earlier complete-frame calibration and the user's g50 approval
remain unchanged.

The exact original230/235/240/245 traces and complete20-count230:249 window
are retained under hwmodel-b18-r119-deterministic-{full,g70,g50}a.
Each private attribution-I008-20261019 copy uses byte-bound relocated overlay
instruction images, exact boot function extents, and the existing model-id
witness exporter. No pre-strip overlay symbols were retained for this old arm,
so boss move/AI cost remains unpriced; no overlay symbol identity is guessed.

Stable NMRM admits source model8ca43b20 at tick179 as gigante-em2b-00,
gig2b00-g70 or gig2b00-g50 respectively. The source getter's exact36 bytes,
kind0 guard, model+0x100 byte load and witnessed commonModelTrans/transaction
ancestry are checked. Disjoint exclusive self charges below each witnessed root
exclude IRQ. Nothing is divided by an actor count. Separate work outside that
root is not included.

| Level | Requested / observed roots / complete non-invalid | Qualified ticks and native presentation MODELLED ms |
|---|---|---|
| Full | 4 /4 /1 | 245:4.483500 |
| g70 | 4 /3 /3 | 235:3.672255;240:3.671705;245:3.661795 |
| g50 | 4 /4 /2 | 235:2.988135;240:2.961195 |

There is **no complete common full/g50 tick**, and no all-three cohort.
A full-to-g50 exclusive draw saving is therefore unpriced. Do not subtract
per-arm qualified averages. The matched comparisons are full/g70 at245 only:
4.483500→3.661795 (-0.821705ms); and g70/g50 at235/240 only:
3.671980→2.974665 (-0.697315ms). These two deltas must not be added because
their cohorts differ. They do not change the g70 skip or g50 choice based on
the earlier whole-frame result. All incomplete/invalid calls and unresolved
field witnesses remain in the reports (6/4/2 unresolved full/g70/g50).

The original, profile and model-witness replays have byte-identical timing
outputs and disjoint charge conservation for all three levels. Replaying the
original boot-only ELF reproduces every old per-trace cycle total exactly.
Adding verified observed overlay bytes changes each arm's mean by only
-0.000395/-0.00039625/-0.0003975ms (full/g70/g50); this input distinction is
recorded, not silently presented as the old identical report. No timing-model
or runtime rule was edited. There is one picture per logic tick in this
calibration; no steady30fps drawn-only multiplier is applied.

Exact final report:
C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/r119-exclusive-draw-attribution-20261019.json.
It includes hashes, source witnesses, complete per-tick coverage, pairwise
cohorts and parity outputs. Earlier quick notes mistakenly treated per-arm
qualified averages as the same tick and quoted full→g50 1.508835ms; that
claim was explicitly withdrawn. Only the qualified cohorts above are final.
