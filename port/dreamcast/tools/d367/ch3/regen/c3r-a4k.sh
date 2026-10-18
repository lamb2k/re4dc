set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
sed 's/^opts = list(A.CAPS) + \[.raw.\]/opts = list(A.CAPS) + [4000, "raw"]/' "$L/aica_search.py" > "$L/aica_search4k.py"
grep -n '^opts' "$L/aica_search4k.py"
