# Test 23 console discs waiting for the user (2026-10-23)

QA overlay: QA menu (hold L + R, press D-pad Down) > Speed display ON; top-right number = fps x10.

| Disc | What it compares | Where to look |
|---|---|---|
| DONE 10-23 (console: A > C > B, closed) RE4DC-QA23-Scratch-71a9b50f | Spare-memory world drawing: QA row WORLD SCRATCH A normal / B half cache / C scratch | R101 by the cross (fog view), R101 close house wall, R109 entry; 9 numbers; keep only if C beats A |
| RE4DC-QA23-PVS-15521d78 | World visibility tables: QA row PVS off/on (expect no gain, Flycast says a bit slower) | R101 by the cross facing east, same spot facing west |
| RE4DC-QA23-actorwallcut-81ba5f95 | Characters behind walls not drawn: QA row ACTOR WALL CUT on/off (boots ON) | QA chapter "ACTOR WALL CUT VIEWS": R101 house wall, R103 barn wall, R119 Gigante cottage |
| RE4DC-QA22-WorldMeter-28e23d82 | World draw meter rows (fog vs house; opaque cut 10 m / 8 m) | as before |
| RE4DC-QA23-Arena-BLayoutFix-7617e07c | Room texture arena + cache write-back line by line (suspected crash cause) | QA preset r101, play 2 min; photo any crash screen, else the Diagnostics VRAM FAILS row |
| RE4DC-QA23-Arena-NoTop-7617e07c | Room texture arena + layout step only (no cache fix) | same as above |
| RE4DC-QA23-DamDiag-87a970c8 | Dam crash diagnostics (I52 line on the crash screen) | QA preset r10c, reach the first villager, fight 2 min, 3 tries; photo any crash |
| RE4DC-QA23-Backface-Off-46623a9e / -CPath- / -SH4ZAM- / -CNoDrop- (4 discs, same source) | Back-face: off, our C path (was 14.9 vs 18.9), Codex SH4ZAM, C walk keeping every triangle (diagnostic) | Same view as the 18.9 fps photo, else R101 by the cross and R100 forest path, 10 s still each (STEPS.txt). SH4ZAM passes only if faster than Off; CNoDrop near CPath = the walk is the cost |
| RE4DC-QA23-BackfaceCone-Off/-World/-Character/-Both-090fe7a0 (4 discs, same source) | Back-face per group: off, world groups, character groups, both (World/Both leave only 1.3 KB heap before the r100 cliff movie) | Same views as the back-face discs above |
| DONE 10-23 (console: both ~9 fps; OFF loses Leon hair = overflow; ON keeps it; next: fix-r10d-speed23) RE4DC-QA23-Hideout-Off-d1bc83cf / RE4DC-QA23-Hideout-On-851c2d64 | #55 merchant cave freeze: back-face cull only in r10d (On) vs release (Off) | QA preset "R10D DAM SIDE ROOM", walk toward the merchant hut, turn so the whole hut is in view; watch for freeze with HUD gone / stray triangle; optional R102 ENTRY, R112 ENTRY. On should not freeze |

