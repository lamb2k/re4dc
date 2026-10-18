# Castle 18: shared Ashley archive admission (2026-10-18)

Castle CH4REC omitted MOTION_BOUNDED_R11F=1, already used by CH2REC. Commit
04af51c2 adds that existing knob to the castle recipe. T15REC, CH2REC, runtime
code and chapter 2 archive bytes are unchanged; no new knob or asset is added.

Selected pl11.drs SHA256:
ecf3098097fcb2b2c86d632b62fd3d9112e61f5e39b56819db6a2e277fffcfa2.
Its 384064-byte body has CRC ddcc1084, v3 table count 69 / limit 32768 / CRC
5f23565e, module 47 / dc000001 / BSS 0: the existing exact admission row.
All 71 FCV ordinal slots reconstruct byte-identically to working castle archive
596b29aa: 69 streamed and two retained; each streamed resident header also matches.

Real native cache host checks exercise all 69 clips three times on storage and
FAST_READ paths. Knob off refuses before allocation; knob on admits and owns
three cells / 52544 host bytes with no leak. This is host storage and relocation
evidence, separate from gameplay acceptance. Ashley look-back uses MotionSetCore.
Face FCVs 0x6c/0x6d retain headers for ShapeSet; CalculateShape_new leases their
keys. r210/r219 paired scripted motions use unchanged room archives.

## Fresh Flycast

Build c18amW, source 04af51c2, ELF
78290ab8e3988b447835bb336475e87c153bba9d19825331229a1c6ba7362697,
_end 8c45fed8, no missing symbols. Current T15REC + CH4REC, cap4, registry
FIRST/LOD/ROLES5, BUMP_FLAT, STATUE_LIGHTS=2 and HEAP4_WATER diagnostics.
Each run is 60 seconds, one owned Flycast at a time through trace_lock.

| Room | Entry / no fatal | Ashley 384064-byte / 69-entry bind | Remaining acceptance |
|---|---|---|---|
| r203 | PASS | PASS | Movie owns window; world/cast/texture play coverage pending |
| r206 | PASS | PASS | em11 GC fallback; no room registry staged |
| r208 | PASS | PASS | em1a GC fallback and texture-residency gaps |
| r210 | PASS | PASS | Three AICA no-fit reports; route/progress pending |
| r212 | PASS | PASS | Route/progress and complete cast coverage pending |
| r219 | PASS | PASS | Route/progress and complete cast coverage pending |

Evidence: C:\Flycast-Evidence\re4-dreamcast\castle18-20261018.
Task1-runtime-summary.json retains checks and last logged VRAM inventory; these
preload observations do not establish a residency pass. Individual logs/captures
are h-c18a/scenarios/cx-<room>-walk-ash3. Chapter 2 archive bytes are unchanged.

First r208 ash1 is INVALID: its fixture overrode the selected boot image with old
c3gmW bytes while overlays/logger symbols were current. It proves no runtime
failure. The corrected owned helper asserts actual staged boot and all overlay
hashes. Tool-only afe0694f also makes fixture_arm retarget an explicit boot
replacement; three regression cases pass (stale boot+overlay, missing boot
refusal, absent replacement preserved).

## Identity and pending gates

Fresh T15REC c18irP (04af51c2) vs independent frozen7d7c05ab i18b2rP:
loadable image3297c00ee84ac6a3d06fcddb5672696dbe9b53c8fb0638d774293688697e89fe,
all ten overlays byte-identical; _end8c400eb8, missing0. Disc1-identity.json
retains hashes. Raw resolved-knobs files have distinct build paths.

Matched chapter 2 runtime/STRICT and castle KOS48KiB remain pending. KOS twin
c18sqW ELF330ab465dcc98d2b is built but ungated. Full castle route, waves, bosses,
cast, residency and visual acceptance remain open. No console acceptance,
integration merge or release is implied.
## Resumed gates, 2026-10-18

