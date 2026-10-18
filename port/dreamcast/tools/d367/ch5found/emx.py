"""emx.py <unarmed.json> <E>...: stage the round-3 island enemy archives (prepem/<EMXPREP or prep>-<E>/<E>.drs, GC data)
into a fixture as em/<E>.drs, plus streamed motions dc/mot/*.fcv when the prepared dir has them (their textures come from
the island pak tex-ch5c)."""
import json, os, sys
P = '/root/probe/lanes-20261016/ch5found/prepem'
pre = os.environ.get('EMXPREP', 'prep')
f = sys.argv[1]; d = json.load(open(f))
nm = 0
for e in sys.argv[2:]:
    src = '%s/%s-%s' % (P, pre, e)
    d['replace']['em/%s.drs' % e] = '%s/%s.drs' % (src, e)
    d['remove'] = [x for x in d.get('remove', []) if x != 'em/%s.drs' % e]
    if os.path.isdir(src + '/mot'):
        for m in sorted(os.listdir(src + '/mot')):
            d['replace']['dc/mot/' + m] = src + '/mot/' + m; nm += 1
d['provenance'].setdefault('ch5found16', {})['emx'] = [pre] + sys.argv[2:]
json.dump(d, open(f, 'w'), indent=1, sort_keys=True)
print('emx', pre, sys.argv[2:], 'mot', nm)
