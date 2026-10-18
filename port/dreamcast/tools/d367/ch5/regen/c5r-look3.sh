set -euo pipefail
ls /root/probe/ 2>/dev/null | head -50
echo ---
ls /root/probe/lanes-20261014 /root/probe/lanes-20261016 /root/probe/lanes-20261018 2>&1 | head -40
echo ---cxfix
P=/root/re4data/private/cxfix-replay-20261018
ls $P; ls $P/output | head -80
ls $P/output | grep -c . || true
