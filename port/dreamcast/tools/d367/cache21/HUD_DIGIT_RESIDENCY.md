# Optional complete ammo-digit preload — 2026-10-20

The selected QA resident list contains decimal ammo digits0/1 but omits2–9. Source `cockpit.cpp` selects all ten patterns from core LIFE TexID0x27 as ammo changes. QA identified first-use index/payload reads for previously unseen digits; warmed shots do not repeat those reads. These finite loads are separate from enemy motion thrashing.

`prepare_hud_digit_residency.py` prepares an optional successor data candidate using the existing `resident_keys.py` packer and unchanged runtime format. It verifies the four HUD source identities against the selected audit, the ten source mappings, current texture-pack index CRC/sorted bounds and exact package extents, and native digit payload dimensions. It retains every original room/core record and adds only the eight missing decimal digit records to the common room0 list.

On the exact retained QA data:

- Source86528B, SHA256 `a9dca43b2b62e75235c6ae1cba0a1880fd18b0df6df61b3001a0441a724ce76d`.
- Candidate87040B, SHA256 `7bb46ff681029b02cee730ef5de17606ac0e8e30dd76c63a7d21e08dcadbe384`.
- Eight additional keys use8192B of native texture payload when admitted. Common key count14 remains below the runtime capacity16. The file grows512B but still occupies43 ISO sectors.
- No texture re-encoding, additional game logic, cache-cap increase, source-list/recipe change or new runtime format.

This is data preparation, not a target pass. Existing room-entry byte/entry limits still decide admission; CORE_PIN=2 retains its current room and menu/movie yield behavior. Verify actual admission, slot/VRAM budget, room/menu/movie transitions and disappearance of the named first-use reads before enabling the candidate. Do not add it to the frozen motion-packing comparison or claim universal first-use elimination.

Private mirrored data: `C:\Game Dev\Emulators\re4-assets-private\cache21-hud-digits-20261020`. The receipt records all ten package identities, actual payload bytes and exact record preservation. The selected source disc/tree remains unchanged.
