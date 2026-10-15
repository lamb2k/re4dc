# reg.sh <spec (WSL path)> <tag> <room>... [-- extra flags]
T=/root/probe/lanes-20261014/ps2cast/tree; G=$T/port/dreamcast/tools/d367/model_registry.py
W=/root/probe/lanes-20261014/ps2cast/work/conv
SP=$1; TAG=$2; shift 2; rooms=(); while [ $# -gt 0 ] && [ "$1" != -- ]; do rooms+=($1); shift; done; [ "${1:-}" = -- ] && shift
for r in "${rooms[@]}"; do o=$W/reg-$r-$TAG; rm -rf $o
  (cd $T && timeout 900 python3 $G "$SP" $o --tree $T --package-room $r --pack-bones 64 --wide-identity "$@" > $o.log 2>&1) || { echo "$r FAIL: $(tail -3 $o.log | tr '\n' ' ' | cut -c1-900)"; continue; }
  python3 - $o.log $r <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); p=d.get('package') or {}
print(sys.argv[2], 'bytes', p.get('bytes'), 'arena', p.get('arena'), 'contracts', [ (c.get('name'), c.get('contract')) for c in d.get('contracts',[])], 'fpart', (p.get('counts') or {}).get('fpart'), 'tex', d.get('textures'))
PY
done
