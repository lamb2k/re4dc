# Linked parts must retire the contiguous indexing promise

An original chapter 3-1 native save/door continuation in r202 stopped at game
frame11598 during normal movement. The preserved pre-watchdog SH4 context points
to AtSphereCapsuleCk (0x8c088298), called by emSphereAtCk (0x8c0af854).
Its capsule endpoints/radius are NaN; conversion produces0x80000000 iterations.
The subsequent main.cpp:548 HALT is the unchanged no-frame watchdog.

The source actor is em11 type7, ESL2C. Its root matrix is finite, but its37-part
pList chain has34 parts outside the arithmetic range while be_flag0x2000 still
promises contiguous storage. Hit part15 therefore indexes unrelated data.
Six matrices in the real linked chain are already nonfinite, consistent with
earlier source joint initialization/indexing also following that false promise.

makePartsList sets0x2000 after a contiguous allocation, but source release does
not clear it. A later individual-allocation fallback must clear the old promise
before constructing the list. PARTS_LINKED_FLAG=1 makes that one change; default0.
The successful contiguous path, source parts count/topology, collision algorithm,
HP, events, renderer and model data are unchanged. It is not a NaN bypass.

The host test extracts the actual allocation and lookup functions. It reproduces
old stale-flag indexing, verifies linked lookup with the fix, and checks later
contiguous reuse plus existing partial-allocation failure cleanup.
CH4 now selects the knob after fresh executable gates. Candidate c18oemW
(ELF0efeb8dc03901b648bb865f7c6482e70b82d37388965464a6307eb4d2b115eac,
_end8c46af18) adds32 bytes. A literal T15 off build retains the exact boot and
ten overlays of the frozen current343 control. Busy-r101 with48KiB held passes
CAST/NOT-DRAWN/TEX/residency and retains5000B KOS free (>4096B floor).

The fresh original chapter3-1 VMU route (nativeK, never a retargeted snapshot)
passes the original r200 door and r202 gate. A later actual source ESL21
allocation has37 linked parts,26 noncontiguous, be_flag0x2010077 (0x2000 clear),
and all37 matrices finite. Normal movement crosses the former tunnel failure;
no collision/NaN bypass is added. These are source-contract gates, not a full
chapter/route claim. Native follower/crank/cannon/doors remain open.

Private evidence under the Castle18 evidence root:
r202-native-tunnel-freeze-snapshot-registers-v2-20261019.json,
r202-native-tunnel-freeze-collision-inputs-20261019.json,
r202-native-freeze-stale-sequential-proof-20261019.json.
The first serialization attempt used the wrong enum width and is superseded by
v2. Each snapshot RAM location is independently anchored to two exact ELF code
signatures. Decoding never modifies game/process/snapshot bytes.
