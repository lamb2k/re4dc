# Opt-in native mipmaps

Native-package mode in tools/vq_export.py adds lower mip levels to an existing
square 16-bit full-codebook VQ package. It retains the original 2048-byte
codebook, largest-level indices, dimensions, material identity, source flags and
CRC convention. Existing base-level texels therefore decode identically.

This is an offline candidate path. It changes no runtime defaults. The existing
CAST_MIPMAP reader path must be enabled when these candidate packages are used.

## One package

    python port/dreamcast/tools/vq_export.py --native-package input.re4tex --package control.re4tex
    python port/dreamcast/tools/vq_export.py --native-package input.re4tex --package candidate.re4tex --add-mipmaps

Without --add-mipmaps the output is byte-identical to the input. New outputs are
exclusive: existing files are never overwritten. Existing encoded-VQ exporter
modes keep their previous behavior.

Input must have one version-2 native descriptor, square power-of-two dimensions
8 through 1024, RGB565/ARGB1555/ARGB4444, and a complete 256-vector VQ codebook.
Already mipmapped packages return unchanged. Rectangles, palettes,
linear/twiddled texels and runtime top-drop representations are refused by this
initial path; they need their own layout contract.

Lower levels use integer premultiplied color box filtering and nearest vectors
from the existing codebook. The optional NumPy engine is an offline speed aid;
its result is byte-identical to pure Python, including ties. No dependency is
required. Lower levels are lossy and need a same-scene visual review before
adoption. No original base texel is re-encoded.

The layout follows primary KOS pvrtex: smallest level first, Morton ordered VQ
indices, TL/BL/TR/BR vectors. The 1x1 level uses the fourth expanded-vector pixel.
Independent tests use the pinned pvrtex decoder, not a second copy of the new
encoder's layout logic.

## Checks

    python -m unittest discover -s port/dreamcast/tests -p test_mipmap_vq.py -v
    python -m unittest discover -s port/dreamcast/tests -p test_mipmap_runtime.py -v
    python -m unittest discover -s port/dreamcast/tests -p test_convert_tpl.py -v

The runtime test host-compiles the existing Package reader with CAST_MIPMAP
off/on. It checks all three formats, TCW VQ/mipmap bits, base admission,
truncated-chain refusal and the existing release streamed-CRC behavior.
It does not build the game or establish rendering or frame time.

Optional independent decoding is enabled with
MIPMAP_PVRTEX_ORACLE=/absolute/path/to/libmipmap_pvrtex_oracle.so. Build that host
library from tests/fixtures/mipmap_pvrtex_oracle.c and pinned KOS
utils/pvrtex/{pvr_texture_decoder.c,pvr_texture.c,mycommon.c}, using the pvrtex
include directory and -lm. No codec sources or binaries are duplicated here.

## Implementation checkpoint, 2026-10-21

At integration source 54cef5d1, the VQ suite passed on WSL using the independent
decoder (one NumPy check skipped), and on Windows with NumPy 2.5.3 (one Linux
decoder check skipped). Existing converter suite: 16/16. Actual reader: 4/4.
No game build, master, emulator, physical console, timing or look acceptance is
implied by these host checks.

The first intended private selection is the r103 farm's 15 compatible keys.
Payload/allocation deltas, precedence and unchanged archive members must be
checked against its exact release input before staging. Private source assets
and generated packages never belong in this repository.

## Room-selected packed candidate

    python port/dreamcast/tools/d367/mipmap21/world_candidate.py --track /private/track03.bin --release-manifest /private/manifest.json --room 103 --output /private/new-control
    python port/dreamcast/tools/d367/mipmap21/world_candidate.py --track /private/track03.bin --release-manifest /private/manifest.json --room 103 --output /private/new-candidate --generate