## SD card (2026-10-23)
Menu slots 152-160, names start "RE4DC T23" / "RE4DC T22" so they sort together in openMenu (alphabetical): Hideout OFF / ON, Backface OFF / SH4ZAM / C, World meter (157), Arena fix / layout, Scratch. All 9 re-hashed OK on the card 10-23. (C keep moved to overflow.)
The openMenu catalog is full at 160 (24,576 B allocation). Copied and verified, but parked off-menu in E:\TEMP\t23-overflow: Cone OFF/world/character/both, Dam diag, PVS, Actor wall cut. To use them, swap them into 152+ after those tests are done (rename the folders, then rerun renum_menu with LAST=160).
| RE4DC-QA23-WaterTraps-fc1a230e (vs the Test 22 QA disc) | #55 water in r10e cave river / r10c dam river / r10d pool, and tree-trap explosion (WATER_PS2_EXT=1 TRAP_FX=1) | README presets r10e, r10c, r10d, r100 tree bomb. Hardware confirmation only (Flycast already shows both) |
| RE4DC-QA23-mendez-a8546da0\off / \on | #55 Mendez barn light flicker (LIGHT_CUT_HOLD) + #41 effect drops (FX_ROOM_SPILL_KB) | README-MENDEZ.txt: "R11F ENTRY" (phase 2, stand on the front loft / crates: light should not flash orange with On), R200 truck preset; pause/settings freeze check |
| RE4DC-QA23-R10D-f263f6ad | r10d cave: torch drop + LOD + static bake, back-face off | README-R10D.txt: R10D DAM SIDE ROOM, hut view: fps, Leon hair present, walk around the hut |
| RE4DC-QA23-Flashlight-cb682b07 (zip) | #55 flashlight pool (option B) | QA presets r11e (with Ashley) / r11d: lit ground ahead of Leon |
| RE4DC-QA23-MendezFreeze-01cface7 | #55 Mendez freeze fix (EM35_ROUTINE_BYTES) + diag rows | R11F ENTRY, let him grab Leon and land the bear hug in both phases; he should keep attacking |
| RE4DC-QA23-FxTrim-8ebe6b7b | Essential-only effects (boots Essential; Y+START cycles 0/1/2/Essential) | Mendez barn (QA preset r11f) and r101 bell fight: fps x10 with Essential vs 0, and does anything important look missing? Extras r118/r200/r113 |

| RE4DC-QA23-StatBytes-2a14662d | Complete routine-byte correctness unit; STAT_ROUTINE_BYTES=1, STAT_DIAG=1, production diagnostics remain off | STEPS.txt: boat boarding shows harpoon/no gun ammo; VMU display; normal R101 fight, R11E boss, R11F grab/fight/window exit. Source/host/target/Flycast checks pass with documented intentional camera-query difference. Physical acceptance pending; no SD copy. |

## Private Audits QA staged locally (2026-10-23, no SD copy)

All four audit fixes are enabled together on qualified t15/int landing d5c1ceab9. Both discs below retain their exact private four-fix-ON QA profiles. Matched source-native dam/puzzle observations and loaded church pictures passed local review; physical acceptance and the historical arena cause remain pending.

| Disc | Profile and local evidence | What remains |
|---|---|---|
| RE4DC-QA23-Audits-5e4de9a0 | Normal private QA, arena OFF; source5e4de9a0, STAT1/DIAG0/QA1/PC0. Own boot/menu-warp/H2 pass, s30 340/340 with heap_before48,768. Staged raw programme and14 overlays read back against exact pins; README/STEPS/IDENTITY/hashes included. | STEPS covers normal village, R10C DAM first-villager and R117 ENTRY puzzle. Local matched event/puzzle checks pass; physical acceptance pending. This disc cannot reproduce the arena-enabled challenge. |
| RE4DC-QA23-Audits-Arena-53fcbc0b | Separate current-source ARENA1 challenge from5e4de9a0, unique source53fcbc0b; NO_TOP0/CACHE_LINEWISE0, KOS_WATCH1/KOS_SQUEEZE1. Bounded boot/warp/H2 pass, s30 340/340/restored1 heap44,672;48KiB fight modes held49,152 with minimum headroom6,152/6,056. | Follow its STEPS.txt: R101 VILLAGE SQUARE (FIGHT START), fight/move around cross and house views for two physical-console minutes. New profile, not historical B/B3 layout identity; no physical crash-cause, repair or speed claim. |

Paths: C:\Game Dev\Emulators\RE4DC-QA23-Audits-5e4de9a0 and C:\Game Dev\Emulators\RE4DC-QA23-Audits-Arena-53fcbc0b. Neither was copied to SD or published.

## Private current RR candidate d5c1ceab (2026-10-23, no SD copy)

