# Lane bossahead (2026-11-02)

User: get ahead of the later bosses and "ensure the bosses are on fast drawing paths". Base t15/int 51260612f.
Evidence: C:\Flycast-Evidence\re4-dreamcast\bossahead (bases moved here because D: was below the fp_run floor),
stills + manifest in D:\RE4DC-Lanes\bossahead. Mostly static; Disc 2/3 rooms are still being built.

## Fast-path table

Light mode is the recipe (ACTOR_LIGHT_FAST_ONLY=1, LEON_LIGHT_DIR26=1, ACTOR_PROBE_LIGHT=2). Every boss below draws
through native_actor_fast (no generic model renderer, no exact light evaluator). "Flat" = fast_only_lights, one colour per part.

| Boss | Room | em / id | Draw data today | PS2 package | Tris (PS2 source) | Light today | BOSS_LIGHT_DIR26=1 |
|---|---|---|---|---|---|---|---|
| El Gigante | r119 / r11e | em2b 0x2b | registry gig2b00/02-g50 | yes (boss18g50r) | 4,244 / 4,296 -> ~2,050 | flat | probe dir, r11e 1302/1302 parts lit (run) |
| Mendez | r11f | em35 0x35 | registry m35*-g70 | yes (cast16) | 6,956 / 5,706 / 1,273 -> g70 | flat | **declined** 2103/2103 (probe_eligible/caps255 refuse; stays flat) |
| Del Lago | r10b | em2f 0x2f | registry dellago-em2f-00 | yes | 2,877 | flat | probe dir, 301/301 lit (run) |
| Garrador | r201 / r20c / r218 | em1b / em1c type 10 | registry zealot-em1b-0ag / em1c-0ag | yes (cast16) | 1,993 | flat (Ganado class) | probe dir (by id+type; not run) |
| El Gigante twins | r224 | em2b type 1 / 3 | registry gigante-em2b-01/03 (r224 not wired on Disc 2) | yes; p51 level unwired | 4,448 / 4,706 | flat | probe dir (not run) |
| Verdugo | r221 | em2c 0x2c (ot_type 5) | **GC source** (no registry json in repo) | prepared only (boss18-verdugo-g70: full 12,346 / g70 9,456, unqualified) | 12,346 + tail | flat | probe dir on the GC data |
| Salazar's monster (+ Salazar, Queen) | r228 | em38 0x38 | **GC source** (r228 json has em25 only) | prepared only (boss18-salazar: 34 TPL images vs 19/23 role cap; alpha order open) | Queen 13,078, tentacles 1,567, roots 3,240 | flat | probe dir on the GC data |
| U-3 | r31b | em32 0x32 | registry u3-em32-00 (ps2-ch5-boss) | yes | 7,920 | flat | probe dir (not run) |
| Krauser (+ arm, gunship em3a) | r31c / r329 | em39 0x39, em3a | Krauser **GC source** (PS2 skeleton differs); em3a registry | Krauser prepared only (boss18-krauser shared atlas fits v1 arena, no runtime) | 8,939 | flat | probe dir on the GC data |
| Saddler | r33x | em31 0x31 | **GC source** (no registry) | prepared only (boss18-saddler: full package over capacity) | 6,976 + tentacle 5,190 + 746 + 112 | flat | probe dir on the GC data |

Census (runs on the A twin = recipe + census diag): r11e, r11f, r10b PS2 registry descriptors, CAST-GC clean, no
`no contiguous` in the windows run. r119: El Gigante did not spawn within 3 chained minutes of bc-r119 (boss-check's
g3 route from r11a is needed); boss-check's 15ed29fe census (gig2b00-g50, PS2) stands.

## Fix: BOSS_LIGHT_DIR26 (commit d448fe41d, default 0, render only)