The named archive and world sidecar must match the supplied release manifest's
sizes and SHA-256. The source pack must rebuild byte-exact with the existing
texpack builder. Only referenced compatible square 16-bit VQ keys are eligible.
The default control is byte-identical. Unsupported format families are listed,
and missing normal packed world keys refuse the candidate. Other archive members
remain byte-identical. The tool reports payload bytes, 32-byte request rounding,
archive-sector padding and every member hash separately. Global keys shared by
another room change there too if this pack is staged.

New private directories only. No disc, source tree, program or release is changed.
SHA256SUMS uses portable slash-separated paths for WSL and Windows mirrors.

    python -m unittest discover -s port/dreamcast/tests -p test_mipmap_world_candidate.py -v

Five selection/control/refusal host tests pass. The first retained Release21
r103 private data candidate changes 15 members, leaves 6486 unchanged, adds
16394 payload bytes and 16544 bytes after 32-byte request rounding. Existing
archive padding absorbs the additions: archive size is unchanged. Independent
pvrtex decoding agrees on all 116 candidate levels and every original base.
This is data evidence; actual residency, look and frame time are pending.

## Compact palette mips

The same --native-package / --add-mipmaps interface also supports one square
twiddled PAL4 ARGB4444 package (native format 4). Its 4-bit base indices and
32-byte palette tail stay exact. Lower levels choose from the same palette using
integer premultiplied-color filtering. No palette expansion or new palette bank
is added. The 1x1 nibble is replicated for hardware/legacy decoder agreement.

Runtime use requires TEX_PAL4_MIPMAP=1 TEX_PAL4_ALPHA=1 CAST_MIPMAP=1.
TEX_PAL4_MIPMAP defaults to 0 and only defines its native texture Package object.
It admits the square compact chain, validates its exact size, preserves the
existing fenced palette owner and forwards the TCW mip flag. With it off, the
actual host object is byte-identical to integration source 54cef5d1. A full
Dreamcast program off-identity build has not been run.

    python -m unittest discover -s port/dreamcast/tests -p test_mipmap_pal4.py -v

Nine host tests cover independent pinned decode of all levels/partial alpha,
palette/base/header preservation, legacy CRC, pure Python/NumPy identity,
exporter opt-in, malformed layouts, actual upload/palette-tail/fence behavior
with ASan/UBSan and both allocator paths, build-flag constraints and host object
off identity. The optional oracle and NumPy run on the respective equipped host.

The retained normal pack has 622 such palette keys, 554 square, with no
world-sidecar owner among them. Three private data fixtures at 8, 64 and 256
square decode correctly across all 20 levels, with exact original bases and
palettes. Subsequent source/reference and library-hash checks identify all 622
as PS2 effect-frame conversions; see the compact cohort below. Compatibility does not
authorize indiscriminate mip generation for UI text or effect atlases.
Palette VQ, PAL8, rectangles and strided textures need their own contracts.

## All selected native worlds

Replace --room 103 with --all-worlds to select the named world sidecars in the
bound release manifest. --progress prints bounded offline conversion progress.
Every input sidecar is hash-bound separately. Shared texture keys are converted
only once. The per_room table reports each room's referenced compatible keys and
payload/32-byte-request sums, with an explicit overlap/non-residency warning.

    python port/dreamcast/tools/d367/mipmap21/world_candidate.py --track /private/track03.bin --release-manifest /private/manifest.json --all-worlds --output /private/new-world-candidate --generate

The retained Release21 candidate covers all 508 directly supported square
16-bit VQ keys among 1488 world-reference keys across 29 selected sidecars.
All 4100 generated levels agree with the independent decoder; all 508 original
bases/codebooks/indices stay exact and 5993 other archive members are identical.
Archive: 156254208 -> 156889088 bytes (+634880). Lower mip payload: +1222312
bytes; 32-byte allocation requests: +1227392, across the entire multi-room
inventory. These are not a simultaneous working set, resident peak or timing.

Seven room-selector tests include all-world path filtering and shared-key
deduplication with intentionally overlapping per-room inventory sums.

