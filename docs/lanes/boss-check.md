# Lane boss-check (2026-11-02)

User 11-02: "check for the reduced boss models which was done recently and run the GameCube debugger or similar to
ensure they are functional". Base: t15/int 15ed29fe (rr candidate cand-15ed29fe). Evidence: D:\RE4DC-Lanes\boss-check
(moved off C: by the coordinator's 11-02 disk rule).

## Reduced boss levels built

| Boss | Room | Level | Body+head tris (full -> level) | Data set | Knob | In release recipe |
|---|---|---|---|---|---|---|
| El Gigante type 0 | r119 | g50 (gig2b00-g50) | 4,244 -> 2,046 (48%) | boss18g50r (boss18-gigante-g50-t18-20261018) | NATIVE_MODEL_REGISTRY_LOD=1 | yes |
| El Gigante type 2 | r11e | g50 (gig2b02-g50) | 4,296 -> 2,064 (48%) | boss18g50r | NATIVE_MODEL_REGISTRY_LOD=1 | yes |
| Mendez forms 0/1/2 | r11f | g70 in every form (m35full/legs/upper-g70) | 6,956 / 6,981 PS2 -> ~70% | cast16 (reg-11fLo) | NATIVE_MODEL_REGISTRY_LOD=1 | yes |
| El Gigante twins type 1 | r224 | p51 (gig2b01-p51, 50.9% positions) | type 3 stays full | boss18-twins-approved-20261019 | NATIVE_MODEL_REGISTRY_LOD | no (no data set on Disc 2) |
| Verdugo | r221 | protected candidate (76% at "g70") | 12,350 PS2 | boss18-verdugo-g70-20261019 | - | no (no selection) |
| Garrador | r201/r20c/r218 | trial 89.6% skipped | 1,993 PS2 | boss18-garrador-lod-20261019 | - | no (full kept) |
| Del Lago | r10b | none (full accepted, g70 skipped) | 2,877 PS2 | - | - | full |

## Results (Flycast, census twin of 15ed29fe, 60 s chunks chained by save state)

- r119 El Gigante g50: drawn g50 all fight (NMRD gig2b00-g50, 0 declines), kill reached (rig, source damage path), CAST-GC
  PS2, TEXCHK PASS. **Broken (not the level):** the parasite event r119s30 (movie 11930) and the death event r119s20
  (11920) are refused, `route movie heap: order: piece N short` (terminal=3, 0 pictures). Same with the full-only r119
  package (A/B disc cfull119), so g50 is not the cause. Test 18 (fix18 sk-g3) played both; heap 4 is 127 KB smaller
  now (7,593,088 -> 7,465,792) and native4 grew. Report: larger fix (movie memory), not in this lane.
- r11e El Gigante g50: kill reached; full model in the grab/event frames, g50 in play (both descriptors drawn).
  **Broken, fixed here:** after the death its whole-model fade (invisible_factor < 1) declined (semantics 3) and the
  corpse drew GC (CAST-GC MIXED, 504 GC draws). Same with the full-only package. Fix: NATIVE_MODEL_REGISTRY_DYING_BOSS=1
  (default 0) extends NATIVE_MODEL_REGISTRY_DYING's fade path to em2b. Fixed run: CAST-GC PASS, TEXCHK PASS. Knob-off
  release image identical (f6f938e6). Trace pair (r11e, kill at room frame 200, 1299 ticks): no discrete divergence,
  pm/em float drift from tick 989 (fade frames): gameplay-equivalent, not STRICT.
- r11f Mendez g70: both forms killed (source damage, 116 + 54 hits), s00 QTE passed, s02 / s10 / s11 movies played, window
  jump and the area 00 door to r10f. CAST-GC PASS (m35*-g70 PS2), TEXCHK PASS.
- r10b Del Lago (full): kill reached, s20 / s22 death movies played, room change to r11b. CAST-GC PASS. TEXCHK FAIL:
  10 `no contiguous block` 256x256 uploads at frame 3018 after the death (VRAM fragmentation; report).

## GameCube reference (Dolphin)

dol2.py (scratch, from Codex boss21's owned-Dolphin method): debug Disc 1, AR room redirect, neutral DTM + game pad
fields written in the owned process, RAM watch of em hp (+0x320) / routines, XFB stills. r119 via the r11a door: El
Gigante type 0 hp 1000 (same as ours), grab event (Status_flg[1] 0x10000000) seen, handgun at the knee: debug HUD
SHOT 30 / HIT 16 (D:\RE4DC-Lanes\boss-check\dolphin\g-r119h). hp did not move under handgun hits in that window.

## Ready to land

- NATIVE_MODEL_REGISTRY_DYING_BOSS (patch boss-check-dying-boss.patch): add to the release CH2 line after a look check.