C:\Game Dev\Emulators\RE4DC-RR\cand-d5c1ceab is the normal arena-OFF current recipe candidate. Source d5c1ceab9e06461462669b3ce1d28a379747a74a; raw programme49a4173a..., all14 overlays read back from the staged disc; original four track hashes preserved. rr quick19/19 and bundled same-source QA boot/warp/one-door checks pass locally. README/STEPS/IDENTITY/QUALIFICATION-SHA256SUMS bind the exact package and limits.

Use its STEPS for normal boot/VMU/boat, village, dam, church and Mendez progression checks. Its qa zip remains packed for manual use in a separate folder; teleport checks do not establish normal route completion. Physical-console and fresh full release acceptance remain pending; the historical dam/arena failure cause is not proved. For the separate ARENA1 two-minute challenge use RE4DC-QA23-Audits-Arena-53fcbc0b. No SDK/guest, SD copy/deletion or publication was performed by this handback.


## Private WorldEmit comparison accepted for console feedback (2026-10-23, no SD copy)

RE4DC-QA23-WorldEmit-Off-49ad20f9 and RE4DC-QA23-WorldEmit-Both-49ad20f9 are root-reviewed private comparison discs. Source 49ad20f9932d638ddb7becf5db6f86b92e0a76a2. Off uses the current recipe; Both enables SELECT_LEAN2 and EMIT_PREFETCH. Both switches remain off in production.

Follow STEPS.md: compare R101 cross and close house-wall views at identical settings, three Diagnostics readings each. Photograph the disc label, world/phase/FPS rows and the matching camera. Hardware improvement is not established; earlier MODELLED combined differences were negligible or slower.

Independent readback verifies all 1,747 files per arm, main/all 14 overlays and the exact two-switch profile difference. Actual final-GDI boots and separately labelled proxy menu-warp/H2 checks pass. Normal QA H2 is 340/340/restored, Off 40,576 / Both 44,448 bytes. These do not replace production-profile KOS/memory gates. No QA Mendez or full-route test was run.

Both arms preserve all original assets and share one private PS2 load/upload repair file. Visible use and appearance remain unproven; production appearance is unapproved. No GameCube fallback was added. Track03: Off 4930522dfb2dcdd68219d159c4f54d30eaf13d28c7f54cd5108447303830f987; Both eb2c05fbe7ed104d91d8ed51048a5a0c7a0fd03b396ddb94eefa03472537647b. ROOT-ACCEPTANCE.json and refreshed IDENTITY/SHA256SUMS accompany each disc; earlier worker metadata is preserved in private root-delivery evidence. No publication, ZIP or SD copy.


## Private Dedup comparison accepted for console feedback (2026-10-23, no SD copy)

RE4DC-QA23-Dedup-Off-4be08e01 and RE4DC-QA23-Dedup-On-4be08e01 are root-reviewed private discs from exact frozen4be. Off uses originals; On selects the validated compact world alternates. Both retain original DATA29, all 41 shared Ganado textures and the same four alternates. Production dedup remains off at integration fb254e82; no hardware speed gain is established.

Use STEPS.txt: two minutes moving between the R101 cross, houses and village edges, matching route/settings in both arms. Check geometry, UV/colour seams, flicker, freezes and loading; preserve labelled photos. Optional R103/R100 and movie return checks remain physical observations. Actual final-GDI boots and separately labelled proxy menu-warp/H2 pass locally; independent readback verifies all 1,750 files and full programme/all-overlay/profile identity per arm. Normal QA heap_before is Off 48,768 / On 98,496 bytes; standard qualification is separately 93,920 / 139,552. Both movie profiles reach full 340/340 and restore the borrow.

Track03: Off 52d2c05d1fa37d5d72546bb560cb317048540eb5ae1e97d6ae350aba9a0dc2a5; On e09cc566770513cd53647a7429d0f7f992fe5d6718e82a8bd960d6effb8d5920. ROOT-ACCEPTANCE/IDENTITY/SHA256SUMS accompany each disc, with original worker metadata preserved externally. The known baseline Mendez late-pair material limitation is unchanged; no separate private PS2 repair is included. No full route, fresh full release, physical acceptance, ZIP, publication or SD copy.
