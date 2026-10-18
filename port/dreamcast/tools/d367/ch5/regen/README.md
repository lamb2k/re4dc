# ch5 island data regeneration (lane ch5regen, 2026-10-18)

Replays of the st3 (10-14) / ch5found16 (10-16) island data chain lost in the 10-17 /root wipe. Targets: the chosen
payload-manifest.json shas of lane ch5found-20261016 in re4dc-recovery\harvest.db (4,960 missing). Outputs:
/root/probe/lanes-20261018/ch5regen (private, never committed); verified copies in
re4-assets-private\ch5regen-20261018 (files/<disc path>, MANIFEST.tsv).

- c5r_srcmap.py: missing target -> recorded fixture source path (stage.json `fixture.replace` of the chosen run).
- c5r_cxrun.py + c5r-tex.sh: st3 lane cx_room_fixtures texture step (le_mirror + prepare_native_ui) on the 2004.11.25
  review Disc 2 .gcm, with ch4regen's rebuilt Codex tree cxtree-b47 (90606dcf + le_mirror 67524643). Byte-exact for
  both recorded variants (ancillary-b47c37112cf4 and ancillary-bc4523fb545b tex/).
- c5r-setup*.sh: tool tree = gitdig18 90606dcf bundle + cxtree-b47 le_mirror + the st3 lane diff
  (origin/lane/ch5found16 tools/d367/st3firstpass/codex-tools-8bf46efe-st3.diff, minus the worlds.json rooms list and
  cx_room_fixtures hunks) + gc_source_disc2 pin; lane-local venv numpy 2.5.3 / Pillow 12.3.0 (pinned in worlds.json).
- c5r_run_rooms_st3.py + c5r-ps2w.sh: the st3 lane's run_rooms_st3.py (surviving copy in
  .claude\jobs\1e668c67\tmp\st3) with only ROOT/GC2 paths changed: PS2 worlds (.assets/rooms-rXXX), byte-exact.
- c5r_verify.py / c5r_cover.py: sha match against the missing list; coverage by recorded source.
- c5r-copyout.sh: ext4 stage, one bulk copy to re4-assets-private\ch5regen-20261018, sha check there.