Compatibility is an implementation boundary:
- 508 square 16-bit VQ keys use the existing direct runtime layout.
- 188 square twiddled 16-bit keys preserve full-resolution texels with a
  mip prefix using TEX_TWIDDLED_MIPMAP, described below.
- 672 rectangular VQ and 120 rectangular twiddled keys need a correct square
  texture-domain/UV/wrap/edge contract. Padding can preserve base pixels but
  changes sampling semantics unless the renderer and each lower level agree.
  Do not silently stretch, pad or recompress them.
- Palette owners, UI/effects and unclassified packages remain a distinct
  adoption decision. Filtered lower mip levels are not lossless copies; the
  promise here is exact preservation of the original full-resolution data.

No recipe, release, runtime defaults or frame-rate claim accompanies this
private whole-world data candidate.


## Native16-bit twiddled mip support

The native-package exporter also supports square twiddled RGB565, ARGB1555 and
ARGB4444 without re-encoding their original texel plane. It places the exact
base words behind the PVR's six-byte/mip prefix and generates lower planes in
the same native format. Integer premultiplied-color filtering prevents hidden
transparent RGB bleeding; the existing converter's native packers preserve the
format's binary or partial alpha rules. Lower planes are deliberately filtered
and quantized, not lossless copies.

Runtime requires TEX_TWIDDLED_MIPMAP=1 CAST_MIPMAP=1. The new knob defaults to
0, defines only the native Package object, admits the exact square native
layout, and uses the existing shared sampler's mip flag. Upload stays a native
copy, not an upload-time twiddle. The original material/UV dimensions and flags
stay exact. Linear payloads and rectangles remain refused by this path.

For all selected worlds, opt in separately:

    python port/dreamcast/tools/d367/mipmap21/world_candidate.py --track /private/track03.bin --release-manifest /private/manifest.json --all-worlds --include-twiddled --output /private/new-square-candidate --generate

Omitting --include-twiddled keeps the previous VQ-only selection. Disabling
--generate is still whole-archive identity, even when the new family is selected.

    python -m unittest discover -s port/dreamcast/tests -p test_mipmap_twiddled.py -v

The complete mip suites now run 39 tests on WSL with the independent decoder,
passing with only the two optional NumPy checks skipped (NumPy parity is checked
on Windows). New cases cover every level/all three formats, exact bases/CRC/
header/flags, binary and partial alpha, hidden-color filtering, CLI opt-in,
actual Package admission/upload/fences with ASan/UBSan, sampler bits, refusal of
malformed/linear/rectangular mips, object-target build guards and explicit room
selection. Both new runtime knobs at 0 retain the exact host object for 54cef5d1;
a full Dreamcast program off-identity gate remains unrun.

This texture path neither removes nor upgrades SH4ZAM. The eventual combined
target must retain its selected SH4ZAM/SKIN_SH4ZAM CPU skinning configuration and
existing skinning-batch UV contract. Source/data/host checks do not replace that
combined target's VRAM, look and frame-time gates.

The sealed combined square-world candidate contains 696 changed keys (508 VQ,
188 native twiddled), with 5805 unrelated keys exact. Its 5376 levels agree with
the independent pinned decoder and every original base is exact. Pack size is
157874176 bytes (+1619968); lower-level payload adds 2335592 bytes and 32-byte
request inventory adds 2343680. These are multi-room inventories, not live peaks.

## Lossless VQ before adding texture cost

compact_native_vq.py dictionary-codes existing native 16-bit or PAL4 base texels
into the existing full-codebook 16-bit VQ format. It changes no full-resolution
RGBA or alpha values. It succeeds only when every distinct 2x2 vector fits 256
entries and both total payload and 32-byte request size shrink, including the
entire 2048-byte codebook. Existing mip chains are preserved. Larger dictionaries
are reported as requiring lossy quantization; small PAL4 frames remain compact
when the VQ codebook overhead would lose. There is no runtime or default change.

