"""st3 lane allpairs.py (surviving copy), with the fixtures root as argv[1] (ch5regen)."""
import collections, glob, json, os, sys
L = sys.argv[1]
pairs = set()
for room_dir in sorted(glob.glob(L + '/fixtures/r3*')):
    reps = sorted(glob.glob(room_dir + '/ancillary-*/tex/native-ui-report.json'), key=os.path.getmtime)
    if not reps:
        continue
    d = json.load(open(reps[-1]))
    by = collections.defaultdict(dict)
    for e in d['entries']:
        by[(e['context'], e['tpl_offset'])][e['image']] = e
    for imgs in by.values():
        if 0 in imgs and 1 in imgs and (imgs[0]['width'], imgs[0]['height']) == (imgs[1]['width'], imgs[1]['height']):
            pairs.add((imgs[0]['key'], imgs[1]['key']))
print(' '.join('--pair %s:%s' % p for p in sorted(pairs)))
