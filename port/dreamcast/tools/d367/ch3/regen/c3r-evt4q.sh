set -euo pipefail
for k in 04e42880-7b859ae2 05f93f11-1b10b7d7 0abd11ae-bf814df3; do
  find /root/probe/lanes-20261018/ch4regen /root/probe/lanes-20261016/ch4found/ -name "$k*" 2>/dev/null | head -3 | while read -r f; do echo "$f $(sha256sum "$f" | cut -c1-8)"; done
done
ls /root/probe/lanes-20261016/ch4found/ 2>/dev/null | head
