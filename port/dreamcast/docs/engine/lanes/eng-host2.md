# Lane eng-host2 (E1 Ashley and E2 Ganado support, PC-only), 2026-11-19

**Goal:** extend the plays-right reference (re4ref) to Ashley as the partner and one Ganado (em10), with
per-actor trace lines, agreement against existing old-game traces, and a failing control per actor.
Full write-up: [../PLAYS_RIGHT.md](../PLAYS_RIGHT.md), section "Actors".

## Result

- **Closures** (eng-shell-map method, variant B, on top of E1): Ashley 2 files, 37,418 B of SH-4 code,
  38 new interface symbols; Ganado 9 files, 292,562 B, 191 new. Map: `hostref/closure-map-actors.tsv`.
- **Builds:** `make -j4` (and `make fma`) in `port/dreamcast/engine/hostref`, every `RE4DC_` knob off,
  sources unedited (build-time renames of the module entries and one objcopy symbol rename).
- **Trace v2:** A lines per actor (position, angles, motion, routine, life, flags, discrete hash, the
  actor's own generator calls), R lines (generator calls per caller). T lines unchanged: door103-walk
  still reproduces eng-host's evidence on every physical field.
- **Agreement (Flycast tier, position every 4th tick, the only enemy fields old traces record):**
  - Ganado 0x14 (walking, bell gate): t=185 to 317, 33 samples, 13 bit-identical, 0.002 units at most;
    first divergence t=319, the room's event freezing the old Ganados (not hosted).
  - Ashley (r11d): t=185 to 289, 26 samples within 0.018 units; first divergence t=291, scripted
    movement inside the room's opening event (not hosted).
- **Controls:** one dropped Ganado generator call (tick 7), a one-tick late hit (tick 60) and Ashley 10%
  further from Leon (tick 51) all fail; every determinism check passes; Leon's four controls unchanged.

## Numbers (tiers)

| What | Value | Tier |
|---|---|---|
| Ganado 0x14 position against the old game, 33 samples | 0.002 units at most, 13 bit-identical | Flycast (old) against PC |
| Same without the generator feed | diverges at the second sample (t=191, 1.6 units) | same |
| Ashley position, 26 samples | 0.018 units at most | same |
| Reference against itself, every actor field | bit-identical (bell-ganado, bell-ganado-hit, square-follow) | PC |

## Evidence

`E:\RE4DC-Lanes\eng-host2\ev`: `closure\` (closure2.md, iface and file lists, partner object graph),
`run\` (traces, logs), `agreement\` (JSON and text per actor, summary, old-trace hashes), `controls\`
(controls.md, traces, JSON), `hashes.txt` (re4ref, data files). Scripts: `E:\RE4DC-Lanes\eng-host2\s`.

## Not done

- No old trace records an enemy's angles, motion, routine or life: those fields compare reference against
  reference only. The LE fixtures that would record them are specified in PLAYS_RIGHT.md (emulator runs).
- Ashley carried and released, hiding, and the farm (em12) Ganado: built and in the closure, no fixture.
- Weapons, carts, room controllers, doors, ladders and room events are stubs.
