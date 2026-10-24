# STAT routine-byte audit qualification

Source unit: 2a14662d4b025031cd93f64eed6a5d8159d473b7, based on integration 933936ea7f45ba81c09277a780ed00111407aa23. Default-off STAT_ROUTINE_BYTES is enabled only in this qualified release recipe. STAT_DIAG remains zero in production. The independent EM35/Ganado knobs remain unchanged.

The unit repairs 62 production source lines and seven routine macros, with the VMU canonical-word consumer included. OFF raw programme and all 14 overlays match baseline exactly. Raw programme SHA256: OFF dba997478ac575140777e60507d854e2138bdfcabe7d546af75758ca0f64a6ab; ON 0745d16c39fcc08dee3afb7d0d1ce473379387190a93b395aa8c4358dad741a2. Assets retain the same 1,712-file release manifest a424cdc4f68460b0d5ea8f591c44c62eefeab85b67941410bc996680dce41547.

Source/host: independent representation audit and exhaustive local byte/macro controls pass; no fresh PS2 executable oracle was acquired. Target: actual SDK builds/link/overlay identity checked; SDK archive unchanged. Flycast console mode: matched H2 s30 340/340, restored1, heap_before93,920 each; 48KiB KOS headroom6,112/6,176; GDEMU seed1; census/TEXCHK/character checks27/27. Bell2,857 matched required-field ticks, zero actor movement drift.

Mendez: both source damage/death forms, full s02/s10/s11, False Eye acknowledgement, normal window event and actual room10f exit in about45seconds. The raw2,643-tick comparison remains MUST-DIFFER for19 line-query-note fields only. A one-line legacy camera-predicate control restores MUST-IDENTICAL against OFF. All other required fields match; zero player/enemy movement drift. This is an attributed correctness change, not a strict trace-identity claim. See the independent camera review.

The actual boat routine is authenticated in both arms. OFF incorrectly shows handgun ammo; ON shows the harpoon with no gun ammo. Stills are intentionally different and asynchronously posed, so full-frame identity is not claimed. VMU target consumer is source/compiled verified; LCD console behavior remains prospective.

Private QA: RE4DC-QA23-StatBytes-2a14662d, raw bfb586d0fc8034ef6c4a1b385e93a837eec6d0addecce157e49f9eef91fcf4bc; QA_MENU1 STAT_DIAG1 PC_SAMPLER0. Its own boot/menu-warp/H2/GDEMU1 pass; QA heap_before48,768 differs from production. Full-release and physical Dreamcast acceptance are not claimed. Later omitted rooms/enemies are source-reviewed only.

Private logs, screenshots, manifests and exact programmes: C:/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d. Public support-tools branch: wip/stat-bytes23-evidence-tools-20261023. Never merge or ship the separate camera-control branch.
