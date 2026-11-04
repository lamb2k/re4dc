# Test 27 scope (FROZEN 2026-11-04, candidate t15/int 6eeae2947)

User 11-04 ("What test build are we on? I haven't seen one pushed"): no candidate since Test 26 (11-02), because the
Coming-soon list held long content items. User choice: **"Ship now, rest to 28"**. Base: Test 26 (tag
test-638521db-20261102, t15/int 799960376). 88 commits since. Rules: release build rules in CLAUDE.md.

## In Test 27 (landed on t15/int 6eeae2947)
| Item | Landing |
|---|---|
| PS2 sky in normal play (outdoor rooms) | sky27h ab8af1d2c, merge b1010b5bb, recipe a484b261c |
| Boss fixes: El Gigante farm cutscenes + fade, Del Lago textures after death | bossmem26 0da704942 (MOVIE_WORLD_ARENA_R119=2, NATIVE_MODEL_REGISTRY_DYING_BOSS=2) |
| Save-reload crash guard (El Gigante death + Ashley) | crash26 35973184f, WEAPON_HEAP4_WALK_GUARD (a484b261c) |
| El Gigante slowdown after objects break | motionpin 4bb1c6df3 + recipe 31b04b9bf (MOTION_PIN=262144) |
| Castle chapter 3-1 rest (r203/r207 PS2 data, r207 hall deferred goto) | world-ch31 26dbcfe4c |
| Castle chapters 3-3 / 3-4 (r20c, r20f, r206, r20d, r20e) | world-ch334 83c26c8ee, trans34d2 623421691, fc950c9b7, 6eeae2947 |
| Castle hitch fixes (r208 615 -> 275, r207 387 -> 7.3, r201 249 -> 7.5, r202 395 -> 8.6 ms worst tick) | coldfix af671994c, 5a763e8ad, 509d113f8 + 5bedbf2cf |
| Speed switches (r10e ~-3 ms, r101 cross -0.5 ms MODELLED) | logicbudget 1696c83a9 + 5c1c9601f, LOGIC_LOD_FAR 5bdd4dcd3 |
| Smoother music stream reads (one 24 KB read per refill) + resident lists | playreads affa7d4bb + 16b0d3aff |

## Moved to Test 28 (still in progress)
- Chapter 3-2 (r205, r209, r20a, r20b): world-ch32 (Novistador native draw, r205 backtrack heap).
- Chapter 4: world-ch4 (r229 FAULT, r21a cap, textures).
- Disc 3, island + final chapter: world-ch5 (waits on assets-dc r300 dcf3isl).
- Torch glow as the PS2 draws it.
- Next PS2 asset batch: assets-dc (cgca27b/cpic27b, cgca32/cpic32b, dcf01-03, arcdrop, PKG_PS2_SIZE).
- roomscan detail cuts (r119/r11d/r111 first), motion folder index (playreads), castle culling/frame budget (castlebudget).

## Release checklist (owner: release lane rel27)
Quick smoke -> QA disc first (non-blocking) -> full tier, KOS, GDEMU race (10 seeds per disc), knob-off identity,
package (two-disc game zip + QA disc), kit-check + kit-boot, front pages (README What's new with Flycast images,
port README At a glance, KNOWN_ISSUES header), notes with "In progress: Test 28", Test 26 -> draft.
A non-blocking finding ships with a KNOWN_ISSUES row + GitHub issue (rule 6); a crash/hang/stuck/save loss or a
regression against Test 26 blocks.

## Scope change 2026-11-04 (user pulled in)
- **em14lc** (castle Zealot em14 with motion streamed cold, PS2 motion; data set /root/re4data/private/em14lc-20261104, D2_DATA
  after cgca26). Found by castlebudget: on 6eeae2947 r20f stalls > 60 s on entry (em14.drs 3.9 MB vs 3.4 MB heap 4 free, endless
  8-retry reads; rr 1104-0628 d2cg-r20f 237 read failures); r204's 11-Zealot chase (live since Test 26) never spawns. Progress is
  not kill-gated in either room. User: "Pull em14lc into Test 27". Landing branch lane/em14lc-t27 (castlebudget); candidate rebuilds.
- LANDED 2026-11-04: t15/int ff to 8570607ff (lane/em14lc-t27: t11-fix em14lc + D2_DATA). Checks on rel27's 6eeae294 programs: r20f 0 read
  failures, Zealots spawn/fight/die, lever event; r204 chase em14 x4, 29.9 fps; KOS 48 KiB PASS; Disc 2 453,343 sectors.
  **New candidate = t15/int 8570607ff.**
