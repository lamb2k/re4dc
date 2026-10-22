# mipmap23: bounded coverage additions

The follow-on item unit qualifies two further PS2 item keys atop the six-chain
candidate below. It uses the unchanged PR53 converter and quality policy.
The 70-row ledger is reused, never rerun as a new census.

| Key | Current PS2 carrier | Result | Extra allocation |
| --- | --- | --- | ---: |
| f9282a10-6ed63371 | ITM itm57 in eleven source room archives | RGB565 VQ chain | 352 bytes |
| fdb79120-f3f8ce57 | ITM document ae/b0/b2/b3/b4 in five source room archives | RGB565 VQ chain | 352 bytes |

next_preflight.py pins the first-six candidate as input, compares it against
the current RR-selected pack, and requires exactly the six prior differences.
It validates actual PS2 manifest/package hashes, current R4NREF records in all
sixteen source uses, current resident preloads and compatible native sampler
source. It does not infer usefulness or release readiness from the ledger.

Input: 6f65275b62838bdff6e7660a2ba8d6b2b43ffabb09cadf5ae05dabb34d9d6c1e.
Combined output: e45f7d6669798715e0edc8f5d88e15eee381d336855aa2a24626f14dcce48f96.
Both packs are 162,205,696 bytes; additional payload 684 bytes and rounded texture
allocation 704 bytes. All 7,297 unselected packages, the first six chains, the
colour-held object and all 41 shared Ganado packages stay exact. Twelve proposed
levels passed through 1x1 and were independently read back; base payloads and
pixels remain exact. Converter suite: eleven tests pass.

The actual RR map still selects mip22b tex.pak, now alongside res22c resident.bin.
The output is a candidate additive texture replacement. Keep current RR resident,
world and other files; this unit produces no runtime or residency files.
qualify.py --report-name qualification-items.json reuses the existing output
readback without a seven-key schema or stale resident-file description.

Native model resolve passes package flags through texture::pvr_format and compiles
a bilinear PVR header; CAST_MIPMAP admits the mip TCW bit. The source TPL LOD
[0,0,0] fields do not clamp this native model-header path. This establishes
source compatibility, not observed minification, visual approval, room fit,
Flycast or physical-console acceptance.

Current resident preloads add r101 704 bytes and r103/r108/r109/r117/r119 352
bytes each. Other positive source consumers add 352 bytes if loaded dynamically.
Full consumer uses are in the private receipt; the review ledger's truncated
room lists must not be used as absence evidence.

Of the original seventy review candidates, eight are now converted and one
remains colour-held. Sixty-one are unconverted: shared GC Ganado 24, cutscene 12,
PS2 item 8, mask 6, Leon variant 4, standard actor 3, core effect 3, shared
breakable 1. These counts describe review progress, not an approval queue.
All 57 original convert-blocked rows remain untouched (including 17 shared
Ganado rows), as do the original excludes and allegedly unreachable rows.
No pruning is authorized.

Next compatibility work: inspect material flag 1 and exact current model binding
before the remaining opaque itm3b/itm1c keys; verify paired alpha/material use for
six remaining item keys; resolve mask consumer/coverage; trace variant selection
and cutscene/effect samplers. Non-square or multi-image blocked inputs require
a separately qualified runtime-compatible layout extension, not speculative
square padding or relaxed gates. Shared consumers remain held while unresolved.

No runtime, arena, allocator, inventory, recipe, guest, disc or release work.
Private generation/mirroring stays local. Coordinator owns adoption.

---

# mipmap23: seven room-object candidates

Local package qualification of the first seven positive-preload PS2 room-object
candidates from PR53. No further keys are approved by this unit.

Source starts at PR53 merge `bfce2800cbd726b18fbb416ee39d64c07ab00c23`,
rebased onto t15/int `64a28a7bdc44312924b14414501b7d4ff1d2d032`;
rebased converter checkout `c3cfd8b254d9b62ecc9877741099a1d6dce37e5f`.
The original PR53 ref is retained locally as
`refs/mipmap23-provenance/pr53-bfce2800`. The parked Claude checkout and its
uncommitted classifier were not used or changed. The PR53 converter, codecs,
quality policy and room-selection manifest were not modified.

