#!/bin/bash
# route-build.sh <label> [make knobs...]  (lane route, 2026-10-01; lane enc's enc-build.sh with the route paths)
# Test ELF of the current play recipe from this tree: tools/d367/build-r21.sh + the play flags
# (D367_PLAY_BUILD_CHECKLIST.md "Play build rules"), PACE_MODE=fast, DBG_WARP=1 (warp twin), PC_SAMPLER=1
# (hwproject frame marks). Extra knobs override.
# Output /root/probe/lanes/route/out-<label> (fresh objdir), packaged for the playability harness as
# programs/candidate-route<label> + programs-route.json. out-<label>/resolved-knobs.txt holds the knobs as make
# resolved them (build-r21.sh + game/knobs.mk: defaults, these flags, Makefile overrides); candidate.txt only
# repeats the command line.
set -euo pipefail
L=$1; shift
T=${TREE:-$(cd "$(dirname "$0")/../../../../.." && pwd)}   # TREE=<checkout>: build another tree (a landing control)
E=/root/probe/lanes/route
H="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
# build-r21.sh passes ASSETS unquoted to make: the space-free link to the verified bundle.
A=/root/probe/lanes/play-actor-bundle
O=$E/out-$L; rm -rf $O; mkdir -p $O
PLAY="LOGIC_TRACE=0 GAME_DECISION_TRACE=0 ACTOR_TRANSACTION_DIAG=0 GAME_PWC_DIAG=1 ARENA_FIT_KOS_BYTES=147456 QUALITY_PICKER=0"
( cd $T && ASSETS=$A OBJDIR=$O/obj OUT=$O \
    bash port/dreamcast/tools/d367/build-r21.sh $PLAY PACE_MODE=fast DBG_WARP=1 PC_SAMPLER=1 "$@" ) \
  > $O/build.log 2>&1 || { tail -30 $O/build.log; exit 1; }
# game/tools/link.sh writes the unresolved-symbol list to the tree's game/obj/missing.txt, not to OBJDIR (so the
# old $O/obj/missing.txt check never saw it): keep this build's copy (builds of one tree run one at a time).
cp $T/port/dreamcast/game/obj/missing.txt $O/missing.txt 2>/dev/null || true
[ -s $O/missing.txt ] && { echo "missing symbols:"; cat $O/missing.txt; }
# A tree with game/knobs.mk must leave resolved-knobs.txt (8f34aa63); only an older control tree may lack it.
if [ -f "$T/port/dreamcast/game/knobs.mk" ]; then
  [ -s $O/resolved-knobs.txt ] || { echo "route-build: $T has game/knobs.mk but wrote no resolved-knobs.txt" >&2; exit 1; }
else
  [ -s $O/resolved-knobs.txt ] || echo "warning: no resolved-knobs.txt (a tree before game/knobs.mk)"
fi
TOOL=/opt/toolchains/dc/sh-elf/bin
ELF=$O/re4dc-game.elf
sha256sum $ELF > $O/elf.sha256
(cd $T && git rev-parse HEAD && git status --short) > $O/stack.txt
echo "$PLAY PACE_MODE=fast DBG_WARP=1 PC_SAMPLER=1 $*" > $O/candidate.txt
# Harness program dir (as prepare-r21.py): scrambled 1ST_READ.BIN, the overlay, the log symbols.
P="$H/programs/candidate-route$L"
rm -rf "$P"; mkdir -p "$P"
$TOOL/sh-elf-objcopy -R .stack -O binary $ELF $O/prog.bin
/root/work/kos/utils/scramble/scramble $O/prog.bin "$P/1ST_READ.BIN"
cp $O/sscrn.ovl "$P/sscrn.ovl"
# ROUTE_OVL=1: the r10b room overlays; stage-scenario.py places only sscrn.ovl, so the route fixture
# carries them: "replace": {"dc/pl0f.ovl": "<P>/pl0f.ovl", "dc/em2f.ovl": "<P>/em2f.ovl"}.
for f in $O/*.ovl; do [ "${f##*/}" = sscrn.ovl ] || cp "$f" "$P/"; done
python3 - "$ELF" "$O/sscrn.ovl" "$P" "$H/programs-route.json" "candidate-route$L" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
elf, ovl, out, pj, arm = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
syms = {}
for line in subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-nm', '-S', str(elf)], text=True).splitlines():
    f = line.split()
    if len(f) == 4 and f[-1] in ('_re4dc_logbuf', '_re4dc_log_head', '_re4dc_stage', '_re4dc_pcs'):
        syms[f[-1]] = int(f[0], 16)
assert len(syms) >= 3, syms
(out / 'syms.txt').write_text(' '.join(hex(syms[n] - 0x8c000000) for n in ('_re4dc_logbuf', '_re4dc_log_head', '_re4dc_stage')) + '\n')
(elf.parent / 'syms.txt').write_text(' '.join(hex(syms[n] - 0x8c000000) for n in ('_re4dc_logbuf', '_re4dc_log_head', '_re4dc_stage', '_re4dc_pcs') if n in syms) + '\n')
report = json.loads(pj.read_text()) if pj.exists() else {}
report[arm] = dict(elf=str(elf), elf_sha256=sha(elf), overlay_sha256=sha(ovl), symbols=syms,
                   resolved_knobs=str(elf.parent / 'resolved-knobs.txt'),
                   files={p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in out.iterdir() if p.is_file()})
pj.write_text(json.dumps(report, indent=2) + '\n')
PY
rm -f $O/prog.bin
echo "built route$L $(cut -c1-16 $O/elf.sha256)"