The unchanged chapter-2 archive remains the common Ashley input. Frozen
7d7c05ab chapter-2 trace c18cbrT and current 11c4ff24 c18ccrT have identical
loadable bytes (`00c764415217c475cf077728ee9721e6817ac4b46538dec7e83c057db7d196fc`)
and all 14 overlays. Both link without missing symbols, ending at 8c41f098.
Fresh matched fixtures pass STRICT/decisions in r11c (370 global ticks), r11e
(652), and r200 (652 STRICT / 651 decisions), with no log overrun. The r11c
55-second window ends before its original room-frame-360 walk action; it
establishes matched source gameplay/partner state, not an active walk or siege.
The other two reach the requested trace stop. These are bounded regression
windows, not chapter completion. `ch2-program-identity.json`, `ch2-gate-inputs.json`
and `ch2-strict/` under the evidence root retain the proofs.

The exact castle c18amW recipe's KOS twin c18sqW passes all six 48 KiB
allocation gates (55-second Flycast windows, one block / 4 KiB pieces):

| Room | Minimum headroom, block / pieces | Result |
|---|---:|---|
| r224 | 52,312 / 52,224 B | PASS |
| r226 | 39,192 / 39,104 B | PASS |
| r227 | 31,416 / 31,328 B | PASS |

Each log confirms held=49152, live room activity, no OOM/HALT/FAULT/MISSING,
and headroom above 4 KiB. CAST, textures, audio and route acceptance are separate.
`kos-castle-summary.json` and `h-c18kos/scenarios/` retain the results. Canonical
CH4REC now includes the same existing cast16 FIRST/LOD/ROLES5/BUMP_FLAT and
approved STATUE_LIGHTS=2 flags previously supplied through XON. c18fmW's actual
boot image and every overlay equal c18amW (`canonical-castle-identity.json`).
HEAP4_WATER remains a diagnostic extra. T15REC and CH2REC are unchanged.

### Remaining room work

- r205's full PS2 conversion stays unchanged. Producer commit 45fe6728 audits
  em2d for the existing version-2 32 KiB motion transport. Its diagnostic body
  falls from 2,542,976 to 1,699,136 B. All 66 FCVs match the resident archive by
  ordinal; 61 streamed clips pass three rounds through each native host storage
  path, with no leak. Five oversized clips stay resident. This is not a hot-set
  residency or route qualification. The private data is mirrored as
  `castle18-em2d-motion-20261018`, with `SHA256SUMS` and host/mirror proofs.
- All 20 missing r205 texture pairs exist in the recovered ch3found data;
  restored fixture selection reuses their exact bytes. No texture regeneration.
- Existing res17b resident file `98c23bc3e40e1658e05fc9a952f453b04e0fbcd695a7e47354bf12d0cb849eb8`
  covers all 116 current room lists (zero short). It preserves the core/water
  records and can replace the incomplete recovered file. No new resident file.
- r203/r206 em11 and r208/r209 em1a packages reuse sealed recovered geometry,
  source bindings, masks and runtime headers. Only audited source-type selection,
  room eligibility metadata and packaging change. All four pass the actual host
  package validator, and are mirrored as `castle18-cast-rooms-20261018`.
  Actual enemy drawing and progression remain required.
- r227's existing 329,920-byte package admits on the current ROLES5 arm. r216
  still needs its actual room gate. The `jump` parser already exists but is
  diagnostic WARP_JUMP=0 by default; c18jmW enables it for the r20d/r206 rig.
  A diagnostic room jump will not qualify natural door progression.
- Boss models are exclusively boss18 under I-005. The prepared r228 fixture
  uses existing full models and the exact emleon05 a506e148 archive; it is a
  diagnostic input, not a completed boss-room gate.

## Current integration and room recovery, 2026-10-18

Merged `origin/t15/int` 293aefcd without conflicts at ba10899e. The current
T15REC off build c18y1rP has the exact frozen integration boot image
`a64f194480afa44a19ea7d8d9960e2593b1e21a38bc4773b64bfa31888396e0e`
and all ten overlays match the independent i18b3rP control. Both have `_end`
8c4061d8 and no unresolved symbols. Historical identity against 7d7c05ab is
retained separately. Evidence: `disc1-current293-identity.json` under the C:
Castle evidence root. Current canonical castle c18y1mW is ELF 7ba732d8,
`_end` 8c465598, with no unresolved symbols. Private drivers only redirect
output/registry paths and refuse existing outputs; recipe assignments remain
literal copies of current source.

