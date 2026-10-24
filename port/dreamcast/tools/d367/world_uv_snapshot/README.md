# World UV snapshot qualification

Qualifies `SCENERY_UV_SNAPSHOT` on integration base
`28da09802ed9ff6756529bab02978230983453be`. The runtime option is default 0 and
requires `SCENERY_CHUNK`. These tools reuse the qualified helpers already present
in `world_setup_spike`, `world_submit_spike` and `world_replay_lean`; they do not
change those helpers or import another runtime base.

See [the report](../../../docs/D367_WORLD_UV_SNAPSHOT_20261023.md) for results,
limits and complete reproduction commands. The companion JSON records source,
object and receipt hashes and the detailed compiled/model costs.

| Tool | Gate |
|---|---|
| `build_controls.py` | Real Make-derived public Test22 recipes; complete SH4 `native_static` and `native_ui` absent/zero/on builds for all eight SELECT_ONLY/SUBMIT_BATCH/REPLAY_LEAN combinations. Exact `.ii`/`.o` comparisons against independently read base sources. |
| `verify_knobs.py` | Actual Make dry runs, defaults, all four switches, invalid values, CHUNK dependency and owner-macro independence. |
| `check_geometry.py` | Actual production material/emitter/portable geometry and documented C SQ-walk adapter. Every TA/state word compared for static offsets and against immediate per-owner replay for dynamic offsets; the old queued path is a negative control. |
| `check_admission.py` | Actual two admission branches and flush body with controlled geometry edges; capacity drains, fallbacks, early/late aborts, valid PVS variants, dynamic-owner reset and special UV bit patterns. |
| `target_build.py` | Real SH4 setup bodies/layout with an observed geometry edge; eight R/B/UV arms using the same Make-derived settings. |
| `target_run.py` | Qualified SH4 interpreter, warm/cold-I pipeline model, actual load/store and line-touch accounting, and exact target special-word checks. |

Every output directory must be new. Host controls require Python 3 and a C++20
compiler. Target controls additionally require SH GCC, KOS source and public SDK
headers; the cost model uses a host C compiler. All meshes are synthetic. No game
assets, game frame, console timing or disc image are produced.

The model uses perfect D-cache. Byte counts are architectural accesses; line
touches are address observations, not cache misses. Timing covers replay setup;
admission snapshot payload and its unpriced cycles are reported separately.
