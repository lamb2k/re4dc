# Boss and character animation-cache coverage — 20 October 2026

The earlier Mendez check was not an all-boss cache audit. This audit reads the current fixed QA Disc 1 bytes, traces source animation consumers, and keeps later castle/island data separate. It introduces no game, renderer, asset or geometry change and runs no new guest or build.

The concrete findings are:

- Ashley's original archive has a source-constructible three-stream loop in a strict two-slot cache. The checker catches the actual failing entries 0/6/61. The fixed archive embeds all three and clears that specific finding; retained QA movement confirms the fix in that window.
- Mendez is the other selected strict two-slot profile. His spear blend uses two FCVs, not four: the sign branches are exclusive and the fourth argument is a sequence. No retained per-Mendez I/O trace establishes thrashing; the other states and borrowed player motions are not closed by this result.
- Leon's two main archives and all 23 selected weapon archives retain their FCVs. His separate hand geometry cache can still read the disc, and weapon/costume/room loading can read archives. “Leon has no I/O” would be false.
- Historical island Krauser logs show a three-entry reload loop. A later prepared archive adds those entries to its preload set, and its retained follow-up stops that loop in the observed window. Preload is not a permanent residency guarantee under pressure.
- No all-boss, all-state, whole-fight cache closure or new console performance result is claimed.

## Exact inputs and meanings

[The asset-free receipt](animation-cache-coverage.json) records every selected wrapper/body hash, cache table identity, source digest, source-family indices, unresolved consumers and retained-log identities. The full private report is retained at `C:/Flycast-Evidence/re4-dreamcast/boss21-20261020/animation-cache-coverage-work.json`; its hash is sealed in the receipt. It includes per-reference ARC→FCV key/state mappings without copying animation payloads.

Source is QA `9eb83d59`, read through checkout `e974d7b0913e69d9fd38676a2e035605128edcbc`. A fresh `git diff --exit-code 9eb83d59` over `src` and the relevant motion/preparation sources passed. The later pause fix and docs do not change these paths. Current fixed image is `/dev/shm/qa21-r11e-hot-20261020/master03/track03.iso`. All 66 selected `em/*.drs` files match the supplied manifest, as do the actual boot program and Leon hand/costume packs. Boot SHA256 is `1e283acbf70ef669e257605484533fcbf39cc95a4ae0f3ba6c3c7467f6b24969`.

“Inline” below means the selected archive embeds its FCVs and has no motion-cache table. Once that archive is admitted, this cache cannot evict those FCVs. This says nothing about archive admission, other archives, texture/render packs, sound or movies.

“v2” means two reserved slabs plus conditionally available spill/cold-pool storage and global pressure eviction. “v3” means the identity-pinned strict two-slab profile, without spill. A table's hot flag preloads a cache entry; it does not lease it permanently. The actual QA knobs are reserve=1, spill=524288 B, pressure=262144 B, cold pool=262144 B, castle cold pool=0; per-miss and working-set logs are off. The source observer provided QA's per-binding evidence instead.

Source contracts: `native_motion.cpp:253` (pressure), `:492` (per-archive miss marker), `:516` (MOTWS working-set usage), `:535` (ordinary archive needs no cache), and `native_motion_r11f_profiles.inc` (three exact v3 identities: Mendez, old Ashley, fixed Ashley). These are in `port/dreamcast/game/platform/`.

## Current fixed QA Disc 1

Counts are distinct FCV payloads, not actor counts or simultaneous motions. A large reachable family alone never proves thrash.

