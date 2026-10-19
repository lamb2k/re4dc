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
A fresh program/native route gate is still required; no old snapshot may be
retargeted to a changed executable. CH4 recipe does not yet select this knob.

Private evidence under the Castle18 evidence root:
r202-native-tunnel-freeze-snapshot-registers-v2-20261019.json,
r202-native-tunnel-freeze-collision-inputs-20261019.json,
r202-native-freeze-stale-sequential-proof-20261019.json.
The first serialization attempt used the wrong enum width and is superseded by
v2. Each snapshot RAM location is independently anchored to two exact ELF code
signatures. Decoding never modifies game/process/snapshot bytes.
