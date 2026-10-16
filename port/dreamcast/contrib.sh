#!/usr/bin/env bash
# contrib.sh [--release <tag>] [--out <dir>] [--toolchain <dir>] [extra make knobs...]
#
# One command from a fresh clone to a bootable disc (see CONTRIBUTING-PORT.md):
#   1. toolchain: reuses one already set up (RE4DC_KOS_BASE in the environment, or <toolchain>/env.sh),
#      otherwise builds it with tools/setup-toolchain.sh (about 11 minutes, once);
#   2. downloads the test release's GDEMU zip and Build-Assets zip from GitHub (no login), checks both
#      against the release's SHA256SUMS.txt;
#   3. builds the program with those assets (build-public.sh);
#   4. puts it on the release disc (tools/swap-program.py), checks the new disc (tools/d367/disc_lint.py) and prints
#      its path.
# Default release: the newest one that has a Build-Assets zip. Downloads are kept in <out>/download.
set -euo pipefail
PORT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=${RE4DC_GITHUB_REPO:-lamb2k/re4dc}
TAG=
OUT=$PORT/out-contrib
TC=${RE4DC_TOOLCHAIN:-$HOME/re4dc-toolchain}
KNOBS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --release) TAG=${2:?--release needs a tag}; shift 2 ;;
    --out) OUT=${2:?--out needs a directory}; shift 2 ;;
    --toolchain) TC=${2:?--toolchain needs a directory}; shift 2 ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *=*) KNOBS+=("$1"); shift ;;
    *) echo "contrib.sh: unknown argument $1 (try --help)" >&2; exit 2 ;;
  esac
done
die() { echo "contrib.sh: $*" >&2; exit 1; }
case "$OUT" in *' '*) die "the output directory must not contain spaces: $OUT" ;; esac

# Host packages (Ubuntu 24.04 names in brackets).
missing=
for c in curl:curl python3:python3 make:build-essential gcc:build-essential git:git sha256sum:coreutils; do
  command -v "${c%%:*}" >/dev/null || missing="$missing ${c#*:}"
done
[ -z "$missing" ] || die "missing host packages:$missing (sudo apt install$missing)"

echo "== toolchain"
if [ -n "${RE4DC_KOS_BASE:-}" ] && [ -f "$RE4DC_KOS_BASE/lib/dreamcast/libkallisti.a" ]; then
  echo "   using RE4DC_KOS_BASE=$RE4DC_KOS_BASE"
elif [ -f "$TC/env.sh" ]; then
  echo "   using $TC"
  # shellcheck disable=SC1091
  . "$TC/env.sh"
else
  echo "   none found: building it into $TC (about 11 minutes, once)"
  for c in bison flex makeinfo patch genisoimage; do
    command -v "$c" >/dev/null || die "the toolchain build needs $c: sudo apt install build-essential bison flex texinfo libgmp-dev libmpfr-dev libmpc-dev libelf-dev libjpeg-dev libpng-dev genisoimage"
  done
  bash "$PORT/tools/setup-toolchain.sh" "$TC"
  # shellcheck disable=SC1091
  . "$TC/env.sh"
fi
command -v sh-elf-objcopy >/dev/null || export PATH="${RE4DC_KOS_CC_BASE:-/opt/toolchains/dc/sh-elf}/bin:$PATH"
command -v sh-elf-objcopy >/dev/null || die "sh-elf-objcopy not found: set RE4DC_KOS_CC_BASE or source the toolchain env.sh"
# SH4ZAM is the git submodule game/third_party/sh4zam, at the commit this checkout pins (a clone without
# --recurse-submodules leaves it empty).
if [ ! -f "$PORT/game/third_party/sh4zam/include/sh4zam/shz_xmtrx.h" ]; then
  echo "== SH4ZAM submodule (git submodule update --init)"
  git -C "$PORT" submodule update --init game/third_party/sh4zam ||
    die "git submodule update --init failed (SH4ZAM, port/dreamcast/game/third_party/sh4zam)"
fi