| Actor / encounter | Actual selected animation storage | Source assessment | Retained cache coverage |
|---|---|---|---|
| El Gigante, r119 and r11e | `em2b`: v2, 89 cached cold + 29 inline; native 2258208 B, two 31616 B slabs | Body blends, attached tree/parasite and borrowed player motions share source archive ownership. `em2b_R1_Walk:1338` and Stamp:1486 consume Work aliases. Multi-owner/state closure remains open. | Historical bind/render checks exist; no per-em2b miss telemetry in the scanned logs. Two older r224 MOTWS traces are usage, not Disc 1 fight closure. Current QA pre-fight Ashley fix does not test the boss fight. |
| Del Lago, r10b | `em2f`: 23 inline, native 1280576 B; no MTC | Literal idle/swim/attack/damage motions remain source-owned and embedded. Boat/player archives are separate dependencies. | No per-em2f cache-I/O trace found; this archive does not use this cache. Whole encounter/global I/O remains separate. |
| Mendez, r11f | `em35`: v3, 82 cold + 1 inline; native 1035392 B; two 123008 B slabs | Reviewed spear set is `6a + (6d OR 6c)`, with SEQ `6b`. Fits two. Player grab/damage callbacks borrow em35; other phase/state concurrency is not fully proved. | 21 matching-size bind logs in this 1012-file scan, no per-em35 miss/MOTWS rows. Earlier focused scan was 917 files / 51 Mendez matches, not all-boss coverage. No confirmed Mendez thrash. |
| Common Ganados | `em11/12/13/15/16/17`: v2, respectively 157/145/155/158/149/133 cached; `em14`: 167 inline | Source idle, five walk/run sequence styles, nearby response, attack, damage/death and initialization families mapped. Work/model alternatives and active actor combinations remain explicit. Existing em12 prefetch audit is diagnostic/incomplete. | Three older matching-size em12 MOTWS traces; no matching-size per-em12 miss records in this scan. Usage and warm success do not establish full multi-actor retention. |
| Partner Ashley | Fixed `pl11`: v3, 61 cold + 10 inline; 411744 B. Original: 69 cold + 2 inline; 384064 B | Known recurring body/back/face set is now inline. Other table/shape states are not automatically certified. | Confirmed baseline thrash; fixed Flycast pre-fight idle and normal movement pass. Console and whole encounter pending. |
| Leon jacket / no jacket | `pl00` 838144 B and `pl08` 861216 B: each 66 inline, no MTC | Main locomotion, damage/death and neck blends stay resident after admission. Weapon table dependencies and hand/render data are audited separately below. | Current QA retained cold start actually loads `pl08`, `wep02`, hand package and PS2 costume pack. `pl00` is present on disc, not exercised in that window. No animation thrash established. |
| Leon weapons | All 23 selected `wep*.drs` have no MTC | Weapon locomotion, aim/ready, gun motion, reload and neck references remain embedded in their admitted weapon archive. A change of equipped archive still calls `ReadWepData`. | `wep02` is observed loaded. No claim that all weapons were equipped/tested. |

Ganado preload bytes for em11/12/13/15/16/17 are 0/225184/198944/242176/0/124736. The latter sets help common transitions but can be evicted by global/movie pressure. The reused em10 audit maps 75 distinct source-reachable keys / 952768 B for its union; that is a reachability inventory, not a simultaneous 952768 B demand.

## Source combinations that matter

**Ashley: demonstrated recurring three-stream set.** `src/game/pl_npc.cpp:373-383` sets healthy body ARC `0x12` and back ARC `0x18`; `backCheckSet:2702-2709` attaches the second MotionWork. `moveFootwork:448-472` can set and hold face 4, then return to normal footwork. `src/pl11/pl11.cpp:103-109` binds held facial FCV `0x6d`. The regular move calls `ShapeMove(subShape)` at `pl_npc.cpp:274`; held shapes still evaluate through the lease at `src/game/shape.cpp:236`. `src/game/motion.cpp:484,493,514` evaluates main and attached blend. Thus body + back blend + held face recur through one binding; this is not three unrelated states.

Original mapping is ARC12→entry0/key `6a300b14-7ae9f066`/5152 B, ARC18→entry6/`5bda6eb4-95dd506d`/5056 B, ARC6d→entry61/`eaa1231b-cb8a14f8`/448 B. All three are cold in original v3 and exceed two slots. The fixed selected archive embeds all three; reserved slab bytes remain 50880. The tool checks these actual old entries and fixed mappings as a regression. The QA receipt reports 167 additional loads/evictions and 3011 physical reads in the stalled baseline continuation, versus one 8192 B physical read and one load/eviction in the fixed movement continuation followed by 28 quiet seconds. This is Flycast evidence for that window, not a console benchmark.

