#!/usr/bin/env python3
"""mergecast.py <out cast dir> <cast dir>:<name[=alias],...> ...   (lane bossahead 2026-11-02)

One cast dir for a model_registry.py spec whose descriptors come from several cast dirs (a room cast from cast16 plus
a boss cast from boss18): symlinked members, merged source/archive-audit.json (an archive in two dirs must have the
same sha256), merged source/candidate-revisions.json and ps2-overlay/integration-bundle/catalog.json (named casts
only). PRIVATE output: it points at converted meshes; never commit it."""
import json, os, sys

out = sys.argv[1]
os.makedirs(os.path.join(out, 'source'), exist_ok=True)
os.makedirs(os.path.join(out, 'ps2-overlay', 'integration-bundle'), exist_ok=True)
audit, revs, cat = {}, {}, []
for arg in sys.argv[2:]:
    d, names = arg.split(':')
    a = json.load(open(os.path.join(d, 'source/archive-audit.json')))
    for k, v in a.items():
        if k in audit and audit[k]['sha256'] != v['sha256']:
            sys.exit(f'mergecast: archive {k} differs between cast dirs')
        audit[k] = v
    r = json.load(open(os.path.join(d, 'source/candidate-revisions.json')))
    c = json.load(open(os.path.join(d, 'ps2-overlay/integration-bundle/catalog.json')))
    for spec in names.split(','):
        # name or name=alias (a descriptor name is at most 15 bytes); the cast's own name stays linked for its paths
        n, alias = (spec.split('=') + [None])[:2]
        alias = alias or n
        for link in {n, alias}:
            if not os.path.islink(os.path.join(out, link)):
                os.symlink(os.path.join(d, n), os.path.join(out, link))
        if n in r:
            revs[alias] = r[n]
        e = [x for x in c if x['name'] == n]
        if len(e) != 1:
            sys.exit(f'mergecast: {n} is not once in the {d} catalog')
        cat.append(dict(e[0], name=alias))
json.dump(audit, open(os.path.join(out, 'source/archive-audit.json'), 'w'), indent=1)
json.dump(revs, open(os.path.join(out, 'source/candidate-revisions.json'), 'w'), indent=1)
json.dump(cat, open(os.path.join(out, 'ps2-overlay/integration-bundle/catalog.json'), 'w'), indent=1)
print('MERGED', out, len(cat), 'casts', sorted(audit))
