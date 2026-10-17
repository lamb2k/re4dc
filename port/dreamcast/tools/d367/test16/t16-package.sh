#!/bin/bash
# t16-package.sh (WSL): test 16 CANDIDATE package from out-$L (test16/t16-build.sh rP, or the test 16 recipe) + $R/fix/pkg-$L.json (t11-fix.py
# --data $DATA_SET on the test 10 package fixture). From test 16 on (test 15 shipped the old layout) the release disc is the STANDARD GD-ROM layout
# (mkgdi.sh LAYOUT=standard, mkdcdisc v0.0.4; CONTRIBUTING-PORT.md section 8): the console test of 2026-10-16 (GDEMU,
# "new gdi runs fine") ran it, and the users' GDEMU-only failures (#27, LinkOrder) were on the legacy layout, which this
# script refuses. Release rules of 2026-10-14:
#   rule 3: the disc tree and GDI tracks are mastered on WSL ext4 ($R/gdemu) and cross to C: once (one bulk copy).
#   rule 4: the knob file test16/release-knobs.txt must hold exactly this build's knobs (release-knobs.py check), and the
#           Build-Assets zip is written from the recipe's private directories (release-knobs.py zip + zipcheck --objdir).
# Disc gates here (the image is not packaged unless both pass): disc_lint.py --profile loader and --profile standard,
# 0 violations (outputs in $R/logs/disc_lint-*-$L.txt), and the boot file on the disc = this build's program image.
# The GDEMU race gate (rule 5, fullplay/gdemu_gate.sh, gdemu + weak profiles) runs on the warp twin swapped into this
# image with tools/swap-program.py (kit-check.sh step 6 makes it).
# Output: $P (default C:\Game Dev\Emulators\RE4DC-Test16-Candidate): gdemu\, the GDEMU zip, the Build-Assets zip,
# README.txt, SHA256SUMS.txt. Not published: the gates run on this package first. $R/logs/manifest-$L.json lists every
# file of the disc (fp_iso.py manifest) for identity checks against other builds.
# PKG_SRC: the package base tree (t8-pkgtree.py); default the test 14 candidate disc tree minus 1ST_READ.BIN
#   (/root/probe/lanes-20261015/t15k/pkgsrc-t14cand, in keep.txt). Without it packages are incomplete (1,736 of 2,612 files).
# The Build-Assets zip also carries the disc data sets named in the knob file's '# disc-sets:' line (as test 15).
# Env: L (play label, default t16rcrP), R (work dir), P (output, /mnt/c path), SRC_SHA (default the build's stack.txt),
#      NOZIP=1 (gdemu folder only; dry runs), MKDCDISC (mkgdi.sh), PKG_SRC.
set -e
DATA_SET=${DATA_SET:-T163_DATA}   # test 16.3: T162_DATA + zr17m + zr17b + res163 (test 16.2: T16_DATA + r108p)   # the data set name in test11/t11-fix.py (T16_DATA once the test 16 recipe defines it)
R=${R:-/root/probe/lanes-20261016/t16rc}
L=${L:-t16rcrP}
O=/root/probe/lanes/route/out-$L
T=$R/tree/port/dreamcast/tools/d367
export PKG_SRC=${PKG_SRC:-/root/probe/lanes-20261015/t15k/pkgsrc-t14cand}
KF=$T/test16/release-knobs.txt
SHA=${SRC_SHA:-$(head -1 $O/stack.txt | cut -c1-8)}
DATE=$(date +%Y%m%d)
TN=${TN:-16}   # test name in the output folder and the assets zip (test 16.1 hotfix: TN=16.1)
P=${P:-"/mnt/c/Game Dev/Emulators/RE4DC-Test$TN-Candidate"}
Z=RE4DC-Console-Test-$SHA-$DATE-GDEMU.zip
A=RE4DC-Test$TN-$SHA-Build-Assets.zip
[ "${LAYOUT:-standard}" = standard ] || { echo "t16-package: the release disc is the standard layout (LAYOUT=$LAYOUT refused)"; exit 1; }
[ $(wc -l < $O/stack.txt) -le 1 ] || { echo "out-$L was built from a dirty tree"; cat $O/stack.txt; exit 1; }
[ -d "$PKG_SRC" ] || { echo "PKG_SRC $PKG_SRC is missing"; exit 1; }
python3 $T/release-knobs.py check $O/candidate.txt $KF || { echo "test16/release-knobs.txt does not match out-$L (rewrite it: release-knobs.py write)"; exit 1; }
grep -q RELEASE_NOTES_PLACEHOLDER $T/test16/README-package.txt && { echo "test16/README-package.txt still has its release-notes placeholder"; exit 1; }
DS=$(sed -n 's/^# disc-sets: //p' $KF)
mkdir -p "$P" $R/logs $R/fix
if [ ! -s $R/fix/pkg-$L.json ]; then
  D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(getattr(m, '$DATA_SET'))")
  python3 $T/test11/t11-fix.py $L $R/fix/pkg-$L.json --data $D
