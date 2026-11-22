# Lane eng-svcspd1: the services row on the calibrated tier, and the first speed fixes

Status: **finished, unaudited.** Branch `lane/eng-svcspd1`. Every timing is **MODELLED (console-build dynarec at
70 MHz, calibrated on the old port)**, slots `fly1` / `fly2`, `Dynarec.Enabled = yes`, `Sh4Clock = 70`. Write-up, account,
cost per unit, per-fix savings and what is left: [../SERVICES_COST_20261121.md](../SERVICES_COST_20261121.md).

## Items
1. **The account**: finished. Lab arm `SVCPROF` (phase times per tick, exclusive; control `SVCPROFCTL`: a 200 us wait
   a tick in the palette phase read +200 us: hill palette 0.62 -> 0.82 ms, row 16.14 -> 16.35, run total +199.6 us a
   tick; runs `finp-d70`, `finc-d70`), counters `E1 SKEL2`, `E1 CLOTH`, `E1 COL2`.
2. **Cost per unit against the code**: finished (the tier charges about one cycle an instruction; every unit costs what
   its code path executes; the waste is in what the code does).
3. **Fixes**: five landed (trig cache, cloth early out, IK-only first pass, world pass inline, no identity hash without
   a pack); 2b and 2c tried and taken back (slower); a deferred last world pass tried, not landed (no gain).
4. **What is left**: in the write-up, section 5.

## Checks and controls (all in the repository)
- PC reference, merged head before 2c: `svc_controls.sh` 79 rows, `camcheck.sh`, `refctl.sh`, `controls.sh` 18,
  `outcome_controls.py` 35, `aim_check.sh`: every row as it must.
- `services/skeleton/speed_controls.sh`: each fix's control (trigstale, clothbound, ikclosure, worldfast, mkstale) FAILs
  the svc comparison as it must; the fixes' plain and no-pack rows PASS.
- Engine against itself (lane script `s\selfcmp.sh`, base cbececd7c): 5 fixtures, wind on and off, every bone and query
  bit-identical, traces byte-identical.
- Flycast (plain, function): LEONT, HILLT, SHOT, LEONS, HILLS, FIGHTS 6 of 6 OK; hill_engine and camengine every row as
  it must; stills 59 pairs against eng-e1p A2, 0 moved (eng-e1j's thresholds); shot_engine on SHOT + its three control
  scenes (disc fins).
- Link check: default 384 allowed, SERVICE 0, PASS; FIGHT=1 and BOSS=1 unchanged by this lane (their SERVICE counts are
  the fight and boss lanes').

## Requests for other lanes
- Loader / disc owner: link a motion key pack on the console (`svc_mk_pack`): every pose sample is decoded from keys
  today (hill 0.60 ms, fight 0.89, boss 1.03 a picture).
- Loader owner: bind an archive's clips at load (the comment in skel.cpp says it happens; nothing calls it).
- Integrator / eng-e2b / eng-e2c: the skeleton and cloth entries request is handed back (lane STATUS.md: where they
  should live; the cloth set-up entry exists, the fight and boss images do not link the cloth service).
