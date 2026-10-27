# PS2 Ashley rig and bounded distance LOD

`ASHLEY_PS2_RIG=1` needs `PS2_ASHLEY=2` and a private `ASHLEY_PS2_RIG_DIR`.
The default is 0. Build the three hand sets with `tools/ps2_ashley.py convert
<new directory> --rig --hands 0|1|3 --ps2-dat <original pl11.dat> --gc-drs
<original source identity archive>`. Run `rig_header.py <hand0> <hand1> <hand3>
<header directory>` to pin their slot maps. Source signatures remain the loaded
game's identity proof; drawn geometry, bind and authored weights come from PS2.
The seventeen PS2 garment bones map to existing game hair/skirt solver outputs,
as Leon's PS2 rig does. No second solver, animation tick or RNG is introduced.

The shared PS2 bones use PS2 rests. Garment influences use the mapped solver's
live matrix and inverse bind. The full source hierarchy is still checked before
the draw slots bind, and a rig build refuses an old surface-transferred slot map.
The authored fixture has 45 draw slots instead of 64, with no folded influences.
This rig arm applies only to converted partner Ashley (model 3, pl11). Playable
Ashley (model 0, pl01) keeps its existing package and bind path, including when
the new knob is enabled. Its different source face, hair and hand contracts need
separate conversion and qualification before the rig can apply there.

`ASHLEY_LOD=1` additionally needs the existing `NMR_POOL_LOD=1`,
`NATIVE_MODEL_REGISTRY_ROLES5=1` and `NATIVE_MODEL_REGISTRY_IMMUTABLE_ALIAS=1`.
The default is 0. Use `lod.py <hand0 conversion> <new output> --pct 70|50
--body-only`. Percentages are requests, not guarantees: the guarded 8mm/20mm
floors produce 4599/4241 triangles from 4925 in the pinned PS2 fixture. Every
face, hair/card, trim and hand triangle stays full. Body open edges, component
anchors, silhouette extrema and the UV guard 0.02 stay protected. Survivors keep
original positions and authored skin weights.

The bounded package contains five descriptors: full hand sets0/1/3 and two
normal-hand 0 body rungs. Interaction hands 1/3 remain full. Camera distance below
5m draws full; 5–10m draws mid; 10m or farther draws far. In-engine events draw
full. No geometry streams from disc when distance changes. Existing package v2
aliases share only exactly equal immutable arrays with the same semantic
context; streams remain independent. The existing 96-bone configuration and
all allocation capacities stay unchanged. The r202 combined admission uses 71
of its existing 72 geometry records (53 room plus 18 partner), behind this knob.

Package using `model_registry.py ... --slots --pool --roles5 --ashley-rig
--immutable-array-alias`; preserve full source/texture identities and all seven
roles. The explicit Ashley mode permits numbered nonpool levels only for the
PS2-rig141-source-joint, seven-role model0/3 contract. All other nonpool types
retain their existing rules. `pack_gate.py` compiles the actual target reader,
tests corruptions, and can check combined room/partner capacity and unchanged
original packages. Run `test_rig.py` for authored-weight and header refusal tests.

Generated meshes, source archives, packages, headers and captures are private
inputs. Keep their recipe and SHA256 manifests outside Git. Source/host/SDK
checks do not establish gameplay, look, measured performance or physical-console
acceptance; the lane handback records those gates separately.
