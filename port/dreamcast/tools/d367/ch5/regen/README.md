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
- Island cast (cast16data-ch5 / ch5b / ch5c / ch5d, geodrop17-r320h), byte-exact:
  c5r-c16in.sh (lane-local ps2_cast inputs: em1d/em1e/em1f/em36/em32/em3a/em3d .drs from the review Disc 2 .gcm; em1d
  sha e8e974fb = the recorded cache), c5r-c16wt.sh (worktrees t5 = 04ef5558, t6 = df054fec, ch5t = d334422c +
  2f4a731e, c5m = 0d64dbf6 + merge 865c67d7), c5r-c16gd.sh (gd = 7f13fa14), c5r-c16conv.sh (Windows python convert
  --bone-tol 0.05), c5r-c16nat*.sh (ps2_cast_native.sh, workspace 512 KB), c5r-c16fin.sh (finish + regcast-st3 /
  regcast-boss / regcast-island), c5r_mask.py (recorded c4mask2.py logic: em1d-02 s0, em1e-06p s2/s5/s6, u3 s2) + heli
  --multi-mask --size 128x128 with the 7f13fa14 ps2_mask_runs.py, c5r_k9edit.py (k9cast + k9cat r315 room edits on a
  regcast copy), c5r-c16reg.sh + c5r-c16r31b.sh (model_registry flag sets: c5pk 64 --roles5; k9pk 96; k10reg 96;
  r31b 128; r320 96 --role-tex23).
- c5r-res.sh: dc/resident.bin (gatlas17 res17g) = resident_keys.py pack + water_resident.py pack at 0cb61387.
- st3-pak-loose last 13 (VQ bytes of the st3 lane's tex-st3vq4 chain; none are in tex-gcatlas.pak = Test 10 release
  tex.pak 7137e9e5, checked with c5r_rawpak.py, nor in any harvested pak, c5r_pakscan.py): 11 are vqroom.py VQ of the
  PS2 worlds r331 / r332 (c5r-ps2w.sh r331 r332, then c5r-vq3132.sh); 2 (38679b3b 32x256, 9c7695f7 64x128) are pairs2
  pair textures added raw by addss.py (below its VQ size rule) and VQ'd by vqroom pass 2 (c5r-vqpair.sh, pairs-e1 /
  pairs-e2 sources). The 3 unresolved logged pairs (2c69ded3, 32bf9191, e7e9019c) are not targets.
- Gates: c5r_gatefix.py + c5r-gatefix.sh (per island room, a fixture whose staged payload equals the recorded run's
  payload-manifest over the stager base, now Test 16.3 a61dfc16: regenerated files, recorded paths still holding the
  sha, harvested loose files and harvested disc members extracted by sha, committed warps; where a run's own sha is not
  recoverable the chosen target sha of that path is used and listed in the fixture provenance), c5r-hsetup.sh /
  c5r-hfix.sh (lane-private copy of the unchanged harness stager via RE4DC_HARNESS, recorded arms cx76mW / cx80mW /
  cx79mW from the ch5found16 harness clones), c5r-stage1.sh + c5r-gate1.sh + c5r-gates.sh (stage, 60 s Flycast, TEX_CHECK
  + cast_gc.py + HALT/FAULT/MISSING summary, disc deleted), c5r-recsum.sh (same summary over the recorded runs).
- c5r-copyout.sh: ext4 stage, one bulk copy to re4-assets-private\ch5regen-20261018, sha check there.
