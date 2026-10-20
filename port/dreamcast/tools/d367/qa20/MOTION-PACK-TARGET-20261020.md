# Motion packing: original QA target gate, 2026-10-20

The reviewed shared cache repair passed a first functional R100 ambush gate in Flycast. Physical Dreamcast acceptance, the farm barn, weapon transitions and the full route remain pending. This is the same normal source encounter as the retained baseline, with different input timing and death variants; it is not a deterministic frame-identical comparison or a console FPS measurement.

## Exact candidate

Source `4aca1f8330941af1e4b20cb33577169f82c4342f` imports the reviewed accounting and v2 packing changes onto the original QA source. The exact original QA recipe adds only `MOTION_PRESSURE_BACKING=1 MOTION_RESERVE_PACK=1`. All gameplay, model, animation, reserve-size and heap-margin settings remain unchanged. No weapon reuse, HUD prewarm or Castle renderer changes are included.

- ELF: `7dafc70fe4d7447d7d770782b95776f8e0479532fb44cbb93e23ee724b069b82`.
- Raw boot: `751a7451c72f7a6e4fac4704018e23026ff3b4ec83a4faf900f4f6e6b782b786`.
- Internal 2048-sector image: `1be6ec3a4722699a3574525ff096c60d45c2d90d92018200f6efcb2a47adc383`.
- All 1743 files manifested: only boot and 14 overlays differ from the retained fixed QA image. Full before/after source manifests prove the shared read-only source tree unchanged.
- Full off build: raw boot and 14 overlays are byte-identical to the original fixed QA. Every ELF PT_LOAD segment byte, address, size and flag matches. Whole ELF container hashes differ; runtime load identity is the claim.

## Original encounter

Fresh boot selects the original R100 QA entry. Ordinary movement triggers area A and s03; ordinary shotgun selection and two shots kill the first Ganado. Normal START skips presentation while retaining original callbacks. Original s20 and radio run, then normal house movement and A at the visible window prompt lead outside to the original pursuing ambush. No gameplay RAM, flags, HP, positions, poses or actor lists were written.

The fresh state's exact raw boot is independently verified with five unique 128-byte RAM anchors. The continuation uses only that same program/image's own state. Read-only observers are rebound by ELF object/file symbol plus offset, with object sizes checked. Reserved payload ownership uses range membership because packed entries can start inside a slab.

## Observed result

Capture `pack-r100-cont03`, 51.1 seconds including closure, errors empty and owned guest exited. Observed source frame 530 to 1969. Original radio and window callbacks precede three actual enemy HP500-to0 transitions at frames1355,1356,1496. Leon takes original damage1200 to1009; enemies and behavior are intact.

- Motion loads21 to24; evictions remain0. Four cold entries27/91 and28/24 coexist without overlap in the original two32416-byte slabs (23744 and20832 bytes used). No new cache backing is allocated.
- The retained baseline's ordinary ambush had682 evictions and periods of0.7–1.4FPS with5.848 seconds blocked on drive calls over just22 source frames. Its death variant included26; this candidate uses27/28, so these figures describe observed encounters, not identical replay frames.
- No further drive-counter, texture or motion-load change for the final16.625 seconds. Low-level drive counters measure sector/stream calls, not distinct physical seeks.
- Native HUD still dips to14.9FPS/70% source speed around first-use combat loads. Late samples are29.4FPS/~100% source speed. These are Flycast observations; hardware timing remains pending.
- Final SDK heap4:74912 bytes free, largest payload73344. Both cell lists pass bounds/alignment/prev-link/cycle and full-size accounting. This is a final checkpoint, not an unsampled minimum.
- Logged VRAM minimum104416 bytes, zero refusals, three retries and22 evictions. First-use texture pressure remains. Logged s20 movie KOS minimum3888 bytes and largest AICA allocation1004192 bytes are checkpoints, not full-run minima. Audio listening and full fights are not qualified by this cache gate.

## Limits and next gates

The baseline's five-key temporal union69792 bytes exceeds64832 bytes of reserved backing. Packing removes the proven one-clip-per-slab defect; it cannot guarantee every larger working set fits. Follow the named shared-policy checks: original R103 no-fire farm/barn workers, then alert/hit; subsequent weapon/HUD changes stay in separate candidates. Preserve SD160 and the original QA/alpha packages. No release, production merge, tag, SD write or publication is authorized by this receipt.

Private receipts: `MOTION-PACK-OFF-IDENTITY.json`, `pack-master-receipt.json`, `MOTION-PACK-R100-QUALIFICATION.json`, and `pack-r100-cont03-{newprogram-state,heap4}-audit.json`; all captures/states/scripts remain in the QA lane evidence. The first fresh helper-only startup failure is retained as fresh01; fresh02 and cont03 complete normally.
