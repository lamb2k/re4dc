# Optional native16 base alpha reader

`tr_classify.py --mip-aware-alpha` (API:
`Textures(dirs, paks, mip_aware_alpha=True)`) reads the **base** plane of
supported native16 textures. The option defaults off. Existing recipes are
untouched. `stats`, `tex_class`, `part_class`, and `classify_room` are unchanged.
This is an offline alpha sampling repair, not a policy change.

VQ reads the full 2048-byte book and the final base index plane. Mipmapped
VQ indices begin with 1x1 and then every 2x2-block level through base.
Twiddled16 reads the final base words after the six-byte prefix and smaller
levels. These contracts match the existing native Package validator and
`mipmap_vq.py` / `mipmap_twiddled.py`. Morton permutation does not change a
histogram. Nonmip linear, twiddled, and full-book VQ RGB565/1555/4444 are
supported, including valid rectangular dimensions.

The opt-in reader validates one standard descriptor, power-of-two dimensions
8..1024, exact whole-file/header/payload extents and expected chain size,
known texture flags, zero disk descriptor reservation, and a recognized CRC.
It returns None for missing, truncated, unsupported or invalid input. PAL and
unknown formats remain explicitly unsupported in this mode. Default mode
retains the historical PAL and mip behavior unchanged. Offline inputs accept
both canonical descriptor+payload CRC and the legacy payload-only CRC
convention; this is **not** a strict runtime Package admission gate.

The opt-in result still passes through the existing classification policy.
Previously generated R4TC class bytes must be compared per material by a
separate gate; this option does not restamp or authorize changing metadata.
No R4TC or asset was generated in this unit. No runtime, programme, image,
guest, rendering, selected-LOD, performance, release or hardware acceptance
is claimed.

## Reproduce source/host qualification

From this Git checkout:

```sh
python3 port/dreamcast/tools/d367/alpha_reader21/qualify.py \
  --oracle /root/probe/mipmap21-checks/libmipmap_pvrtex_oracle-twiddled.so \
  --out /path/to/new/summary.json
```

The oracle must already exist and export both VQ and twiddled decode APIs.
Qualification does not build it. The existing pinned KOS pvrtex library
independently decodes 1555/4444 BASE texels for all 64 authored layout/size/
mip/CRC cases. Lower levels deliberately differ from base, reproducing both
legacy bugs. Tests compare full decoded alpha histograms and texel counts,
prove default/explicit-off and supported nonmip compatibility against parent
0425534d, compare the unchanged classification ASTs and legacy reader body,
and reject malformed/unsupported inputs. Package/oracle/source identities
are recorded in the summary. Fixtures are synthetic and remain in memory.
