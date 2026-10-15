"""merge_cast.py <out cast dir> <cast dir>...: one registry cast dir holding every model of the given cast dirs
(model dirs copied, catalog / candidate-revisions / archive-audit merged; an archive named twice must carry the same
sha256). Lets model_registry.py build ONE room package from descriptors converted by different lanes."""
import json, os, shutil, sys
out, srcs = sys.argv[1], sys.argv[2:]
if os.path.exists(out): shutil.rmtree(out)
os.makedirs(out + '/source'); os.makedirs(out + '/ps2-overlay/integration-bundle')
cat, revs, audit = [], {}, {}
for s in srcs:
    c = json.load(open(s + '/ps2-overlay/integration-bundle/catalog.json'))
    for e in c:
        if any(x['name'] == e['name'] for x in cat): raise SystemExit('duplicate model ' + e['name'])
        cat.append(e)
        shutil.copytree(s + '/' + e['name'], out + '/' + e['name'], symlinks=True)
    revs.update(json.load(open(s + '/source/candidate-revisions.json')))
    for k, v in json.load(open(s + '/source/archive-audit.json')).items():
        if k in audit and audit[k]['sha256'] != v['sha256']: raise SystemExit('archive %s differs between cast dirs' % k)
        audit[k] = v
json.dump(cat, open(out + '/ps2-overlay/integration-bundle/catalog.json', 'w'), indent=1)
json.dump(revs, open(out + '/source/candidate-revisions.json', 'w'), indent=1)
json.dump(audit, open(out + '/source/archive-audit.json', 'w'), indent=1)
print('merged', out, [e['name'] for e in cat])
