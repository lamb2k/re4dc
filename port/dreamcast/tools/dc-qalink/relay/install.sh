#!/bin/bash
# Installs the dc-qalink relay as a systemd service on this Linux box (a DreamPi or any box whose pppd answers the
# Dreamcast). Idempotent. Usage: sudo ./install.sh [user]   (default: the user who ran sudo)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
user=${1:-${SUDO_USER:-$(id -un)}}
home=$(getent passwd "$user" | cut -d: -f6)
dir="${home:?}/dc-qalink"
install -d -o "$user" "$dir"
install -m 0755 -o "$user" "$here/dc_qalink_relay.py" "$dir/dc_qalink_relay.py"
unit=/etc/systemd/system/dc-qalink-relay.service
tmp=$(mktemp)
sed -e "s|@USER@|$user|" -e "s|@DIR@|$dir|g" "$here/dc-qalink-relay.service" > "$tmp"
if ! cmp -s "$tmp" "$unit" 2>/dev/null; then install -m 0644 "$tmp" "$unit"; systemctl daemon-reload; fi
rm -f "${tmp:?}"
systemctl enable --now dc-qalink-relay.service
systemctl restart dc-qalink-relay.service
# The relay listens on UDP 52040 (from the console over ppp0); the control port stays on 127.0.0.1 (use ssh).
if command -v ufw >/dev/null && ufw status | grep -q active; then ufw allow 52040/udp >/dev/null; fi
command -v pppd >/dev/null || echo "warning: pppd not found; the console needs a PPP peer (DreamPi image or pppd + a modem)"
systemctl --no-pager --lines=3 status dc-qalink-relay.service || true
