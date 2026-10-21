# Packed member retry candidate

The current native UI loader spaces pack header/index failures, but not a found member's open, descriptor or texture-upload read failure. It evicts its selected cache entry before opening that member. Actual loader control-flow characterization with mocked Package/PVR and a successful ordinary cache refill between demands produced 20 opens and 20 evictions over 20 UI frames. This is a source test, not measured game traffic or timing.

`TEX_PAYLOAD_RETRY=1` is default off and requires `TEX_PACK=1 TEX_RESIDENT=1`. The candidate throttles only a validated exact packed member that actually failed for one of twelve explicit Package source I/O/validation error strings. It does not add a missing key, affect resident hits or loose paths, change owner/render fences, or throttle allocator/palette/VRAM refusals.

Two 8192-bit maps cover the existing maximum validated pack count with no replacement or global overflow gate. A failure sets its bit in both the current and following 30-frame epoch. Retries become eligible 31 to 60 UI frames later, remain periodic, and clear on success. Frame arithmetic is unsigned and supports natural wrap. Skipped epochs clear expired bits. Existing room retirement clears all failed-member bits. Successful ready-index publication replaces index identity and clears bits before publishing.

An ordinal is the index sector times 128 plus the matched sorted row. The existing complete index validation establishes sorted unique members and checks the full index CRC. With the candidate enabled, each sector also has an immutable CRC receipt; reloading a sector checks that receipt before returning a member ordinal. This prevents same-first-key silent index corruption from lending a different member an old failure bit. Room retirement retains these ready-index CRC receipts because the immutable pack stays ready across rooms. A newly validated index replaces the receipts; file replacement without index reinitialization is unsupported by the existing runtime. Pack payload correction at an unchanged validated member is observed by the periodic retry.

Expected SH4 state: 2048 map bytes, eight aligned epoch bytes, 256 sector-receipt bytes = 2312 BSS bytes, no heap. Initial index validation adds a 256-byte temporary receipt array. Additional index-sector CRC CPU cost, target retry appearance/recovery, full program identity, full release and physical Dreamcast acceptance remain open. No gameplay performance improvement is claimed.

The negative menu-window restoration candidate remains excluded and disabled: the measured matched inventory cycle added 102 low-level requests and 168,032 bytes.

## Qualification

Run `python3 test_payload_retry.py --all` and `python3 test_payload_retry.py --on --all`. These extract the actual current load function and compile the actual runtime index/helper against mocks. The helper probe covers 21,898 assertions including every epoch phase, boundaries 29/30/59/60, skipped epochs, UINT wrap, success/reset, all 8192 bits and healthy first-use after 4096 failures. The source loader probes distinguish packed reads, heap refusal and loose paths. Tests do not certify actual Package media behavior, target visuals or target traffic.

Before the per-sector receipt follow-up, UBSan passed the source loader, policy and extended original index tests. The latest receipt follow-up and Make/SH4 controls are pending the shared resource hold. No latest-source passing status is inferred from the earlier result.