**Mendez: avoid a false four-clip claim.** `src/em35/em35.cpp:3257` calls the spear blend with `6a,6d,6c,6b`. `em35BlendMotSet:5055-5084` sets the main FCV and one sign-selected secondary; `6b` supplies the sequence. The sign is established before repeated spear case 1. The separate player callbacks borrow the enemy archive (`:1719`, `:1806`, `:1931`, etc.); they matter to a complete state/concurrency proof. The dead lower body is not assumed to animate forever: Divide `:1098-1141` stops advancing after completion. No third recurring cold stream is proven here. No-Mendez-thrash and full closure are both unproven.

**Krauser: demonstrated historical three-owner demand.** `src/em39/em39.cpp:3747,3755` sets attached gun ARC `0x2f`, main body `0x7f` and positive-pitch secondary `0x81`. `em39BlendMotSet:7347-7371` chooses the secondary by pitch sign. The attached weapon's `src/game/emwep.cpp:2791` evaluates its own motion each tick. Those source indices map to entries 4/48/50, keys `877ecc58-ed74072d`, `294e016a-4433ef5f`, `076d1510-ec40a72e` (1056/4800/4704 B). This is three concurrent recurring streams, not merely a library of many attacks.

Historical `island18-20261018/h-i18s4/.../cx-r31c-walk-kev1/capture/run-output.txt` has 267 per-binding miss records; entries 4/48/50 occur 85/81/81 times. Its bind preload is 67712 B. Prepared `island18-krauser-triplets-20261018/em39.drs` changes only five hot flags and table CRC, adding entries 4/6/48/50/83; SHA `0125b0a8285f5b7626a2f0d106d8c50ad4a3c845c6c714084e16126e034c0675`, preload 90144 B. Retained kev2 binds that preload contract and has 30 misses total, with each dominant-triplet entry loaded at preload and once again after pressure eviction. The fixed prepared hash is verified against its prior verification receipt. The old log's byte count/preload contract is not a substitute for an exact disc hash, and no full-fight acceptance is inferred.

## Leon's separate dependencies

`prepare_enemy_motions.py:162-165,256,325,333` permits textures-only preparation of both main costumes; actual bytes confirm it. `src/game/read.cpp:794-870` chooses/loads the main costume. `src/game/player.cpp:438-601` chooses idle, walk/run and neck motions; `pl_class.cpp:1677-1689` binds a separate neck MotionWork. Hokan is interpolation from stored pose, not automatically another live clip (`motion.cpp:157-176,333`).

Weapon `setMotion` fills `pMotTbl`; for the actual Mauser, `src/wep02/objMauser.cpp:284-309` maps idle/walk/run/back/turn/neck/damage entries into `wep02`, keeps the player-owned damage entry and sets weapon hand models. Its ready/down/reload paths and multiline reload macro are included by the checker. `ReadWepData` at `src/game/read.cpp:1205-1393` remaps weapon variants and reads a new archive. Those load-point reads must not be described as per-frame animation misses.

The independent hand package at `port/dreamcast/game/coarse_actor_leon_hands.inc:6-19,101-125,163-230` has four AICA geometry cells, two per side. Room/equip prefetch helps standard poses; uncommon pose misses queue an async package read while the previous hand remains drawn. Movie audio yields and later refills these cells. Costume render pack loading is in `coarse_actor_pl08_pack.inc:35-48,75-81`. Actual selected files are the 95520 B hand pack (SHA `d752aac5…16697f`) and 61184 B PS2 pl08 pack (`beb8c198…5283f`).

Qualified QA cold-start hot02 logs explicitly read `em/pl08.drs:597`, publish the 61184 B pack `:606-607`, and read `em/wep02.drs:928`. Separate hand worker landed reads occur in hot01; hot01 was rejected for audio and supplies no performance acceptance. There is no basis to attribute the Ashley animation stall to Leon or to promise that Leon's render/hand path performs zero reads.

