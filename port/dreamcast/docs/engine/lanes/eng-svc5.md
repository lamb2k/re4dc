# Lane eng-svc5: the strict plays-right reader and the remaining native services (E1 audit section 1)

**Status: finished, unaudited** (item 4 finished by lane eng-e1g). Hand-back: `E:\RE4DC-Lanes\eng-svc5\HANDBACK.md`. PC-only (re4ref); no timing, no
emulator, no console. Write-up: `PLAYS_RIGHT.md` "Outcome reader"; `SERVICES.md` sections 32 to 38.

| Brief item | Result |
|---|---|
| 1. Strict plays-right reader | `tools/plays_right/outcome.py` (by outcome, fails closed), `outcome_controls.py` 30 rows as they must; `plays_right.py` strict by default, `controls.sh` 18 rows as they must (its stale drop-rng control fixed) |
| 2. Math helpers (math_sub, sub2) | native, `services/math/math_svc.cpp` on SH4ZAM vector arithmetic; mathtest bit-identical; 0 original functions kept |
| 3. Garment pose (pl_cloth) | native, `services/cloth/garment.cpp`; garmenttest identical; 0 kept |
| 4. SDK math, allocator, fdlibm | written here, built and proven by lane eng-e1g after the stall: sdktest and alloctest bit-identical, the float library judged by outcome (SERVICES.md 35-37); linked into the image by eng-e1g (section 38) |
| 5. objWep laser, manager templates | decided: drawLaserSight is decision code (proposed allowed); drawPoint / Draw_line3d_* and the cEm / cLight manager templates are service code, **remaining** (design in the hand-back) |
| 6. Documents | PLAYS_RIGHT.md, SERVICES.md 32-38, this note |

SH4ZAM: one fix on the submodule's local branch `re4dc/eng-svc5` (6d7d1e4: three-term `shz_dot6f` / `shz_mag_sqr3f` on
the SH-4 back-end without FIPR; no zero fourth term, so one FADD fewer and -0 sums kept); not pushed, the gitlink not
changed (an upstream pull request needs the owner's OK). Noted, not changed: SH4ZAM's `shz_sqrtf` is FSQRT (exact) on
the SH-4 back-end but x * (1 / sqrt(x)) on the SW back-end, so it cannot serve a PC proof; the services use the exact
root directly.

Finding outside the brief: on the new fixtures bell-ganado-kill / -clear the dying Ganado's skinning palette differs
between the reference and the native build from tick 241 / 204, with or without round 5 (bones, queries and traces
agree): a round 1-4 skeleton matter, for the integrator.
