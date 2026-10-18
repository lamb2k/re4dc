#!/bin/bash
# t15-package.sh (WSL): test 15 CANDIDATE, copy of test14/t14-package.sh: package from out-$L (test15/t15-build.sh rP) +
# $R/fix/pkg-$L.json (t11-fix.py --data T15_DATA on the test 10 package fixture). Release rules of 2026-10-14:
#   rule 3: the disc tree and GDI tracks are mastered on WSL ext4 ($R/gdemu) and cross to C: once (one bulk copy).
#   rule 4: the knob file test15/release-knobs.txt must hold exactly this build's knobs (release-knobs.py check), and the
#           Build-Assets zip is written from the recipe's private directories and files plus the disc data sets named in
#           the knob file's '# disc-sets:' line (release-knobs.py zip + zipcheck --objdir).
# PKG_SRC: the package base tree (t8-pkgtree.py); default the test 14 candidate disc tree minus 1ST_READ.BIN
#   (/root/probe/lanes-20261015/t15k/pkgsrc-t14cand, in keep.txt). Without it packages are incomplete (1,736 of 2,612 files).
# The disc keeps the current (test 14) layout: the standard-layout image (mkdcdisc) is test 16.
# Output: $P (default C:\Game Dev\Emulators\RE4DC-Test15-Candidate): gdemu\, the GDEMU zip, the Build-Assets zip,
# README.txt, SHA256SUMS.txt. Not published: the gates run on this package first.
# Env: L (play label, default t15rcrP), R (work dir), P (output, /mnt/c path), SRC_SHA (default the build's stack.txt),
#      NOZIP=1 (gdemu folder only; dry runs), PKG_SRC.
set -e
R=${R:-/root/probe/lanes-20261016/t15rc}
L=${L:-t15rcrP}
O=/root/probe/lanes/route/out-$L
T=$(cd "$(dirname "$0")/.." && pwd)
# payload root (lane payroot18, 10-18): RE4DC_PAYLOAD_ROOT/tree replaces the lost pkgsrc-t14cand (fullplay/fp_iso.py extract)
export RE4DC_PAYLOAD_ROOT=${RE4DC_PAYLOAD_ROOT:-/root/re4payload/t164-20261018}
export PKG_SRC=${PKG_SRC:-$RE4DC_PAYLOAD_ROOT/tree}
KF=$T/test15/release-knobs.txt
SHA=${SRC_SHA:-$(head -1 $O/stack.txt | cut -c1-8)}
DATE=$(date +%Y%m%d)
P=${P:-"/mnt/c/Game Dev/Emulators/RE4DC-Test15-Candidate"}
Z=RE4DC-Console-Test-$SHA-$DATE-GDEMU.zip
A=RE4DC-Test15-$SHA-Build-Assets.zip
[ $(wc -l < $O/stack.txt) -le 1 ] || { echo "out-$L was built from a dirty tree"; cat $O/stack.txt; exit 1; }
[ -d "$PKG_SRC" ] || { echo "PKG_SRC $PKG_SRC is missing"; exit 1; }
python3 $T/release-knobs.py check $O/candidate.txt $KF || { echo "test15/release-knobs.txt does not match out-$L (rewrite it: release-knobs.py write)"; exit 1; }
DS=$(sed -n 's/^# disc-sets: //p' $KF)
mkdir -p "$P" $R/logs $R/fix
if [ ! -s $R/fix/pkg-$L.json ]; then
  D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T15_DATA)")
  python3 $T/test11/t11-fix.py $L $R/fix/pkg-$L.json --data $D
fi
PKG_K=$R python3 $T/test8/t8-pkgtree.py $L $R/fix/pkg-$L.json | tee $R/logs/pkgtree-$L.txt | tail -1 | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 $R/logs/pkgtree-$L.txt; exit 1; }
rm -rf $R/gdemu
(cd $T && bash mkgdi.sh $O/re4dc-game.elf $R/pkgtree $R/gdemu | tail -1)
(cd $R/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin) > $R/gdemu-sha256.txt
rm -rf "$P/gdemu"; mkdir -p "$P/gdemu"
for f in disc.gdi track01.bin track02.raw track03.bin; do cp $R/gdemu/$f "$P/gdemu/"; done
tr -d '\r' < $T/test15/README-package.txt | sed "s/SHA_PLACEHOLDER/$SHA/g" | sed 's/$/\r/' > "$P/README.txt"
(cd "$P/gdemu" && sha256sum disc.gdi track01.bin track02.raw track03.bin | sed 's#  #  gdemu/#') > $R/SHA256SUMS-inner.txt
cmp <(cut -c1-64 $R/SHA256SUMS-inner.txt) <(cut -c1-64 $R/gdemu-sha256.txt) && echo tracks-match-ext4-build
if [ "${NOZIP:-0}" != 1 ]; then
  cd "$P"
  rm -f RE4DC-Console-Test-*-GDEMU.zip RE4DC-Test15-*-Build-Assets.zip
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
