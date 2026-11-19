# Lane eng-shell-map (M2 groundwork), 2026-11-19

Claude Opus lane, PC-only analysis. Deliverable: [../SHELL_MAP.md](../SHELL_MAP.md).
Scripts and outputs: `E:\RE4DC-Lanes\eng-shell-map\s\` (`s/out/`). Gate: `gate_doc.py` (54 numbers, 0 mismatches; control caught).

## Done
- Budget rows from the 11-12 console samples (slot 157), five rows, four benchmark scenes plus barn inside; rules and
  function lists; logic-thread samples match the game's logic timer to 0.1 ms (three scenes) and 0.8 ms (hay-fork).
- Boundary inventory: call sites, distinct callees and shim status per service; RE4DC patch counts.
- The frame today and the engine loop that hosts behaviour unchanged.
- Memory map today (code, Flycast boot log, console counters), coupling to image size, allocation-dependent decisions;
  proposed RAM and VRAM maps (estimates).
- Services ranked by console cost across rows, interface, data, tangle.
- E1 link closure from the lab33 ELF (code and data-table edges): 22 files, 103,856 B code, 175 engine interface entries.
- Equivalence checks for skeleton, collision, effects; host-build precedent (`tools/motion/host`).

## Numbers (ms a picture, console)
| Scene | Behaviour | Services | Publication | Drawing | System |
|---|---:|---:|---:|---:|---:|
| Cross | 1.6 | 15.5 | 16.3 | 17.8 | 3.9 |
| Bell fight | 1.6 | 17.9 | 17.5 | 19.7 | 4.3 |
| Hay-fork view | 1.5 | 26.3 | 31.4 | 30.6 | 5.6 |
| Quiet farm | 0.7 | 13.0 | 8.7 | 9.0 | 2.9 |

## Left
- Fight heap census by tag (`HEAP_CENSUS=1`) to size the behaviour arena.
- Per-row worst interval (needs a denser sampler or a phase timer per row).
- VRAM map document; engine-build sizes (closure sizes are lab33's).
