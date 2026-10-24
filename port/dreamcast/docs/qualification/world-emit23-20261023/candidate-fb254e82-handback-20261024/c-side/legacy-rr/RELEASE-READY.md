# RELEASE-READY (lane rr: always-ready release candidate)

Updated 2026-10-23 23:56 by `rr-cycle.sh` (WSL watcher, every 10 min when origin/t15/int moves). Commands: `rr.sh status | cycle | full | package <tag>`.

**Last good candidate:** t15/int fb254e82, image 49a4173a1792823f, cycle 1023-2350-fb254e82, disc `C:\Game Dev\Emulators\RE4DC-RR\cand-fb254e82\gdemu`.

## This cycle: PASS (quick tier)

- t15/int fb254e82; recipe: Test 20 line (T15_V of t15-build.sh at the built commit)
- image (objcopy -R .stack) 49a4173a1792823f
- heap 4 before s30: 93920
- KOS min headroom: 6112
- evidence: C:\Flycast-Evidence\re4-dreamcast\rr\1023-2350-fb254e82

| check | result | detail |
|---|---|---|
| step trees | PASS | rc=0, 1 s |
| step build-release | PASS | rc=0, 40 s |
| step build-twins | PASS | rc=0, 48 s |
| step package | PASS | rc=0, 37 s |
| step bases | PASS | rc=0, 61 s |
| missing.txt empty | PASS | release build out-rrfb254e8rP |
| disc_lint loader | PASS | DISC_LINT PASS /root/rr/work/1023-2350-fb254e82/pkg/gdemu/disc.gdi profile=loader violations=0 |
| disc_lint standard | PASS | DISC_LINT PASS /root/rr/work/1023-2350-fb254e82/pkg/gdemu/disc.gdi profile=standard violations=0 |
| boot to title | PASS | title reached |
| h2 s30 movie | PASS | frames 340/340, heap_before 93920 |
| KOS 48 KiB fight | PASS | PASS kos-fight-49152-0 headroom 6208, PASS kos-fight-49152-1 headroom 6112 |
| GDEMU race gdemu | PASS | GDEMU RACE GATE (gdemu) PASS 0/1 failed |
| census ran | PASS | 26/26 rooms: r100 r101 r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r10f r111 r112 r113 r117 r118 r119 r11a r11b r11c r11d r11e r11f r200 |
| CAST-GC | PASS | CAST-GC rr: 413 census lines, 57 room/model rows, 0 GC or MIXED character rows not allowed (PASS) |
| NOT-DRAWN | PASS | NOT-DRAWN rr: 249 alivelist lines, 22 room/id rows, 0 alive but never drawn (PASS) |
| LEON-GC | PASS | 26/26 PASS |
| TEXCHK | PASS | 26/26 PASS |
| VRAM no-contiguous 0 | PASS | all rooms 0 |
| census HALT/FAULT/MISSING 0 | PASS | none |

NOT-DRAWN rows (judged, see the NOT-DRAWN check): NOT-DRAWN rr: 249 alivelist lines, 22 room/id rows, 0 alive but never drawn (PASS)

## Wall times

| step | seconds |
|---|---|
| trees | 1 |
| build-release | 40 |
| build-twins | 48 |
| package | 37 |
| bases | 61 |
| jobs | 0 |
| flycast | 225 |
| total | 412 |

Flycast jobs (30, slots <= 12): first start 23:53:09, last end 23:56:54.

| job | seconds | rc |
|---|---|---|
| h2 | 168 | 0 |
| kos | 63 | 0 |
| cg-r100 | 62 | 0 |
| cg-r102 | 62 | 0 |
| cg-r103 | 62 | 0 |
| cg-r104 | 62 | 0 |
| cg-r105 | 62 | 0 |
| cg-r106 | 62 | 0 |
| cg-r107 | 62 | 0 |
| cg-r10b | 62 | 0 |
| cg-r10f | 62 | 0 |
| cg-r111 | 62 | 0 |
| cg-r112 | 62 | 0 |
| cg-r113 | 62 | 0 |
| cg-r117 | 62 | 0 |
| cg-r118 | 62 | 0 |
| cg-r11b | 62 | 0 |
| cg-r11d | 62 | 0 |
| cg-r11e | 62 | 0 |
| cg-r11f | 62 | 0 |
| cg-r200 | 62 | 0 |
| cg-r101 | 61 | 0 |
| cg-r108 | 61 | 0 |
| cg-r109 | 61 | 0 |
| cg-r10a | 61 | 0 |
| cg-r119 | 61 | 0 |
| cg-r11a | 61 | 0 |
| cg-r11c | 61 | 0 |
| gdemu | 60 | 0 |
| boot | 10 | 0 |

## Diff since the last good candidate

