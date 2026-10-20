set -euo pipefail
# rcpub.sh: MANIFEST.tsv (room, file bytes, OCCL bytes, occluders) + SHA256SUMS, then one copy to re4-assets-private.
O=/root/re4data/private/rc19o2-20261019
P="/mnt/c/Game Dev/Emulators/re4-assets-private/rc19o2-20261019"
cd $O
python3 - <<'PY'
import ast, glob, os, re
info = {}
for lg in sorted(glob.glob('compile-*.log')):
    for ln in open(lg):
        m = re.match(r'^(r[0-9a-f]{3})\s+\d+ B .* vis=(.*)$', ln.strip())
        if m:
            v = ast.literal_eval(m.group(2))
            info[m.group(1)] = v or {}
rows = []
for r in sorted(os.listdir('.')):
    f = os.path.join(r, 'room.r4rc')
    if not os.path.isfile(f): continue
    oc = info.get(r, {})
    rows.append((r, os.path.getsize(f), oc.get('bytes', 0), oc.get('occluders', 0)))
with open('MANIFEST.tsv', 'w') as m:
    m.write('room\tfile_bytes\toccl_bytes\toccluders\n')
    for x in rows: m.write('\t'.join(str(v) for v in x) + '\n')
tot = sum(x[1] for x in rows); oct_ = sum(x[2] for x in rows if isinstance(x[2], int))
print('rooms', len(rows), 'total', tot, 'occl', oct_)

PY
sha256sum */room.r4rc > SHA256SUMS
grep -E "^(r100|r101|r103|r10b|r11b)\b" MANIFEST.tsv
mkdir -p "$P"
cp -r $O/. "$P"/
(cd "$P" && sha256sum -c --quiet SHA256SUMS && echo "copy verified")
