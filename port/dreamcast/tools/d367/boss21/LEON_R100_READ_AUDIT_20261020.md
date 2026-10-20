# Leon transitions and R100 shooting: source and selected-file read audit

The selected QA data exposes real first-use HUD/muzzle texture reads and unconditional archive replacement on weapon changes. It does **not** establish the cause of the reported crippling console slowdown after s20. A new enemy's first visible frame can also admit a render package even though R100 pre-reads its main archive. Motion-cache pressure is a separate conditional risk. No runtime, game logic, asset, renderer, recipe or geometry change is included here.

This supplements [the boss/enemy animation coverage matrix](BOSS21_CACHE_COVERAGE_20261020.md); render/census/STRICT evidence is not cache closure. QA owns fresh normal-input reproduction. Boss used no build or guest for this audit.

## Identity and reusable checker

Source is QA initial `9eb83d59`; all 29 file hashes in [the asset-free receipt](leon-r100-read-sites.json) match that commit exactly. Input is the fixed QA `master03/track03.iso`, manifest SHA256 `40f329d4d1f2b9e92ed4d4003181ef51b4c5b6223762aeafe1a14fdb813c4c9d`. The QA boot hash is `1e283acbf70ef669e257605484533fcbf39cc95a4ae0f3ba6c3c7467f6b24969`. This does not include an unreviewed boss renderer integration.

[transition_read_audit.py](transition_read_audit.py) reads the ISO without modifying it. It checks selected wrapper identities against the manifest, validates MTC and texture-index CRCs, follows source ARC indices to selected FCV keys, validates actual loose FCV bytes/CRC/FNV, derives muzzle and HUD texture identities, and emits index/payload ISO LBA spans. Native identity records are required for stripped cartridge textures; placeholder pixels are not hashed as original images. Regression guards check the actual ammo-unit binding, observed digit keys, ordinary Ruger sequence and weapon guard ordering. `animation_cache_audit.py` separately tests original Ashley 0/6/61 versus the fixed inline set.

Reproduce with Python, supplying `--repo`, `--source-root`, `--iso`, `--manifest`, and `--output`. The source root must be the selected QA checkout, not an assumed current main branch. LBAs are absolute ISO9660 extents: an observer using drive FAD must verify the possible +150 convention.

## Ordinary fire: effects, casing, sound and HUD