```
fb254e82e Document current dedup gates and default-off integration limits
81aefb0d4 Merge commit '0d30bd83098af2bcd5e9ca2197ffd4cd926e73c4' into wip/dedup-offline23-land-20261023
0d30bd830 fix: refresh offline decoder on prefetch corner path
4be08e011 Include reviewed current-source qualification and admission helpers
cb8f67f69 Bind private QA staging to its built programme overlays
7e84c4915 Prepare landed-audits baseline with frozen compact dedup unit
26b3ec582 Reject dirty Git inputs before composition extraction
b917ade84 Prepare compact dedup current-source qualification controls
386cded74 Pin legacy and compact qualification planner smoke checks
1678dbff4 Plan compact SDO3 qualification with frozen manifest and source extent
712a109aa Merge commit 'b034166e6' into wip/dedup-offline23-next-20261023
dc52bc4f5 Merge commit '82d5f827bc295c53bdd583c73cc2cb4e503c4ec2' into wip/dedup-offline23-next-20261023
b034166e6 Pin compact SDO3 binding reader and composition controls
11109d046 Share exact SDO3 strip blocks with authenticated original extent
5a1785231 Record matched standard H2 failure and corrected arena threshold
6d6cff386 Merge commit 'dc87c4658' into wip/dedup-offline23-next-20261023
a8421ca3e Merge commit '7daa521c5' into wip/dedup-offline23-next-20261023
7daa521c5 Plan private SDO3 QA pair without sampler contamination
6d7304ece Pin merged SDO3 composition with lean2 explicitly off
6634f3584 Pin SDO3 footprint controls and replacement failure recovery
5be38f009 Merge commit '3467e45c6ea8c94a4a7cc26f4cc2623197330ee6' into wip/dedup-offline23-next-20261023
1c5ab8c27 Record current integration standard OFF image identity
3467e45c6 Reduce SDO3 code footprint by reusing current decoder context
5940bbbbf Merge remote-tracking branch 'origin/t15/int' into wip/dedup-offline23-next-20261023
cf0d675ac Merge commit '4126f48e393cf8be915517ae6f5b0a696c829d9a' into wip/dedup-offline23-next-20261023
4126f48e3 Record composition rerun against exact merged c388 source
c388020e9 Preserve standard gate media and bounded full H2 helpers
d28079064 Merge commit '75229c8fa54d4a939095666036c8ee1c8f52e2fe' into wip/dedup-offline23-next-20261023
c36cd58f6 Merge commit '25f7517e9dde692585f7ff9bc3bb19652feb7c72' into wip/dedup-offline23-next-20261023
b344ef771 Merge commit '168b08df65246567e0720701b14fc1e402a3686a' into wip/dedup-offline23-next-20261023
25f7517e9 Preserve corrected standard-memory gate helpers and historical first attempt
168b08df6 Control offline dedup with reused replay emitter contexts
54240115d Merge commit '831a2115e78e762f5a14886e3b1a4b17dbf9fab1' into wip/dedup-offline23-next-20261023
04e1c8f20 Record qualified dedup snapshot, memory-profile correction and restrip queue
3911ebb40 Merge commit '75f3df38c154fecf60c19a96aede375a06ce292d' into wip/dedup-offline23-next-20261023
4c5ce8a52 Merge commit 'dffc315b30b00a1a2caf05c19f3d702edb156097' into wip/dedup-offline23-next-20261023
7e67c89c1 Merge commit 'eb1fe9533' into wip/dedup-offline23-next-20261023
dffc315b3 Trace s30 memory floor to release twin and QA image costs
75f3df38c Checkpoint dedup image, memory and full-route qualification helpers
daabb0dba Merge commit '28da09802ed9ff6756529bab02978230983453be' into wip/dedup-offline23-next-20261023
```

## Knobs vs the newest published knob file

```
newest published knob file: port/dreamcast/tools/d367/test22/release-knobs.txt
284a285,303
> PS2_WORLD_SOURCE_TEX_MIP=1
> PS2_WORLD_ROOT_POSE=1
> WATER_PS2_EXT=1
> TRAP_FX=1
> LIGHT_CUT_HOLD=1
> FX_ROOM_SPILL_KB=24
> DISC_DMA_WAIT_TIMEOUT=1
> EM35_ROUTINE_BYTES=1
> FX_LEVEL=3
> FX_TRIM=1
> SCENERY_SELECT_ONLY=1
> SCENERY_REPLAY_LEAN=1
> SCENERY_SUBMIT_BATCH=1
> STAT_ROUTINE_BYTES=1
> ESP_POOL_RECYCLE=1
> R117_EFFECT_FAILURE_SAFE=1
> KOS_CACHE_P2=1
> R10C_SPAWN_LIVE_GUARD=1
> EM_READ_RETRY=1
```

## QA disc: PASS, candidate fb254e82 (does not change the game verdict)

- QA build of the same recipe + QA_MENU=1 (QA_TEST=RR QA_SRC=fb254e82); zip kept in the candidate dir for testers
- wall: qa-disc 118 s, qa-flycast 67 s
- evidence: C:\Flycast-Evidence\re4-dreamcast\rr\1023-2350-fb254e82-qa

| QA check | result | detail |
|---|---|---|
| QA build + package | PASS | rr-qa.sh rc=0; QA_OK |
| QA disc_lint loader | PASS | DISC_LINT PASS /root/rr/work/1023-2350-fb254e82/qa/gdemu/disc.gdi profile=loader violations=0 |
| QA disc_lint standard | PASS | DISC_LINT PASS /root/rr/work/1023-2350-fb254e82/qa/gdemu/disc.gdi profile=standard violations=0 |
| QA zip | PASS | QA zip RE4DC-QA-TestRR-fb254e82-20261023-GDEMU.zip testzip ok |
| QA boot | PASS | boot keys down,a,a,a: room reached |
| QA warp | PASS | qa_menu warp to r103: room reached |
| QA GDEMU door103 | PASS | GDEMU RACE GATE (gdemu) PASS 0/1 failed |