The actual RR64a28a7b package map selects the current private mip22b pack, which
includes mip22. Input pack SHA-256:
`5bba464a1175d8ebe153d5aecb629ea9637807c2bf4fc438a32c17148d0729da`.
Output pack SHA-256:
`6f65275b62838bdff6e7660a2ba8d6b2b43ffabb09cadf5ae05dabb34d9d6c1e`.

## Result

| Key | Result | Added texture allocation, bytes |
| --- | --- | ---: |
| 09b9d35d-9a1a2fc2 | 64 RGB565 VQ chain | 352 |
| 4f784887-fc80dbee | 64 RGB565 VQ chain | 352 |
| 5926862b-e61d4941 | 256 RGB565 VQ chain | 5,472 |
| c8d0db2f-3126bc5d | Held exact original: lower-level VQ colour gate | 0 |
| daa3d452-b10799f3 | 256 ARGB4444 twiddled chain | 43,712 |
| de020f0a-cc184ee1 | 256 RGB565 VQ chain | 5,472 |
| f56596f9-c3b192f2 | 64 RGB565 VQ chain | 352 |

Pack size: 162,154,496 -> 162,205,696 bytes (+51,200). Added payload is
55,646 bytes, rounded texture allocation +55,712 bytes. Pack alignment explains
why the pack-file delta differs from the payload delta.

All 7,299 member keys stay present. All 7,292 unselected packages are exact,
as is the one selected held package. All 41 shared Ganado packages stay exact;
39 unresolved consumers remain held. No pruning or format/codec substitution.

## Qualification and limits

The existing texsrc22 converter suite passed 11 tests, including the actual
current external quality gate. The actual whole pack is exact with conversion
OFF. Generation audited all 49 proposed lower levels through 1x1; independent
output readback through the existing native decoders rechecked 42 accepted
levels, every selected base payload/pixel array, alpha histograms and package
checksums. The seven rejected levels belong to the held texture and are not
claimed to exist in the output. Original VQ codebooks/base indices and twiddled
base texels stay exact. Gate thresholds were not loosened.

Quality gate SHA-256:
`5eeba3db83758935d4302d7bbd7d2942edc4e61ef90a1bc58884e9e7e481c7fd`.
Current room-select SHA-256:
`fd9dc25d14e05cfc581a777814480e0f3cacf02f5d574bb5785bf57e2b25fe3d`.
Input pack hash, size and timestamp, the RR package map, and resident.bin hash
remain unchanged after qualification.

Static per-room preload allocation changes are:

| Room | Added bytes |
| --- | ---: |
| r103 / r108 / r118 | 0 (held member) |
| r104 | 352 |
| r106 | 10,944 |
| r109 / r119 | 352 each |
| r10a | 5,472 |
| r10b | 44,064 |
| r11b | 43,712 |

These are additions for each room's actual resident.bin references, not measured
VRAM peaks or demonstrated room fit. A key can also be loaded by another object
or event. In particular de020f0a has an r104 source label but no r104 preload
record in the selected current resident.bin; such a dynamic consumer would add
another 5,472 bytes there. Do not infer absence from that missing preload.

The inspected R4PW world-material tables do not bind these seven object keys.
Positive preload evidence authorizes this private candidate; actual object
sampler binding, minification, look, room/re-entry fit, Flycast, release checks
and physical Dreamcast acceptance remain open. No FPS or performance gain is
claimed. This unit changes no runtime, recipe, arena, inventory or benchmark.

## Local workflow

Use a new private output directory for every run. Private assets never leave
the local machine. The exact input identities and seven-key selection are
checked before the converter runs:

```sh
python3 preflight.py --rr-package /local/current-rr-package.json --out /local/new-private-set
python3 ../texsrc22/convert.py --pack /local/current-mip22b/dc/tex.pak \
  --selection /local/new-private-set/selection.json \
  --quality-gate ../mipmap21/mip_quality.py \
  --hold-keys ../mipmap22/room-select.tsv --enable \
  --out /local/new-private-set/dc/tex.pak \
  --report /local/new-private-set/conversion-report.json
python3 qualify.py --dataset /local/new-private-set
```

The preflight intentionally pins this bounded unit's exact current pack and
seven-key cohort. A future baseline requires a separately reviewed input pin.
The private dataset carries full receipts and SHA256SUMS; it supplies only
`dc/tex.pak` as an add-on over current mip22b. Current resident.bin, world
packages and runtime tables remain in place. Coordinator owns adoption.
