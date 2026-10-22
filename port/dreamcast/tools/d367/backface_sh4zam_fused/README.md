# Patched SH4ZAM fused strip submission

The complete outcode, exact facing, run/parity selection and SQ emitter live
inside the checked-in patch against clean SDK pin33fa4850. RE4 contains thin
material/model/clip adapters. CPU0/C1 add no SDK object or include path.

The implementation now includes:

- Short strips<=64 indices: six raw-ABC/parity phases, next-index/outcode/XY
  work interleaved with the current exact FMAC determinant, and a64-bit mask.
- Original run starts are derived before odd-parity repair. Contiguous kept
  spans use a peeled lean SQ emitter; all-front skips mask/span traversal.
- World count streams and actor bit7-EOL streams share one public register/
  FPSCR lease across their entire batch. Long strips retain the qualified
  SDK assembly, with no C facing fallback.
- A first-outcode conservative gate avoids facing work for common rejected
  strips. Oversize first-depth0 strips stop immediately; other possible
  all-depth cases retain depth rejection before limit/clip ordering.

The public API takes projected32-byte PVR cache entries. It saves **zero
transformation or skinning work**. Cull-none, alpha-mask and no-depth-write
policy stays in RE4. No hidden-house, fog-view, PVS or view-distance benefit is
claimed. Exact target arithmetic remains four rounded subtractions, rounded
second product, FNEG and FMAC. `check_area.py` binds both rotating and pipelined
arithmetic to the real compiler-selected SDK DAG checked by `generate.py`.

`materialize.py` verifies clean SDK pin, patch and produced source identities,
then creates or verifies an owned overlay. It never edits the vendor gitlink,
fetches a private commit or contacts upstream. Patch updates require a fresh
OBJDIR/overlay. CPU2 Make rules compile the actual patched SDK sources.
`repack.py --source <owned-sdk-source>` reproducibly updates the local patch.

Run `bash qualify.sh /absolute/new/output`. Small compiles acquire shared slot2
and the tree lease, then release both before opcode interpretation. Output must
not exist. `materialize_test.py` verifies reproducibility and rejection of
source/patch/pin drift. No guest or game assets are generated.

Frozen compile09 passed4,220 kernel comparisons plus32 mode controls and740
complete SDK world-caller comparisons plus32 controls. These cover exact vertex
words, terminal flags, winding, full SQ bursts, NaN/cancellation, short/long/EOL
streams, all/any/limit ordering, exact clip-stop pointers, counters, callee
registers, exact FPSCR and all opposite-bank words under adversarial tracing.
New caller controls count actual floating-point instructions: conservative
rejects perform zero area work; first0 interior depth crossings explicitly pay
all62 facing tests. Expanded mask/six-phase controls are being sealed separately.
Internal SH section relocations are checked against the real target linker's
result, rather than assuming raw object literals are executable addresses.

Independent caller-inclusive MODELLED64-index first0 costs are2,421 cycles
front,1,611 back,2,637 mixed; OFF is1,141. Batch32 costs per strip are2,309.59,
1,499.59,2,525.59 versus fair OFF1,109.03. First4-but-eligible and first0 interior
depth-crossing cases are separate cost rows. This improves the first fused
candidate but still **fails the OFF submission gate**. Transform cost is common
and unchanged; cache/bus/PVR timing and scene distributions are uncalibrated.

No full programme OFF identity, Flycast pixels, memory gate, console timing or
QA disc is claimed here. Root owns integration/runtime and packaging gates.
