# Frozen QA farm and weapon controls, 2026-10-20

These later checks do not hold the already qualified original R100 motion fix. Code/image stay at4aca1f83/1be6ec3a; no successor weapon, HUD, movie, region or hand repair is included. See MOTION-PACK-TARGET-20261020.md for the sealed original ambush comparison and its timing limits.

## Farm worker and ordinary hit

Original r103 QA entry is an explicit warp fixture, not a normal r100-to-farm route. It retains the original actors and events without the separate farm-fight kill substitution. Exact selected staged SAT collision data is read offline to suggest normal walking waypoints; the game decides actual collision and actions.

The cowbarn06 t20 framebuffer positively shows Leon inside the wooden barn. Original Suki8 work, alert and attack run without firing. Source5200 to5858:23 to25 motion loads, zero evictions. Original damage changes Leon1200 to820; a verified owned-PID/creation-time request makes the normal harness save and close at26.4 seconds/errors empty. Worker100/102 remain in their original reserved slabs; attack97 is a guarded heap allocation. This is location and functional evidence, not a blanket read-quiet or console clearance claim.

The same-program bodyhit07 checkpoint then receives ordinary handgun aim/fire. The actual worker HP1200 to1050 transition at6055 is followed for20 reaction ticks. Added entry20 (ARC33,15584B) is DmSmall and93 (ARC157,9376B) is Back, rather than an assumed entry14. Loads25 to27 and one eviction; worker100/102 persist,20 spills to heap and93 packs after102 at offset21152. SDK heap4 has1341568 free bytes, so this is a high-free fixture, not proof of a low-heap two-bin capacity failure. Source6085/Leon820; normal save/close10.5 seconds/errors empty. Receipt: MOTION-PACK-R103-QUALIFICATION.json.

## Weapon controls and next shared read defect

Weapon-control01 forks this frozen program's safe pre-s03 state; no actor or gameplay data is written. Thirteen ordinary quick-select requests produce11 actual distinct switches. The initial current-handgun no-op makes no reads. One early handgun-return request remains shotgun and has no slot-post log: it is gated input, not cache reuse.

Warmed distinct returns still read: handgun55 low-level calls/478880B with zero hand reads; shotgun61/521984B; rifle61/638048B; TMP61/528320B. Warm texture-load deltas are zero. TMP-to-handgun alternation repeatedly misses hand blobs7 and1, with worker reads; those cells are a separate source follow-up. Existing same-archive reuse code does not retain all distinct weapon files.

The largest repeated pass follows the weapon task: after a warm handgun task89101us, the same room texture preloader reports picked0/loads0 but722193us. It scans all 169 pieces of 512 bytes of dc/resident.bin again; re4dc_ui_bind_weapon sets the global preload_pending flag. Native HUD reports13.3FPS/47% source speed. This is Flycast evidence, not hardware timing. Drive totals include this post-task settle window and must not be called weapon-load-only duration. A bounded current-room copied-list cache is assigned separately; new-owner texture admission must still run.

Private receipts: WEAPON-CONTROL-BASELINE.json and WEAPON-HAND-CELLS.json. No same-file type/upgrade reinitialization case exists in this small kit, and no inventory-equipping gate is claimed. The hand package hash is d752aac59ae99256b767da74ab8fefc98d896e37d29e42b188dfa8a6ab16697f. All states, raw logs, frames and source-SAT data remain private.

## Read-only observer utilities

elf_scope_symbols.py exports ELF32 little-endian object symbols with STT_FILE scope. rebind_qa_observer.py relocates the exact QA observer literals from old scoped metadata to a new ELF, checks observed object sizes and the known hand-counter block, and injects an exact-ELF run receipt check. It must be used with the matching archived original metadata; it is not permission to reuse a binary save state across programs. Packed reserved ownership uses pointer ranges rather than base equality.
