#!/bin/bash
# One-shot install of the QA link service on the DreamPi. Run as the normal Pi user (it uses sudo for systemd):
#   scp qalink_pi.py qalink.service install.sh pi@dreampi:/tmp/qalink-install/
#   ssh pi@dreampi 'bash /tmp/qalink-install/install.sh'
# Safe to run again (it updates the files and restarts qalink.service only). Remove with: install.sh --uninstall
# It never touches DreamPi's own services, config or packages: it writes ~/qalink/ and
# /etc/systemd/system/qalink.service, nothing else.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="$(id -un)"
HOME_DIR="$(getent passwd "$USER_NAME" | cut -d: -f6)"
DEST="${HOME_DIR:?}/qalink"
UNIT=/etc/systemd/system/qalink.service

if [ "${1:-}" = "--uninstall" ]; then
  sudo systemctl disable --now qalink.service 2>/dev/null || true
  sudo rm -f "$UNIT"
  sudo systemctl daemon-reload
  echo "qalink.service removed (logs kept in $DEST)"
  exit 0
fi

[ "$USER_NAME" != root ] || { echo "run as the normal Pi user, not root" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 1; }
for f in qalink_pi.py qalink.service; do [ -f "$SRC/$f" ] || { echo "missing $SRC/$f" >&2; exit 1; }; done
if ss -lun 2>/dev/null | grep -q ':52040 ' && ! systemctl is-active --quiet qalink.service; then
  echo "UDP 52040 is already in use by something else; stop it first" >&2; exit 1
fi

mkdir -p "$DEST"
install -m 0644 "$SRC/qalink_pi.py" "$DEST/qalink_pi.py"
python3 -m py_compile "$DEST/qalink_pi.py"
sed -e "s|@USER@|$USER_NAME|g" -e "s|@HOME@|$HOME_DIR|g" "$SRC/qalink.service" > "$DEST/qalink.service"
sudo install -m 0644 "$DEST/qalink.service" "$UNIT"
sudo systemctl daemon-reload
sudo systemctl enable qalink.service >/dev/null
sudo systemctl restart qalink.service
sleep 1
systemctl is-active qalink.service
echo "installed to $DEST; log $DEST/qalink.log; commands: python3 $DEST/qalink_pi.py send PING"