echo "== release"
DL=$OUT/download
mkdir -p "$DL"
# The release list (public API, no login): tag, GDEMU zip, Build-Assets zip, checksums.
read -r TAG GDEMU ASSETS_ZIP < <(python3 - "$REPO" "$TAG" <<'PY'
import json, sys, urllib.request
repo, want = sys.argv[1], sys.argv[2]
req = urllib.request.Request('https://api.github.com/repos/%s/releases?per_page=50' % repo,
                             headers={'Accept': 'application/vnd.github+json', 'User-Agent': 're4dc-contrib'})
try:
    releases = json.load(urllib.request.urlopen(req, timeout=60))
except Exception as e:
    sys.exit('contrib.sh: cannot list the releases of %s: %s' % (repo, e))
for r in releases:
    names = [a['name'] for a in r.get('assets', [])]
    g = [n for n in names if n.endswith('-GDEMU.zip')]
    b = [n for n in names if n.endswith('-Build-Assets.zip')]
    if (r['tag_name'] == want or (not want and b)) and g and b and 'SHA256SUMS.txt' in names:
        print(r['tag_name'], g[0], b[0]); break
else:
    sys.exit('contrib.sh: no release %s with a GDEMU zip, a Build-Assets zip and SHA256SUMS.txt' % (want or '(any)'))
PY
)
echo "   $TAG"
BASE=https://github.com/$REPO/releases/download/$TAG
curl -fsSL -o "$DL/SHA256SUMS.txt" "$BASE/SHA256SUMS.txt" || die "download failed: $BASE/SHA256SUMS.txt"
for f in "$ASSETS_ZIP" "$GDEMU"; do
  want=$(awk -v f="$f" '$2==f || $2=="*"f {print $1}' "$DL/SHA256SUMS.txt")
  [ -n "$want" ] || die "$f is not listed in SHA256SUMS.txt"
  if [ ! -f "$DL/$f" ] || [ "$(sha256sum "$DL/$f" | cut -c1-64)" != "$want" ]; then
    echo "   downloading $f"
    curl -fL --progress-bar -o "$DL/$f.part" "$BASE/$f" || die "download failed: $BASE/$f"
    mv "$DL/$f.part" "$DL/$f"
  fi
  [ "$(sha256sum "$DL/$f" | cut -c1-64)" = "$want" ] || die "$f does not match SHA256SUMS.txt (delete $DL/$f and retry)"
  echo "   $f ok"
done

echo "== build assets"
A=$OUT/assets
rm -rf "$A"
python3 - "$DL/$ASSETS_ZIP" "$A" <<'PY'
import os, sys, zipfile
src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(src) as z:
    for i in z.infolist():
        name = i.filename.replace('\\', '/')  # the zip may use Windows separators
        if name.endswith('/') or name.startswith('/') or '..' in name.split('/'):
            continue
        dst = os.path.join(out, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with z.open(i) as r, open(dst, 'wb') as w:
            w.write(r.read())
PY
ASSETS=$(dirname "$(find "$A" -name leon4k_runtime.h | head -1)")
[ -d "$ASSETS" ] && [ "$ASSETS" != . ] || die "the Build-Assets zip has no leon4k_runtime.h"
echo "   $ASSETS"

echo "== program"
ASSETS=$ASSETS OUT=$OUT/build bash "$PORT/build-public.sh" "${KNOBS[@]}"

echo "== disc"
rm -rf "$OUT/disc"
python3 "$PORT/tools/swap-program.py" "$DL/$GDEMU" "$OUT/build" "$OUT/disc"
# the disc check every release disc passes (CONTRIBUTING-PORT.md section 8): the loader rules must hold; the standard
# GD-ROM layout rules hold on every release from test 16 on (an older release disc is in the legacy layout)
python3 "$PORT/tools/d367/disc_lint.py" --profile loader "$OUT/disc/disc.gdi" > "$OUT/disc_lint.txt" ||
  { grep -vE '^(ok|WARN) ' "$OUT/disc_lint.txt"; die "the new disc fails disc_lint (loader profile): $OUT/disc_lint.txt"; }
python3 "$PORT/tools/d367/disc_lint.py" --profile standard "$OUT/disc/disc.gdi" | tail -1 || true
echo
echo "DISC $OUT/disc/disc.gdi"
echo "Open it in Flycast, or copy the four files of $OUT/disc to a new GDEMU SD card folder."
