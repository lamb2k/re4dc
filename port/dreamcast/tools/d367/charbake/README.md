# charbake: offline character texture options and the hair regroup (D367, 2026-10-10)

charbake makes the Dreamcast characters look closer to the GameCube without touching anything the game reads. The
coarse owner path draws Leon (`coarse_actor.cpp`, atlas `ec255e66-76812316`, 512x512 RGB565 twiddled, 524 KB of VRAM)
and the Ganado cast (`coarse_ganado_cast.cpp`, atlas `1279a218-f8cb0063`, 1024x512 VQ, 133 KB) with constant white
vertex colour times the texture (source lighting off, MODULATE): the texture is the only shading, so a bake into the
texture lights nothing twice. Every option is a texture package under a key the play recipe already draws, or a
default-off knob. The meshes, skeletons, bone order, part lists, weights, palettes, attachment points, bounds, blob
flags and every collision / atari input stay byte-identical (the texture options carry no geometry; the hair regroup
keeps every triangle, UV word, palette and bound and only reorders and restripes role 7's draw).

Private by rule: the inputs (approved meshes, atlases, play tex.pak) and every output (packages, previews, paks,
`leon_hair_runs_g2.h`) are game assets and live in the private store (`re4-assets-private/charbake-20261010`); this
directory holds code and the pinned configuration only.

## Options

| option | what changes | how it is staged |
|---|---|---|
| AO | ambient occlusion baked into Leon's atlas and the cast atlas (Blender Cycles AO in the bind pose at 0.05 / 0.15 / 0.4 m, weight 0.3 each, floor 0.55; no gain, so the mean texel darkens 12 % on Leon, 10 % on the cast) | `charbake.py pak <tex.pak> <out> leon:ao ganado:ao` |
| SKY | AO + a soft sky / ground term from the interpolated source normal (sky 1.15, ground 0.8: lit from above) | `leon:aosky ganado:aosky` |
| GCB | SKY + a texel-space gain 1.2 and warm tint (1.05, 1.0, 0.92) toward the GameCube frames; Leon's two hair colour pairs graded too (gain 1.3, tint 1.04 / 1.0 / 0.88) | `leon:gcb ganado:gcb hair:gcb` |
| LVQ | Leon's atlas encoded as VQ (pvrtex full codebook, as the cast atlas already is): 524 KB of VRAM -> 66 KB, play shading | `leon:vq` |
| GVQ | GCB with Leon's atlas as VQ | `leon:gcbvq ganado:gcb hair:gcb` |
| hair regroup | `CHARBAKE_HAIR=1` (`game/charbake.mk`): Leon's hair as 2 owned runs (one per hair material, restripified by the cl lane's fastpath `build_blob.py`) instead of 14 source-ordered runs: 9 runs per Leon instead of 21, 2 hair TA headers instead of 14, 2,131 strip corners instead of 4,317 | build knob + `CHARBAKE_HAIR_DIR=<dir with leon_hair_runs_g2.h>` |

The texture options are staged-asset switches: the pak keeps every other package and the ELF is unchanged (a
`pak` rebuild with no changes reproduces its input byte for byte). AO, SKY and GCB keep each package's size and format,
so VRAM use is unchanged; LVQ / GVQ free 456,704 bytes of VRAM while Leon is resident.

Not covered: pl08 (Leon without the jacket, atlas `7506e95f-68cf2211`) keeps its play atlas under every option; the
other enemy types keep theirs.

## Commands (Windows Python with numpy + PIL; Blender 5.2; the pinned KOS pvrtex in WSL for VQ)

```
python charbake.py bake  [leon|ganado]      # Blender AO per mesh, cached by input hash (re4-assets-private/charbake-20261010/cache)
python charbake.py build [leon|ganado|hair] # transfer onto the atlas, compose each variant, encode packages + previews
python charbake.py verify                   # rebuild everything into a temp dir and compare every package byte
python charbake.py pak <base tex.pak> <out tex.pak> <char:variant>...           # staged switch: play keys replaced
python charbake.py pak <base tex.pak> <out tex.pak> --add <char:variant>...     # toggle disc: variants under own keys
python charbake.py table <game/charbake_variants.h>                             # CHARBAKE_TOGGLE key table
python cb_hair.py <leon_hair_runs.h> <leon4k_runtime.h> <out leon_hair_runs_g2.h> [--report r.json]
```

Inputs are pinned by sha256 in `charbake.json` (paths relative to the store, env `CHARBAKE_STORE`). `build` is
deterministic from the cached bake (same packages byte for byte on every rerun; the cast atlas re-encode of the
unshaded variant reproduces the play package exactly). The Blender step (`blender_ao.py`) is deterministic for one
Blender build (fixed seed, CPU, fixed threads); its cache key includes the script hash. Cast meshes are read in their
own schema (`v4-fit/conservative-mesh.json`; no conversion step is needed). `cb_uv.py` (texel reuse map),
`cb_hair_scan.py` (coincident hair triangles per material) and `blender_preview.py` (flat textured renders) are
analysis helpers.

Shading model: `out_linear = albedo_linear * shade` (gamma 2.2), `shade = max(prod(1 - k_d (1 - ao_d)), floor) *
(ground + (sky - ground) (n_y + 1) / 2) * gain`; the AO is averaged over every surface point that maps to a texel,
weighted by its broad exposure (the source atlases reuse texels for mirrored parts), and dilated 6 texels past each
island so the bilinear filter never reads an unshaded gutter. GCB then multiplies the texel by gain x tint, as the
GameCube's TEV multiplies a texel by its light colour.

## Test discs: the look toggle (`CHARBAKE_TOGGLE=1`)

`CHARBAKE_TOGGLE=1` (test builds; needs COARSE_LEON, COARSE_GANADO_CAST and ACTOR_TRANSACTION) builds the variants of
`charbake_variants.h` (CUR, AO, SKY, GCB, LVQ, GVQ; keys and labels only) into the owner path: each variant draws
through its own image identity (the texture cache keeps the first key of an identity) and its own keys, the hair pair
keys derived as `native_ui.cpp` model_mask_key derives them. The disc's tex.pak must carry the variant packages
under their variant keys (`charbake.py pak ... --add leon:ao ganado:ao leon:aosky ganado:aosky leon:gcb ganado:gcb
hair:gcb leon:vq leon:gcbvq`; 10 packages, +2.1 MB on the disc). With the look study's `LOOK_TOGGLE=1` (and the small
integration patch in native_static.cpp) the look presets gain CA, CS, CG, CV, CQ after the look's own: the play world
with each character variant, stepped with X + START like the rest. DBG_WARP's `charbake <n>` selects a variant at load
and `charbake <n> <room frame>` switches at that frame of the first room (up to 8 lines; the scripted form of the
run-time switch). `CHARBAKE_VARIANT=<n>` sets the boot variant.

## Files

`charbake.py` (driver), `charbake.json` (pinned inputs, variants, toggle rows), `cb_tex.py` (package / twiddle / VQ /
tex.pak I/O), `cb_blob.py` (native actor blob reader), `cb_hair.py` (hair regroup), `cb_hair_scan.py`, `cb_uv.py`,
`blender_ao.py`, `blender_preview.py`. Game side: `game/charbake.mk` (knobs), `game/charbake_variants.h` (generated),
`coarse_actor.cpp` / `coarse_actor_owner_leon.inc` / `coarse_ganado_cast.cpp` / `coarse_actor_owner_ganado.inc`
(CHARBAKE_TOGGLE identities, CHARBAKE_HAIR include), `dbgwarp_bridge.cpp` (`charbake` warp line).
