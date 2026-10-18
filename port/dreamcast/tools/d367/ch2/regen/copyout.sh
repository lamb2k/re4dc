set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen
O="/mnt/c/Game Dev/Emulators/re4-assets-private/ch2regen-20261018"
mkdir -p "$O"
cd $L
for d in rooms worlds snd/fit113 snd/search em16 ps2cast; do [ -e "$d" ] && mkdir -p "$O/$(dirname $d)" && cp -a "$d" "$O/$(dirname $d)/"; done
find "$O" -type f \( -name '*.arc' -o -name '*.dar' -o -name '*.re4mesh' -o -name '*.r4pw' -o -name '*.ids' -o -name '*.re4nmr' -o -name '*.drs' \) -exec sha256sum {} + | sed "s#$O/##" > "$O/SHA256SUMS.txt"
wc -l "$O/SHA256SUMS.txt"; du -sh "$O"