compact_candidate.py requires an explicit key selection with original package
hashes and source-owner evidence, bound to the exact release manifest/pack SHA.
The default produces an exact control; --generate opts in. Unselected members
remain byte-identical. Inputs may be a retained track or an exact pack file:

    python port/dreamcast/tools/d367/mipmap21/compact_candidate.py --source-pack /private/tex.pak --release-manifest /private/manifest.json --selection /private/selection.json --output /private/new-compact-candidate --generate

Source converter fx_ps2_pack.py creates one package per effect frame with a
shared 16-color palette and a covered-UV marker. All 622 selected Release21 PAL4
keys have active EFF source references and byte-exact private-library matches.
Of 554 square frames, 20 fit lossless VQ with a total byte win: 19 at 128 square
and one at 256 square. The private candidate saves 53888 payload/request bytes
and 53248 archive bytes. All 20 independent before/after RGBA decodes agree; 6481
other keys are exact. Material, dimensions, alpha and covered-UV flags remain
exact. No new mip levels or runtime flags accompany this candidate.

The original retained raw track is no longer available at its recorded path.
The exact original texture pack was recovered from the sealed farm candidate
by restoring its 15 preserved source members. Its whole-pack SHA-256 matches
both the original receipt and release manifest:
18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef.
This recovers texture-pack bytes, not a game disc or program. No newly hosted
release or replacement raw-track identity is claimed.

    python -m unittest test_compact_native_vq test_compact_candidate -v

Run from port/dreamcast/tests with the optional pinned decoder enabled. Nine
tests cover exact RGBA/alpha/metadata, every 16-bit family and both source CRC
conventions, dictionary overflow and overhead refusals, existing-chain safety,
actual Package upload and sampler VQ bits under both allocator paths with
ASan/UBSan, source/selection hash binding, exclusive output and OFF identity.
No game build, rendered-look, live VRAM or physical-console gate was run.

## Whole-pack owner and quality policy

source_coverage.py combines the exact packed-winner descriptors with the
preserved named-source probe, native-world sidecars and native-model registries.
Every preserved source-file hash/size must match the release receipt. Normal
pack entries, four overridden loose duplicates and 47 conditional texlow
entries remain separate. Source references do not prove current alias choice,
an actual draw or simultaneous residency. No asset conversion occurs in this
coverage step.

The selected Release21 inventory has 6501 normal packed winners. 5297 have
typed source/native ownership references; 11 have only generic other-source
references and 1193 remain unclassified. All source categories overlap. UI,
inventory images/3D models, font sheets, effects and actor references are
explicit policies rather than omitted from scope. Runtime-generated glyph
atlases and diagnostics are separate from stored package coverage.

Format analysis finds 176 lossless VQ opportunities. The private selection uses
162 with typed owners; it holds nine unclassified and five other-only owners.
This changes exact base encoding only, without adding mips. The candidate pack
is 154206208 bytes (-2048000 archive bytes); payload and 32-byte-request
inventories each shrink 1942144 bytes. All 324 independent before/after decodes
match exact RGBA/alpha; 6339 unselected packages and all earlier 20 FX outputs
remain exact. The release streamed Package reader admits all 162. Its 160
full-body CRC packages also pass strict validation; two existing legacy
texel-only CRC conventions are preserved and retain their prior strict-reader
refusal. No newly corrupted payload is inferred from that known convention.

    python port/dreamcast/tools/d367/mipmap21/source_coverage.py --source-pack /private/tex.pak --release-manifest /private/manifest.json --census /private/census.json --owner-probe /private/owner-probe.json --output /private/new-coverage

51 related host tests pass (two optional NumPy checks skipped on WSL; separate
Windows parity checks exist). No full repository suite or game/console run is
claimed. The coverage and 162-key candidate are sealed in separate private sets
with complete hashes and C: mirrors.

