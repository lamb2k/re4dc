# eng-bench M1 handback, 2026-11-19

**Blocked at step 2.** Each Flycast capture must contain 300 contiguous, complete pictures. The two capture designs below failed that check. Handing back under the binding lane rule for a failing gate. The console is not needed to reproduce this blocker.

| Scene | Complete pictures in final run | Phase ms | Mean ms | p99 ms | Worst ms | Over-budget count / 600 | Tier |
|---|---:|---|---|---|---|---|---|
| r101 cross | 1 / 300 | unmeasured | — | — | — | — | Flycast capture only |
| r103 hayfork | 0 / 300 | unmeasured | — | — | — | — | Flycast capture only |

## Capture evidence

Both runs booted the fixture from the lab32 disc, using r101x for cross and p103h for hayfork. Render timing from these instrumented game images is ineligible for the M1 budget.

| Design | Cross | Hayfork |
|---|---|---|
| One 64 KiB slot, sequence-checked read | Saved picture 1. Next stable picture was 5. | Overflow flag at picture 1, after 62,452 payload bytes. |
| Byte-identical palette and light back-references, 80 ms guest hold after presentation submission | Saved picture 1. Next stable picture was 15. The host attempted a synchronous VRAM snapshot in this run. | Overflow flag at picture 1, after 63,956 payload bytes. |

The final cross record is 28,140 payload bytes at game frame 466. It has one camera, 89 world batches with pick lists, 16 actor-part records, 18 sprite records and 20 HUD quads. The checker accepted its structure and rejected the one-picture directory. Neither run produced an accepted still pair. Host polling, snapshot latency and disk latency have not been isolated from one another.

- Evidence root is `E:\RE4DC-Lanes\eng-bench`. Outcome logs are `runs\eng-bench-{cross,hayfork}-{1,3b}-reader.log`. Each matching run directory has its fixture, game log and emulator log. Final cross sample is `runs\eng-bench-cross-3b\picture-001.bin`.
- The intermediate `*-2` diagnostic caught a warmup-counter error. The corrected build ran in `*-3b`. The `*-3` launch attempts ended before boot while the host image was being copied.
- Capture code commit is `cf5da3247f547dc53428b9a0889139f8839ca11b`. Final capture game ELF SHA-256 is `d080ab6f0ec858f72384cd3b36ce3f401f0a635359b9e40342ea48b78bb558d0`. Its private Flycast track SHA-256 is `40c0ee9368393eade17992949649de65ce59117c57d061e56f6b4a7dce8d9faf` in `base3\track03.sha256`. **Bench image hash unavailable.**
- SH4ZAM changed from `33fa485` to `cff97e81c57d4b6ac5a9299d31a24130f0d44804` in `a808450f3`. Compatibility build linked with `GAME_SH4ZAM=1`, zero missing symbols, ELF SHA-256 `3c51be95bafbea636d85f4e4d89eda1550e23f6bbce5d65d1762330352973992`. No kernel changed in this lane and no SH4ZAM speed benchmark ran.
- Step 2 still needs lossless transport, stable pack identities for the captured resources, coverage checks for selected world levels and drawn parts, and picture-matched stills. If resumed, a transport that publishes smaller chunks independently of frame size would address the observed hayfork limit. The host can buffer those chunks before disk or screenshot processing.
- Steps 3–6 remain open, including the private bake, renderer, KOS bench, both 600-picture replays, timing controls, hardware model and GDEMU staging. No M1 budget result, renderer stop-line result or console request.
