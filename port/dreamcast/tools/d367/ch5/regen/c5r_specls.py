import json, sys
for f in sys.argv[1:]:
    s = json.load(open(f))
    print(f.split('/')[-1], s['cast_dir'])
    print('  desc', [(d['name'], d.get('mask_runs')) for d in s['descriptors']])
    print('  rooms', {r: v['descriptors'] for r, v in s['room_packages'].items()})
