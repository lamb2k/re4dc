#!/bin/bash
# ident.sh (WSL): knob-off identity, w16mrP (lane/worldtest16 5197fa04) vs w16brP (t15/int 189ac886): every output but the ELF.
A=/root/probe/lanes/route/out-w16mrP; B=/root/probe/lanes/route/out-w16brP
cd $A; for f in *; do
  [ -f "$f" ] || continue
  a=$(sha256sum "$f" | cut -c1-16); b=$(sha256sum "$B/$f" 2>/dev/null | cut -c1-16)
  [ "$a" = "$b" ] && s=same || s=DIFF
  echo "$s $f $a $b"
done | sort
diff <(cd $A && git -C /root/probe/worldtest16-20261016/tree diff --stat 189ac886 5197fa04 -- port/dreamcast/game port/dreamcast/Makefile 2>/dev/null) /dev/null && echo "no game/Makefile source change 189ac886..5197fa04"
