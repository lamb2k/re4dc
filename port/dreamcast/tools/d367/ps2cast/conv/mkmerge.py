import json, sys, copy
S = '/root/probe/lanes-20261014/ps2cast/tree/port/dreamcast/tools/d367/model-registry/'
W = '/root/probe/lanes-20261014/ps2cast/work/conv'
ch1 = json.load(open('/mnt/c/Game Dev/Emulators/ps2cast-20261014/spec/ps2-ch1-cast.json'))
new = {d['name']: d for d in ch1['descriptors']}
dl = json.load(open('/mnt/c/Game Dev/Emulators/ps2cast-3-20261011/spec/ps2-dl-gctex.json'))
plan = {  # room: (base spec, base descriptors kept first, added)
 '100': (S + 'ps2-crow.json', ['dog-01', 'crow-folded', 'crow-spread'], ['trap-em2a-00', 'trap-em2a-02']),
 '105': (S + 'ps2-crow.json', ['crow-folded', 'crow-spread'], ['trap-em2a-00', 'trap-em2a-02']),
 '108': (S + 'ps2-r108.json', ['ganado-em17-0c', 'crow-folded', 'crow-spread'], ['snake-em24-00']),
 '10b': (dl, ['dellago-em2f-00'], ['fish-em27-00', 'boat-pl0f-00']),
 '11b': (S + 'ps2-wolf.json', ['wolf-em22-00'], ['fish-em27-00', 'boat-pl0f-00']),
}
for room, (base, keep, add) in plan.items():
    b = json.load(open(base)) if isinstance(base, str) else base
    descs = [d for d in b['descriptors'] if d['name'] in keep] + [new[n] for n in add]
    spec = dict(registry='ps2-ch1-r%s' % room, about='lane ps2cast2 (2026-10-14): r%s combined room package = the test 10 package (%s, byte-identical descriptors) + the chapter-1 PS2 cast additions %s.' % (room, b['registry'], add),
                cast_dir=W + '/regcast-merged-r' + room, revision_overlay='ps2-overlay', level='conservative', archive_audit='source/archive-audit.json',
                lighting=b.get('lighting'), cast_sources=[b['cast_dir'], W + '/regcast-ch1'], descriptors=descs,
                room_packages={room: dict(descriptors=keep + add, evidence='test 10 package + CH1 audit models-by-room.md')})
    json.dump(spec, open('/mnt/c/Game Dev/Emulators/ps2cast-20261014/spec/ps2-ch1-r%s.json' % room, 'w'), indent=1)
    print(room, spec['cast_sources'])
