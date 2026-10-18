set -euo pipefail
find /root/probe/lanes-20261017r/ch2regen \( -name 'r113.dar' -o -name 'r11d.dar' -o -name 'r11e.dar' \) 2>/dev/null | while read -r f; do
  echo "$f $(stat -c %s "$f") $(sha256sum "$f" | cut -c1-12)"
done
