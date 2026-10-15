#!/bin/bash
# bench-zip.sh <arm label>   (WSL; tools/d367/benchpub) packages a mastered benchmark disc (bench-package.sh) for testers.
# The zip is written on ext4 and crosses to Windows once (release build rule 3), with the extracted gdemu folder:
#   $P/RE4DC-Benchmark-NOT-THE-GAME-<sha>-GDEMU.zip  (README.txt first, gdemu/ four files, SHA256SUMS.txt)
#   $P/gdemu/, $P/README.txt, $P/SHA256SUMS.txt (zip sha256 + file sha256s)
# Env: K (work dir), P (Windows output, default C:\Game Dev\Emulators\RE4DC-Benchmark-v2),
#      GATED (required): the track03.bin sha256 of the image the gates ran (the r1 evidence disc); the zip is made only
#      when the staged image is that image (coordinator 2026-10-15, after a package was zipped from a re-mastered dev disc).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
L=${1:?arm label}
K=${K:-/root/probe/bench-public}
O=/root/probe/lanes/route/out-$L
D=$K/disc-$L
P=${P:-"/mnt/c/Game Dev/Emulators/RE4DC-Benchmark-v2"}
[ $(wc -l < $O/stack.txt) -le 1 ] || { echo "out-$L was built from a dirty tree"; cat $O/stack.txt; exit 1; }
SHA=$(head -1 $O/stack.txt | cut -c1-8)
grep -qx "BENCH_ID=$SHA" <(tr ' ' '\n' < $O/resolved-knobs.txt) || { echo "BENCH_ID is not the source sha $SHA"; exit 1; }
Z=RE4DC-Benchmark-NOT-THE-GAME-$SHA-GDEMU.zip
GATED=${GATED:?GATED=<track03 sha256 of the gated image>}
T3=$(cd $D/gdemu && sha256sum track03.bin | cut -c1-64)
[ "$T3" = "$GATED" ] || { echo "staged track03 $T3 is not the gated image $GATED" >&2; exit 1; }
echo "staged image = gated image: track03 $T3"
S=$K/zip-$L; rm -rf $S; mkdir -p $S
python3 - "$here/README-package.txt" "$D/fix" "$SHA" > $S/README.txt <<'PY'
import sys, os, re
src, fix, sha = sys.argv[1:4]
rows = []
for f in sorted(os.listdir(fix)):
    for line in open(os.path.join(fix, f)):
        m = re.match(r'bench (\d+) (\d+) (\d+) (.+)', line.strip())
        if m:
            no, b, e, name = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
            how = 'sweep, the game freezes at room frame %d' % b if b == e else 'measured room frames %d..%d (%d s of game time)' % (b, e - 1, (e - b) // 30)
            rows.append((no, '%d  %-14s %s' % (no, name, how)))
rows.sort()
t = open(src).read().replace('\r', '').replace('SHA_PLACEHOLDER', sha).replace('SCENES_PLACEHOLDER', '\n'.join(r for _, r in rows))
sys.stdout.write(t.replace('\n', '\r\n'))
PY
grep -q PLACEHOLDER $S/README.txt && { echo "README placeholder left" >&2; exit 1; }
(cd $D/gdemu && sha256sum disc.gdi track01.bin track02.raw track03.bin | sed 's#  #  gdemu/#') > $S/SHA256SUMS.txt
cmp <(cut -c1-64 $S/SHA256SUMS.txt) <(cut -c1-64 $D/gdemu-sha256.txt)
python3 - "$S/$Z" "$S/README.txt" "$D/gdemu" "$S/SHA256SUMS.txt" <<'PY'
import sys, zipfile, os
z, readme, g, sums = sys.argv[1:5]
with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    zf.write(readme, 'README.txt')                     # first entry: says it is not the game
    for f in ('disc.gdi', 'track01.bin', 'track02.raw', 'track03.bin'):
        zf.write(os.path.join(g, f), 'gdemu/' + f)
    zf.write(sums, 'SHA256SUMS.txt')
zf = zipfile.ZipFile(z)
assert zf.namelist()[0] == 'README.txt' and zf.testzip() is None
print('zip ok', zf.namelist())
PY
grep -n -- '–\|—' $S/README.txt && { echo "long dash in README"; exit 1; } || true
mkdir -p "$P"
rm -rf "$P/gdemu" "$P"/RE4DC-Benchmark-NOT-THE-GAME-*-GDEMU.zip
cp $S/$Z $S/README.txt "$P/"
mkdir -p "$P/gdemu"; cp $D/gdemu/{disc.gdi,track01.bin,track02.raw,track03.bin} "$P/gdemu/"
(cd $S && sha256sum $Z && cat SHA256SUMS.txt) > "$P/SHA256SUMS.txt"
(cd "$P" && sha256sum -c --quiet <(sed -n '2,$p' SHA256SUMS.txt) && sha256sum -c --quiet <(head -1 SHA256SUMS.txt)) && echo "copies verified"
cat "$P/SHA256SUMS.txt"
rm -rf $S
echo "PACKAGE $P/$Z"