Actual weapon 2 uses `cObjRuger`, selected by [wep02.cpp](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/wep02/wep02.cpp#L23). Weapon initialization registers its EFF once at line 39. [moveFire](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/wep/objRuger.cpp#L85) selects inline weapon FCV 0x34/0x39, queues shot sound 2:0/1/2 (or 2:18), starts effect owner 0x36 sequence 0 and creates a casing. The selected wep02 DRS has 42 inline FCVs and no MTC. `EspDataLoad` and `EstSet` use admitted memory; they do not open a file per shot. The nine selected sequence-0 records reference core sprite IDs 0x1e/0x1f and weapon texture 0x22. Texture 0x21 belongs to another sequence.

The actual file read occurs when [native_ui load](https://github.com/lamb2k/re4dc/blob/9eb83d59/port/dreamcast/game/platform/native_ui.cpp#L3196) cannot find the image key in its live texture entries. A hit returns before filesystem/index lookup at 3213/3217; a miss can evict a slot at 3285 and open the packed texture at 3296/3305. Missing-key and fragment safeguards exist, but pressure, owner retirement or an I/O-error retry can still make a later use cold. Resident EFF data alone does not prove texture residency.

[Cartridge creation](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/wep/objRuger.cpp#L173) uses already admitted weapon BIN 8/TPL 9, then landing effect 0x13. The normal shot sound path in [snd.cpp](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/game/snd.cpp#L890) checks an admitted SIT/bank and queues the AICA one-shot; no per-shot sample-bank/DVD read was found in that path. Streaming voices, bank admission and event sound paths remain separate audit subjects.

The ammo counter is another per-shot draw consumer. [BulletInfo::move](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/game/cockpit.cpp#L552) reads the loaded count, splits it into decimal digits and sets `texNo` on LIFE units 0x0b/0x0a/0x17 (566, 579, 584-592). In the actual selected core's LIFE UWF v2 table, all three units refer to texture ID 0x27. Its patterns 8 and 9 are **exactly** the keys QA reported loading; this is an asset/caller match, not an inference from image size. [ui_bridge](https://github.com/lamb2k/re4dc/blob/9eb83d59/port/dreamcast/game/ui_bridge.cpp#L83) selects that TPL descriptor and resolves it through native UI.

| Consumer | Actual key | Packed payload LBA | Index LBA | Package bytes |
|---|---|---:|---:|---:|
| Ammo digit 9, core Tex27 pattern9 | 951a629c-a43ebab7 | 302853 | 258250 | 1168 |
| Ammo digit 8, core Tex27 pattern8 | 48c096e1-fcd52e2d | 280466 | 258235 | 1168 |
| Muzzle Tex22 pattern0 | 3a866b91-f0606d3c | 276645-276646 | 258232 | 2224 |
| Muzzle Tex22 pattern1 | 148d2ff5-6f9ba526 | 264511-264512 | 258225 | 2224 |
| Core sprite1e | 29558ab4-8b936f66 | 272428-272432 | 258229 | 8368 |
| Core sprite1f | dbbad2e7-5b0b1eed | 325195-325199 | 258264 | 8368 |
| Casing pattern0 | 75eb4ee2-5f583ae1 | 294247-294248 | 258244 | 2192 |
| Casing pattern1 | 797dba9a-fa553624 | 295343 | 258244 | 656 |

Each newly displayed decimal digit can require one index sector and one payload sector: two physical reads / 4 KiB at sector granularity. The receipt includes all 15 Tex27 patterns (only 0-9 are selected by the ordinary decimal counter) and the two alternate Tex21 patterns. This predicts finite first-use loads; it does not predict continuous warmed per-shot reloads without retirement or pressure.

QA `r100-shoot01` is an eight-shot **missed-shot control**, not a hit/death test. Core sprite keys loaded at room entry and muzzle Tex22 keys on first fire. QA's corrected raw timeline places the later two-read/4-KiB windows alongside newly displayed digit textures, with quiet after the final pulse. QA reports six warmed shots plus reload in `r100-shoot02` with zero physical reads and zero new texture loads, unchanged enemy HP and no hand/motion changes. Retained QA receipts are `r100-shoot01-read-timeline.json`, `r100-shoot02/run-result.json`, `r100-shoot02/readonly-combat-io.jsonl`, `r100-shoot02-summary.json` and `r100-shoot02-state-audit.json` under `C:/Flycast-Evidence/re4-dreamcast/qa21-r11e-20261020`. The warmed read-only window is source904-1992; later saved frame2387 is outside that trace window. Those results are QA's current bounded Flycast evidence; they do not reproduce or clear the console's severe post-s20 stall, enemy admission or hit reactions.

## Enemy appearance and combat motions

[R100Init](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/st1/r100.cpp#L163) calls `EmReadSearch(0x12,0,0)` before appearance. The source archive loader [read.cpp](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/game/read.cpp#L532) admits DRS data; `EmReadSearch` reuses an already loaded matching module. Actual QA em12 native body is 1,105,152 bytes, v2 MTC has 145 cached keys and 225,184 hot-preload bytes. It is not strict v3 two-slab/no-spill Ashley policy.

[Ganado render admission](https://github.com/lamb2k/re4dc/blob/9eb83d59/port/dreamcast/game/coarse_ganado_lod.inc#L108) remains lazy: first owner-plan `ready()` loads the wanted level. The selected gameplay g70 record is 71,584 bytes at LBA 354504-354539; full event level is 106,112 bytes at 354409-354461. A wanted-level change can reload after retirement (123-128). This is a concrete additional first-appearance/event-transition read site, not proof it caused the report.

Small flinches in [em10_R1_Dm_Small](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/em10/em10.cpp#L13719) choose torso 0x26/0x28 or hit-zone/weapon alternatives. Current 0x26/0x28 are cold keys 69370ad4-e309c0fd (11,840 B) and 8ec50b82-32efc065 (12,032 B), separate from their sequence partners. Head reactions choose 0x2c/0x2e/0x30 at [14242](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/em10/em10.cpp#L14242); these three cold FCVs are 10,848/16,992/17,152 bytes. Independently reacting live actors can request different keys repeatedly. This is a concrete conditional working-set risk, not the invalid inference that all reachable clips are simultaneous. Down/death 0x6b/0x6c are also cold; ordinary death 0x67 is hot-preloaded. The receipt records keys, state and actual FCV sectors for the named combat set.

[Native motion](https://github.com/lamb2k/re4dc/blob/9eb83d59/port/dreamcast/game/platform/native_motion.cpp#L325) uses two reserved slabs and conditional v2 spill/cold pool. Heap/global-pressure eviction can discard hot keys; hot means preload hint, not a permanent lease (260). Thus the three-cold actor combination is conditional on actual overlap and spill/pressure state; strict-v3 overflow is false. Current first missed-shot QA run had startup loads and no evictions, so that run does not implicate these reactions.

[Movie allocation](https://github.com/lamb2k/re4dc/blob/9eb83d59/port/dreamcast/game/platform/native_movie.cpp#L247) can evict unleased motion keys if its staging allocation needs room. No explicit all-hot restoration after every movie was found: preload occurs on binding, then an evicted key reloads on use. This is a conditional post-movie restoration gap, not proof s20 actually evicted a needed R100 key. World-arena/available memory can avoid the eviction entirely.

## Leon, weapon changes and pressure

Both [quick select](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/game/sscrn.cpp#L310) and [inventory Equip](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/game/sscrn.cpp#L889) call weaponRelease -> weaponLoad -> weaponInit when the equipped no/type/tune changes. [ReadWepData](https://github.com/lamb2k/re4dc/blob/9eb83d59/src/game/read.cpp#L1205) has one current mapped-archive guard, not a multi-weapon warm archive cache; distinct A -> B -> A changes reload the DRS at 1347. There is also a specific guard-order risk: it assigns `oldWepId = no` at 1320, then calls `ReleaseWepData`, which resets the key to 0xff when releasing an owner/heap body (1043/1052). No later general restore was found. This is a source defect/risk suitable for a separate reviewed fix, not an implemented change here.

Main Leon jacket pl00 and no-jacket pl08 have 66 inline FCVs each, and all 23 selected weapon archives have no MTC. Ordinary aim/lower, reload, recoil, locomotion/aim transitions, damage/death therefore do not use the ordinary external-FCV cache for those selected source clips. That does not clear their other read paths:

- `initWepHand` stores source pointers; hand setters build infos from admitted BIN/TPL. [LEON_HAND_PACK](https://github.com/lamb2k/re4dc/blob/9eb83d59/port/dreamcast/game/coarse_actor_leon_hands.inc#L101) has four AICA cells (two per side), an LRU, weapon prefetch, async miss/refill and movie yield. More alternated hand blobs than cells can cause repeated reads even though FCVs are inline.
- The pl08 render pack can survive a same-room bind away/back, but room leave frees it. Owner unbind retires draw/source memoization; it does not by itself prove every texture is evicted. Native UI may return texture-key hits or read after cache pressure.
- Weapon heap allocation may evict motion keys to make room; weapon bank replacement is distinct from the finite hand cache. Historical `qws19/gd2` shows distinct weapon loads of 14-16 calls / roughly 397-543 KiB, but is not exact-current QA/console timing.
- Costume changes use `PlSetCostume` -> `PlChangeData` -> `ReadPlayerData`, releasing/reloading player and weapon data. Movie release/restore can also reload weapon data. These are admission/transition reads, not per-shot FCV misses.

QA owns exact-current normal weapon switching, Equip, aim/reload and enemy hit/appearance coverage. The source sites above identify what to observe; no no-I/O or full-fight closure is claimed from main-DRS residency alone.

## Validation and remaining attribution

The selected-data checker succeeds: 23 texture patterns, three correct ammo-unit bindings, ordinary nine-record muzzle sequence, combat FCV file identity, packed index CRC, weapon guard ordering, and 29/29 source hashes byte-identical to 9eb83d59. Python compilation and the existing six semantic cache-audit tests pass. No new build or capture was needed.

Next useful evidence is QA's normal first-appearance and hit control with exact active actor ABI, physical-sector tags and cache counters. Modern GCC has a manager vptr: QA verified pAlive at +0x14, cUnit be_flag +4/next +8; stale commented +0x10/+0/+4 offsets must not drive conclusions. Physical read timing, CPU work, texture first use and recurring cache thrash remain separate findings until caller/archive/key evidence joins them.