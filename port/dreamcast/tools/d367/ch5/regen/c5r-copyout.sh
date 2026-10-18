set -euo pipefail
# ch5regen: stage verified files on ext4 in disc-path layout, bulk copy to re4-assets-private, sha check there.
L=/root/probe/lanes-20261018/ch5regen
D="/mnt/c/Game Dev/Emulators/re4-assets-private/ch5regen-20261018"
O=$L/out
mkdir -p $O/files
python3 - "$L/found.tsv" "$O" <<'P'
import sys, os, shutil, hashlib
found, O = sys.argv[1], sys.argv[2]
rows = []
for line in open(found):
    p, sha, src = line.rstrip('\n').split('\t')
    dst = os.path.join(O, 'files', p)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst): shutil.copyfile(src, dst)
    assert hashlib.sha256(open(dst, 'rb').read()).hexdigest() == sha, p
    rows.append((p, sha, str(os.path.getsize(dst)), src))
rows.sort()
with open(os.path.join(O, 'MANIFEST.tsv'), 'w') as f:
    f.write('path\tsha256\tsize\tregenerated_from\n')
    for r in rows: f.write('\t'.join(r) + '\n')
print('staged', len(rows))
P
mkdir -p "$D"
tar -C $O -cf - MANIFEST.tsv files | tar -C "$D" -xf -
cd "$D"
python3 - <<'P'
import hashlib
n = bad = 0
for line in list(open('MANIFEST.tsv'))[1:]:
    p, sha, size, src = line.rstrip('\n').split('\t')
    n += 1
    if hashlib.sha256(open('files/' + p, 'rb').read()).hexdigest() != sha: bad += 1; print('BAD', p)
print('C: copy checked', n, 'bad', bad)
P
