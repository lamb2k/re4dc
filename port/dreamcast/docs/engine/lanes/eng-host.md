# Lane eng-host (E1 support, PC-only), 2026-11-19

**Goal:** a PC build of Leon's original player and camera code that replays recorded inputs and writes a
per-tick trace, and the plays-right comparison tool with tolerances and failing controls.
Full write-up: [../PLAYS_RIGHT.md](../PLAYS_RIGHT.md).

## Result

- **Builds:** `port/dreamcast/engine/hostref` (`make -j4`) gives `re4ref`, an i386 Linux program: the
  20 closure files, the original skeleton, collision, math, pad and held-weapon code, every `RE4DC_` knob
  off, logging stubs for the rest. Every row of the E1 interface is accounted for in `closure-map.tsv`.
- **Compares:** `port/dreamcast/tools/plays_right/plays_right.py A B --tolerances tolerances.json` reads
  re4ref traces and the old game's logic traces; first divergence, per-field summary, float-step counts.
- **Controls:** walk-speed +2% fails at tick 285 (position), one dropped generator call at tick 5,
  a one-tick input shift at tick 283; two runs of the reference are bit-identical (`controls.sh`).
- **Agreement with the old game (Flycast tier):** door103 (village square, the walk to the farm door),
  t=829 to 1151, 323 ticks within tolerance, 272 bit-identical, walk and wall slide included; first
  divergence t=1152 when A opens the door (door and room change not hosted).

## Numbers (tiers)

| What | Value | Tier |
|---|---|---|
| Position, largest difference from the old game, 323 ticks | 0.0115 units (height only, ticks 1 to 51, the resume's start-up) | Flycast (old) against PC (reference) |
| Ticks bit-identical in every compared field | 272 of 323 | same |
| Fused multiply-add variant | 68 of 323 bit-identical, 50 float steps at most | same |
| Reference against itself | 349 of 349 ticks bit-identical | PC |

## Evidence

`E:\RE4DC-Lanes\eng-host\ev`: `run\` traces and logs, `agreement-door103-*.json/txt`, `controls\`
(traces, `controls.md`, per-control JSON), `closure-map.tsv`, `hashes.txt` (binaries, data files, old trace).

## Not done

- Only one walking fixture; running, turning, aiming and shooting need old-game logic-trace runs first.
- No camera agreement with the old game (its trace has the camera as a hash only).
- No console (SH-4 hardware) float measurement; Flycast only.
