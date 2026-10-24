#!/usr/bin/env bash
set -euo pipefail
if ! command -v rg >/dev/null 2>&1;then
 apt-get install -y --no-install-recommends ripgrep
fi
/usr/bin/rg --version | head -1
sha256sum /usr/bin/rg