Extends LEON_LIGHT_DIR26: boss parts (model_bridge re4dc_actor_is_boss: em2b/2c/2f/31/32/35/38/39/3a, em1b/1c type 10)
take the probe direction + ambient (no camera fill) on the fast pass_lights kernel instead of one colour per part.
Needs LEON_LIGHT_DIR26=1. Log `BD26 f= tried= lit=` every 300 frames.
- Knob-off identity: recipe build from this tree = rr rP binary 019b9a79b800f89c.
- Still pair (Flycast, labelled, wall-timed shots so frames differ): still-r11e-t0043/t0055-A-off-B-on.png: El Gigante
  shaded by direction, no artefacts.
- MODELLED ms (scaled from Leon's DIR26 rr delta, ~1.1 ms for ~6.7k verts / 2 dirs; not hwproject): ~0.1 us per vertex
  for one direction: Gigante g50 ~0.3 ms, Del Lago ~0.3, U-3 ~0.8, Verdugo full ~1.8, Saddler ~1.8 while on screen.
- Gate: render only (lighting colour); the logic trace is untouched by design. Not yet in the recipe.
- Open: Mendez declines every part (probe refuses the record); needs a look at its SourceLighting (vertex colour or
  material < 255) before it can be lit.

## Risk list (the three Disc 1 problems)

1. Heap 4 at boss movies: bossmem26 MOVIE_WORLD_ARENA_R119=2 lets any room movie borrow the room's PS2 world package
   when the package is >= 363,360 bytes (movie_world arena). r11f already borrows (11f10, 11f11 seen). Every Disc 2/3
   boss room (r201, r20c, r218, r221, r224, r228, r31b, r31c, r329, r33x) needs its PS2 world package registered at that
   size; check when the world lanes land each room.
2. Death fade: NATIVE_MODEL_REGISTRY_DYING_BOSS=2 covers registry-drawn ids > 0x20 with ot_type 0 only. Gaps: Verdugo
   (ot_type 5) is excluded; Garrador (id 0x1b/0x1c) relies on the base Ganado fade; Verdugo, Salazar, Krauser, Saddler
   are GC-drawn anyway until their packages land.
3. VRAM after the death: SS11_ROOM_DEFER (bossmem26) covers room changes behind chapter-end screens. Chapter ends after
   bosses: Del Lago, Mendez, Salazar (r228), U-3, Krauser, Saddler. Check each with TEXCHK on the after-death door.

Rooms that need bossmem26's general fixes: r228, r221 (plus an ot_type 5 fade), r224, r31b, r31c/r329, r33x; r201/r20c/r218
for movies only.

## Per-boss play-through test plan

Each: route in (door, not warp, for the user's run; warp preset for ours), fight start (boss census line, CAST-GC),
kill (source damage), death movie (no `order: piece short`, MOVIEARENA borrow allowed), exit door (TEXCHK, no `no
contiguous`), BD26 lit > 0 when the switch is on.
- Del Lago r10b: from r10a pier; boat start; kill; s20/s22; r11b save screen; r11b TEXCHK.
- El Gigante r119: from r11a door (g3 fixture); s10 start; parasite s30; kill; s20; exit to r11a/r11b.
- El Gigante r11e: from r11d; Ashley gate; kill; corpse fade PS2 (DYING_BOSS); exit.
- Mendez r11f: s00 QTE; two forms; s02/s10/s11; window jump; r10f door.
- Garrador r201 / r20c / r218: bell; kill from behind; exit door.
- Verdugo r221: freeze; grab (GRAB_FULL); kill or escape lift; death fade (ot_type 5 gap).
- Twins r224: both deaths; door.
- Salazar r228: eye hits; tentacles; death movie; chapter-end save; next room TEXCHK.
- U-3 r31b: container sequence; kill; movie; exit.
- Krauser r31c / r329: knife fight QTEs; arm form; death movie; exit.
- Saddler r33x: eye hits, crane; death movie; ending.

## Gaps to give owners (data conversion, not done here)

Verdugo, Salazar's monster, Krauser and Saddler still draw GameCube data (GC-ASSET). Codex boss18 prepared PS2 casts
for all four, each with an open qualification (above). Integrating them is a registry data job per room; it should land
with the world lane that builds each room.
