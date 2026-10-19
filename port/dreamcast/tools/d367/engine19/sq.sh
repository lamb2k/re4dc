set -euo pipefail
# sq.sh <src warp> <dst warp> <bytes> <frag>: prepend the KOS squeeze line
{ echo "squeeze ${3:?} ${4:?}"; tr -d '\r' < "${1:?}"; } > "${2:?}"
