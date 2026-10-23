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
