# Test 21 Verdugo source fixtures (2026-10-20)

The current source program produces an ordinary, nonlethal Verdugo custom-damage callback. This is the live fixture for `NATIVE_MODEL_REGISTRY_GRAB_FULL`; complete boss acceptance remains open.

## Program and data

Built source `87cff2a4` is current base `5f26453a9`, merged as `6643bf94`, plus the existing renderer item 3 reused as `11298e54` and the Salazar positive-control spec. Item 3 was absent from actual upstream despite I014's landed statement. There is no new runtime implementation here.

The r221-only recipe extends the current rr CH2 and existing CH4 recipe with `DISC_SET=1 NATIVE_MODEL_REGISTRY_OT5=1 NATIVE_MODEL_REGISTRY_GRAB_FULL=1 NATIVE_MODEL_REGISTRY_ROLES5=1 NATIVE_MODEL_REGISTRY_BONES=96 NATIVE_BUMP_FLAT=1 HEAP4_WATER=1 PVR_RTT=1`. Diagnostic arm mW uses `KOS_SQUEEZE=1 KOS_SQUEEZE_BYTES=49152 PC_SAMPLER_BYTES=8192`. ELF SHA256 is `0633b72fb0ba45dbd6f95799d897756e57540c9030d213bc6f1fbd8752dcc7d2`. PVR_RTT is not added to a global or chapter default.

The full retained H040 Verdugo package is reused without a new level. It is a full-only fixture, so observing the full-selection predicate cannot prove a reduced/full switch or saving.

Private data/receipts are in `C:/Flycast-Evidence/re4-dreamcast/boss21-20261020`. `r221b-disc2-additions.json` adds r221 to Castle's immutable current Disc2 tree using existing mkdisc2.py. Final data has 6925 files/501928 sectors; the ISO has 503059 sectors, 941 below the 504000 limit, adding 5794 data sectors. The current corrected RAM image SHA256 is `a0083a08ee3a0adca6922445d8e2b65a95df184db551e739b72b4dd9225ef45b`. Master proof: 6925 identical files, three allowed fixture differences, zero unexpected differences.

The first run correctly stopped at PE4 list5's guard: inherited `etc/emleon05.esl` was the exact raw GC big-endian input, SHA256 `57c251fb92baf9ee6b44f4376828d5e34f6187787c060d7d933d5329cbc8c860`. Existing `le_mirror.py:fmt_esl` converts that 8160-byte source to `a506e148c5ce57b5640f8068299cf1c127422254ff67b26cfdec86143327c6dd`; all 163 selected current PE4 baseline rows agree. This is the sole inherited-baseline data replacement. The result is mirrored under `re4-assets-private/boss21-verdugo-fixtures-20261020`; no guard was changed.

## Original source path

`r221-source-appearance.txt` supplies the original persisted room flags and places only Leon at source area19 through the existing fixture API. The original `r221_appearBoss2nd` callback sets the boss's flag1, and original C_Wait/C_Fall performs its ground appearance. An idle post-appearance fixture alone leaves the source boss overhead, and D-pad input does not supply analog walking. Those attempts remain retained diagnostics.

The area19 center in this room is approximately (-2242,836,-1920). The original ground appearance begins at the source hardcoded (-12725,886,-80973), then ordinary AI catches up through HideWait/HideFall. No boss position, routine, material, attack or pose is written.

Run `normal-appearance-i` retains the current healthy source snapshot. Run `normal-attack-j` continues that exact snapshot, same program/disc/VMU/fixtures, with neutral controller input and no process writes. It closes after 50.8 seconds with no runner errors. The asset-free receipt pins the seed, log and observation bytes.

There are 43 read-only observations from host seconds12.203 to13.328 with Leon routine4 and `dmgType == 0x8ca8cba0`, the live Verdugo body. The first has original Global life140/1440 and boss routine1/9/1/0. This is a nonlethal ordinary attack callback. It matches `SetPlDamage`'s original state contract and the current GRAB_FULL selector. The source render target reads64x64/repeat1; source PVR_RTT logs its64x64 first pass.

## Qualification limits

The actual 49152-byte KOS hold is logged and TEXCHK remains0. Initial idle body drawing is450 native frames with zero declines. The longer source appearance/attack lineage accumulates11 registry semantics declines, first during hidden catch-up and later by source1080. Final ordinary-arm body count is2163 native,11 registry declines. A clean whole-arm native/CAST gate is therefore not claimed; the cause of the semantic declines is not resolved by this fixture.

The enemy AICA bank reports no-fit at load, and later death UI has unsupported entries. Texture residency is not clean merely because checksums pass. Complete fight/route, audio, disjoint costs, visibility, STRICT/decisions, frozen native look and matching GC reference remain open. All runs use the root-approved RAM-only functional policy: C preflight16GiB+128MiB, retained floor16GiB+64MiB, output128MiB, at most60seconds. There is no hardware, IO or FPS acceptance claim.
