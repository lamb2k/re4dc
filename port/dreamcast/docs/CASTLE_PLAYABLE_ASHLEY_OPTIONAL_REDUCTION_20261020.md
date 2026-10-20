# Optional playable Ashley reduction, 2026-10-20

One conservative body/skirt candidate is prepared for comparison with the full PS2 package. It retains about 75% of the full converted PS2 positions, rather than forcing the requested g70 style target through the protected features. It is a private alternate fixture; no shared recipe or default changes.

## Baseline and resulting work

The original PS2 pl01 input is SHA256 `6799931bf25a9e53321bef1bcce737c156cb396d29fd7fc4c3436edb59725427`; the source GC owner is `7dbffe5a7111f53dd20b491308bdaaca15cf7aab483e3a4866af8824020bb529`. The separate full package and its texture winner correction remain available.

| Normal open-hand appearance | Full | Candidate |
|---|---:|---:|
| Unique converted PS2 positions | 2,975 | 2,241 (75.33%) |
| Native positions | 3,054 | See native report |
| Triangles | 4,925 | 3,717 |
| Fitted transformed records | 4,100 | 3,251 |
| Fitted strip corners | 7,129 | 5,613 |
| Palettes | 289 | 222 |
| Per-room package plus skin arena | 219,504 B | 175,112 B |

The closed hand retains 75.44% of its positions; r20e open/closed retain 75.74% / 75.85%. r20e changes 5,029 / 5,055 triangles to 3,821 / 3,847. The complete flashlight hand remains full.

No qualified exclusive modeled cost exists for the current playable owner yet. Retained partner draw sums include Leon and cannot establish this owner's cost. These geometry and encoded-byte counts are not milliseconds or a measured speed gain. The current c21amW recipe has full PS2 Leon (`LEON_LOD=0`, `PS2_LEON=1`); its enabled Ganado reduction is a different selection.

## Protections and checks

The existing `leonlod/lod_mesh.py` half-edge reducer changes body role 0 and skirt role 3 only. It retains source vertices, weights, normal/UV wedges, role junctions and small components. The candidate uses an 8 mm per-collapse limit and 165 projected-contour anchors. These restrictions stop the body before its triangle target; the limit is not a global surface-error bound. Face, hair, extra, both hands and the flashlight keep their full source corners. The complete 141-joint owner, all 68 draw slots, original morph payload, motions, source cloth solvers and links remain unchanged. There are no cloth-link folds.

The four native appearances pass host drawing with zero failures, and strip verification retains every candidate triangle. The actual target reader admits both room packages and rejects all sixteen malformed source/slot/bind cases; the r20e armour plus candidate secondary package also passes. These are host compatibility results, not target pose or appearance acceptance.

Offline surface sampling reports 95th-percentile distances below 4.9 mm across rest and two synthetic kinematic poses. The nearest-centroid search overestimates some maxima; exact checks of its 32 largest rest errors give body 14.6 mm and skirt 12.1 mm. Sampling is not a rigorous surface bound or actual cloth-motion validation. Full-versus-candidate four-view rest sheets retain all major components on inspection; look approval and real-target still/movement checks remain open.

The Blender 5.2 review file contains locked full reference and conservative-candidate collections, all original owner joints, source-joint vertex groups, packed source atlases and review cameras. Blender was an isolated offline factory session; the source-compatible reducer and current native packer produced the actual candidate.

## Optional handoff

Private set: `/root/re4data/private/castle21-playable-ashley-g70-20261020`, mirrored under the same name in `C:/Game Dev/Emulators/re4-assets-private/`.

- `fixture-additive.json` replaces only the two room secondary packages, two new skirt pair files and a separate resident file.
- r20d package: 167,552 B, SHA256 `54f969318e03210c38358d8bdeb381ec60d0cdb597a563e26c63483c254e366d`.
- r20e package: 169,664 B, SHA256 `038de7c45534fd92deb3b411ee1141534c412575c10255c41749986cc022a098`.
- Each candidate skirt pair uses the same 6,144 VQ bytes as the full baseline. The optional resident union swaps only the two per-room skirt keys, retaining 5,882 records and 94,208 bytes. Reference and candidate skirt textures are not both listed in those rooms.
- `full-baseline.json`, `candidate-summary.json`, `reduction-report.json`, `PROVENANCE.json`, `pack-host/` and `SHA256SUMS` preserve the counts, contract and checks.
- `review/` contains the two full-versus-candidate sheets and `PLAYABLE_ASHLEY_FULL_AND_OPTIONAL_75.blend`.

The owned runtime observer and r206 source-selection fixtures have separate `-optional75.json` variants under the Ashley21 evidence folder. All use the same current program and source selection as the full fixture. Main owns coordinated Disc 2 staging. Run actual CAST-GC / NOT-DRAWN, decline census, still and moving-cloth/hands, residency/VRAM/KOS and exclusive-cost checks before any selection decision. This optional work does not block qualification of the full package.