## Later castle and island — separate from QA Disc 1

Castle identities are from the retained boss21 r221 diagnostic tree, not a new final castle image. Island identities are prepared candidates, not proven currently selected shipping bytes.

| Boss | Actual later inspected archive policy | Retained telemetry and remaining closure |
|---|---|---|
| Garrador r201/r20c/r218 | `em1b`: v2 173 cached + 5 inline, 1163168 B; `em1c`: v2 179 + 4 inline, 1276800 B | em10 ClawAtk/ClawWalk/ClawCriHit, nearby/bell responses, damage/death and module Work alternatives mapped. Matching-size em1b bind logs exist, no per-binding misses. Older r218 MOTWS is a different 1597952 B body; usage is not current I/O closure. |
| Twin El Gigantes r224 | Same em2b v2 policy and exact wrapper hash as QA | Older MOTWS exists but frozen-window zero usage is not whole-fight evidence; current render/601-tick STRICT checks do not certify cache retention. Two bodies, auxiliaries and player callbacks remain encounter-specific concurrency work. |
| Verdugo r221 | `em2c`: 81 inline, 2888992 B; no MTC | Source Work blends, claw/tail/grab and source damage mapped. Ordinary grab and frozen native fixture are retained; no independent cache-I/O proof. Inline FCVs remove this archive's eviction loop, not texture/audio reads or ice look mismatch. |
| Salazar r228 | `em38`: 54 inline, 2377440 B; no MTC | Wait/head/attack/damage Work motion alternatives mapped. Role package checks are render checks; whole fight/global reads remain open. |
| U3 r31b | Prepared `em32`: v2 51 cached + 47 inline, 3684000 B | Walk/dash/attack Work blend fields mapped. Helper selects two FCVs; four arguments are not four simultaneous clips. Historical misses use a different 1132416 B body, so do not cover this prepared layout. |
| Krauser r31c | Prepared `em39`: v2 154 cached + 13 inline, 1423712 B; 90144 B preload | Historical triplet thrash and targeted mitigation above. Other knife, bow, mutation, player callbacks, transitions and pressure remain open. |
| Saddler r332 | Prepared `em31`: v2 77 cached + 6 inline, 1452032 B; 255616 B preload | Four old per-binding miss logs, 71 records total (some repeated fixtures), exist. They show reads, not a repeating thrash loop or full retention. Body/head/tentacle/player aliases and phase-specific indirect selectors remain open. |

The retained scan covers 1012 `run-output.txt` files in the named boss21, boss18, island18, cast16, ch2code, ch2regen, rel19, rel191 and rel20 roots. It is not a search of every private file or an assertion about files absent from those roots. `motion miss` records identify actual per-binding I/O; MOTWS identifies used keys/bytes; global disc/cache counters require room/binding attribution. Log throttling and diagnostics-off builds make absent miss lines inconclusive.

## Reuse and checks

[animation_cache_audit.py](animation_cache_audit.py) reads an ISO, its selected manifest, optional original control ISO, later tree and explicit prepared archives. It verifies actual tables/CRCs, maps source ARC word indices (`slot+4`) to actual FCVs/keys/inline-or-cache state, expands the existing em10 WALK/BACK audit, records literal function families and exact indirect consumer/Work references, and checks only reviewed recurring sets for capacity overflow. It never converts a total reachable set into a concurrent demand or promotes a production hot set.

Run with `--source-root`, `--tools-root`, `--iso`, `--manifest`, `--resolved-knobs`, `--baseline-iso`, `--later-tree`, repeated `--archive label=path`, repeated `--log-root`, and a fresh owned `--output`. Private exact invocation is retained in `codex-lanes/boss18/boss21-cache-run.ps1`. All data remains private; the committed files are source and metadata only.

Validation: the actual original/fixed Ashley regression passed; six asset-free semantic tests passed (strict overflow, inline repair, key aliases, v2 spill distinction, missing mapping, multiline macro/comment parsing). Source-pin comparison and Python compilation passed. No new geometry, capture, build, integration or publication occurred.