22 of these keys overlap the preserved 696-key square-world mip candidate.
Do not blindly overlay the base-only pack onto it and lose mip levels. The
composition step must use the selected compact base first, regenerate selective
mips for these keys, then compare lower-level quality and per-room requests.
The original 696-key candidate remains unchanged. Actor VQ mip work and the
rectangular UV/wrap/edge architecture retain their separate owners.

## Compact-base-first world mip composition

compose_candidate.py validates both sealed input archives and every member
receipt, binds the whole-pack owner policy, then combines the 162 compact bases
with the 696 world mip keys. It refuses unclassified base conversions and mip
keys without a selected native-world reference. OFF is the original pack.
When enabled, 22 overlapping keys regenerate their chains from the exact new
compact VQ base rather than overwrite or discard the previous mip levels.

    python port/dreamcast/tools/d367/mipmap21/compose_candidate.py --source-pack /private/tex.pak --compact-candidate /private/compact-set --world-mip-candidate /private/world-mip-set --coverage /private/coverage.json --output /private/new-composition --generate

mipmap_compact_vq.py preserves every referenced base vector and the entire base
index plane. It uses spare codebook slots for the previous native16-bit mip
targets, using integer premultiplied features and deterministic weighted
farthest residual selection. The base remains lossless; the regenerated lower
levels can have VQ error. The original 508 source-VQ codebooks are not altered.
Only the newly compacted overlap keys use this spare-slot policy.

The sealed composition is 155764736 bytes, 489472 bytes smaller than the
original pack and 2109440 bytes smaller than the prior world-mip pack. It changes
836 keys, preserves 5665 unrelated members, retains all 674 non-overlapping
world-mip outputs and all 140 non-overlapping compact-only outputs exactly.
Its 701 mipmapped keys comprise the 696 world keys and five unchanged Ganado
atlases. UI/text and other compact-only keys receive no new mip levels.

All 156 regenerated levels and 22 original bases agree with independent pinned
PVR decoding. All original base RGBA/alpha, referenced base vectors and base
indices are exact. Four chains also exactly match every prior native lower
level; 18 require rendered-look acceptance. Compared with those native mip
targets, worst per-level premultiplied RGB RMSE is about 9.89/255 and worst alpha
RMSE about 36.06/255. These metrics do not establish visual acceptance. The
actual host Package release-streamed reader admits every regenerated package.

The sampler policy keeps dimensions, UVs, wrap, filter and MIPD configuration;
the existing Package TCW mip bit enables the selected chains. The combined
target requires CAST_MIPMAP=1 and TEX_TWIDDLED_MIPMAP=1, while keeping its
SH4ZAM/SKIN_SH4ZAM and skinning-batch UV contract. No renderer/default or recipe
change accompanies the source/data candidate.

Per-room reports include every source-referenced world key, its actual payload
bytes, rounded 32-byte request and the optional UI_VRAM page-placement branch.
allocate_texture first requests payload bytes; an unaligned VQ or crossing
small texture can retry payload+2016 bytes. Reported upper sums describe this
branch, not observed addresses or retries. Differences of upper sums are not
guaranteed bounds on the actual allocation delta; before/after placement can
differ. Inventory totals are not simultaneous residency, peaks or largest
blocks, and omit actor/effect/UI working sets.

| World references | Plain request delta vs original | Delta vs prior world-mip candidate |
|---|---:|---:|
| r100 | +147904 B | 0 B |
| r101 | +90816 B | 0 B |
| r103 farm | +121792 B | -7520 B |

Six new host tests cover exact bases/alpha, spare/full dictionaries, independent
all-level decoding, source/reference rejection, OFF identity, overlapping-key
composition and request accounting. They join the 51 prior related tests.
No game build, live VRAM, rendered-look, hardware timing or release gate passed
by implication; the 18 approximate lower chains remain an explicit review gate.

## Source-pair and shared-core coverage extension

