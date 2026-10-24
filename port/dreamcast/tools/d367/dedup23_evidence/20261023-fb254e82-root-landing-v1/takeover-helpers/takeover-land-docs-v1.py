from pathlib import Path
import hashlib,json
c=Path(r'C:\Game Dev\Emulators\codex-lanes\dedup-offline23')
p=Path('/root/work/lanes/dedup-offline23-land/port/dreamcast/docs/qualification')
p.mkdir(parents=True,exist_ok=True)
text='''# Offline scenery dedup qualification and default-off integration

This unit integrates frozen source 4be08e0110592510e3630c01fa9f49b3ac2fed3d and the narrow prefetch decoder correction 0d30bd83098af2bcd5e9ca2197ffd4cd926e73c4, on d5c1ceab9e06461462669b3ce1d28a379747a74a. Production recipe and assets are unchanged; SCENERY_DEDUP remains 0. The experimental mode is 3, using explicitly bound private ps2-dd3 alternates. No GameCube asset, texture prune, visibility approximation or triangle reordering is introduced.

Frozen 4be source-profile evidence: actual OFF main and all 14 overlays match production; ON raw main is 1077a1386ac3431b97d069291424a14117adf55f267aff78fbedf166bdc6df09. Full standard H2 completes 1465/571/340 decoded, uploaded and presented frames with restored arena return. OFF s30 heap_before is 93,920 bytes; ON is 139,552 (+45,632). Eight 48 KiB KOS challenges, all ten actual GDEMU seeds, scoped census/TEXCHK/LEON/VRAM checks, bell/Mendez common-window decisions and cross/farm/forest held stills pass. Fragmentation retries/evictions and bell presentation drops are retained explicitly. Known baseline Mendez late-pair material failure remains; no all-material completeness claim.

Separate normal QA programmes at exact 4be pass full staged-disc file/track readback and loader/standard lint. Both actual final-GDI ordinary-input boots pass. Separately labelled same-programme/all-overlay/asset fixture proxies pass menu-warp and full H2, with normal QA s30 heap_before OFF 48,768 / ON 98,496 (+49,728). Do not substitute those QA values for standard-profile floors. Original DATA29, all 41 shared Ganado textures and the same exact four compact alternate files are retained on both arms. No private Mendez repair is included. No ZIP, SD copy or publication.

Review confirmed an unqualified combination defect: the prefetch helper bypassed corners(), leaving the offline decoder absent or stale. The five-line 0d30 correction initializes/clears current meshlet context before every plain/indexed/empty return. Eight actual-method host configurations and 96 composition comparisons, explicit context sequences, omission/stale mutants and independent root rerun pass. The changed region preprocesses away under PREFETCH0. This does not qualify DEDUP3+PREFETCH1 target execution, pictures or performance. All frozen source-profile and QA evidence uses PREFETCH0 and SELECT_LEAN2=0.

Root requires an actual newly linked landing OFF main/all-overlay identity against production, and an ON3/PREFETCH0 identity against frozen4be before pushing integration. This permits the unchanged frozen-image guest evidence to apply without promoting the new PREFETCH1 combination. The landing-build-off-identity.json and landing-build-on-identity.json receipts bind actual landing source and SDK archive. Recipe remains off regardless of these source checks; physical console feedback is separate.

Private discs: RE4DC-QA23-Dedup-{Off,On}-4be08e01. Their README/STEPS/IDENTITY and root review receipts state exact limits. Exact qualification is under C:/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01. private-qa-pair-seal-r1.json SHA256 4180931954be3dc47e587bea96b82a550799c898a7491a9de4df5e01a69f95be. Old failing control and implicit-FPS/watchdog captures remain preserved. No hardware performance, complete route, fresh full release or physical acceptance is claimed.

After this current-integration unit lands, queued I-001 starts with an offline re-strip estimate at actual r101/r103/r100 benchmark cameras/LOD. Its own GO bar and exact-triangle/winding gates apply independently. Cloud queue, old scratch/backface experiments and parked castle work remain untouched.
'''
(p/'DEDUP23_20261023.md').write_text(text)
print('Added current bounded qualification and explicit new-link acceptance requirement.')
