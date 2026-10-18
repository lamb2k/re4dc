# reg.sh TREE SPECJSON OUTNAME ROOM CASTDIR "MAPS" FLAGS... : model_registry replay with lane path rewrites.
# MAPS = space-separated old=new path prefix rewrites applied to the spec; the cast archive-audit is pointed at lane GC extracts.
set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen; TREE=${1:?}; SPEC=${2:?}; OUT=${3:?}; ROOM=${4:?}; CAST=${5:?}; MAPS=${6:-}; shift 6
T=$L/$TREE; W=$L/regs; mkdir -p $W
python3 - "$SPEC" "$W/$OUT.json" "$CAST" "$MAPS" <<'P'
import json, sys
src, dst, cast, maps = sys.argv[1:]
s = open(src).read()
for m in maps.split():
    a, b = m.split('='); s = s.replace(a, b)
j = json.loads(s); j['cast_dir'] = cast
json.dump(j, open(dst, 'w'), indent=1)
P
python3 - "$CAST/source/archive-audit.json" "$L" <<'P'
import json, sys, os, glob, hashlib
p, L = sys.argv[1:]
a = json.load(open(p)); ch = 0
for k, v in a.items():
    if os.path.exists(v['source']): continue
    for c in glob.glob(L + '/**/' + k + '.drs', recursive=True):
        if hashlib.sha256(open(c, 'rb').read()).hexdigest() == v['sha256']: v['source'] = c; ch += 1; break
    else: print('audit: no lane copy of', k)
json.dump(a, open(p, 'w'), indent=1)
P
o=$W/$OUT; rm -rf "${o:?}"; cd $T
python3 port/dreamcast/tools/d367/model_registry.py $W/$OUT.json $o --tree $T --package-room $ROOM "$@" > $o.log 2>&1 || { tail -3 $o.log; exit 1; }
sha256sum $o/package/r$ROOM/registry.re4nmr | cut -c1-16; stat -c %s $o/package/r$ROOM/registry.re4nmr
