# ch4regen cast replay (cast16data-ch4 49 + ch4found/cast reg-20d / reg-216 / reg-22c 8)

Replays the lost cast16 (10-16/17) and ch4found16 (10-17) cast chain. Result: 56 of 57 byte-exact.
Order: drs.py (GC em/*.drs -> /root/probe/lanes/ps2cast/inputs, 17/17 recorded shas) -> c16setup/c16real
(tool worktrees at the recorded commits under the /root/probe/lanes-20261016/cast16 shim: tree=710cfa49,
c4m=lane/ch4found16, t8d4=8d401351, t9b4=9b4cb31f) -> c16conv.sh (Windows python, drv.py = c4drv.py logic) ->
native.sh -> finish -> mask.py -> regcast (c4m) -> reg.sh (flag set b = zq6/k7reg) -> r22c.sh, em3c.sh+r216.sh,
c5.sh+gen209.sh, c3g.sh (conv3 em1b, gigante r224) -> c16pub.sh (stage + C: copy).
Not reproducible: dc/tex/3/3407b158-738db8c7.re4tex (748dcbb7): a stale file left in cast16data-ch4 by an
uncommitted, reverted preset (zealot-em14-79u, 02:28Z); no final registry references it.
Substitutions (all verified by sha): em11-07p / merchant18 / bat members from the 01:54Z conv4 reconversions instead of
the older lane dirs; bat mask from re4-assets-private/ps2lib/cast/common/mask-bat-em29-00; /root/re4data/em/em12.drs
restored from the GC ISO (sha 6468f2d0, the audit's recorded sha).
