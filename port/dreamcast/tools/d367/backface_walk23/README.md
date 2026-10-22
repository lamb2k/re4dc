# World C-walk diagnostic

This default-off diagnostic isolates the first requested console experiment: the C world walker keeping every eligible triangle versus the original OFF walker. It is not a performance improvement or an extension of the fused SDK implementation. Base: a2477bd2b4d2dc5354fe1bbcc5b5c6b45312928f.

| Arm | CPU_BACKFACE | ACTOR_BACKFACE | BACKFACE_WALK_PROBE |
|---|---:|---:|---:|
| A: original OFF | 0 | 0 | 0 |
| B: C world walk, keep all | 1 | 0 | 1 |
| C: C world walk and drop | 1 | 0 | 2 |

The B arm retains `strips_bf`, its outcode/clip decisions, the plain-index copy and the existing SQ emitter. It excludes facing, run selection and splitting at preprocessing. Existing depth-all/screen-all rejection and clipper continuation are unchanged. B minus A estimates the change to C walking/emission, including the index copy. C minus B measures the net classifier/run/drop cost together with reduced submission; it does not independently measure pure drop benefit. All arms perform the same earlier transformations.

Nonzero probe modes leave actor CPU_BACKFACE undefined, so actors follow OFF even when their original material already culls. ACTOR_BACKFACE=0 alone would not guarantee this for source-culling bosses. Probe0 preserves the original CPU1 world **and actor** behavior. Invalid, empty or multiple probe values, nonzero probe with CPU0 and nonzero probe with ACTOR1 are rejected. Production edits are limited to `game/backface.mk` and `room/backface_emit.hpp`; renderer, recipes, SDK and PVS are unchanged.

For later console timing, use the existing meter selected by main and `TA_HASH=0 BACKFACE_CENSUS=0 WORLD_METER=1`. Importing that meter, complete-programme identity, pixel/logic/memory gates, media and hardware execution belong to main and have not run for this unit. For a separate counts-only replay use `TA_HASH=1 BACKFACE_CENSUS=1`; those hooks add work and their timings are unsuitable for the causal comparison. Keep PS2_PVS=0, arena/OCRAM modes off and all remaining integrated recipe/assets/settings identical. Record runtime Near18.75m without a far shell first; compile FAR_SHELL alone does not establish the runtime view.

Stage `r101-calm.txt` as `/cd/dc/warp.txt` and `r101-calm-repeat.txt` as `/cd/dc/bench2.txt`. Use `DBG_WARP=1 WARP_AFTER_RESET=1 BENCHMARK=1 BENCH_SCENES=2 BENCH_CENSUS=0 BENCH_FILES=2`. Both files use the same cross position and room-tick [300,600) window, with no alert or freeze. BENCH_FILES is dormant outside BENCH_CENSUS, so verify bench.o resolves two scenes and stage both files. Do not enable BENCH_CENSUS to force one file: it also requires unrelated rigid/mist changes. Fixture hashes and all diagnostic overrides are in `arm-matrix.json`. A freeze fixture is for pixels, not post-freeze timing.

C `stats.strips` counts accepted input strips even when zero or several pieces are emitted; `output` counts accepted source triangles. Existing census class1 can infer complete culling 32-byte pieces as `(cv-t)/2` when all strips have at least three vertices. Vertex SQ writes for that subset equal cv; vertex payload bytes equal 32*cv. This excludes cull-none/64-byte formats and TA/OPB/header overhead. `emit_sq` writes a complete 32-byte vertex per PREF; its split calls add EOL/piece work, not new polygon headers or partial vertex writes. Do not equate reduced vertices with faster rendering.

## Validation

Run host controls into a new directory:

```
python3 port/dreamcast/tools/d367/backface_walk23/test_host.py --output /absolute/new/owned/host
```

Run only the two production translation units under both shared and private build leases:

```
bash port/dreamcast/tools/d367/backface_walk23/qualify_target.sh /absolute/new/owned/target
```

The target script replays the exact commands from the retained integrated a2477 build, pins candidate.txt SHA256 f1b86f54a1c6fdf2ccf496c5fb504f5c20047727d9488b3872cba2bfb0646a22 and KOS libkallisti SHA256 5e2d867fb5825e7825e1843f2542446288e18c383341a58426e452a0b620daaf, and changes only output paths and Make-derived diagnostic defines. Inherited generated headers are read-only and hash-bound. It temporarily substitutes the base header under the private lease for original-object controls and restores it in `finally`; do not run concurrent source edits. The selected source, commands, preprocessing and object identities are recorded. `--verify-existing` repeats postprocessing assertions without compiling.

Sealed results are in `evidence/`:

- 1,024 strip cases cover every n=0..255, both masks and both cull modes, with exact words/order/piece lengths and untouched output sentinels. One additional nonfinite-XY case proves keep-all copies those words.
- 701 cases exercise the unedited extracted C caller for batches, all/depth/screen/limit ordering, interior crossings and clip stop results. Portable codes/SQ stubs and an observed clip continuation are used; this is not a host execution of the real clipper. Counts 0..2 are tested only at the strip API: native count streams require n>=3. Oversized means n>limit, not a byte count greater than255.
- OFF full target objects and preprocessing match original byte for byte. Their stripped objects also match the retained integrated production objects. Normal CPU1 probe0 preprocessing and code/data/symbols/relocations match original; raw debug line records differ because header lines moved.
- B/C actor objects and preprocessing match OFF byte for byte, with CPU_BACKFACE absent. C world object equals normal CPU1 probe0. Actual B strip contains zero FSUB/FMUL/FMAC/FCMP; C retains 4 FSUB, 2 FMUL, 1 FMAC and 1 FCMP. Original target arithmetic is unchanged.

No full programme, pixels, STRICT, heap/VRAM gate, guest, disc, console timing or rendering gain is established. Scratch is owned and preserved below the allocated 256 MiB. PVS remains the primary delivery.
