"""c3r_stage.py COVER.json MISSING.json OUTROOT: (WSL) copy each covered target to OUTROOT/<lane>/<disc path>, re-verify its
sha256 against the target, write OUTROOT/SHA256SUMS and OUTROOT/MANIFEST.tsv (lane, path, sha, origin, source)."""
import hashlib, json, os, shutil, sys
cov = json.load(open(sys.argv[1])); miss = json.load(open(sys.argv[2])); out = sys.argv[3]
def wsl(p):
    q = p.replace('\\', '/')
    if q.startswith('//wsl.localhost/Ubuntu-24.04'): return q[len('//wsl.localhost/Ubuntu-24.04'):]
    if q[1:3] == ':/': return '/mnt/' + q[0].lower() + q[2:]
    return q
sums = []; man = []; bad = 0
for key, (src, origin) in sorted(cov.items()):
    lane, path = key.split('|', 1)
    want = miss[lane][path]['sha256']; s = wsl(src)
    d = os.path.join(out, lane, path); os.makedirs(os.path.dirname(d), exist_ok=True)
    if not os.path.exists(d):
        shutil.copyfile(s, d)
    h = hashlib.sha256(open(d, 'rb').read()).hexdigest()
    if h != want:
        bad += 1; os.remove(d); print('BAD', key); continue
    sums.append('%s  %s/%s' % (h, lane, path)); man.append('\t'.join([lane, path, h, origin, s]))
open(os.path.join(out, 'SHA256SUMS'), 'w').write('\n'.join(sums) + '\n')
open(os.path.join(out, 'MANIFEST.tsv'), 'w').write('lane\tpath\tsha256\torigin\tsource\n' + '\n'.join(man) + '\n')
print('staged', len(sums), 'bad', bad)