The source probe originally indexed only image keys present individually in
the normal pack. Combined material packages require the runtime R4MPv001
identity of their color and mask source keys. pair_references now derives that
identity only from equal-dimension images in the same receipt-bound source TPL,
or from the explicit inventory-pair producer with both source references.
This proves source ownership, not a selected native material binding or draw.
It resolves 158 of 161 source-pair keys; the other three remain open. The 73
explicit inventory pairs are already within those 158 and are not additive.
The packed-key-filtered original probe cannot establish every source-only
input namespace, so missing pair input identities are not declared absent.

All 11 previously generic other-only references are in etc/core.das. The source
file table in src/game/dvd.cpp and the re4dc_ui_bind_core call in read.cpp prove
shared core-resource ownership. Their individual consumer/sampling purpose
remains separate, so they receive no automatic mips. This is a named source
binding, not a material-label guess.

The current whole-pack policy has 5466 typed-owner keys and 1035 unclassified
keys. The extra pair proof permits one exact base conversion, and the core
binding permits five, all 64 square. Eight owner-unclassified format-only
opportunities remain held. Older Ashley/zealot mask comments still do not prove
their selected native ownership and do not authorize conversion.

The source-owned base cohort is now 168 keys, saving 1972864 payload/request
bytes and 2084864 archive bytes; 6333 other members remain exact. The six new
before/after bases independently decode to exact RGBA/alpha, and all earlier
162 outputs are unchanged. The combined private world-mip composition changes
842 keys and keeps 5659 unrelated originals exact. Its pack is 155727872 bytes,
526336 bytes smaller than the original. All earlier 836 composed outputs,
all 22 regenerated mip packages and all 29 world-request rows remain exact;
the four-exact/18-look-review lower-chain gate is unchanged.

These are new versioned private sets; earlier 162/163/836/837 sets remain
preserved with their own receipts and supersession notes. No runtime, sampler,
recipe/default or release changes accompany the extension. Three new owner
tests cover pair identity/table/dimension constraints, explicit inventory
source pairs and shared-core ownership without automatic mips. The latest six
coverage tests pass; the earlier mip/compaction/composition suites are unchanged.

## Square PS2 effect frame candidate

fx_candidate.py is an opt-in private candidate builder layered on a sealed
compact-base-first archive. It admits only exact-library-matched, full-square
PS2 EFF frames whose known source consumers are all effects. Shared non-effect
consumers and rectangles are held. PAL4 chains retain the original palette and
base indices. Already losslessly compacted VQ frames retain their base vectors,
index plane and RGBA/alpha while unused codebook slots fit lower-level targets.
Those targets are newly filtered PAL4 candidate levels, not accepted artwork.

OFF preserves the selected base archive exactly. The current source fixtures
cover OFF identity, PAL4 and VQ alpha/base preservation, independent mip decode,
source-library mismatch and shared-consumer exclusion. The private review
superset now has 553 frames: 533 PAL4 and 20 already-compacted VQ, with 3795
independently decoded levels and 553 exact original bases. Both actual Package
host allocator modes admit/upload/release every frame under ASan/UBSan. It
changes 1375 original keys and keeps 5126 exact, with a 155963392-byte archive
290816 bytes smaller than the original pack. None of this is target acceptance.

EFF ownership alone does not establish screen/world sampling purpose. The
offline preview includes letters, borders and other symbols, and some coarse
levels have substantial alpha error. This review superset must not be treated
as a blanket release selection. EST/SST and direct consumer policy is the next
source gate. Rendering, resource use and appearance remain separate gates.
This tool does not change recipes, defaults or runtime sampling; the effect
renderer's existing bilinear/clamp/alpha contract is kept. Sealed private
receipts distinguish the generated superset from any later selective candidate.

effect_consumers.py reads direct frame TPL bindings and EST/SST records from
retained native archives, including the existing R4ESQTBL compact EST format.
It reconstructs packed records through the existing codec with index CRC,
offset, record-count, padding and eligibility checks. It does not reinterpret
compact data as 300-byte raw records or infer live drawing from static data.
The read-only source probe verifies each named input against the original
release manifest before parsing. Source slots bind the binocular, scope and
main HUD EFF resources to IdTexDataLoad, so those are explicit fixed-ID-UI
holds rather than presumed particle textures. Unknown, mixed screen/world,
custom and generator consumers retain separate follow-up policies.