fi
PKG_K=$R python3 /root/probe/lanes-20261011/test8/t8-pkgtree.py $L $R/fix/pkg-$L.json | tee $R/logs/pkgtree-$L.txt | tail -1 | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 $R/logs/pkgtree-$L.txt; exit 1; }
rm -rf $R/gdemu
(cd $T && LAYOUT=standard bash mkgdi.sh $O/re4dc-game.elf $R/pkgtree $R/gdemu | tail -1)
# disc gates: both disc_lint profiles, and the boot file is this build's program
for prof in loader standard; do
  python3 $T/disc_lint.py --profile $prof $R/gdemu/disc.gdi > $R/logs/disc_lint-$prof-$L.txt ||
    { grep -vE '^(ok|WARN) ' $R/logs/disc_lint-$prof-$L.txt; echo "t16-package: disc_lint $prof FAILED"; exit 1; }
  tail -1 $R/logs/disc_lint-$prof-$L.txt
done
python3 $T/fullplay/fp_iso.py manifest $R/gdemu/track03.bin -o $R/logs/manifest-$L.json
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary $O/re4dc-game.elf $R/img-$L.bin
want=$(sha256sum < $R/img-$L.bin | cut -c1-64); rm -f $R/img-$L.bin
have=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['1ST_READ.BIN']['sha256'])" $R/logs/manifest-$L.json)
[ "$want" = "$have" ] || { echo "t16-package: 1ST_READ.BIN on the disc ($have) is not out-$L's program ($want)"; exit 1; }
echo "boot file = out-$L program ${want:0:8}"
(cd $R/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin) > $R/gdemu-sha256.txt
rm -rf "$P/gdemu"; mkdir -p "$P/gdemu"
for f in disc.gdi track01.bin track02.raw track03.bin; do cp $R/gdemu/$f "$P/gdemu/"; done
tr -d '\r' < $T/test16/README-package.txt | sed "s/SHA_PLACEHOLDER/$SHA/g" | sed 's/$/\r/' > "$P/README.txt"
(cd "$P/gdemu" && sha256sum disc.gdi track01.bin track02.raw track03.bin | sed 's#  #  gdemu/#') > $R/SHA256SUMS-inner.txt
cmp <(cut -c1-64 $R/SHA256SUMS-inner.txt) <(cut -c1-64 $R/gdemu-sha256.txt) && echo tracks-match-ext4-build
if [ "${NOZIP:-0}" != 1 ]; then
  cd "$P"
  rm -f RE4DC-Console-Test-*-GDEMU.zip RE4DC-Test$TN-*-Build-Assets.zip
  python3 - "$P" "$Z" "$R/SHA256SUMS-inner.txt" <<'E'
import sys, zipfile, os
p, z, sums = sys.argv[1:4]
with zipfile.ZipFile(os.path.join(p, z), 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for f in ('disc.gdi', 'track01.bin', 'track02.raw', 'track03.bin'):
        zf.write(os.path.join(p, 'gdemu', f), 'gdemu/' + f)
    zf.write(os.path.join(p, 'README.txt'), 'README.txt')
    zf.write(sums, 'SHA256SUMS.txt')
print('zip ok')
E
  python3 $T/release-knobs.py zip $O/candidate.txt $R/$A ${DS:+--disc-sets "$DS"}
  python3 $T/release-knobs.py zipcheck $O/candidate.txt $R/$A --objdir $O/obj ${DS:+--disc-sets "$DS"}
  cp $R/$A "$P/$A" && rm -f $R/$A
  sha256sum $Z $A > SHA256SUMS.txt
  cat SHA256SUMS.txt
  python3 -c "import zipfile,sys;print('testzip', zipfile.ZipFile(sys.argv[1]).testzip(), zipfile.ZipFile(sys.argv[2]).testzip())" "$P/$Z" "$P/$A"
fi
cp $O/syms.txt $R/syms-$L.txt
grep -n -- '–\|—' "$P/README.txt" || echo "no long dashes"
# keep $R/pkgtree for the package audit (deleted by the release lane after the gates)
rm -rf $R/gdemu/track0*.bin $R/gdemu/track02.raw
echo "PACKAGE $P"
