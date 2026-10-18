set -euo pipefail
O="/mnt/c/Game Dev/Emulators/re4-assets-private/ch2regen-20261018/datasets"; mkdir -p "$O"
cd /root/re4data/private
tar -cf - ch2data-20261016 cast16data-20261016 | (cd "$O" && tar -xf -)
(cd /root/re4data/private && find ch2data-20261016 cast16data-20261016 -type f -exec sha256sum {} + | sort -k2) > /tmp/ch2regen-a.txt
(cd "$O" && find ch2data-20261016 cast16data-20261016 -type f -exec sha256sum {} + | sort -k2) > /tmp/ch2regen-b.txt
cmp /tmp/ch2regen-a.txt /tmp/ch2regen-b.txt && echo "copy verified $(wc -l < /tmp/ch2regen-a.txt) files"
cp /tmp/ch2regen-b.txt "$O/SHA256SUMS.txt"; rm -f /tmp/ch2regen-a.txt /tmp/ch2regen-b.txt