The additional unchanged-chapter-2 r11c early walking pair passes STRICT and
decisions for 366 ticks, with three fired inputs and 1,053.449 source units of
maximum horizontal displacement after the first input. The initial warp is
excluded. All four matched chapter-2 pairs stage 4,158 identical files. This
closes the targeted regression scope; it does not prove full chapter play.

Current Flycast room windows, each requested 55 seconds:

| Room | Observed result | Remaining limit |
| --- | --- | --- |
| r203 | Normal native movie START at picture 16, terminal 2; then PS2 zealot draw, zero declines/TEX/Leon fallback and one completed source kill | Full waves, clear and doors unproven |
| r201 | PS2 em1b draw, zero character fallback/TEX/Leon fallback | Route and combat completion unproven |
| r218 | PS2 em1c 09h/0ag/0dg draws, zero character fallback/TEX/Leon fallback | Room/FOOT/enemy sound fitting and full route remain |
| r214 | PS2 em14 draw and zero texture failures with existing res17b | Sound and full route remain |
| r226 | Nine completed source kills; one em11 eight-info class still declines 48 times | No cast or room acceptance |
| r22b | All eleven event VQ keys load; TEX 0, no VRAM rejection/retry/eviction, free 531,456 bytes at frame 720 | Character census and full event/route unproven |

The first r203 current attempt reopened the normal Retry/Load menu through an
inherited post-movie START action; it is not combat proof. The corrected cur2
fixture removes that obsolete action. Raw NOT-DRAWN output also reports IDs
41/43 in several rooms; no allowlist was changed and no full-room pass follows
from the character-only census rows.

`castle18-r22b-event-vq-20261018` regenerates ten missing historical VQ outputs
and reuses the first new candidate. The verified native input winners and
pvrtex 95a71290 are pinned; alpha is exact and the historical RGBA PSNR metric
matches within 0.055 dB. The old output hashes were lost: these are regenerated
outputs, not byte-verified recovery. The 47-file WSL/C mirror manifest is
`63ce5d178471b7b59befeb8cdcb5574f20788c75b4a46003eff84af7936aaa7e`.
A source/VQ/difference sheet is retained for look review. Existing res17b
98c23bc3 still covers all 116 current resident lists; no resident regeneration
was needed.

The r205 raw sound bank is now prebuilt through the existing frozen-layout
fitter. All non-sound bytes, including the prepared motion body and FCVs, are
identical. The current guest loads bank 8 with zero bank fit failures and zero
texture failures; the missing SBB 2408000 voice stream remains separate.
Mirror `castle18-audio-fit-20261018` has manifest 8280ebf7 and archive f0522287.
Active Novistador camouflage remains refused: changing blend ratio/type and
Shader_type 1/refraction require a separate renderer contract review. The type-4
idle result is not generalized. No enemy-drawing or full-audio pass is claimed.

The r214 private sound-only candidate deduplicates one exact source sound ID
in the host budget: em14/em1a have identical nested MRAM and ARAM banks with
sndType 8/sndArg 0x11. dvd.cpp calls SndEmDataReadCheck, and snd.cpp skips an
already loaded ID. All archive files remain staged. The unchanged fitter then
fits ROOM 100,844 bytes at 16 kHz and FOOT 69,348 at 11,025 Hz into the frozen
arena, leaving 20,224 bytes. Only those two sound ranges change. Mirror
`castle18-r214-audio-fit-20261018` has manifest 3178c9ea; runtime gate is pending.
The separate raw BGM0 and rejected BGM1 are not fixed by this candidate, and
AICA_SPILL was not enabled without a complete fit.

Higher-thinking model work is queued through the parent for em1a type 08's
alternate accessories and em3c's source weapon attachments. The r216 package
itself admits, but its live type-2 weapon BIN 0xC/TPL 0xD is omitted by the
existing descriptor; source types 1/3 use BIN 0xE/TPL 0xF. No skeleton tolerance,
role or material admission was relaxed. Existing WARP_JUMP already reaches
r206 through SceAtExecRoomJump and the 470-picture s20 completes; that is a
diagnostic transition, not proof of the natural door route. Current integration
KOS pressure gates are queued separately because its static image grew.
