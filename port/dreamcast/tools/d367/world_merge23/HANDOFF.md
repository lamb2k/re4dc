# world-merge23 corrected LOD policy, 2026-10-23

The previous `516bfe3b8` estimate used effective LOD divisor 5, while the release
selector uses 20. Its receipts and table are preserved below as historical LOD5
evidence. Both estimators now require `--lod-px` and `--profile-receipt`, record
the effective divisor and receipt hash, and pass the same divisor to selection
and independent SG reference costing. Future profiles have no implicit default.

## Corrected decision

**NO-GO for the tested ownership-safe fixed-cell whole-part policy remains.**
The generous full-detail + baked-UV arm was rerun on the same pinned assets and
43 exact cross/farm views (frames 500..794, stride 7), at effective divisor 20.
The gate requires >=40% fewer selected part contexts and <=10% vertex growth.

| Cell | Cross context reduction | Cross vertex growth | Farm context reduction | Farm vertex growth |
|---|---:|---:|---:|---:|
| 2 m | 0.0000% | 0.4331% | 0.0000% | 0.0000% |
| 4 m | 1.0947% | 37.6650% | 0.0000% | 0.0000% |
| 8 m | 5.0105% | 74.1350% | 0.0000% | 0.0000% |
| 16 m | 3.2000% | 81.0244% | 0.0000% | 0.0000% |

Cross baseline means: 460.9302 selected meshlets, 390.6047 nonzero-transform
meshlets, 356.1860 emitting meshlets, 110.4651 part contexts, 85.2558 placements
and 17059.3488 transformed vertices. At 8 m, the result is 104.9302 contexts and
29706.3023 vertices. Farm baseline: 406 selected meshlets, 129 part contexts,
74 placements and 22111 vertices. These are offline model units, not measured
runtime draws or timings. The 8 m cross conservative added geometry storage is
still 1,119,876 bytes; reader/layout and memory acceptance remain unbuilt.

Deleting every eligible context at zero replacement cost gives an optimistic
farm ceiling of 7.75194%, below the gate. The cross ceiling is 64.98947%, so this
decision does not rule out all cross placement merges. The tested fixed cells
and material grouping fail; no new partition design or runtime was introduced.

## Policy and evidence

- At frozen `516bfe3b8`, `native_static.cpp:6173-6180` multiplies quality lod_px
  by SCENERY_FAR_LOD; `quality.cpp:50` supplies Standard 5. Original and current
  release `test15/t15-build.sh:165` set SCENERY_FAR_LOD=4. Effective divisor: 20.
- The exact camera programme receipt also records 4:
  `/root/probe/lanes/route/out-iv23e9bf7camrW/resolved-knobs.txt`, SHA256
  `047029285b5b2e48b33446604555cf8c722af9f0b2eb6271a00db02622da49a9`.
  Its camera-only overrides do not establish a runtime performance result.
- Resolved inputs remain SHA256
  `2eb567e74aa1c529ac820b0fef78faf8574a7f9b66777691a8ea4205b05771e0`.
  Mesh, policy, strip groups, IDs and camera pins are unchanged.
- Corrected full-row reports remain in RAM only:
  `/dev/shm/world-merge23-lod20-f2r0002d`.
  Cross SHA256 `ea9f9a9b397450bcb9507b528a4095e1a64179c4027d67a8c49ec286b61ad78b`;
  farm SHA256 `651e4c7a6432265556760e7d00ec9a2d4eaef32e68db81353c2004c241e28515`;
  eligibility ceiling SHA256 `23bf660d5d776acd0dc02ae800bd123a4d2e29aab93949410f3aac9b213a9820`.
  Tiny durable summaries live in the lane HANDBACK and correction review.
  Original private receipts are unchanged; private input data is not committed.

## Checks and reproduction

Eight controls pass: five grouping cases; a two-level sensitivity case selecting
six corners at 5 versus three at 20 while checking independent SG reference
agreement; and zero-group identity on all 43 views in each room at 20. Historical
cross 8 m LOD5 means were independently reproduced exactly before comparison.

