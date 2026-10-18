# r11cm.sh (lane ch2regen): cast16 r11cm.sh + ps2cast m13.sh replayed on lane paths. Arg: r11c = also add r11c to merchant rooms.
set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen; R=$L/luis; W=$R/conv; mkdir -p $W
[ -d $L/t-8d401351 ] || git -C $L/tree worktree add -q --detach $L/t-8d401351 8d401351
T=$L/t-8d401351; M=$T/port/dreamcast/tools/d367/model-registry
rm -rf "${W:?}/regcast-merchant13" "${W:?}/regcast-r11cm"; cp -a $R/regcast-merchant $W/regcast-merchant13
python3 - "$W" "${1:-}" <<'P'
import json, glob, sys
W, extra = sys.argv[1], sys.argv[2]
def fix(o):
    n = 0
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'rooms' and isinstance(v, list) and 'r104' not in v: v.insert(0, 'r104'); n += 1
            else: n += fix(v)
    elif isinstance(o, list):
        for v in o: n += fix(v)
    return n
def fix2(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'rooms' and isinstance(v, list) and 'r11c' not in v: v.append('r11c')
            else: fix2(v)
    elif isinstance(o, list):
        for v in o: fix2(v)
for p in glob.glob(W + '/regcast-merchant13/**/*.json', recursive=True) + glob.glob(W + '/regcast-merchant13/*/source.json'):
    s = json.load(open(p)); n = fix(s)
    if extra == 'r11c': fix2(s); n = 1
    if n: json.dump(s, open(p, 'w'), indent=1)
P
python3 "/mnt/c/Game Dev/Emulators/ps2cast-20261014/sh/conv/merge_cast.py" $W/regcast-r11cm $R/candidate-v2/cast $W/regcast-merchant13 | tail -1
E12=$(find $L/ps2cast/gcx -name em12.drs | head -1); python3 -c "import json,sys;p=sys.argv[1];a=json.load(open(p));a[\"em12\"][\"source\"]=sys.argv[2];json.dump(a,open(p,\"w\"),indent=1)" $W/regcast-r11cm/source/archive-audit.json "$E12"
python3 - "$M" "$R" "$W" <<'P'
import json, sys
M, R, W = sys.argv[1:]
s = json.load(open(R + '/candidate-v2/spec.json'))
m = json.load(open(M + '/ps2-ch1-r104.json'))
s['registry'] = 'ps2-ch2-r11cm'; s['cast_dir'] = W + '/regcast-r11cm'
s['about'] = s['about'] + ' + lane cast16 (2026-10-16): merchant13-c0 / -o0 (em13 type 6, the robed merchant: r11c census 10-16 drew him GC every frame), descriptors as ps2-ch1-r104 / ps2-r10f.'
ds = [d for d in m['descriptors'] if d['name'].startswith('merchant13')]
for d in ds:
    for k, v in d.get('mask_runs', {}).items(): d['mask_runs'][k] = R + '/models/' + v.rstrip('/').split('/')[-1]
s['descriptors'] += ds
s['room_packages']['11c']['descriptors'] += ['merchant13-c0', 'merchant13-o0']
json.dump(s, open(W + '/ps2-ch2-r11cm.json', 'w', newline='\n'), indent=1); print('spec ok', [d.get('mask_runs') for d in ds])
P
cd $T; o=$W/reg-11cm; rm -rf "${o:?}"
python3 port/dreamcast/tools/d367/model_registry.py $W/ps2-ch2-r11cm.json $o --tree $T --package-room 11c --ch22-luis-coverage --pack-bones 96 --wide-identity --pool > $o.log 2>&1 || { tail -3 $o.log; exit 1; }
python3 -c "import json;d=json.load(open('$o/registry-manifest.json'));print(d['room_package']['bytes'])"
sha256sum $o/package/r11c/registry.re4nmr; ls $o/tex
