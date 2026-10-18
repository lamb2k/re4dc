#!/bin/bash
# ch5regen: model_registry room packages for the island cast, recorded flag sets:
#  A c5pk.sh (ROLES5=1): t5 tool + specs, --tree ch5t, --pack-bones 64 --roles5           -> cast16data-ch5
#  B k9pk.sh + k9cast.py + k9cat.py: c5m tool, 0e87c009 em1ep spec, --tree ch5t, 96 --roles5 -> ch5b r315
#  C k10reg.sh: t6 tool + ps2-ch5-em36.json, --tree c5m, 96 --roles5                     -> ch5c
#  D k10reg2.sh: t6 tool + ps2-ch5-boss.json, --tree c5m, 96 --roles5                    -> ch5d
#  E geodrop17: gd tool + ps2-ch5-r320.json, --tree gd, 96 --roles5 --role-tex23        -> geodrop17-r320h
# Specs are copied with the recorded absolute paths mapped to this lane's dirs.
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
C=/root/probe/lanes-20261018/ch5regen/c16
O=$C/reg; SP=$C/specs
mkdir -p "$O" "$SP"
remap() { # remap <src spec> <dst>
  sed -e "s#/root/probe/lanes-20261016/cast16/#$C/#g" -e "s#/root/probe/lanes-20261016/geodrop17-data/#$C/conv6/#g" "$1" > "$2"
}
pk() { # pk <set> <tooltree> <spec> <room> <gametree> <flags...>
  local set=$1 tt=$2 spec=$3 r=$4 gt=$5; shift 5
  local o=$O/$set/reg-$r; rm -rf "${o:?}"; mkdir -p "$O/$set"
  (cd "$tt" && python3 port/dreamcast/tools/d367/model_registry.py "$spec" "$o" --tree "$gt" --package-room "$r" --pool --wide-identity "$@" > "$o.log" 2>&1) \
    && echo "$set $r $(sha256sum "$o/package/r$r/registry.re4nmr" | cut -c1-8) tex=$(ls "$o/tex" | wc -l)" \
    || echo "$set $r FAIL $(tail -1 "$o.log" | cut -c1-200)"
}
M5=$C/t5/port/dreamcast/tools/d367/model-registry
for a in em1dp em1dp2 em1ep em1fp; do remap "$M5/ps2-ch5-$a.json" "$SP/A-ps2-ch5-$a.json"; done
for a in ${SETA-em1dp em1dp2 em1ep em1fp}; do
  for r in $(python3 -c "import json,sys;print(' '.join(json.load(open(sys.argv[1]))['room_packages']))" "$SP/A-ps2-ch5-$a.json"); do
    pk A "$C/t5" "$SP/A-ps2-ch5-$a.json" "$r" "$C/ch5t" --pack-bones 64 --roles5
  done
done
# B: r315 on a copy of regcast-st3 with the k9cast / k9cat room edits
B=$C/conv5b; rm -rf "${B:?}"; mkdir -p "$B"; cp -a "$C/conv5/regcast-st3" "$B/regcast-st3"
for m in soldr-em1e-06p:2 soldr-em1e-06p:5 soldr-em1e-06p:6 soldr-em1d-02:0; do n=${m%%:*}; i=${m##*:}; ln -sfn "$C/conv5/mask-$n-s$i" "$B/mask-$n-s$i"; done
python3 "$S/c5r_k9edit.py" "$B/regcast-st3"
git -C "$C/t5" show 0e87c009:port/dreamcast/tools/d367/model-registry/ps2-ch5-em1ep.json > "$SP/B-raw.json"
sed -e "s#/root/probe/lanes-20261016/cast16/conv5/#$B/#g" "$SP/B-raw.json" > "$SP/B-ps2-ch5-em1ep.json"
pk B "$C/c5m" "$SP/B-ps2-ch5-em1ep.json" 315 "$C/ch5t" --pack-bones 96 --roles5
M6=$C/t6/port/dreamcast/tools/d367/model-registry
remap "$M6/ps2-ch5-em36.json" "$SP/C-ps2-ch5-em36.json"; remap "$M6/ps2-ch5-boss.json" "$SP/D-ps2-ch5-boss.json"
for r in 306 307 308 30d 326 309 310; do pk C "$C/t6" "$SP/C-ps2-ch5-em36.json" "$r" "$C/c5m" --pack-bones 96 --roles5; done
for r in 31b 31c; do pk D "$C/t6" "$SP/D-ps2-ch5-boss.json" "$r" "$C/c5m" --pack-bones 96 --roles5; done
remap "$C/gd/port/dreamcast/tools/d367/model-registry/ps2-ch5-r320.json" "$SP/E-ps2-ch5-r320.json"
pk E "$C/gd" "$SP/E-ps2-ch5-r320.json" 320 "$C/gd" --pack-bones 96 --roles5 --role-tex23
grep -h "/root/probe/lanes-20261016" "$SP"/*.json | grep -v B-raw | head -3 || true
echo REGDONE