select_effect_candidate.py applies the receipt-bound source consumer policy to
the sealed review bytes. The first selective set has 74 common world-sprite
source candidates (65 PAL4, nine already-compacted VQ). It holds 35 source-proven
ID UI keys, six screen/mixed keys, 179 custom/generator keys and 259 unresolved
keys. Seventy of 89 named inputs match the original release manifest and parse;
missing or different source bytes are not silently promoted. Static source
records still do not establish every runtime override or a rendered result.

The selective archive changes 907 original keys and keeps 5594 exact. It has
775 mipmapped keys: 696 world, 74 FX and five original Ganados. Its 155840512
bytes are 413696 below the original pack. Compared with the sealed842 input it
adds 169394 payload bytes and 170784 rounded request bytes; those are inventories,
not live residency. All selected bytes exactly reuse the independently decoded
review packages (564 levels and 74 original bases), including both host Package
allocator/lifecycle checks. The new selective receipts bind original-source
members as well as their selected base ancestor, so later composition validates
without confusing the review superset's base-relative receipts. OFF preserves
the selected842 base. Three tests reject forged UI/world labels, source/ancestor
hash mismatches, screen records and incomplete policies, and verify ordinary
sealed-candidate composition and unchanged UI bytes.

The full6501 policy snapshot includes the 51 loose/conditional descriptors
separately, these fixed-ID-UI refinements and the 20 separate actor mip candidates
without overlaying them. Lower-level alpha/look, target sampler, combined VRAM
and timing remain open. No runtime/default, recipe or release change occurred.

The next source contract expands that selective set to 167 frames (157 PAL4,
10 existing VQ) without touching the fixed-ID-UI holds. Espgen00 emits its same
record through EspSeqSet and Esp0b_Trans uses EspCommonTrans after position
jitter. Esp11 light state, Esp46 colour-filter state and Esp4a camera shake do
not sample the record's nominal texture; they therefore do not falsely hold a
key used by a reviewed sprite. Esp4c remains held because it changes reflection
texture state even though its own Trans is empty. Generator02, screen/mixed,
reflection, shimmer, negative/RTT and other custom consumers stay explicit.

The 167-frame archive changes 999 original members, keeps 5502 exact and has
868 mipmapped keys. It is 155869184 bytes, 385024 below the original archive,
with 238808 added payload bytes /242048 rounded request bytes versus the842
input. It exactly reuses 1178 verified review levels and167 original bases.
The smaller74-frame artifact is preserved. Sampling contract versions are
explicit and unknown versions are refused. Eighteen focused tests now pass;
the two extra cases cover emitter/jitter versus reflection/negative paths and
the selector's reviewed generator contract. Target appearance, combined memory
and timing remain separate gates, with no recipe or runtime default changes.

## Generic native16/VQ effects and reporting

generic_effect_candidate.py applies the same source contract outside the PS2
PAL4-frame family. All 220 square native16/VQ EFF keys are assessed, including
44 source-proven ID UI holds, 173 unresolved consumers, one screen/mixed key and
two source-qualified world-sprite keys. Forty-five of 57 named source files
match the original manifest and parse; missing/different inputs remain held.
Native world/actor material aliases are refused. Original source VQ codebooks
and full-resolution texels stay exact; an earlier compact base retains its
used vectors/indices while unused slots fit its mip targets. OFF keeps the
selected167-FX ancestor. Three new tests cover these families, shared/UI holds,
bad source hashes, sampling versions and full-resolution RGBA equality.

