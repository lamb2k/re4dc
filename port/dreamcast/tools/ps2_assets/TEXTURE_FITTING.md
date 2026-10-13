# Conservative PS2 world texture fitting

`../fit_ps2_world_textures.py` consumes the existing per-room handback indices and
writes private texture proposals and exact staging lists. It never writes a
pack, fixture, source texture, mesh, game runtime or shared output. The existing
`vq_native_ui.py` command line is unchanged; its encoder is reused directly.

```sh
python port/dreamcast/tools/fit_ps2_world_textures.py \
  --index /private/stage1/index.json --index /private/castle-index.json \
  --output /private/texture-fit
python port/dreamcast/tools/fit_ps2_world_textures.py \
  --output /private/texture-fit --verify
```

The default priority is r117, r112, r200. Lists become available room by room.
Inputs are checked against their handback hashes before encoding. Each lookup
key has one central choice, shared by every room. Baselines with the same key
must have identical bytes from offset 112 onward (dimensions, format, flags,
layout and payload); material-label differences alone are compatible. Conflicts
fail closed and appear in `collisions.json`.

## Selection policy

Existing VQ files remain unchanged. Native twiddled 16-bit files of at least
32,768 payload bytes and with both sides at least 32 are tested using full
256-entry KOS pvrtex VQ. Dimensions, format, original material label and flags
are retained. Every output is decoded from its actual payload and compared
with the baseline's already-quantized pixels. Selection requires:

- Exact decoded alpha at every texel, including graded alpha, with zero alpha
  changes. Equal opaque coverage alone is insufficient.
- At least 30 dB unweighted RGB PSNR over the entire native image. The report
  also records coverage-weighted RGB PSNR and alpha/coverage counts. Values of
  99 dB represent exact equality, not a measured finite PSNR.
- A smaller payload and acceptance by the runtime-derived texture parser.

These are conservative, configurable candidate criteria, not human appearance
acceptance. Selected textures still require room stills and user review. A
failed candidate retains native bytes even when room residency is unknown.
The report never asserts a complete room fits on the basis of world payload.
Framebuffers, actors, UI, effects, allocator overhead and transition overlap
are excluded from these world-only sums. Runtime residency evidence is needed
to decide whether more fitting is required.

No mipmaps are added. The present inputs have a base level only; the runtime's
optional mip mode requires square VQ plus `CAST_MIPMAP`, and mip chains increase
payload. Indexed/palette conversions and unsupported mip inputs are not
silently introduced. Twiddled16 and existing VQ sampling contracts remain.

## Private outputs

- `rooms/<room>.json`: source world package paths/hashes, every source baseline
  texture, chosen exact path/SHA-256/body CRC, dimensions/format/mip policy,
  candidate metrics, reason and world payload before/after. Complete-room
  budget/headroom is explicitly unknown.
- `winners.json`: one choice per key, rooms consuming it, all candidate metrics,
  collision state and a digest of the ordered winning key/SHA/body-CRC list.
- `index.json` and `winner-inventory.txt`: complete room inventory, per-room
  staging-list digests, unique payload sums and pinned converter/tool hashes.
- `cache/<input-and-tool-digest>/`: one proposal plus source/VQ PNG previews,
  pvrtex transport data and comparison metadata. Originals are never modified.

The runtime lookup filename is intentionally retained for VQ overlays. The
fresh converter's filename-derived payload hash invariant therefore does not
apply to a changed overlay. Runtime descriptor/body CRC validation still does.
The package CRC is the uint32 at offset 36 over all bytes from offset 48.

## Check actual fixture winners

```sh
python port/dreamcast/tools/audit_ps2_texture_winners.py \
  --pack /private/existing-tex.pak --room /private/texture-fit/rooms/r200.json \
  --fixture r200=/private/cx-r200-entry.armed.json \
  --output /private/texture-fit/r200-fixture-audit.json
```

This command reads the pack without writing it. A matching packed key wins; an
absent key may select the fixture's exact loose replacement. A stale packed
member shadows a correct loose file and fails selection. Removals are honored;
matching texlow overrides require explicit mode resolution. The source pack
and fixture must remain stable during the audit.

`PASS_SELECTED_RENDER_BYTES` means the sampled fixture resolves bytes 112 onward
to the requested selection. Label-only variants keep their actual winning
header/body CRC in the report; canonical CRC differences are separately counted.
This does not certify a live TEX_CHECK run, memory headroom, or the complete
future shared pack. Final pack application remains a separate integration step.

## Tests

```sh
python port/dreamcast/tools/test_fit_ps2_world_textures.py -v
```

The suite uses synthetic packages and the actual pinned encoder when available.
It checks native/VQ roundtrip, deterministic output, exact alpha, preserved
flags, an independently specified codebook/twiddle example, corrupted CRC and
malformed payload rejection, and packed-versus-loose precedence. The actual
runtime `Package::adopt/validate` is compiled with host-only filesystem/PVR
stubs; upload and gameplay are not executed. A missing pinned encoder skips its
roundtrip test explicitly rather than claiming an encoding result.