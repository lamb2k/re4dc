# Cluster PVS proof candidates

The historical finite-ray caster produces an under-approximation of visibility.
Neighbor-cell union, near-object retention and random verification do not prove
continuous visibility. `pvs_emit.py emit` now rejects bare sampled sets. Explicit
`--research-sampled` preserves the old experiment and labels it unsafe research.
Neither it nor `ceil`/`verify` is a shipping correctness gate.

`pvs_prove.py` provides outward-rounded interval predicates for a real source
triangle and an exact shared-edge triangle pair. They require strict opposite
plane sides for the entire eye and target volumes, positive normal clearance,
strict outer-edge signs, and, for pairs, opposite sides of the exact shared
diagonal and a convex projected boundary. Each signed tetrahedron is affine in
eye and target separately, so all 8 by 8 endpoint combinations prove the whole
continuous volumes. Interval vertex uncertainty is independent except that a
shared renderer corner is the same value on both triangles. No rectangle,
convex hull of disconnected surfaces, sampled coverage or hole fill is used.

`pvs_certify.py PACKAGE WORK ROOM --limit 128` prepares geometric candidates.
It uses the existing cluster instance order and R4PV v1 layout, not meshlet PVS.
Targets enclose the actual vertices at every selectable LOD. Occluders are
opaque, non-sky, non-dynamic, non-appended source placements. A single triangle
comes only from a single-level cluster. A paired panel must exist with exactly
the same directed world boundary at every actual LOD. Each pair is in one
actual meshlet with identical shared corner-cache indices, and its source
integer grid is exactly coplanar. Every used pair/LOD is checked separately.
All proposed occluder clusters are pinned visible. Unsupported cases stay
visible. Source geometry and material/state dependencies are recorded in
`proof.json`; no source game coordinates belong in public source commits.

The initial candidate uses 32 mm eye, target and vertex intervals and a 2000 mm
eye-to-plane clearance. **These are requested error budgets, not an accepted
bound on the SH-4 renderer.** Before admission, the actual float matrix build,
FTRV, reciprocal, FPSCR mode, projection and cell-eye inversion must be proved
inside those budgets. A finite scene coordinate range alone is insufficient.
HW_LEAN/FSRRA requires a separately established error envelope. Source camera
samples and random eyes cannot discharge these obligations.

The existing caster can cheaply supply cell domains with one direction. Those
sample bits are ignored by certification. Ground samples merely choose which
closed camera volumes receive a candidate; they do not infer invisibility.
Certification covers the actual stored f32 grid and the int16 decimetre Y
volumes, including emitter Y expansion and an additional eye error budget.
Out-of-domain cameras draw everything.

For scoped texture policies, run preparation with `--original-policy FILE`.
The ids must authenticate that original policy; both policy payload CRCs must
be genuine. Apart from texture key bytes and the payload CRC, **every byte**
of both policies must match, including placement matrices and material flags.
Mesh payload CRC, ids count and prepared input SHA256 identities are checked.
The original append provenance is required to exclude appended owned objects.

Example, after preparing and creating cell domains in WORK:

```
python pvs_certify.py PACKAGE WORK 101 --limit 128
python pvs_emit.py emit WORK candidate.pvs --geometric-candidate --dilate 0 --near 0
python test_pvs_prove.py
python test_pvs_emit.py
```

Geometric emission checks the hashes of the prepared metadata, cells, instance
rows and certified bits. The output sidecar explicitly says
`runtime_admitted: false`. A candidate is not an accepted table. The runtime
must authenticate the exact file and all package/source identities and refuse
without its independently qualified table and per-pass frame guards.

Those guards must establish actual source rest pose/AREA/gate visibility,
opaque depth-writing material and resident matching texture/header, current
packet/stream eligibility, every applicable LOD/piece-selection policy, and
that all paired vertices remain safely within near/far clipping. Back-face,
dedup, piece hiding and root-pose variants require their own qualification.
The packet and source checks must guarantee the occluding surface is actually
submitted; a loaded package alone is insufficient. Failure means draw all.

The current data receipt records geometric candidate cuts, not active-frame
work saved, FPS, hardware acceptance or guaranteed gains in a particular view.
All-visible controls remain explicitly labelled controls.
