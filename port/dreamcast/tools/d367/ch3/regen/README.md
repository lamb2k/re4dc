# ch3 castle data regeneration (lane ch3regen, 2026-10-18)

Replays of the castle-20261015 / ch3found-20261016 data chain lost in the 10-17 /root wipe. Targets: the chosen
payload-manifest.json shas in re4dc-recovery\harvest.db (targets table). Outputs: /root/probe/lanes-20261018/ch3regen
(private, never committed), verified copies in re4-assets-private\ch3regen-20261018.

- c3r_srcmap.py: missing target -> recorded fixture source path (stage.json of the chosen run).
- c3r_gcx.py: GC FST extractor (debug disc 1 b7fcbf12).
- c3r-tex1.sh: prepare_native_ui room textures (cx_room_fixtures prepare_room step); byte-exact at 8b6449b1, e5ec39f0, dreamcast-port.
- c3r-pkg.sh: release31.sh step 1 (convert_room_bins prelit MAINSCENARIO) at origin/lane/castle-1015: byte-exact.
- c3r-rel.sh / c3r-lm2.sh + c3r_compact.py: compact31/32.py compaction + room_smd release. le_mirror: 90606dcf for
  r202/r204/r206/r20b..r20f, Codex b47c (=+67524643, ch4regen replay lm-b47.py) for r201/r203/r205/r207/r208/r20a;
  ch3found16 tools for r221/r228, ch4found16-land4 for r216.
- c3r-aica.sh + aica_search4k.py: ch2regen aica_search with the castle 4000 Hz cap; layout from the harvested aica-c32
  r209.dar header (127936,253856,72544,264576,0,0,0,32736,1004192). AICA after release == release after AICA here.
- c3r-prepem.sh: castle prepem.sh / prepem19.sh (prepare_native_ui em textures + prepare_enemy_motions).
- c3r_cover.py: coverage against the missing list.