The two-key compatibility set has 17 independently decoded levels and two
exact original bases, plus actual Package host ASan/UBSan upload/lifecycle/mip
checks under both allocator modes. It changes 1000 original keys and keeps
5501 exact, with 870 total mipmapped keys and a 155912192-byte archive (342016
below original). Compared with the167-FX ancestor, it adds 45062 payload bytes
and45088 rounded request bytes. Most of that is one256-square ARGB4444 native
chain: +43696 payload bytes. It is a format-compatibility candidate, not an
over-budget fallback or a blanket enablement recommendation. Compression/
appearance and combined memory remain gates; no speculative speed is claimed.
The other128-square key retains its prior exact compact VQ base. The producer
snapshot and every private file are mirrored with hashes. The full6501 policy
now has79 explicit fixed-ID-UI holds; all51 loose/conditional descriptors and
the20 separate actor candidates remain separate.

assetpipe.texture.read_re4tex also now counts a stored mip payload's complete
descriptor size, including lower levels and palette tails. Existing nonmip
reports keep their prior values. The base-only vram_bytes formula remains for
proposed textures. Two reproduced reader failures now pass; ten relevant
reader/formula/palette tests pass. These values are payload inventories, not
allocator rounding/page placement or live residency. Existing candidate
inventories already used descriptor sizes, so their receipts do not change.

### Exact uncompressed PAL8 compatibility fixture

`../../compact_native_pal8.py` is an opt-in offline ARGB4444 path for square
native twiddled bases or complete native mip chains containing 17–256 distinct
16-bit words. It replaces each existing word with an 8-bit palette index; every
existing decoded base and lower-level RGBA/alpha value stays exact. Grayscale
plus alpha uses one canonical 256-color palette so compatible frames can share
a palette. A 512-byte palette tail counts toward package bytes; smaller PAL4
inputs and conversions without an actual rounded-payload saving stay unchanged.

The experimental descriptor format is 5. Runtime admission is now implemented
behind `TEX_PAL8_ALPHA=1`, requiring `TEX_PAL4_ALPHA=1` for the shared ARGB8888
palette manager. Chains also require `TEX_PAL8_MIPMAP=1 CAST_MIPMAP=1`. Both new
switches default to zero and add no definition while off. No recipe enables them.
The combined manager owns aligned 256-entry blocks, excludes reserved/PAL4 banks,
shares only identical full palettes, preserves ARGB1555 versus ARGB4444
interpretation and releases each block after its final reference and render fence.
It checks the complete transaction after normal payload upload, before changing
any palette. Streamed metadata has no palette tail; this ordering adds no separate
disc reads. On refusal, the package retains its partial VRAM allocation until
`close()`, as other upload failures do. No live palette is changed on exhaustion.
The enabled path also avoids closing a borrowed live-window handle on payload
release. Baseline controls reproduce both that existing ownership bug and the
old cross-interpretation palette-sharing error; their broader default-path fixes
remain separate from this opt-in extension.

It does not change UVs, wrap, sampler, dimensions, alpha mode or a release recipe.
Target sampling/look, combined palette/VRAM/KOS budgets and timing remain open.
Source-qualified data fits are not blanket enablement: most distinct PAL8 palettes
cannot coexist because the message renderer leaves only three aligned blocks.
`test_compact_native_pal8.py` checks OFF identity, exact base/chain values, both
CRC conventions, rejected inputs, palette overhead and the independently decoded
PVR layout. Set `MIPMAP_PVRTEX_ORACLE_PAL8` to a separately built oracle library
from `tests/fixtures/mipmap_pvrtex_oracle.c` to run the pinned C decoder cases.

`tests/test_pal8_runtime.py` compiles the actual Package with ASan/UBSan across
both UI VRAM modes, bases/chains, aliases, sharing, fragmentation, whole-transaction
refusal, metadata/payload release, partial failures and ordinary/live/closed-window
pack reads. It checks OFF object identity and make guards. The older PAL4 capacity
fixture now uses distinct palettes for actual exhaustion and expects the already
shipped exact-palette sharing for aliases; repeating identical palettes no longer
counts as filling separate banks.
