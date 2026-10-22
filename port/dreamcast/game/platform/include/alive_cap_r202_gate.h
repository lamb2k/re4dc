#pragma once

// The source r202 gate event uses catapult 2's rock without a null check. Its
// operator is ESL 2E; the old four slots are patrols 2C/32, gate 2A and operator21,
// so 2E is held and never loads that rock. Swap only the initial-list iteration
// positions of21/2E: gate2A and operator2E fit beside both original patrols.
// All256 entries still run the original eligibility/death/cap checks exactly once.
// No created actor is parked, no held entry is deleted, no event is bypassed.
namespace re4dc_r202_gate {
inline unsigned entry(unsigned room, unsigned order) {
    if (room != 0x202u) return order;
    if (order == 0x21u) return 0x2Eu;
    if (order == 0x2Eu) return 0x21u;
    return order;
}
}
