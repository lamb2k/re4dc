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
- c3r-pakloose.sh + c3r_paksrc.py: ch3found castle-pak-loose (99) = vq_pak.py of the recovered 16-bit sources.
- c3r-chap3.sh, c3r-pairs.sh: castle chap3.sh (chap03 + vq_native_ui), pairs2/3/4 (pairs-c31/c32/c33).
- c3r-warps.sh: castle cx-r20d-s20 / pad-r206-s20 verbatim (ch3found k4-r203-kw needs cx_room_fixtures' cx-r203-walk.txt).
- c3r-res.sh: castle resident-d.bin = resident_keys pack of lane/castle-1015 lists (ch3found's cfcc77d6 = ch2regen data set).
- c3r-str.sh: aica_str.dat streams (ch31 castle tree, ch3 ch3found tree) from a le_mirror of GC bgm.
- c3r_vq34.py: ch3found tex-c34.pak = vqsel34 replay on the test 15 pak 15611245 (RE4DC-Water-R10A-Off disc).
- c3r-pl11.sh + c3r_pl11b.py: castle pl11-hot; staged r117 AICA container recovered from the Codex r11f container.
- c3r_stage.py + c3r-copyout.sh: ext4 stage, one bulk copy to re4-assets-private\ch3regen-20261018, sha check.
