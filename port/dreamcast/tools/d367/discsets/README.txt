Lane discsets20 (2026-10-20): the three-disc split (DISC-LAYOUT-20261016.md), DISC_SET=1.
Programs (one recipe, ch2/ch2-build.sh rP with rr/recipe.conf CH2):
  disc 1: CH2="$CH2 DISC_SET=1"                       (data = the release disc, unchanged; no dc/disc.id = disc 1)
  disc 2: CH2="$CH2 $CH4REC DISC_SET=1"               (CH4REC from ch4found/ch4-build.sh, PE2=ps2enemy-ch2-20261016,
                                                      PE3/PE4=/root/re4data/private/ps2enemy-ch34-20261018/PE3|PE4)
Disc 2 tree: mkdisc2.py <disc-1 tree (fp_iso.py extract)> <castle18 r200b.json>,<castle18 r201j.json> <disc-2 out> <dir> <set id>
  = disc 1 + castle18 r200b (castle 3-1 data, wins) + r201j add-only keys - stage-1 rooms (st1/, r1xx movies, worlds,
  events, st1 overlays) + disc-2 1ST_READ.BIN/overlays + dc/disc.id. Then fullplay/fp_master.sh as usual.
Warp rig: `chapter <n>` sets pG->chapter so disc-2/3 warps pass the disc check (6 = chapter 3-1).
