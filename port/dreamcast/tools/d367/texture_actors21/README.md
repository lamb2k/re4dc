# Actor texture mip candidates

This opt-in offline tool prepares sparse replacements for already accepted
square RGB565 VQ actor textures. The input contract pins the exact normal-pack
winner, selected consumer and private source evidence. It reuses `mipmap_vq.py`;
it adds no runtime, recipe, rendering or SH4ZAM changes.

The existing 2048-byte codebook and full-resolution index plane remain exact.
Lower levels are box filtered and quantized into that existing codebook. They
are intentionally approximate. The five existing Ganado mip packages are
protected and cannot be selected by this tool.

## Selected Leon checkpoint, 2026-10-21

Private set: `texture-actors21-20261021/leon-v1`, mirrored under the Windows
private asset store, with 42 SHA256-verified files. No game data is in Git.

| Evidence | Result |
|---|---|
| Exact recovered Release21 normal pack | 6501 entries, 156254208 bytes, SHA256 `18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef` |
| Selected standard Leon key | `ec255e66-76812316`, 512-square RGB565 VQ |
| Consumer | `coarse_actor.cpp` and `charbake_variants.h`: CUR / boot variant 0; Test21 recipe enables PS2_LEON and CHARBAKE_TOGGLE; `charbake.mk` defaults the variant to 0 |
| Selected private runtime header | SHA256 `4bc27368debda1009875c0d69e9fa15da4589f7825385eb9179ca3360a219d22`; every role's quantized source-mesh UV set matches its runtime array |
| Source package | `954af686e924e0d7c5d8043b1fec60bf7b17b254cf61154408be840a35a93c99` |
| Candidate package | `dae101e984f8e373188006345d543480f329995755a1614ee1a60cc4a7c1fd6c` |
| Exact preserved codebook | `19b7db700fc8fe7c254245fa8f5780e18f942ea93da51ff22f6ea70813b02242` |
| Exact preserved base indices | `87f0ea6c56b1038318f27751d89d9b0cfa62e494d292d6575dd2eb8081e029c5` |
| Independent decoder | Pinned KOS pvrtex oracle, binary SHA256 `79f1a50557ca59383ce12c67f370eaa30393fe8015ede0c0186a72714d0f8868`; all 10 levels pass |
| Unrelated pack entries | All 6500 exact, including the existing five Ganado mip packages |
| Payload allocation request | 67584 to 89430 bytes: +21846 bytes |
| Request rounded to 32 bytes | 67584 to 89440 bytes: +21856 bytes |
| Canonical reconstructed pack | 156274688 bytes, +20480 archive bytes; SHA256 `0e3544de07b3543bfb83e31f5197ecb9ed551f735560f2a65edd47a7c414d55f`; reconstructed in memory, no full pack output |
| Private file receipt | `leon-v1/SHA256SUMS`, SHA256 `0eb41ec8489be58e4d1a904ffc1e2374c727ff8c53af96e7e9343eb4bb285af1` |

The raw original Release21 disc track is absent. The exact pack was recovered
from the sealed farm candidate and preserved originals, then checked against
the retained release manifest. The selected source files and manifest are
copied into this private candidate and hash pinned.

## Leon sampling policy and limitation

Leon's nine atlas tiles retain their two-texel gutters. The source mesh uses
`x=u*512, y=(1-v)*512`, matching `ps2leon/pack_arm.py`. All 4473 body triangles
and 13419 corners belong to one tile per triangle. The separately owned hair
role uses its colour/mask runs and is excluded from the body footprint audit.
The atlas is opaque RGB565; its alpha values and the separate masks are exact.

The audit combines each mip's aligned source box with both bilinear taps. It
is a conservative source footprint bound, not measured screen derivatives or
proof that a camera selects a level. At an exact tap centre it still includes
both taps. It does not assume that a two-pixel gutter is sufficient forever.

| Mip side | Body corners with a footprint crossing their tile | Filter boxes mixing tile owners |
|---|---:|---:|
| 512 | 0 | 0 |
| 256 | 0 | 0 |
| 128 | 69 | 0 |
| 64 | 1172 | 0 |
| 32 | 2371 | 0 |
| 16 | 4065 | 0 |
| 8 | 7094 | 0 |
| 4 | 11827 | 2 |
| 2 | 13419 | 3 |
| 1 | 13419 | 1 |

**The full Leon chain is a private review candidate. Its sampling has not been
accepted for runtime adoption.** The 512 and 256 footprints are contained;
the 128 and smaller levels need an explicit sampler/atlas decision and a look
check. The tool changes neither UVs, atlas layout nor sampling state. Blind
padding or stretching would change the source contract and is not performed.

Private previews include the unchanged original, each mip, corresponding box
references, a contact sheet and `quality.json`. At 256, fixed-codebook
quantization measures 29.37 dB RGB PSNR against the rounded box reference;
this describes a texture-level difference, not a gameplay image or acceptance.

## Use

The private JSON contract has schema `re4dc-actor-mip-contract-1`, an exact
`source_pack_sha256`, SHA256-pinned `proofs` with explicit IDs and paths, and
explicit `textures`. A standard Leon binding requires the selected source,
variant, recipe, default, tile, source mesh and selected runtime header proofs.
A native-registry binding requires a pinned `.re4nmr` whose texture entry is
actually referenced by a descriptor's primary geometry. Native registry UVs
are read for bounds and preserved. Atlas lower-level acceptance stays pending
unless separately qualified. Alpha-bearing actor textures currently refuse:
they require a separately reviewed coverage policy.

Generate with a Python environment containing NumPy and Pillow:

```sh
python actor_candidate.py --source-pack /private/tex.pak \
  --contract /private/actor-contract.json --out /private/new-actor-candidate \
  --enable-mipmaps --engine numpy --previews
```

Omit `--enable-mipmaps` for exact base-package identity. Existing output
directories refuse. Only the sparse original/replacement packages and their
evidence are written; normal-pack lookup remains authoritative.

On the Linux host, independently decode and seal all levels:

```sh
python3 seal_candidate.py /private/new-actor-candidate \
  --source-pack /private/tex.pak --oracle /private/pinned-oracle.so \
  --oracle-sha256 EXPECTED_SHA256
```

The seal checks every decoded mip against the actual KOS decoder, independently
compares original and candidate base pixels, verifies protected/unselected
members, reconstructs the canonical pack in memory and writes SHA256SUMS.
Mirror that sealed set to the Windows private store and verify every receipt.

```sh
python3 test_actor_candidate.py
```

Eight source/tool regression tests cover explicit selection, disabled identity,
owner and hash refusal, primary-geometry binding, protected Ganado packages,
atlas boundaries and source-mesh/selected-runtime UV disagreement. These and
the private decoder seal establish source/data correctness. Runtime VRAM,
residency, look, gameplay and physical hardware timing remain separate gates.