```
python placement_estimate.py --inputs INPUTS.json --room r101 --camera CROSS.log \
  --full-detail --bake-uv --lod-px 20 --profile-receipt RESOLVED.txt --output NEW.json
python test_placement_estimate.py --inputs INPUTS.json --cross-camera CROSS.log \
  --farm-camera FARM.log --lod-px 20
```

No runtime/game-data change, build, staging, emulator/camera replay or production
recipe edit occurred. All prior model omissions and hardware limits still apply.

## Historical LOD5 receipt preserved

# world-merge23 offline milestone, 2026-10-23

Branch: `wip/world-merge23-20261023`. Pushed source: `e371b16c2`.
Base: `451bed6faa2c37f7f9aa05d6fb1116ec64219ebc`.

The tested ownership-safe, fixed-cell whole-part merge is **NO-GO** against the
handover's 40% context reduction and <=10% vertex-growth gate. No runtime knob,
new game data set, binary or console disc was built. This does not rule out all
future world batching designs.

The estimate groups complete compatible opaque parts across at least two
different placements. Each new part can contain many <=256-corner meshlets.
It preserves original paths for shared mesh instances, unique live-owned props,
sky and alpha/transparent parts. A separate generous arm uses full level-zero
geometry and bakes final UVs so original UV quantization does not prevent a merge.

## Results

Geometry estimates only, same 43 cameras per room: frames 500..794 stride 7.
Current release asset precedence is resolved; R4IM comes from the retained t164
payload and sidecars from mip22b. Ownership IDs bind the original policy CRC and
count, with identical current placement records after texture rekeying.

| Full-detail + baked-UV cell | Cross context reduction | Cross vertex growth | Farm context reduction |
|---|---:|---:|---:|
| 2 m | 0.00% | 0.39% | 0.00% |
| 4 m | 1.05% | 30.10% | 0.00% |
| 8 m | 4.43% | 62.92% | 0.00% |
| 16 m | 2.70% | 69.09% | 0.00% |

The cross's original static reference has 505.21 selected meshlets, 431.67
nonzero-transform meshlets, 396.53 emitting meshlets, 115.42 selected part
contexts and 86.07 placements per view. Those are different units. They must not
be equated with actual release draw counts or a fresh timing measurement.

Conservative additional storage for the 8 m cross arm is 1,119,876 bytes if the
original geometry coexists with copied float XYZ/UV/color, strips and descriptors.
No replacement-package memory fit is established. r100 data is unchanged and
no new runtime code exists, so no new s30 heap result is claimed. The baseline
model omits placement world_out, sky-far and live dynamic gates, as its original
sgprice documentation states.

## Checks and evidence

Seven estimator controls pass: five small cases and unchanged zero-group counts
for both rooms across all 43 views. Independent reviews are `REVIEW.md` (earlier
probe findings) and `REVIEW-PLACEMENT.md` (correct whole-context method).

Private evidence root:
`C:\Flycast-Evidence\re4-dreamcast\world-merge23-20261023`.

- `resolved-inputs.json`: `2eb567e74aa1c529ac820b0fef78faf8574a7f9b66777691a8ea4205b05771e0`.
- `input-census.json`: `57563b92aa0a62fc89b475961b130690fb6e6e18959088f2ebc74bbc1fd4f9f9`.
- `r101-placement-uv-full-r2.json`: `015fc35166553c263e7cfa31da76c0a8a5b6a0768b82618ea98aaa791431bea4`.
- `r103-placement-uv-full-r2.json`: `ac41285ad2bc6787f0ece55558d2a4d3a54ab3197477d6c1d07ae9fb059c0585`.

Earlier meshlet-only r1/r2/r3 probes are preserved and superseded. They mostly
merged inside existing placements and are not the whole-placement decision.
Source/runtime/Flycast/release/physical gates remain distinct: only source and
offline host geometry checks ran in this lane. No screenshots were generated.

## Next

Keep production recipes unchanged. Continue independent `dedup-offline23`.
Main owns its reader/clip/lifetime review and later target/memory/QA integration.
Do not resurrect actor-vis wide, meshlet PVS, castle or historical cache queues
from earlier notes; the new handover controls scope. Claude retains merges,
releases, SD and production measurement ownership.
