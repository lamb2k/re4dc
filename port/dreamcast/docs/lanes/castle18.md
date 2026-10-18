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