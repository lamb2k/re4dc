# Patched SH4ZAM fused strip submission

Follow-up: [EARLY-CLIP.md](EARLY-CLIP.md) documents the default-off
`BACKFACE_EARLY_CLIP=1` optimization, exact object controls, executed-instruction
benchmarks, and remaining scene/console gates. The modeled CPU2-versus-OFF
numbers below are the original candidate's evidence, not new measurements.

The complete outcode, exact-facing, run/parity selection and SQ emitter live
inside a reproducible patch against clean SDK pin33fa4850. RE4 contains thin
material/model/clip adapters. CPU0/C1 add no SDK object or include path.

The implemented SDK path has:

- Short strips<=64 indices: six raw-ABC/parity phases,64-bit facing masks and
  next-index/outcode/XY work interleaved with the exact current determinant.
- Four next-triangle FP seeds carried through compare/carry/branch slots.
  World/plain streams process six-triangle blocks without per-triangle end
  checks or phase branches; bounded tails and actor EOL streams stay safe.
- Original run starts derived before parity repair. Contiguous kept spans use
  peeled lean SQ bursts; all-front bypasses mask/span traversal.
- One public register/FPSCR lease across a world count stream or actor bit7-EOL
  stream. Long strips retain qualified SDK assembly; no C facing fallback.
- Conservative first-outcode gates for common rejects; oversized first-depth0
  strips stop immediately. Possible all-depth cases preserve rejection before
  limit/clip ordering. Interior first0 depth crossings still pay facing work.

This API consumes projected32-byte PVR cache entries and saves **zero transform
or skinning work**. No hidden-house, fog-view, PVS or view-distance benefit is
claimed. Excluded materials remain RE4 policy. The target determinant keeps
four rounded subtractions, rounded second product, FNEG and FMAC. The compiler
SDK DAG check also verifies carry seeds and that raw A survives its last use.

The retained candidate12 object passes29,572 actual-opcode comparisons plus64
FR/SZ/PR/DN/callee/opposite-bank controls. These include24,252 expanded mask/
six-phase/short-long-EOL comparisons,740 complete caller/gate comparisons and
360 controls proving no SQ store at all before rejection/clipping. Vertex words,
terminal flags, winding, full bursts, NaN/cancellation, clip-stop/counters and
adversarial tracing match the unchanged target-lowered C oracle. Internal SH
section relocations match the actual target linker. Patch materialization is
repeatable and fails closed on source/patch/pin drift. No game data is used.

Independent caller-inclusive MODELLED64-index world costs:

| Pattern | One strip | Batch32 per strip | OFF batch32 per strip |
|---|---:|---:|---:|
| All front | 2126 | 2014.59 | 1109.03 |
| All back | 1316 | 1204.59 | 1109.03 |
| Mixed retained replay | 2342 | 2230.59 | 1109.03 |

These are cycles, with trace disabled. A first4-but-eligible strip adds451
cycles; first0 interior depth crossings cost1244 per64-index input. Depth-all/
screen-all rejects cost629/641; oversized first0 clip costs140. The hot full
block models15 cycles/triangle, but the complete caller still **fails OFF**.
Text is8160 bytes (candidate10:6976); layout/conflict/cache/bus/PVR costs are
uncalibrated. Scene weights and common transform cost are not credited as gains.

Full actor OFF caller binding and Leon/Ganado/El Gigante scene distributions
remain missing. Old12/13-cycle actor copy-body figures are not complete actor
costs and must not be presented as such. Actor correctness is covered here;
actor scene performance acceptance is not.

`materialize.py` verifies clean SDK pin, patch and produced identities, then
creates/verifies an owned overlay. It never edits the vendor gitlink or contacts
upstream. Patch changes need a fresh OBJDIR. CPU2 compiles those actual patched
SDK sources. `repack.py --source <owned-sdk-source>` regenerates the patch.

Run `bash qualify.sh /absolute/new/output`. Compiles use shared slot2 plus the
tree lease, then release both before host opcode tests. Output must be new.
`materialize_test.py` checks repeatability and source/patch/pin rejection.

Full programme OFF identity, Flycast pixels, memory gates, console timing and
QA disc remain parent-owned and unrun here. This is a tested implementation
with a failed performance gate, ready for architecture review and calibration.
