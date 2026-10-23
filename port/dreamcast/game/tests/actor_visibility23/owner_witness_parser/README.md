# Strict owner-witness log parser

Reads the exact private schema from schema `actor-owner-witness23-material-r1`, runtime commit `f1a6807c7324260c664fa1ca3d33d4b60a62712a` (parent18a9), with exact embedded formatter/header hashes. This is support for a future witnessed programme. The current frozen bea2 programme has no owner witness and cannot pass this format gate.

```
python3 -B parse_owner_witness.py captured.log
python3 -B parse_owner_witness.py captured.log --binding caller-assertions.json
python3 -B test_parser.py
```

Exit0 means the format is complete and consistent; exit2 rejects it. JSON always has `qualified:false` and requires a separately verified runtime receipt downstream. Even a complete synthetic control never certifies a programme, reader closure, real owner cut, visual result or performance.

Optional binding JSON has `source` (caller-asserted actual40-hex runtime source), `source_parent` (exact18a9), `format_source_sha256` (exact embedded runtime formatter), `log_sha256`, `programme_sha256`, `reader_complete:true`, and `log_overflow:false`. These are labelled caller assertions. Their syntax/matching hashes are checked; their truth is not independently proved. No binding or asserted closure becomes runtime evidence here.

Admission requires one start/completion pair, all600 ordered AV23/AV23WORK pairs, complete owner summary (`fail=0`, binds600), and both body/head role rows. Expected slots derive from each role's counters: even slot2*role when bound>potential, odd slot2*role+1 when potential>0. Every expected slot must have all nine distinct rows: SAMPLE, SOURCE, ADDR, BOX, VIEW, WORLD, RECEIPT, COVER, RANGE. Raw BOX/VIEW/RANGE values must contain exactly6/25/4 32-bit words. Native message length stays below256B. Missing, duplicate, truncated, reordered, unknown or unexpected rows, loss markers, overflow sentinels, refused potential receipts and inconsistent identities/counters are rejected. Logs are bounded to64MiB; no unbounded output or framework is introduced.

Potential and actual are separate reported observations: `reported_owner2b_potential_sections` includes positively attributed source queries in modes1/2. `reported_owner2b_pre_position_skips` requires mode2, paired committed samples and matching skip/position/triangle counters. Aggregate AV23 rows supply window closure and counter ceilings only; they never attribute any work to owner2b. A refused/nonpotential draw can be retained as a draw sample and never supplies a positive cut. Actual selected field/receipt/address/FPSCR/frame/scene, lifetime, posed bounds, LOD/section and both caller paths are checked from the owner records. The parser does not recompute visibility or accept a witness for destroyed cover.

The exact ready contract permits `current_far <= retained_far`, with equal near; requiring equal far would reject valid retained full-distance receipts. Fixed expected masks/addresses are not guessed from aggregate counters. Formatter and State header source hashes are embedded; the host control checks the actual frozen formatter when available.

Tests generate synthetic complete records in memory, then mutate malformed controls; no private log/assets or guest evidence are included. No target compilation, guest, build, resource census or sealed-unit changes are performed by this unit.

The two existing PART records now require refused/refuse count/hex fields. This successor rejects the old18a9 PART schema; its sealed parser is untouched. Refusal counts cannot exceed query-bound; counts and nonzero known masks must agree. Unsafe provenance reason bits64..1024 are not attributed. All-refused windows report zero potential/actual cuts and remain unqualified. No source self-hash cycle is introduced: the format is pinned by exact formatter/header SHA256; actual programme source and closure require downstream verification.
