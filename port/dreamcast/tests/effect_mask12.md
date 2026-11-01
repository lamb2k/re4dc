# EFFECT_MASK12: bounded RGB565 mask material

`EFFECT_MASK12=0` is the default. The strict selector requires
`EFFECT_SPRITES=1 EFFECT_LEAN=1 NATIVE_DRAW_OUTCOMES=1 FX_STRIP21=1
D349_RENDERER_STACK=1 PVR_STREAM=1 UI_HANDLES=1`. It defines the new macro only
for esp_sub.o, native_ui.o and gx_stub.o. No public sprite layout changes.

The supported producer remains EspCommonTrans and its existing eligibility,
callback, owner, policy and ChannelSet path. A separate result entrypoint carries
one private material argument through the existing packet/FIFO machinery.
EspMaskClass12 checks the current mask descriptor is RGB565 (TEXA=1), the source
blend/material flags, base object/descriptor identity, captured clamp/linear
sampler and LOD state, identity base UV rows and finite independent mask UV rows.
Deformed 1b, haze, variable-alpha masks, unsupported TEV/depth/destination alpha,
RTT capture and whole-EFB operations are excluded.

The source stage preserves CPREV RGB and replaces alpha with mask TEXA times
raster alpha. With TEXA=1 this is exactly raster alpha or clamped four times
raster alpha. Final alpha <=1 is culled after source policy; raw alpha 1 under
SCALE4 becomes 4. The PVR material disables texture alpha, preserving native
sampled RGB. Ordinary/masked headers and body-only reuse include material mode.
Masked draws bypass base-alpha trimming. This does not change ordinary trimming.

Entry acquisition uses existing resolve/upload and UI_HANDLES reset epochs.
Before publication the masked path checks frame/epoch, Entry key and validity,
frame pin, completed upload, one texture and nonnull VRAM. It admits only
RE4DCTX v2 ordinary RGB565/ARGB1555/ARGB4444 linear/twiddled payloads, alpha/binary
alpha flags and zero reserved/header metadata. Marked PS2/coverage replacements,
palettes, VQ and mips are refused: their preprocessing lacks a preserved
transparent-RGB contract. In particular PS2 palette matching uses premultiplied
distance, and VQ quality metrics ignore fully transparent RGB. Neither class is
claimed to recover the required color. Refusal before publication can use the
existing legacy fallback; stream abort remains PartialAbort even with zero
submitted bytes and cannot replay.

Run from the repository root:

```sh
python3 port/dreamcast/tests/test_effect_mask12.py --output /tmp/mask12-host
python3 port/dreamcast/tests/test_effect_mask12.py --sanitize --output /tmp/mask12-san
python3 -m unittest port/dreamcast/tests/test_effect_outcomes03.py port/dreamcast/tests/test_esp1b_grid03.py
```

The dedicated fixture executes actual eligibility, EspCommonTrans, emitter,
native result/header/packet, FIFO drain/reset and actual gx_stub sampler capture.
Four FAST/SETUP/GRID configurations cover every raster alpha and SCALE1/4 with
transparent/partial/opaque base samples, mode transitions, queue/direct/abort0,
cold-load/retirement and refusal boundaries. A separate witness executes real
RGBA8 decoding and convert_tpl packing through production Package adopt, upload
and release_payload; alpha-zero colored texels survive both linear and twiddled
upload paths. The upload device and PVR header compiler remain synthetic.

OFF checks compare preprocessed complete recovered esp_sub.cpp and gx_stub.cpp
against the clean requested dependency merge, including grid and __sh__ branches;
native packet/result scaffold and complete gx_stub host objects are compared too.
Make tests cover exact expanded selectors, whitespace, dependencies and target
macro scope. Whole native_ui target object identity, SH4 compilation, GPU blending,
interpolation/rounding, runtime frequency, cost and console/image acceptance
remain separate gates. No speed claim follows from these fixtures.

Dependencies are origin 9fed62186acbfbd0f36aa6ff328244b51a94ce39 plus clean
automatic merges of EF03 corrective 7ded0fa430f122eebeb38d2617d8ff19c67cd5c2
and grid 73e73e02202f3b6b3658f0b8a72b8ed2d5cf004b. The resulting baseline is
15308a90d35b9b30e99ae320eaa42b29cfaf7f6b; the identity fixture records that pin.
